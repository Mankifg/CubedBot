import requests
from bs4 import BeautifulSoup

import json


COUNTRIES_API = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/countries.json"


USER_ENDPOINT = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{}.json"
WCA_USER_URL = "https://www.worldcubeassociation.org/persons/{}"
SINGLE_COMP_BY_ID = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/competitions/{}.json"

c_data = requests.get(COUNTRIES_API).json()
COUNTRIES_DICT = {}
for elem in c_data["items"]:
    COUNTRIES_DICT.update({elem["iso2Code"]:elem["name"]})
    

def wca_id_exists(wca_id):
    resp = requests.get(url=USER_ENDPOINT.format(wca_id))
    return resp.status_code == 200

def get_wca_data(wca_id):
    resp = requests.get(url=USER_ENDPOINT.format(wca_id)).json()
    return resp

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
    resp = requests.get(SINGLE_COMP_BY_ID.format(id))
    
    if resp.status_code != 200:
        return False,{}

    return True,resp.json()
    
