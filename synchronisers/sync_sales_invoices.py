import logging
from helpers import sage_url, doli_url
from datetime import datetime

def sync_sales_invoices(s_api, d_api, lastrun):
    sage_payload = {
        "updated_or_created_since": lastrun,
        "attributes": "all",
        "page": 1,
        "$itemsPerPage": 500
    }

    logging.info("Importing Customer Invoices")
    while True:
        r = s_api.get(sage_url("sales_invoices"), params=sage_payload)
        sales_invoices_response = r.json()
        logging.info("Found {} purchase invoices to load (page {})".format(len(sales_invoices_response["$items"]), sage_payload["page"]))

        for sales_invoice in sales_invoices_response["$items"]:
            logging.debug("Invoice: {}".format(sales_invoice['displayed_as']))
            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(sales_invoice["id"])
            }
            r = d_api.get(doli_url('invoices'), params=payload)
            existing_sales_invoices = r.json()
            found = len(existing_sales_invoices) == 1

            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(sales_invoice["contact"]["id"])
            }

            r = d_api.get(doli_url('thirdparties'), params=payload)
            if len(r.json()) != 1:
                logging.warning("Third party missing - {}".format(sales_invoice["contact"]["displayed_as"]))
                continue
            thirdparty = r.json()[0]

            payload = {
                "ref_client": sales_invoice['contact_reference'] or sales_invoice['date'],
                "ref_ext": sales_invoice["id"],
                "label": sales_invoice['displayed_as'],
                "socid": thirdparty["id"],
                "socnom": thirdparty["name"],
                "status": 0,
                "buy_status": 0,
                "date": int(round(datetime.strptime(sales_invoice['date'], "%Y-%m-%d").timestamp()))
            }
            if found:
                logging.debug("Found existing dolibarr invoice ({}) - updating".format(existing_sales_invoices[0]['id']))
                payload["fk_statut"] = 0
                payload["statut"] = 0
                req = d_api.put(doli_url('invoices/{}'.format(existing_sales_invoices[0]['id'])), data=payload)
                sales_invoice_id = req.json()["id"]
                req = d_api.get(doli_url('invoices/{}/lines'.format(sales_invoice_id)))
                lines = req.json()
                for line in lines:
                    logging.debug("Deleting {}".format(line['id']))
                    d_api.delete(doli_url('invoices/{}/lines/{}'.format(sales_invoice_id, line['id'])))
            else:
                logging.debug("Creating new invoice")
                req = d_api.post(doli_url('invoices'), data=payload)
                if req.status_code == 500:
                    # logging.warning("Invalid response: {} {}".format(req.json(), payload))
                    payload['ref_client'] = "{}_{}".format(payload['ref_client'], sales_invoice['date'])
                    req = d_api.post(doli_url('invoices'), data=payload)
                    if req.status_code == 500:
                        logging.warning("Double failure for {}".format(payload))
                        continue
                sales_invoice_id = req.json()
                

            for line in sales_invoice["invoice_lines"]:
                if line["tax_amount"] != '0.0':
                    vat_rate = line["tax_breakdown"][0]["percentage"]
                else:
                    vat_rate = 0
                if line["product"] is None and line["service"] is None:
                    # Not an existing product/service
                    logging.debug("No product/service")
                    payload = {
                        "description": line["description"],
                        "subprice": line["unit_price"],
                        "pu_ht": line["unit_price"],
                        "qty": line["quantity"],
                        "tva_tx": vat_rate,
                        "product_type": "0",
                        "ref_ext": line["id"]
                    }
                else:
                    if line["product"]:
                        product_id = line["product"]["id"]
                    else:
                        product_id = line["service"]["id"]
                    payload = {
                        "sqlfilters": "(t.ref_ext:=:'{}')".format(product_id)
                    }
                    r = d_api.get(doli_url('products'), params=payload)
                    products = r.json()
                    if len(products) != 1:
                        logging.warning("Could not find product with ref_ext: {}; length: {}".format(product_id, len(product)))
                        continue
                    product = products[0]
                    payload = {
                        "description": line["description"],
                        "subprice": line["unit_price"],
                        "pu_ht": line["unit_price"],
                        "qty": line["quantity"],
                        "tva_tx": vat_rate,
                        "product_type": product["type"],
                        "fk_product": product["id"],
                        "ref_ext": line["id"]
                    }
                logging.debug("Creating new invoice line: {}".format(payload))
                req = d_api.post(doli_url('invoices/{}/lines'.format(sales_invoice_id)), data=payload)

            d_api.post(doli_url('invoices/{}/validate'.format(sales_invoice_id)))

            
            if sales_invoice["status"]["id"] == "PAID":
                logging.debug("Marking as paid")
                d_api.post(doli_url('invoices/{}/settopaid'.format(sales_invoice_id)))
        if sales_invoices_response["$next"] is None:
            break
        else:
            sage_payload["page"] += 1

    logging.info("Finished importing customer invoices")