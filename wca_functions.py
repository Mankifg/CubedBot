import requests

import json

USER_ENDPOINT = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{}.json"

def wca_id_exists(wca_id):
    resp = requests.get(url=USER_ENDPOINT.format(wca_id))
    return resp.status_code == 200

def get_wca_data(wca_id):
    resp = requests.get(url=USER_ENDPOINT.format(wca_id)).json()
    return resp