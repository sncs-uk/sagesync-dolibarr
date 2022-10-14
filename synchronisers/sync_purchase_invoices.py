import logging
from helpers import sage_url, doli_url
from datetime import datetime

def sync_purchase_invoices(s_api, d_api, lastrun):
    sage_payload = {
        "updated_or_created_since": lastrun,
        "attributes": "all",
        "page": 1,
        "$itemsPerPage": 500
    }

    logging.info("Importing Purchase Invoices")
    while True:
        r = s_api.get(sage_url("purchase_invoices"), params=sage_payload)
        purchase_invoices_response = r.json()
        logging.info("Found {} purchase invoices to load (page {})".format(len(purchase_invoices_response["$items"]), sage_payload["page"]))


        for purchase_invoice in purchase_invoices_response["$items"]:
            logging.debug("Invoice: {}".format(purchase_invoice['displayed_as']))
            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(purchase_invoice["id"])
            }
            r = d_api.get(doli_url('supplierinvoices'), params=payload)
            existing_supplier_invoices = r.json()
            found = len(existing_supplier_invoices) == 1

            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(purchase_invoice["contact"]["id"])
            }

            r = d_api.get(doli_url('thirdparties'), params=payload)
            if len(r.json()) != 1:
                logging.warning("Third party missing - {}".format(purchase_invoice["contact"]["displayed_as"]))
                continue
            thirdparty = r.json()[0]

            payload = {
                "ref_supplier": purchase_invoice['vendor_reference'] or purchase_invoice['date'],
                "ref_ext": purchase_invoice["id"],
                "label": purchase_invoice['displayed_as'],
                "socid": thirdparty["id"],
                "socnom": thirdparty["name"],
                "status": 0,
                "buy_status": 0,
                "date": int(round(datetime.strptime(purchase_invoice['date'], "%Y-%m-%d").timestamp()))
            }
            if found:
                continue
                logging.debug("Found existing dolibarr invoice ({}) - updating".format(existing_supplier_invoices[0]['id']))
                payload["fk_statut"] = 0
                payload["statut"] = 0
                req = d_api.put(doli_url('supplierinvoices/{}'.format(existing_supplier_invoices[0]['id'])), json=payload)
                supplier_invoice_id = req.json()["id"]
                req = d_api.get(doli_url('supplierinvoices/{}/lines'.format(supplier_invoice_id)))
                lines = req.json()
                for line in lines:
                    logging.debug("Deleting {}".format(line['id']))
                    d_api.delete(doli_url('supplierinvoices/{}/lines/{}'.format(supplier_invoice_id, line['id'])))
            else:
                logging.debug("Creating new invoice")
                req = d_api.post(doli_url('supplierinvoices'), json=payload)
                if req.status_code == 500:
                    # logging.warning("Invalid response: {} {}".format(req.json(), payload))
                    payload['ref_supplier'] = "{}_{}".format(payload['ref_supplier'], purchase_invoice['date'])
                    req = d_api.post(doli_url('supplierinvoices'), json=payload)
                    if req.status_code == 500:
                        logging.warning("Double failure for {}".format(payload))
                        continue
                supplier_invoice_id = req.json()
                

            for line in purchase_invoice["invoice_lines"]:
                if line["product"] is None and line["service"] is None:
                    logging.debug("No product/service")
                    # Not an existing product/service
                    if line["tax_amount"] != '0.0':
                        vat_rate = line["tax_breakdown"][0]["percentage"]
                    else:
                        vat_rate = 0
                    payload = {
                        "description": line["description"],
                        "subprice": line["unit_price"],
                        "pu_ht": line["unit_price"],
                        "qty": line["quantity"],
                        "tva_tx": vat_rate,
                        "product_type": "0"
                    }
                else:
                    if line["product"]:
                        product_id = line["product"]["id"]
                    else:
                        product_id = line["service"]["id"]
                    if line["tax_amount"] != '0.0':
                        vat_rate = line["tax_breakdown"][0]["percentage"]
                    else:
                        vat_rate = 0
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
                        "fk_product": product["id"]
                    }
                logging.debug("Creating new invoice line: {}".format(payload))
                req = d_api.post(doli_url('supplierinvoices/{}/lines'.format(supplier_invoice_id)), json=payload)

            d_api.post(doli_url('supplierinvoices/{}/validate'.format(supplier_invoice_id)))

            if purchase_invoice["status"]["id"] == "PAID":
                logging.debug("Marking as paid")
                payload = {
                    "statut": "2",
                    "paye": "1",
                    "paid": "1",
                    "fk_statut": "2"
                }
                r = d_api.put(doli_url('supplierinvoices/{}'.format(supplier_invoice_id)), json=payload)
        if purchase_invoices_response["$next"] is None:
            break
        else:
            sage_payload["page"] += 1

    logging.info("Finished importing products")
