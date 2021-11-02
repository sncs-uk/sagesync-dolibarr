import logging
from helpers import sage_url, doli_url
from datetime import datetime

def sync_sales_quotes(s_api, d_api, lastrun):
    sage_payload = {
        "updated_or_created_since": lastrun,
        "attributes": "all",
        "page": 1,
        "$itemsPerPage": 500
    }

    logging.info("Importing Sales Quotes")
    while True:
        r = s_api.get(sage_url("sales_quotes"), params=sage_payload)
        sales_quotes_response = r.json()
        logging.info("Found {} sales quotes to load (page {})".format(len(sales_quotes_response["$items"]), sage_payload["page"]))

        for sales_quote in sales_quotes_response["$items"]:
            logging.info("Quote: {}".format(sales_quote['displayed_as']))
            logging.debug("{}".format(sales_quote['status']))
            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(sales_quote["id"])
            }
            r = d_api.get(doli_url('proposals'), params=payload)
            existing_sales_quotes = r.json()
            found = len(existing_sales_quotes) == 1

            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(sales_quote["contact"]["id"])
            }

            r = d_api.get(doli_url('thirdparties'), params=payload)
            if len(r.json()) != 1:
                logging.warning("Third party missing - {}".format(sales_quote["contact"]["displayed_as"]))
                continue
            thirdparty = r.json()[0]

            payload = {
                "ref_client": sales_quote['reference'] or sales_quote['date'],
                "ref_ext": sales_quote["id"],
                "socid": thirdparty["id"],
                "socnom": thirdparty["name"],
                "status": 0,
                "date": int(round(datetime.strptime(sales_quote['date'], "%Y-%m-%d").timestamp())),
                "cond_reglement_id": "2",
                "cond_reglement_doc": "Due in 30 days",
                "cond_reglement_code": "30D"
            }
            if found:
                logging.debug("Found existing dolibarr proposal ({}) - updating".format(existing_sales_quotes[0]['id']))
                payload["fk_statut"] = 0
                payload["statut"] = 0
                req = d_api.put(doli_url('proposals/{}'.format(existing_sales_quotes[0]['id'])), data=payload)
                sales_quote_id = req.json()["id"]
                req = d_api.get(doli_url('proposals/{}/lines'.format(sales_quote_id)))
                lines_local = req.json()
                for line in lines_local:
                    logging.debug("Deleting {}".format(line['id']))
                    d_api.delete(doli_url('proposals/{}/lines/{}'.format(sales_quote_id, line['id'])))
            else:
                logging.debug("Creating new proposal")
                req = d_api.post(doli_url('proposals'), data=payload)
                if req.status_code == 500:
                    # logging.warning("Invalid response: {} {}".format(req.json(), payload))
                    payload['ref_client'] = "{}_{}".format(payload['ref_client'], sales_quote['date'])
                    req = d_api.post(doli_url('invoices'), data=payload)
                    if req.status_code == 500:
                        logging.warning("Double failure for {}".format(payload))
                        continue
                sales_quote_id = req.json()
                

            for line in sales_quote["quote_lines"]:
                if line["tax_amount"] != '0.0':
                    vat_rate = line["tax_breakdown"][0]["percentage"]
                else:
                    vat_rate = 0
                
                if line["product"] is None and line["service"] is None:
                    # Not an existing product/service
                    logging.debug("No product/service")
                    payload = {
                        "desc": line["description"],
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
                        "desc": line["description"],
                        "subprice": line["unit_price"],
                        "pu_ht": line["unit_price"],
                        "qty": line["quantity"],
                        "tva_tx": vat_rate,
                        "product_type": product["type"],
                        "fk_product": product["id"],
                        "ref_ext": line["id"]
                    }
                
                r = d_api.get(doli_url('proposals/{}/lines'.format(sales_quote_id)), params={ "sqlfilters": "(t.ref_ext:=:'{}')".format(line["id"]) })
                existinglines = r.json()
                # if len(existinglines) == 1:
                #     logging.debug("Updaing proposal line: {}".format(payload))
                #     d_api.put(doli_url('proposals/{}/lines/{}'.format(sales_quote_id, existinglines[0]["id"])), data=payload)
                # else:
                logging.debug("Creating new proposal line: {}".format(payload))
                req = d_api.post(doli_url('proposals/{}/lines'.format(sales_quote_id)), data=payload)

            d_api.post(doli_url('proposals/{}/validate'.format(sales_quote_id)))

            if sales_quote["status"]["id"] == "CONVERTED":
                logging.info("Setting SQ as accepted")
                payload = {
                    "status": "2"
                }
                r = d_api.post(doli_url('proposals/{}/close'.format(sales_quote_id)), data=payload)

                if sales_quote["invoice"]:
                    r = d_api.post(doli_url('proposals/{}/setinvoiced'.format(sales_quote_id)))
            if sales_quote["status"]["id"] == "DECLINED":
                logging.info("Setting SQ as declined")
                payload = {
                    "status": "3"
                }
                r = d_api.post(doli_url('proposals/{}/close'.format(sales_quote_id)), data=payload)
        if sales_quotes_response["$next"] is None:
            break
        else:
            sage_payload["page"] += 1

    logging.info("Finished importing sales quotes")