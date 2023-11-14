import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt

import db

print("profile loaded")

class profileCog(commands.Cog, name="profile command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="profile",
        usage="",
        description="Gives a profile for essentially everything.",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def profile(self, ctx, member: discord.Member = None):
        if member == None:
            userObj = ctx.author
        else:
            userObj = member

        db.create_account(userObj.id)

        user_data = db.get_user_data(userObj.id)
        # {'user_id': 650756055390879757, 'wca_id': '', 'data': {"solves": [],adata': {'created_at': 1697998640}}}

        timestamp = user_data["data"]["adata"]["created_at"]

        wca_id = user_data["wca_id"]
        if wca_id == "":
            wca_id = "**Not found**"

        q = discord.Embed(title=f"{userObj.name}'s profile", description="")

        q.set_thumbnail(url=userObj.avatar.url)

        q.add_field(name="WCA id", value=wca_id)
        q.add_field(
            name="Joined", value=f"<t:{timestamp}:R>, <t:{timestamp}:f>", inline=True
        )

        await ctx.respond(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(profileCog(bot))
