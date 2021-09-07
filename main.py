from SageApi import SageApi
from DolibarrApi import DolibarrApi
from dotenv import load_dotenv
from os import getenv

load_dotenv()

s_api = SageApi(getenv('client_id'), getenv('client_secret'), getenv('redirect_uri'))
d_api = DolibarrApi(getenv('dolibarr_url'), getenv('dolibarr_api_key'))

r = s_api.get("https://api.accounting.sage.com/v3.1/countries")
print(r.json())

r = d_api.get("http://erp.ad.securenetcoms.com/api/index.php/projects")
print(r.json())