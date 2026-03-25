import requests
from bs4 import BeautifulSoup

import json

import math
from math import sin,cos
from datetime import datetime

WCA_BASE = "https://www.worldcubeassociation.org"
COUNTRIES_API = WCA_BASE + "/api/v0/countries"
USER_ENDPOINT = WCA_BASE + "/api/v0/persons/{}"
SINGLE_COMP_BY_ID = WCA_BASE + "/api/v0/competitions/{}"

WCA_USER_URL = "https://www.worldcubeassociation.org/persons/{}"

c_data = requests.get(COUNTRIES_API).json()

LAT_RANGE = [43.8,50.2]
LON_RANGE = [8.8,20.7]


COUNTRIES_DICT = {}
for elem in c_data:
    if not isinstance(elem, dict):
        continue
    iso2 = elem.get("iso2")
    name = elem.get("name")
    if isinstance(iso2, str) and isinstance(name, str):
        COUNTRIES_DICT.update({iso2:name})
    

def wca_id_exists(wca_id):
    try:
        resp = requests.get(url=USER_ENDPOINT.format(wca_id), timeout=8)
    except requests.RequestException:
        return False
    return resp.status_code == 200

def get_wca_data(wca_id):
    try:
        resp = requests.get(url=USER_ENDPOINT.format(wca_id), timeout=10)
    except requests.RequestException:
        return {}
    if resp.status_code != 200:
        return {}
    try:
        payload = resp.json()
    except ValueError:
        return {}
    
    person = payload.get("person", {}) if isinstance(payload, dict) else {}
    country_iso2 = person.get("country_iso2")
    if not country_iso2 and isinstance(person.get("country"), dict):
        country_iso2 = person["country"].get("iso2")

    raw_prs = payload.get("personal_records", {}) if isinstance(payload, dict) else {}
    singles = []
    averages = []
    if isinstance(raw_prs, dict):
        for event_id, values in raw_prs.items():
            if not isinstance(values, dict):
                continue
            single = values.get("single")
            average = values.get("average")
            if isinstance(single, dict):
                singles.append({
                    "eventId": event_id,
                    "best": single.get("best", 0),
                    "rank": {
                        "world": single.get("world_rank", -1),
                        "continent": single.get("continent_rank", -1),
                        "country": single.get("country_rank", -1),
                    },
                })
            if isinstance(average, dict):
                averages.append({
                    "eventId": event_id,
                    "best": average.get("best", 0),
                    "rank": {
                        "world": average.get("world_rank", -1),
                        "continent": average.get("continent_rank", -1),
                        "country": average.get("country_rank", -1),
                    },
                })

    return {
        "id": person.get("id", wca_id),
        "name": person.get("name", wca_id),
        "country": country_iso2 or "",
        "numberOfCompetitions": payload.get("competition_count", 0) if isinstance(payload, dict) else 0,
        "rank": {
            "singles": singles,
            "averages": averages,
        },
    }

def get_html_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        html_code = str(soup)

        return html_code
    else:
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return None

def get_picture_url(wca_id):
    html_code = get_html_data(WCA_USER_URL.format(wca_id))

    if not html_code:
        return ""
        
    soup = BeautifulSoup(html_code, 'html.parser')

    img_tag = soup.find('img', class_='avatar')
    image_url = img_tag['src']

    return image_url

def get_comp_data(id):
    try:
        resp = requests.get(SINGLE_COMP_BY_ID.format(id), timeout=10)
    except requests.RequestException:
        return False, {}
    if resp.status_code != 200:
        return False,{}
    try:
        payload = resp.json()
    except ValueError:
        return False, {}
    start_date = payload.get("start_date")
    end_date = payload.get("end_date")

    number_of_days = 1
    if isinstance(start_date, str) and isinstance(end_date, str):
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            number_of_days = (end - start).days + 1
        except ValueError:
            number_of_days = 1

    website = payload.get("website", "")
    if isinstance(website, str) and "worldcubeassociation.org" in website.lower():
        website = ""

    out = {
        "id": payload.get("id", id),
        "name": payload.get("name", id),
        "country": payload.get("country_iso2", ""),
        "city": payload.get("city", ""),
        "date": {
            "from": start_date,
            "till": end_date,
            "numberOfDays": number_of_days,
        },
        "events": payload.get("event_ids", []),
        "organisers": payload.get("organizers", []),
        "wcaDelegates": payload.get("delegates", []),
        "venue": {
            "name": payload.get("venue", ""),
            "address": payload.get("venue_address", ""),
            "details": payload.get("venue_details", ""),
        },
        "externalWebsite": website,
    }

    return True,out
    
