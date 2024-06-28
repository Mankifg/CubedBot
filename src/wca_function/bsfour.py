import requests
import bs4
import json
from bs4 import BeautifulSoup
from .basic import *
from datetime import datetime as dt
from datetime import timedelta


URL = "https://www.worldcubeassociation.org/competitions?region=all&year=all+years&state=custom&from_date={}&to_date={}&display=list"
COMP_ULR = "https://www.worldcubeassociation.org/competitions/{}/registrations"


def list_of_events_from(start_date=None, end_date=None):

    print(start_date, end_date)

    cids = []

    resp = requests.get(url=URL.format(start_date, end_date)).text
    soup = BeautifulSoup(resp, "html.parser")
    competitions_list = soup.find("div", id="competitions-list")
    if competitions_list:
        links = competitions_list.find_all("a")
        for link in links:
            href = link.get("href")
            if href and "/competitions/" in href:
                comp_id = href.split("/")[-1]
                cids.append(comp_id)

    return cids


def competitors_in_comp(cid, nationality):
    comp_url = COMP_ULR.format(cid)
    response = requests.get(comp_url)

    soup = BeautifulSoup(response.text, "html.parser")
    matching = 0

    country_cells = soup.find_all("td", class_="country")

    for cell in country_cells:
        # print(cell.get_text().lower())
        if cell.get_text().lower() == nationality:
            print("match")
            matching += 1

    return matching
