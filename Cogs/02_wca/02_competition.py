import discord
from discord.ext import commands
import requests, json

import db
import hardstorage
import wca_functions
import functions

from datetime import datetime as dt



class compCog(commands.Cog, name="comp command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="comp", usage="", description="")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def comp(self, ctx, id):

        success, data = wca_functions.get_comp_data(id)

        if not success:
            q = discord.Embed(
                title="Competition not found",
                description=f"id: *{id}*",
                color=discord.Colour.red(),
            )
            await ctx.send(embed=q)
            return

        q = discord.Embed(
            title=f":flag_{data['country'].lower()}: | {data['name']}",
            description=f"{data['city']}, {wca_functions.COUNTRIES_DICT.get(data['country'])}",
            color=discord.Colour.blue(),
        )

        date = ""
        
        start_date = data["date"]["from"]
        end_date = data["date"]["till"]
        
        if start_date == end_date:
            date = f'<t:{dt.strptime(start_date, "%Y-%m-%d").timestamp()}:f>'
        else:
            start_date = dt.strptime(start_date, "%Y-%m-%d").timestamp()
            end_date = dt.strptime(end_date, "%Y-%m-%d").timestamp()
            date = f"<t:{int(start_date)}:f> - <t:{int(end_date)}:f> ({data['date']['numberOfDays']})"

        q.add_field(name="Datum", value=date, inline=False)
        
        events = data["events"]
        
        for i in range(len(events)):
            events[i] = hardstorage.SHORT_DICTIONARY.get(events[i])
        
        q.add_field(name="Discipline", value=", ".join(events), inline=False)

        organizer = data["organisers"][0]
        q.add_field(
            name="Organizator", value=f"{organizer['name']}", inline=True,
        )

        delegates = "\n".join(
            [ f"{delegate['name']}" for delegate in data["wcaDelegates"]]
        )
        
        q.add_field(name="WCA Delegati", value=delegates, inline=True)

        q.add_field(
            name="Prizorišče", value=f"{data['venue']['name']}\n{data['venue']['address']}\n{data['venue']['details']}", inline=False,
        )

        # Add additional information
        # q.add_field(name='Additional Information', value=data['information'], inline=False)

        if data["externalWebsite"]:
            q.add_field(
                name="Spletna stran", value=data["externalWebsite"], inline=False
            )

        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(compCog(bot))
