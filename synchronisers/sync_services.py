import logging
from helpers import sage_url, doli_url

def sync_services(s_api, d_api, lastrun):
    logging.info("Importing Services")

    finished = False
    sage_payload = {
        "updated_or_created_since": lastrun,
        "attributes": "item_code,displayed_as,description,item_code,sales_rates,cost_price",
        "page": 1,
        "$itemsPerPage": 500
    }
    while not finished:
        r = s_api.get(sage_url("services"), params=sage_payload)
        services_response = r.json()
        logging.info("Found {} services to load (page {})".format(len(services_response["$items"]), sage_payload["page"]))

        for service in services_response["$items"]:
            logging.debug("Service: {}".format(service['item_code']))
            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(service["id"])
            }
            r = d_api.get(doli_url('products'), params=payload)
            existing_services = r.json()
            found = len(existing_services) == 1

            payload = {
                "label": service['displayed_as'],
                "description": service['description'],
                "type": 1,
                "ref": service["item_code"],
                "ref_ext": service["id"],
                "status": 0,
                "buy_status": 0
            }

            for_sale = service["sales_rates"][0]["rate"] != "0.0"
            for_purchase = service["cost_price"] != "0.0"

            if for_sale:
                payload["status"] = 1
                payload["price"] = service["sales_rates"][0]["rate"]
                payload["tva_tx"] = "20.000"
            if for_purchase:
                payload["cost_price"] = service['cost_price']
                payload["status_buy"] = 1

            if found:
                logging.debug("Found existing dolibarr service ({}) - updating".format(existing_services[0]['id']))
                req = d_api.put(doli_url('products/{}'.format(existing_services[0]['id'])), data=payload)
            else:
                logging.debug("Creating new service")
                req = d_api.post(doli_url('products'), data=payload)

        if services_response["$next"] is None:
            finished = True
        else:
            sage_payload["page"] += 1

    logging.info("Finished importing services")
