import discord
from discord.ext import commands
import requests, json

import src.db as db

import src.wca_function as wca_function


class changewcaidCog(commands.Cog, name="changewcaid command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="changewcaid", usage="(wca id:str)", description="Link your Discord account to a WCA ID.")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def changewcaid(self, ctx, user_input_wca_id = None):
        userObj = ctx.author

        user_data = db.get_user_data(userObj.id)
        current_wca_id = user_data.get("wca_id", "")
        
        if user_input_wca_id is None:
            if current_wca_id:
                q = discord.Embed(
                    title="WCA ID linked",
                    description=f"You currently have WCA ID `{current_wca_id}` linked.",
                    color=discord.Colour.blue(),
                )
            else:
                q = discord.Embed(
                    title="No WCA ID linked",
                    description="You do not have a WCA ID linked yet.",
                    color=discord.Colour.orange(),
                )

            await ctx.respond(embed=q, ephemeral=True)
            return

        if isinstance(user_input_wca_id, str) and user_input_wca_id.upper() == str(current_wca_id).upper():
            q = discord.Embed(
                title="WCA ID already linked",
                description=f"You already have WCA ID `{current_wca_id}` linked.",
                color=discord.Colour.orange(),
            )
            await ctx.respond(embed=q, ephemeral=True)
            return

        wca_id_exitsts = wca_function.wca_id_exists(user_input_wca_id)

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

        await ctx.respond(embed=q, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(changewcaidCog(bot))
