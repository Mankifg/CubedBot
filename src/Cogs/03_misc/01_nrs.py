import discord
from discord.ext import commands
import requests, json

from discord.ext import tasks
import asyncio
from datetime import datetime as dt

import src.wca_function as wca_function
import src.db as db
import src.hardstorage as hardstorage
import src.functions as functions

class nrCog(commands.Cog, name="nr command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.wca_live_check.start()


    @discord.command(name="nr", usage="", description="")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def nr(self, ctx,):
        pass

    @tasks.loop(seconds=900)
    async def wca_live_check(self):

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
        
        for record in resp:
            if record["result"]["person"]["country"]["iso2"] == "CN":
                passing.append(record)
                
        already_submited = db.load_second_table_idd("5")
        
        print(already_submited)   
                    
        for record in passing:
            if not record["id"] in already_submited["data"]["already_sent"]:
                q = discord.Embed(title=f'{record["tag"]} | New {record["type"]}')
                
                person = record["result"]["person"]
                round_obj = record["result"]["round"]
                
                q.add_field(
                    name=f':flag_{person["country"]["iso2"].lower()}: | {person["name"]}', # ( https://www.worldcubeassociation.org/persons/{person["wcaId"]} )',
                    value=f'{person["wcaId"]} from {person["country"]["name"]}',
                    
                )
                q.add_field(
                    name=f':{round_obj["competitionEvent"]["event"]["id"]}: | {round_obj["competitionEvent"]["event"]["name"]}',
                    value=f'{round_obj["competitionEvent"]["competition"]["name"]}',
                    inline=False,
                )
                
                    
                times = []
                nice_times = []
                for el in record["result"]["attempts"]:
                    times.append(el["result"])
                    nice_times.append(functions.readify(el["result"]))

                if record["type"] == "average":                        
                    q.add_field(
                        name=f"AVG: {functions.readify(functions.avg_of(times,round_obj['competitionEvent']['event']['id']))}",
                        value=f"TIMES: {','.join(nice_times)}",
                    )
                    
                else:
                    q.add_field(
                        name=f"TIME: {functions.readify(min(times))}",
                        value=f"AVG: {functions.readify(functions.avg_of(times,round_obj['competitionEvent']['event']['id']))}",
                    )
                
                
                channel = int(already_submited["data"]["channel"])
                print(channel)
                ch = self.bot.get_channel(channel)
                
                await ch.send(embed=q)
                print("send")
                
                
                already_submited["data"]["already_sent"].append(record["id"])
                
                db.save_second_table_idd(already_submited)
                
                


    @wca_live_check.before_loop
    async def before_send_message(self):
        print("PRIMED")
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(nrCog(bot))
