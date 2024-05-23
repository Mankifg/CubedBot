import requests
from bs4 import BeautifulSoup

import json



MAIN = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/"

COUNTRIES_API = MAIN + "countries.json"
COMPETITIONS_DATE = MAIN + "competitions/"
USER_ENDPOINT = MAIN + "persons/{}.json"
SINGLE_COMP_BY_ID = MAIN + "competitions/{}.json"

WCA_USER_URL = "https://www.worldcubeassociation.org/persons/{}"

LAT_RANGE = [43.8,50.2]
LON_RANGE = [8.8,20.7]


c_data = requests.get(COUNTRIES_API).json()
COUNTRIES_DICT = {}
for elem in c_data["items"]:
    COUNTRIES_DICT.update({elem["iso2Code"]:elem["name"]})
    
