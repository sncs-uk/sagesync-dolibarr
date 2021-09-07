from SageApi import SageApi
from DolibarrApi import DolibarrApi
from dotenv import load_dotenv
from os import getenv
import logging

from helpers import sage_url, doli_url

load_dotenv()

s_api = SageApi(getenv('client_id'), getenv('client_secret'), getenv('redirect_uri'))
d_api = DolibarrApi(getenv('dolibarr_url'), getenv('dolibarr_api_key'))

lastrun="2000-01-01T00:00:00"

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests_oauthlib").setLevel(logging.ERROR)

# import products
sage_payload = {
    "updated_or_created_since": lastrun,
    "attributes": "item_code,displayed_as,description,item_code,sales_prices,cost_price",
    "page": 1
}

finished = False

logging.info("Importing Products")
while not finished:
    r = s_api.get(sage_url("products"), params=sage_payload)
    products_response = r.json()
    logging.info("Found {} products to load (page {})".format(len(products_response["$items"]), sage_payload["page"]))

    for product in products_response["$items"]:
        logging.debug("Product: {}".format(product['item_code']))
        payload = {
            "sqlfilters": "(t.ref_ext:=:'{}')".format(product["id"])
        }
        r = d_api.get(doli_url('products'), params=payload)
        existing_products = r.json()
        found = len(existing_products) == 1

        payload = {
            "label": product['displayed_as'],
            "description": product['description'],
            "type": 0,
            "ref": product["item_code"],
            "ref_ext": product["id"],
            "status": 0,
            "buy_status": 0
        }

        for_sale = product["sales_prices"][0]["price"] != "0.0"
        for_purchase = product["cost_price"] != "0.0"

        if for_sale:
            payload["status"] = 1
            payload["price"] = product["sales_prices"][0]["price"]
            payload["tva_tx"] = "20.000"
        if for_purchase:
            payload["cost_price"] = product['cost_price']
            payload["status_buy"] = 1

        if found:
            logging.debug("Found existing dolibarr product ({}) - updating".format(existing_products[0]['id']))
            req = d_api.put(doli_url('products/{}'.format(existing_products[0]['id'])), data=payload)
        else:
            logging.debug("Creating new product")
            req = d_api.post(doli_url('products'), data=payload)

    if products_response["$next"] is None:
        finished = True
    else:
        sage_payload["page"] += 1

logging.info("Finished importing products")


logging.info("Importing Services")

finished = False
sage_payload = {
    "updated_or_created_since": lastrun,
    "attributes": "item_code,displayed_as,description,item_code,sales_rates,cost_price",
    "page": 1
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

# r = d_api.get("http://erp.ad.securenetcoms.com/api/index.php/projects")
# print(r.json())