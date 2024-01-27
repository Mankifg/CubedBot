import discord
from discord.ext import commands
import requests, json

import db

import wca_functions


class changewcaidCog(commands.Cog, name="changewcaid command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="changewcaid", usage="(wca id:str)", description="Changes your wca id assciated with your discord username")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def changewcaid(self, ctx, user_input_wca_id: str = None):
        userObj = ctx.author

        user_data = db.get_user_data(userObj.id)

        wca_id_exitsts = wca_functions.wca_id_exists(user_input_wca_id)
        
        if user_input_wca_id is None:

            user_data["wca_id"] = ""

            q = discord.Embed(
                title=f"Id reseted | {userObj.name}'s profile",
                description="",
                color=discord.Colour.green(),
            )
            q.set_thumbnail(url=userObj.avatar.url)
            q.add_field(name="WCA id", value=user_data["wca_id"])

            await ctx.respond(embed=q)
            return

        if wca_id_exitsts:
            # found
            user_data["wca_id"] = user_input_wca_id

            q = discord.Embed(
                title=f"Id changed | {userObj.name}'s profile",
                description="",
                color=discord.Colour.green(),
            )
            q.set_thumbnail(url=userObj.avatar.url)

            q.add_field(name="WCA id", value=user_data["wca_id"])

            db.save_user_data(user_data)

        else:
            q = discord.Embed(
                title=f"Id: **{user_input_wca_id}** was not found",
                description="If you think this is an error, please let us know.",
                color=discord.Colour.red(),
            )

        await ctx.respond(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(changewcaidCog(bot))
