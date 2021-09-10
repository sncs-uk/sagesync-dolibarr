import logging
from helpers import sage_url, doli_url

def sync_purchase_invoices(s_api, d_api, lastrun):
    sage_payload = {
        "updated_or_created_since": lastrun,
        "attributes": "all",
        "page": 1
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
                return
                continue
            thirdparty = r.json()[0]

            payload = {
                "ref_supplier": purchase_invoice['vendor_reference'],
                "label": purchase_invoice['displayed_as'],
                "socid": thirdparty["id"],
                "socnom": thirdparty["name"],
                "status": 0,
                "buy_status": 0
            }
            existing_supplier_invoices = [{"id": 19}]
            found = True
            if found:
                logging.debug("Found existing dolibarr invoice ({}) - updating".format(existing_supplier_invoices[0]['id']))
                req = d_api.put(doli_url('supplierinvoices/{}'.format(existing_supplier_invoices[0]['id'])), data=payload)
                supplier_invoice_id = req.json()["id"]
                logging.debug("Clearing old lines")
                req = d_api.get(doli_url('supplierinvoices/{}/lines'.format(supplier_invoice_id)))
                lines = req.json()
                for line in lines:
                    logging.debug("Deleting {}".format(line['id']))
                    d_api.delete(doli_url('supplierinvoices/{}/lines/{}'.format(supplier_invoice_id, line['id'])))
            else:
                logging.debug("Creating new invoice")
                req = d_api.post(doli_url('supplierinvoices'), data=payload)
                supplier_invoice_id = req.json()
                

            for line in purchase_invoice["invoice_lines"]:
                print(line)
                if line["product"] is None and line["service"] is None:
                    logging.debug("No product/service")
                    # Not an existing product/service
                    payload = {
                        "description": line["description"],
                        "subprice": line["unit_price"],
                        "pu_ht": line["unit_price"],
                        "qty": line["quantity"],
                        "tva_tx": line["tax_breakdown"][0]["percentage"],
                        "ref_ext": line["id"]
                    }
                else:
                    continue
                print(payload)
                logging.debug("Creating new invoice line")
                req = d_api.post(doli_url('supplierinvoices/{}/lines'.format(supplier_invoice_id)), data=payload)
                print(req.status_code)
                print(req.json())
                return

                d_api.post(doli_url('supplierinvoices/{}/validate'.format(supplier_invoice_id)))
                d_api.put(doli_url('supplierinvoices/{}'.format(supplier_invoice_id)), data=payload)
            return
        if purchase_invoices_response["$next"] is None:
            break
        else:
            sage_payload["page"] += 1

    logging.info("Finished importing products")