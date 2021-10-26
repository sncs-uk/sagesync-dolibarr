import logging
from helpers import sage_url, doli_url, format_vat_number

def sync_contacts(s_api, d_api, lastrun):
    logging.info("Importing Contacts")

    finished = False
    sage_payload = {
        "updated_or_created_since": lastrun,
        "attributes": "all",
        "nested_attributes": "all",
        "page": 1,
        "$itemsPerPage": 500
    }
    while True:
        contacts_page = sage_payload["page"]
        r = s_api.get(sage_url("contacts"), params=sage_payload)
        contacts_response = r.json()
        logging.info("Found {} contacts to load (page {})".format(len(contacts_response["$items"]), contacts_page))
        
        for contact in contacts_response["$items"]:
            if contact["system"]:
                continue
            logging.debug("Contact: {}".format(contact["reference"]))
            
            payload = {
                "sqlfilters": "(t.ref_ext:=:'{}')".format(contact["id"])
            }
            r = d_api.get(doli_url('thirdparties'), params=payload)
            existing_thirdparties = r.json()
            found = len(existing_thirdparties) == 1

            client = contact["contact_types"][0]["id"] == "CUSTOMER"
            vendor = contact["contact_types"][0]["id"] == "VENDOR"
            payload = {
                "name": contact['name'],
                "address": "{}\n{}".format((contact["main_address"]["address_line_1"] or ""),(contact["main_address"]["address_line_2"] or "")),
                "town": (contact["main_address"]["city"] or ""),
                "zip": (contact["main_address"]["postal_code"] or ""),
                "status": 1,
                "prospect": 0,
                "country_id": 7,
                "country_code": "GB",
                "ref_ext": contact["id"],
                "tva_intra": format_vat_number(contact["tax_number"])
            }
            if client:
                payload["code_client"] = contact["reference"]
                payload["client"] = 1
            if vendor:
                payload["fournisseur"] = 1
                payload["code_fournisseur"] = contact["reference"]
                
            if not client and not vendor:
                continue

            
            if found:
                logging.debug("Found existing dolibarr thirdparty ({}) - updating".format(existing_thirdparties[0]['id']))
                req = d_api.put(doli_url('thirdparties/{}'.format(existing_thirdparties[0]['id'])), data=payload)
                thirdparty_id = existing_thirdparties[0]['id']
            else:
                logging.debug("Creating new thirdparty")
                req = d_api.post(doli_url('thirdparties'), data=payload)
                thirdparty_id = req.json()

            logging.debug("Syncing contact people")
            sage_payload = {
                "attributes": "all",
                "nested_attributes": "all",
                "page": 1,
                "contact_id": contact["id"]
            }
            r = s_api.get(sage_url("contact_persons"), params=sage_payload)
            people_response = r.json()
            while True:
                for person in people_response["$items"]:
                    payload = {
                        "sqlfilters": "(t.ref_ext:=:'{}')".format(person["id"])
                    }
                    r = d_api.get(doli_url('contacts'), params=payload)
                    existing_contacts = r.json()
                    found = len(existing_contacts) == 1

                    r = s_api.get(sage_url("addresses/{}".format(person["address"]["id"])))
                    address = r.json()
                    nameparts = person["name"].split()
                    if person["name"] == "Main Contact":
                        last_name = contact["name"]
                        first_name = ""
                    elif len(nameparts) == 2:
                        last_name = nameparts[1]
                        first_name = nameparts[0]
                    else:
                        last_name = person["name"]
                        first_name = ""

                    payload = {
                        "name": person["name"],
                        "lastname": last_name,
                        "firstname": first_name,
                        "address": "{}\n{}".format((address["address_line_1"] or ""),(address["address_line_2"] or "")),
                        "town": (address["city"] or ""),
                        "zip": (address["postal_code"] or ""),
                        "poste": person["job_title"] or "",
                        "phone_pro": person["telephone"] or "",
                        "phone_mobile": person["mobile"] or "",
                        "email": person["email"] or "",
                        "country_id": 7,
                        "country_code": "GB",
                        "socid": thirdparty_id,
                        "socname": contact['name'],
                        "ref_ext": person['id']
                    }

                    if found:
                        logging.debug("Found existing dolibarr contact ({}) - updating".format(existing_contacts[0]['id']))
                        req = d_api.put(doli_url('contacts/{}'.format(existing_contacts[0]['id'])), data=payload)
                    else:
                        logging.debug("Creating new contact")
                        req = d_api.post(doli_url('contacts'), data=payload)

                if people_response["$next"] is None:
                    break
            logging.debug("Finished syncing contact people")
        if contacts_response["$next"] is None:
            break
        else:
            sage_payload["page"] = contacts_page + 1

    logging.info("Finished importing contacts")