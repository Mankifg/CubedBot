import discord
from discord.ext import commands
import requests, json

import db
from hardstorage import * 
import wca_functions
import functions

USER_ENDPOINT = "https://raw.githubusercontent.com/robiningelbrecht/wca-rest-api/master/api/persons/{}.json"


class wcapCog(commands.Cog, name="wcap command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="wcap", usage="", description="")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def wcap(self, ctx, member: discord.Member = None, user_wca_id: str = None):

        if user_wca_id is None:
            if member is None:
                userObj = ctx.author
            else:
                userObj = member

            user_data = db.get_user_data(userObj.id)
            wca_id = user_data["wca_id"]

        else:
            wca_id = user_wca_id

        wca_id_exists = wca_functions.wca_id_exists(wca_id)

        if not wca_id_exists:
            q = discord.Embed(
                title=f"Id: **{wca_id}** was not found",
                description="If you think this is an error, please let us know.",
                color=discord.Colour.red(),
            )
            await ctx.send(embed=q)
            return

        user_data = wca_functions.get_wca_data(wca_id)

        picture_url = wca_functions.get_picture_url(wca_id)


        idd = user_data["id"]
        name = user_data["name"]
        country = user_data["country"]
        num_of_comps = user_data["numberOfCompetitions"]
        num_of_championships = user_data["numberOfChampionships"]

        medals = user_data["medals"]

        """{
            gold": 0,
            "silver": 0,
            "bronze": 0
        }"""

        q = discord.Embed(
            title=f":flag_{country.lower()}: | {name}", description=f"ID: {idd}",
            color=0xFFFFF
        )
        
        q.set_image(url=picture_url)
        
        table = []
        
        q.add_field(
            name=f"Medals: {medals['gold']} 🥇,{medals['silver']} 🥈,{medals['bronze']}🥉",
            value=f"({num_of_championships+num_of_comps}) **{num_of_comps}** - Competitions, **{num_of_championships}** Championships",
            inline=False,
        )
        
        u_data = []
        
        for i in range(len(user_data["rank"]["singles"])):
            #print(len(user_data["rank"]["singles"]),len(user_data["rank"]["singles"]))
            
            print(user_data["rank"]["singles"][i]["eventId"],user_data["rank"]["averages"][i]["eventId"])
            
            '''try:
                avgObj = user_data["rank"]["averages"][i]
            except IndexError:
                avgObj = {}
                avgObj["best"] = "N/A"
            
            singleObj = user_data["rank"]["singles"][i]
            
            
            if singleObj["eventId"] == "333mbf":
                print(avgObj,singleObj)
                continue
            
            try:
                table.append([DICTIONARY.get(singleObj['eventId']),functions.readify(singleObj['best']),functions.readify(avgObj['best'])])
            '''
        new_t = ""
            
        q.add_field(name="Table",value=table)

           
        
        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(wcapCog(bot))
