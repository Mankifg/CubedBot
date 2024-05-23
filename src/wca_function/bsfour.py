import requests
import bs4
import json
from bs4 import BeautifulSoup
from .basic import *
from datetime import datetime as dt
from datetime import timedelta

NUMBER_OF_DAYS_TO_SEARCH = 7

URL = "https://www.worldcubeassociation.org/competitions?region=all&year=all+years&state=custom&from_date={}&to_date={}&display=list"
COMP_ULR = "https://www.worldcubeassociation.org/competitions/{}/registrations"

def list_of_events_from(start_date=None,end_date=None):
    if start_date is None and end_date is None:
        start_date = dt.now().strftime("%Y-%m-%d")
        end = dt.now() + timedelta(days=NUMBER_OF_DAYS_TO_SEARCH)
        end_date = end.strftime("%Y-%m-%d")
    
    print(start_date,end_date)
    
    cids = []
    
    resp = requests.get(url=URL.format(start_date,end_date)).text
    soup = BeautifulSoup(resp, 'html.parser')
    competitions_list = soup.find('div', id='competitions-list')
    if competitions_list:
        links = competitions_list.find_all('a')
        for link in links:
            href = link.get('href')
            if href and "/competitions/" in href:
                comp_id = href.split("/")[-1]
                cids.append(comp_id)
            
    return cids

def competitors_in_comp(cid):
    print(cid)
    response = requests.get(COMP_ULR.format(cid))
    soup = BeautifulSoup(response.text, 'html.parser')
    competitor_ids = []
    for row in soup.find_all('tr', {'data-index': True}):
        country_cell = row.find('td', class_='country')
        if country_cell and country_cell.text.strip() == "Slovenija":
            id_link = row.find('a', href=True)
            competitor_ids.append(id_link)

    # Print the extracted competitor IDs
    
        
    return competitor_ids
    
'''
def competitors_in_comp(cid):
    print(cid)
    user_ids = []
    
    html = requests.get(url=COMP_ULR.format(cid)).text
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find('tbody').find_all('tr')
    print(rows)
    for row in rows:
        print("*"*10,row)
        competitor_id = row.find('a').get('href').split('/')[-1]
        user_ids.append(competitor_id)
    
    return user_ids
'''