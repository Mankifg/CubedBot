from .storage import *

def find_by_date(dan,mesec,leto):
    
    base_url = f"{COMPETITIONS_DATE}{leto}"

    if mesec and mesec > 0: # 
        base_url = base_url + f"/{mesec:02}"
        
    if dan and dan > 0:
        base_url = base_url + f"/{dan:02}"

    base_url = base_url + ".json"
    resp = requests.get(url=base_url)
    
    if resp.status_code == 200:
        data = resp.json()["items"]
        data = data
    else:
        data = []
        
    print(base_url)

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
        
        coords = competitionn.get("venue")
        latlot = coords.get("coordinates")
        lat,lon = latlot["latitude"],latlot["longitude"]
        
        if distance_suitable(lat,lon):
            filtered_comp.append(competitionn)
            
    return filtered_comp
