import discord
from discord.ext import commands

import src.db as db
import src.hardstorage as hardstorage
import src.wca_function as wca_function
from src.guild_access import both_guild_ids

from datetime import datetime as dt


def _people_field(singular, dual, plural, people):
    if not isinstance(people, list):
        people = []
    names = [
        person.get("name")
        for person in people
        if isinstance(person, dict) and person.get("name")
    ]
    if len(names) == 1:
        label = singular
    elif len(names) == 2:
        label = dual
    else:
        label = plural
    if not names:
        return label, "-"
    if len(names) <= 5:
        return label, "\n".join(names)
    return label, ", ".join(names)


class compCog(commands.Cog, name="comp command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="comp",
        usage="(id)",
        description="Show details for a WCA competition.",
        guild_ids=both_guild_ids(),
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def comp(self, ctx, id):
        await ctx.defer()

        success, data = wca_function.get_comp_data(id)

        if not success:
            q = discord.Embed(
                title="Competition not found",
                description=f"id: *{id}*",
                color=discord.Colour.red(),
            )
            await ctx.respond(embed=q)
            return

        is_special_fmc = wca_function.is_special_fmc_comp(data["name"])

        q = discord.Embed(
            title=f"{wca_function.comp_title_prefix(data['name'], data['country'])} | {data['name']}",
            description=f"{data['city']}, {wca_function.COUNTRIES_DICT.get(data['country'])} | [{data['id']}](https://www.worldcubeassociation.org/competitions/{data['id']})",
            color=discord.Colour.blue(),
        )
        start_date = data["date"]["from"]
        end_date = data["date"]["till"]
        date = wca_function.format_comp_date(
            data["name"],
            start_date,
            end_date,
            data["date"]["numberOfDays"],
        )
            
        q.add_field(name="Datum", value=date, inline=False)
        
        #*********
        events = data["events"]
        
        for i in range(len(events)):
            events[i] = hardstorage.SHORT_DICTIONARY.get(events[i])
        
        q.add_field(name="Discipline", value=", ".join(events), inline=False)

        if not is_special_fmc:
            organizer_label, organizer_value = _people_field(
                "Organizator",
                "Organizatorja",
                "Organizatorji",
                data["organisers"],
            )
            q.add_field(name=organizer_label, value=organizer_value, inline=True)

            delegate_label, delegate_value = _people_field(
                "WCA delegat",
                "WCA delegata",
                "WCA delegati",
                data["wcaDelegates"],
            )
            q.add_field(name=delegate_label, value=delegate_value, inline=True)
            
            q.add_field(name="Prizorišče", value=f"{data['venue']['name']}\n{data['venue']['address']}", inline=False,)

        if data["externalWebsite"]:
            q.add_field(name="Spletna stran", value=data["externalWebsite"], inline=False)

        send_msg = await ctx.respond(embed=q)
        
        #? forced into this
        channel = db.load_second_table_idd(5)["data"]["announcer_channel"]
        channel = int(channel)
        if ctx.channel.id == channel:
            if send_msg is not None:
                await send_msg.add_reaction("🟢")
                await send_msg.add_reaction("🟡")
                await send_msg.add_reaction("🔴")


def setup(bot: commands.Bot):
    bot.add_cog(compCog(bot))
