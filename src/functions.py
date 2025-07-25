import time
from datetime import datetime as dt
import json

import src.hardstorage as hs 
import src.functions as functions
import src.db as db


class SkillIssue(Exception):
    print(Exception)


def avg_of(solves, a_type):

    if solves == []:
        return -1

    a_type = a_type.lower()

    if a_type in hs.AO5:
        averge_mode = "ao5"
    #elif a_type in hs.BO3:
    #    averge_mode = "bo3"
    elif a_type in hs.MO3:
        averge_mode = "mo3"
    elif a_type in hs.BO1:
        averge_mode = "bo1"
    else:
        raise SkillIssue(f"it appears that {a_type} isn't in any group")

    print(f"Calculating average of {solves} with mode: {a_type},{averge_mode}")

    # average type
    # ? 1. ao5
    # ? 2. bo3
    # ? 3. mo3
    if averge_mode == "bo1":
        return solves[0]
    
    
    if averge_mode == "bo3" or averge_mode == "bo5":
        solves = list(filter(lambda a: a != -1, solves))
        if len(solves) == 0:
            return -1
        
        return min(solves)

    elif averge_mode == "ao5":
        n_of_dnfs = solves.count(-1)

        if n_of_dnfs == 0:
            # clean
            solves.sort()

            solves.pop(0)  # best
            solves.pop(-1)  # worst
        
            #return round(sum(solves) / len(solves), 2)
            
        elif n_of_dnfs == 1:
            solves.sort()

            solves.remove(-1) # the DNF one
            solves.pop(0)  # best

            #return round(sum(solves) / len(solves), 2)
        else:
            return -1
        
        try:
            real_avg = sum(solves) / len(solves)
            print(real_avg,round(real_avg))
            return round(real_avg)
        except ZeroDivisionError:
            print(solves)
            print("ERROR ZeroDivisionError")
            return -1

    elif averge_mode == "mo3":
        solves.sort()
        if len(solves) == 5:
            solves.remove(-1)
            solves.remove(-1)
        if -1 in solves:
            return -1

        
        try:
            real_avg = sum(solves) / len(solves)
            print(real_avg,round(real_avg))
            return round(real_avg)
        except ZeroDivisionError:
            print(solves)
            print("ERROR ZeroDivisionError")
            return -1

    else:
        raise SkillIssue("Invalid type")


def convert_to_centisec(time_str):

    try:
        time_str = time_str.lower()
    except AttributeError: # number
        pass

    if time_str in [-1, "-1", "dnf"]:
        return -1
    elif time_str in [-2,"-2","dns"]:
        return -2
    
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours, minutes, seconds = parts
                total_centiseconds = (int(hours) * 3600 + int(minutes) * 60 + float(seconds)) * 100
            elif len(parts) == 2:
                minutes, seconds = parts
                total_centiseconds = (int(minutes) * 60 + float(seconds)) * 100
        else:
            total_centiseconds = float(time_str) * 100
    except:
        print(f"[ERROR] Parsing time went wrong: {time_str}")
    
    return int(total_centiseconds)


def convert_to_human_frm(centisec,eventId="333"):
    
    if eventId == "333mbf":
        mbld = str(centisec)
        solved = 99 - int(mbld[0:2]) + int(mbld[7:9])
        all_cubes = 99 - int(mbld[0:2]) + 2 * int(mbld[7:9])
        c_time = int(mbld[2:7])
        c_time = functions.convert_to_human_frm(c_time*100)
        mbld = f"{solved}/{all_cubes} {c_time}"
        
        return mbld
    
    elif eventId == "333fm":
        return centisec
    
    if centisec == -1:
        return "DNF"
    elif centisec == -2:
        return "DNS" 
    
    hours = centisec // 360000
    centisec %= 360000
    minutes = centisec // 6000
    centisec %= 6000
    seconds = centisec // 100
    centisec %= 100
    
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    elif minutes >= 10:
        return f"{minutes:02}:{seconds:02}"
    elif minutes > 0:
        return f"{minutes}:{seconds:02}.{centisec:02}"
    else:
        return f"{seconds}.{centisec:02}"


def db_times_to_user_format(array_of_times):
    # None or [] 5x time in centisecs
    if array_of_times is None:
        return ""

    formatted_times = [convert_to_human_frm(time) for time in array_of_times]

    return ",".join(formatted_times)


def parse_times(times, event_id):
    # if event id in mo3 or bo3 only 3
    
    if event_id in hs.AO5:
        averge_mode = "ao5"
    #elif event_id in hs.BO3:
    #    averge_mode = "bo3"
    elif event_id in hs.MO3:
        averge_mode = "mo3"
    else:
        raise SkillIssue(f"it appears that {event_id} isn't in any group")
    
    times = times.lower()
    times = times.replace(" ", "")

    if len(times) in [0, 1]:
        return -1

    if ";" in times:
        t = times.split(";")
    else:
        t = times.split(",")

    if t[-1] == "":
        t = t[:-1]

    if len(t) > 5:
        t = t[0:5]
        
    if averge_mode == "mo3" or averge_mode == "bo3":
        t = t[0:3]

    if len(t) < 5:
        for _ in range(5 - len(t)):
            t.append(-1)

    print("parsed times", t)

    for i in range(len(t)):
        t[i] = convert_to_centisec(t[i])

    print(t)
    return t


"""
def this_week():
    now = dt.now()
    return f"{now.year}-{now.isocalendar()[1]}"
"""


def this_week():
    week = db.load_second_table_idd(1)
    return week["data"]["data"]


def find_in_array_with_id(arry, id, what):
    for ele in arry:
        # print(type(ele.get(what)),type(id))
        if ele.get(what) == id:
            return ele

    return None


def combine_two(list1, list2):  # a2 is primary
    # print(list1,list2)

    if list1 == None:
        list1 = []

    if list2 == None:
        list2 = []

    new = []

    for ele in list2:
        new.append(ele)

    # print("new ","*"*10, new)
    if not list1 == None:
        for i in range(len(list1)):
            ele = list1[i]
            # print(f"{ele=}")
            # {'id': '333', 'data': [10, 20, 40, 55, 100]}

            unique = True
            for i in range(len(new)):
                v = new[i]
                # print(v,ele)
                if v["id"] == ele["id"]:
                    unique = False
                    break

            if unique:
                new.append(ele)

    # print("not final",new)

    # rint("final" , new)

    return new


"""for item in list1:
    merged_dict[item["id"]] = item

# Merge list2 into merged_dict, overriding if "id" already exists
for item in list2:
    merged_dict[item["id"]] = item

# Convert the values of merged_dict back to a list
merged_list = list(merged_dict.values())

print("*"*10)
print(list1,list2,merged_dict)

return merged_dict"""


def arry_to_human_frm(arry, event_id):

    print(f"Readify arry of solves: {arry}")

    # ? [10, 20, 30, 40, 50] 5x time in centisec

    avg = avg_of(arry[:], event_id)
    if event_id in hs.MO3: #or event_id in hs.BO3
        arry = arry[0:3]

    for i in range(len(arry)):
        print(arry[i], convert_to_human_frm(arry[i]),event_id)
        arry[i] = convert_to_human_frm(arry[i],event_id)

    r = f"{convert_to_human_frm(avg,event_id)} | {', '.join(arry)}"

    return r


def generate_all_important_data(data):

    week = this_week()

    important_data = []

    for user_data in data:
        u_data = user_data["data"]["solves"]
        user_id = user_data["user_id"]
        w_data = find_in_array_with_id(u_data, week, "week")
        if not w_data is None:
            w_data = w_data["data"]

            important_data.append({"user_id": user_id, "data": w_data})

    return important_data


def get_diff_ids_from_importantant_data(important_data):

    diff_ids = []

    for u_data in important_data:
        d_data = u_data.get("data")
        for category in d_data:

            if not category["id"] in diff_ids:
                diff_ids.append(category["id"])

    return diff_ids


def extract_data_with_id_and_data(id, data):

    new_data = []

    for u_data in data:
        new_user_data = []
        d_data = u_data["data"]
        for category in d_data:
            if category["id"] == id:
                new_user_data.append(category)

        if not new_user_data == []:

            data_to_add = {"user_id": u_data["user_id"], "data": new_user_data}
            new_data.append(data_to_add)

    return new_data


def add_avg(data):
    for i in range(len(data)):
        data[i]["data"][0]["avg"] = avg_of(
            data[i]["data"][0]["data"][:], data[i]["data"][0]["id"]  #! [:]
        )
    return data


def user_points_add(user_points, user, points):
    user_in = False

    for i in range(len(user_points)):
        if user_points[i]["user_id"] == user:
            user_in = True
            break

    if user_in:
        user_points[i]["points"] = user_points[i]["points"] + points
    else:
        user_points.append({"user_id": user, "points": points})

    return user_points


def sort_user_points(user_points):
    return sorted(user_points, key=lambda x: x["points"], reverse=True)


def place_symbol(place):
    if place == 1:
        return "🥇"
    elif place == 2:
        return "🥈"
    elif place == 3:
        return "🥉"

    return ""


def place_symbol_for_all(place):
    if place == 1:
        return "🥇"
    elif place == 2:
        return "🥈"
    elif place == 3:
        return "🥉"

    return ""


def give_user_points(data):
    for user_data in data:
        user_id = user_data["user_id"]
        points = user_data["points"]

        db_user_data = db.get_user_data(user_id)

        db_user_data["data"]["adata"]["points"] += points

        db.save_user_data(db_user_data)

def any_object_same(a1,a2):
    passed = False
    for idd in a2:
        if idd in a1:
            return True
        
    return False

def true_week_num():
    week_data = db.load_second_table_idd(1)
    # {'id': 1, 'data': {'data': '5', 'old': [None, '1', 'b', '3', '4', '5']}}
    week_data = week_data["data"]
    c_week = week_data["data"]
    all_weeks = week_data["old"]
    
    ind = int(all_weeks.index(c_week) % 3)
    print(ind)
    return ind


def sort_weeky_data(data):
    # [(id:x,data:y),(id:x,data:y)]
    
    new = {}
    
    categories = list(data)
    
    for cat_id in hs.CATEGORIES_SORTED:
        if cat_id in categories:
            new.update({cat_id:data[cat_id]})
    
    if len(data) != len(new):
        print("Error",data)
        for elem in data:
            if not elem in hs.CATEGORIES_SORTED:
                new.update({elem:data[elem]})
    
    return new

def fix_same_avg(data):
    #[{'user_id': /, 'data': [{'id': cat_id, 'data': [100, 200, 300, -1, -1], 'avg': float}]}]
    
    for i in range(len(data)-1):
        p1 = data[i]["data"][0]
        p2 = data[i+1]["data"][0]
        
        
        if p1["avg"] == p2["avg"]:
            print(p1["avg"], p2["avg"])
            
            minP1 = p1["data"]
            minP2 = p2["data"]
            
            minP1 = [x for x in minP1 if x != -1]
            minP2 = [x for x in minP2 if x != -1]
            
            minP1 = min(minP1)
            minP2 = min(minP2)
            
            if minP1 > minP2:
                data[i],data[i+1] = data[i+1],data[i]
                
    return data