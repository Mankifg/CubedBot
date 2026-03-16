import requests
from bs4 import BeautifulSoup

import json



WCA_BASE = "https://www.worldcubeassociation.org"
COUNTRIES_API = WCA_BASE + "/api/v0/countries"
USER_ENDPOINT = WCA_BASE + "/api/v0/persons/{}"
SINGLE_COMP_BY_ID = WCA_BASE + "/api/v0/competitions/{}"
COMPETITION_INDEX_API = WCA_BASE + "/api/v0/competition_index"

WCA_USER_URL = "https://www.worldcubeassociation.org/persons/{}"

LAT_RANGE = [43.8,50.2]
LON_RANGE = [8.8,20.7]


c_data = requests.get(COUNTRIES_API).json()
COUNTRIES_DICT = {}
for elem in c_data:
    if not isinstance(elem, dict):
        continue
    iso2 = elem.get("iso2")
    name = elem.get("name")
    if isinstance(iso2, str) and isinstance(name, str):
        COUNTRIES_DICT.update({iso2: name})
    
