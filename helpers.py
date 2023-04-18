from os import getenv

def sage_url(endpoint):
    return "{}/{}".format(getenv('SAGE_API_ENDPOINT'), endpoint)

def doli_url(endpoint):
    return "{}/{}".format(getenv('DOLIBARR_API_ENDPOINT'), endpoint)

def format_vat_number(number):
    if number is None:
        return None
    if len(number) == 11:
        return "{} {}".format(number[:2], number[2:])
    return number