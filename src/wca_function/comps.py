from .storage import *
import calendar
from datetime import date

def find_by_date(dan,mesec,leto):
    if mesec and mesec > 0:
        if dan and dan > 0:
            start = date(leto, mesec, dan)
            end = start
        else:
            last_day = calendar.monthrange(leto, mesec)[1]
            start = date(leto, mesec, 1)
            end = date(leto, mesec, last_day)
    else:
        start = date(leto, 1, 1)
        end = date(leto, 12, 31)

    params = {
        "include_cancelled": "false",
        "sort": "start_date,end_date,name",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "page": 1,
    }

    data = []
    while True:
        resp = requests.get(url=COMPETITION_INDEX_API, params=params)
        if resp.status_code != 200:
            break
        page_data = resp.json()
        if not isinstance(page_data, list) or not page_data:
            break
        data.extend(page_data)
        params["page"] += 1

    return data

def distance_suitable(lat,lon):
    if lat > LAT_RANGE[0] and lat < LAT_RANGE[1] and \
        lon > LON_RANGE[0] and lon < LON_RANGE[1]:
            return True
    else:
        return False


def filter_by_distance(comps):
    
    filtered_comp = []
    for competitionn in comps:
        lat = competitionn.get("latitude_degrees")
        lon = competitionn.get("longitude_degrees")
        if lat is None or lon is None:
            coords = competitionn.get("venue")
            if isinstance(coords, dict):
                latlot = coords.get("coordinates")
                if isinstance(latlot, dict):
                    lat = latlot.get("latitude")
                    lon = latlot.get("longitude")
        if lat is None or lon is None:
            continue
        
        if distance_suitable(lat,lon):
            filtered_comp.append(competitionn)
            
    return filtered_comp
