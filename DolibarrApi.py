from requests import Session
from BaseApi import BaseApi

class InvalidApiKeyException(Exception):
    pass

class DolibarrApi(BaseApi):
    def __init__(self, dolibarr_url, api_key):
        self._session = Session()
        self._session.headers.update({"DOLAPIKEY": api_key})

        r = self._session.get("{}/api/index.php/status".format(dolibarr_url))

        if r.status_code != 200:
            raise InvalidApiKeyException()