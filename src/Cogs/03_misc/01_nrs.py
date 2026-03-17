import discord
from discord.ext import commands
import requests

from discord.ext import tasks
from datetime import datetime as dt

import src.wca_function as wca_function
import src.db as db
import src.functions as functions

# Static WCA Europe ISO2 list (sourced from /api/v0/countries on 2026-03-17).
EUROPEAN_ISO2 = {
    "AD","AL","AM","AT","AZ","BA","BE","BG","BY","CH","CY","CZ","DE","DK","EE","ES","FI","FR","GB","GE","GR","HR","HU","IE","IL","IS","IT","LI","LT","LU","LV","MC","MD","ME","MK","MT","NL","NO","PL","PT","RO","RS","RU","SE","SI","SK","SM","TR","UA","VA","XE","XK",
}
MEAN_EVENT_IDS = {"444bf", "555bf", "333fm", "666", "777"}

def should_post_record(record):
    tag = str(record.get("tag", "")).upper()
    person = record.get("result", {}).get("person", {})
    country_iso2 = str(person.get("country", {}).get("iso2", "")).upper()
    if country_iso2 == "SI" or tag == "WR":
        return True
    if tag == "CR":
        return country_iso2 in EUROPEAN_ISO2
    return False

def display_tag(record):
    tag = str(record.get("tag", "")).upper()
    country_iso2 = str(record.get("result", {}).get("person", {}).get("country", {}).get("iso2", "")).upper()
    if tag == "CR" and country_iso2 in EUROPEAN_ISO2:
        return "ER"
    return tag

def display_record_type(record_type, event_id):
    if record_type == "average" and event_id in MEAN_EVENT_IDS:
        return "mean"
    return record_type

def load_nr_row():
    return db.load_second_table_idd(4)

def get_nr_channel():
    row = db.load_second_table_idd(3)
    return int(row["data"]["records_channel"])

def already_sent_nr(nr):
    """
    if nr already sent:
        1 - already sent nr
        
        0 - first time seeing nr && will update
        
    """
    print("chekcing nr",nr)
    row = load_nr_row()
    if not isinstance(row.get("data"), dict):
        row["data"] = {}
    already_sent = row.get("data", {}).get("records_dedupe")
    if not isinstance(already_sent, list):
        already_sent = []
        row["data"]["records_dedupe"] = already_sent

    print(nr in already_sent)
    if not (nr in already_sent):
        print("ins")
        already_sent.append(nr)
        db.save_second_table_idd(row)

        print(0)
        return 0
    print(1)
    return 1

class nrCog(commands.Cog, name="nr command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.wca_live_check.start()


    @tasks.loop(seconds=300)
    async def wca_live_check(self):
        print("[INFO] wca live record check (SI + WR + ER)")
        resp = requests.post(
            url="https://live.worldcubeassociation.org/api/graphql",
            json={
                "query": """
                query {
                    recentRecords {
                    id
                    type
                    tag
                    attemptResult
                    result {
                        attempts {
                        result
                        }
                        person {
                        name
                        wcaId
                        country {
                            iso2
                            name
                        }
                        }
                        round {
                        id
                        competitionEvent {
                            event {
                            id
                            name
                            }
                            competition {
                            id
                            name
                            }
                        }
                        }
                    }
                    }
                }
                """
            },
        ).json()["data"]["recentRecords"]
        
      
        passing = []
        print(len(resp))
        for record in resp:
            if should_post_record(record):
                passing.append(record)
        print(len(passing))
            
        for record in passing:
            print(record["id"])
            #print("fdfff",already_sent_nr(record["id"]))
            if not already_sent_nr(record["id"]):
                print("RECORD FOUND !!!", record)
                
                show_tag = display_tag(record)
                person = record["result"]["person"]
                round_obj = record["result"]["round"]
                event_id = round_obj["competitionEvent"]["event"]["id"]
                shown_type = display_record_type(record["type"], event_id)
                titl = f"{show_tag} {shown_type}"
                
                if show_tag == "NR":
                    q = discord.Embed(title=titl,color=discord.Colour.green())
                elif show_tag == "ER":
                    q = discord.Embed(title=titl,color=discord.Colour.yellow())
                else:
                    q = discord.Embed(title=titl,color=discord.Colour.red())
                    
                q.add_field(
                    name=f':flag_{person["country"]["iso2"].lower()}: {person["name"]}', # ( https://www.worldcubeassociation.org/persons/{person["wcaId"]} )',
                    value=f'[{person["wcaId"]}](https://www.worldcubeassociation.org/persons/{person["wcaId"]})', 
                )
                
                q.add_field(
                    name=f'{round_obj["competitionEvent"]["event"]["name"]}',
                    value=f'{round_obj["competitionEvent"]["competition"]["name"]}',
                    inline=False,
                )
                
                times = []
                for el in record["result"]["attempts"]:
                    times.append(el["result"])
                    
                if shown_type == "mean":
                    result_label = "MEAN"
                elif record["type"] == "average":
                    result_label = "AVERAGE"
                else:
                    result_label = "SINGLE"

                result_value = functions.convert_to_human_frm(record["attemptResult"], event_id)
                solves_value = functions.arry_to_human_frm(times, event_id)
                event_name = round_obj["competitionEvent"]["event"]["name"]
                comp_name = round_obj["competitionEvent"]["competition"]["name"]
                q.set_field_at(
                    1,
                    name=event_name,
                    value=(
                        f"{comp_name}\n"
                        f"\n"
                        f"**{result_label}:** `{result_value}`\n"
                        f"SOLVES: {solves_value}"
                    ),
                    inline=False,
                )
                    
                """if record["type"] == "average":  
                                 
                    q.add_field(
                        name=f'AVERAGE: ```{functions.convert_to_human_frm(functions.avg_of(times,event_id))}```',
                        value=f'SOLVES: `{functions.arry_to_human_frm(times,event_id)}`',
                    )
                else:
                    q.add_field(
                        name=f'SINGLE: ```{functions.convert_to_human_frm(record["attemptResult"],event_id)}```',
                        value=f'SOLVES: `{functions.arry_to_human_frm(times,event_id)}`',
                    )
                """
                
                if show_tag == "NR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/nr.png")
                elif show_tag == "ER":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/cr.png")
                elif show_tag == "WR":
                    q.set_thumbnail(url="https://raw.githubusercontent.com/JackMaddigan/images/main/wr.png")
                else:
                    print("[ERROR] not nr,er or wr?")
                
        
                
                channel = get_nr_channel()
                ch = self.bot.get_channel(channel)
                if ch is None:
                    print(f"[ERROR] records_channel not found: {channel}")
                    continue
                
                await ch.send(embed=q)
                print("sent")
                
              
                
                
    @wca_live_check.before_loop
    async def before_send_message(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
