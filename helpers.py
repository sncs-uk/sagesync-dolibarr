from os import getenv

def sage_url(endpoint):
    return "{}/{}".format(getenv('sage_api_endpoint'), endpoint)

def doli_url(endpoint):
    return "{}/{}".format(getenv('dolibarr_api_endpoint'), endpoint)