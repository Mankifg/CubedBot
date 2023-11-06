import discord
from discord.ext import commands
import requests, json
import functions

from datetime import datetime as dt

import db

from hardstorage import *


class weaksolvesCog(commands.Cog, name="weaksolves command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="weaksolves",
        usage="",
        description="Prikaže tedenske rezultate za izbranega uporabnika",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def weaksolves(self, ctx, member: discord.Member = None):
        if member == None:
            userObj = ctx.author
        else:
            userObj = member

        db.create_account(userObj.id)

        user_data = db.get_user_data(userObj.id)
        # {'user_id': 650756055390879757, 'wca_id': '', 'data': {"solves": [],adata': {'created_at': 1697998640}}}

        c_weak = functions.this_weak()
        # YYYY-WN weak num
        f = False
        for i in range(len(user_data["data"]["solves"])):
            if user_data["data"]["solves"][i]["weak"] == c_weak:
                x = i
                f = True
                break

        if not f:
            #! Error
            print("Not founddd")
            weak_time = []
        else:
            weak_time = user_data["data"]["solves"][x]["data"]

        q = discord.Embed(title="Solves")
        q.set_author(name=userObj.display_name, icon_url=userObj.avatar)

        if weak_time == []:
            q.add_field(
                name="No data found", value="Plase submit (ask user to) send solves."
            )
            q.set_footer(text="If you believe this is an error please report it.")

        else:
            for elem in weak_time:
                # {'id': '333', 'data': ['1', '1', '1', '1', '1']}

                # *print(f"elem - {elem}")
                # *print(elem["id"])
                # *print(elem["data"])
                # *print("=" * 10)

                q.add_field(
                    name=f"Event: **{DICTIONARY.get(elem['id'])}**, id: {elem['id']}",
                    value=f"```{functions.beutify(elem['data'],elem['id'])}```",
                    inline=False,
                )

        await ctx.respond(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(weaksolvesCog(bot))
