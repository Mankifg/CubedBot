import discord
from discord.ext import commands
import requests, json
import functions

from datetime import datetime as dt

import db

from hardstorage import *

mod_roles = db.load_second_table_idd(2) # role
mod_roles = mod_roles["data"]
mod_roles = list(map(int,mod_roles))


class resultsCog(commands.Cog, name="results command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(name="results", usage="", description="MOD: Skupni tedenski rezultati")
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def results(self, ctx,add_points:bool):
        
        role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids,mod_roles)
        
        if not passed:
            q = discord.Embed(title="no", description="You don't have permissions to execute this command",color=discord.Colour.blue())
            await ctx.respond(embed=q,ephemeral=True)
            return
        

        data = db.get_all_data()
        print(data)
        week_all_data = functions.generate_all_important_data(data)

        diffent_ids = functions.get_diff_ids_from_importantant_data(week_all_data)

        important_data = {}

        for idd in diffent_ids:
            idd_data = functions.extract_data_with_id_and_data(idd, week_all_data)
            # print(f"{idd_data=}")
            important_data.update({idd: idd_data})

        final_data = {}

        for event_id, value in important_data.items():
            final_data_cat = []
            important_data[event_id] = functions.add_avg(important_data[event_id])
            important_data[event_id] = sorted(
                important_data[event_id], key=lambda x: x["data"][0]["avg"]
            )

            important_data[event_id] = [
                item
                for item in important_data[event_id]
                if item["data"][0]["avg"] != -1
            ]

            # print(f"{important_data[event_id]=}")

            final_data.update({event_id: important_data[event_id]})

        user_points = []

        q = discord.Embed(
            title=f"🔵 🔵 🔵 REZULTATI {functions.this_week()} 🔵 🔵 🔵",
            color=discord.Color.blue(),
        )
        await ctx.send(embed=q)

        for event_id, event_data in final_data.items():

            event_id_to_display = DICTIONARY.get(event_id)
            q = discord.Embed(title=event_id_to_display, color=discord.Colour.blue())

            to_send = ""

            for i in range(len(event_data)):
                user_data = event_data[i]

                d_name = await self.bot.fetch_user(user_data["user_id"])  # display name
                d_name = d_name.display_name

                avg = user_data["data"][0]["avg"]

                points_to_reward = POINTS[i]

                one_line = f"{i+1}. {d_name} - **{functions.readify(avg)}** - _{points_to_reward}_"

                to_send = to_send + one_line + "\n"

                user_points = functions.user_points_add(
                    user_points, user_data["user_id"], points_to_reward
                )

            q.add_field(name="Lestvica", value=f"{to_send}")

            await ctx.send(embed=q)

        user_points = functions.sort_user_points(user_points)

        to_send = ""
        q = discord.Embed(title="Tedenska lestvica", color=discord.Color.blue())
        
        if add_points:
            bottom_msg = "Adding to db"
        else:
            bottom_msg = "Not adding to db"
        
        for i in range(len(user_points)):
            u = user_points[i]

            user_obj = await self.bot.fetch_user(u["user_id"])  # display name
            d_name = user_obj.display_name

            symbol = functions.place_symbol(i + 1)

            one_line = f"{symbol} | {i+1}. {d_name} - **{u['points']}**"

            to_send = to_send + one_line + "\n"

        q.add_field(name="Lestvica", value=f"{to_send}")
        q.set_footer(text=bottom_msg)

        await ctx.send(embed=q)

        if add_points:
            
            functions.give_user_points(user_points)
            
        all_data = db.get_all_data()
        
        all_clean_data = []
        for user_data in all_data:
            user_id = user_data["user_id"]
            points = user_data["data"]["adata"]["points"]
            
            all_clean_data.append({"user_id": user_id, "points": points})
            
        q = discord.Embed(title="Skupna lestvica", color=discord.Color.yellow())

        all_clean_data = functions.sort_user_points(all_clean_data)
    
        to_send = ""
        for i in range(len(all_clean_data)):
            u = all_clean_data[i]

            user_obj = await self.bot.fetch_user(u["user_id"])  # display name
            d_name = user_obj.display_name

            symbol = functions.place_symbol_for_all(i + 1)

            one_line = f"{symbol} | {i+1}. {d_name} - **{u['points']}**"

            to_send = to_send + one_line + "\n"

        q.add_field(name="Lestvica", value=f"{to_send}")
    
        await ctx.send(embed=q)
        


# userObj = await self.bot.fetch_user(u_data["user_id"]).display_name


def setup(bot: commands.Bot):
    bot.add_cog(resultsCog(bot))
