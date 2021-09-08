from os import getenv

def sage_url(endpoint):
    return "{}/{}".format(getenv('sage_api_endpoint'), endpoint)

def doli_url(endpoint):
    return "{}/{}".format(getenv('dolibarr_api_endpoint'), endpoint)

def format_vat_number(number):
    if number is None:
        return None
    if len(number) == 11:
        return "{} {}".format(number[:2], number[2:])
    return number