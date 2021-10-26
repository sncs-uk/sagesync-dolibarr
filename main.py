from SageApi import SageApi
from DolibarrApi import DolibarrApi
from dotenv import load_dotenv
from os import getenv
import logging

load_dotenv()

s_api = SageApi(getenv('client_id'), getenv('client_secret'), getenv('redirect_uri'))
d_api = DolibarrApi(getenv('dolibarr_url'), getenv('dolibarr_api_key'))

lastrun="2000-01-01T00:00:00"
# lastrun="2021-10-25T15:00:00"

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests_oauthlib").setLevel(logging.ERROR)

from sync import sync_products, sync_services, sync_contacts, sync_purchase_invoices, sync_sales_invoices

sync_products(s_api, d_api, lastrun)
sync_services(s_api, d_api, lastrun)
sync_contacts(s_api, d_api, lastrun)
sync_purchase_invoices(s_api, d_api, lastrun)
sync_sales_invoices(s_api, d_api, lastrun)