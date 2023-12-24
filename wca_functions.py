import requests

import json

USER_ENDPOINT = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{}.json"

def wca_id_exists(wca_id):
    resp = requests.get(url=USER_ENDPOINT.format(wca_id))
    return resp.status_code == 200

def get_wca_data(wca_id):
    resp = requests.get(url=USER_ENDPOINT.format(wca_id)).json()
    return resp

import requests
from bs4 import BeautifulSoup

def scrape_website(url):
    # Send a GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get the HTML code
        html_code = str(soup)

        return html_code
    else:
        # Print an error message if the request was not successful
        print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
        return None

# URL of the website to scrape
url = "https://www.worldcubeassociation.org/persons/2012ZAKE02"

# Call the function to scrape the website and get the HTML code
html_code = scrape_website(url)

# Print the HTML code if it was successfully retrieved
if html_code:
    print(html_code)