import requests
import json
#from .basic import *


FIND_URL = "https://www.worldcubeassociation.org/api/v0/competition_index?include_cancelled=false&sort=start_date%2Cend_date%2Cname&start={}&end={}&page={}"

def list_of_events_from(start_date=None, end_date=None):
    # YYYY-MM-DD x2 
    print(start_date, end_date)

    cids = []
    
    page = 1
    while 1:
        resp = requests.get(FIND_URL.format(start_date,end_date,page)).json()
        if resp == []:
            break
        
        cids = cids + [item['id'] for item in resp]
        
        page += 1

    return cids
