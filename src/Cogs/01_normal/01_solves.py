import discord
from discord.ext import commands


from datetime import datetime as dt

import src.db as db
import src.functions as functions

from src.hardstorage import *

REVERSE_DICT = reverse_dict = {v: k for k, v in DICTIONARY.items()}


class MyView(discord.ui.View):
    def __init__(self, idd):
        super().__init__()
        self.id = int(idd)

    @discord.ui.button(label="Glavne discipline", row=0, style=discord.ButtonStyle.primary)
    async def button1(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id == self.id:
            await interaction.response.send_modal(
                MyModal(id="classic", user_id=interaction.user.id)
            )

    @discord.ui.button(label="Stranske discipline", row=0, style=discord.ButtonStyle.secondary)
    async def button2(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id == self.id:
            await interaction.response.send_modal(
                MyModal(id="special", user_id=interaction.user.id)
            )


class MyModal(discord.ui.Modal):
    def __init__(self, id, user_id) -> None:
        super().__init__(title="Vnesi svoje čase")
        self.id = id
        self.user_id = user_id

        user_data = db.get_user_data(user_id)
        solves_data = user_data["data"]["solves"]

        week_times = functions.find_in_array_with_id(
            solves_data, functions.this_week(), "week"
        )
        # none if first inp
        print(f"this week:\n{week_times}")

        used_ids = []

        if id == "classic":
            # normal catgories
            using_ids = POPULAR_EVENT_IDS
        elif id == "special":
            true_week_num = functions.true_week_num()
            using_ids = ALL_WEEKS[true_week_num]
        else:
            return 1

        if week_times is not None:
            actual_week_data = week_times["data"]
        else:
            actual_week_data = []

        print(f"{actual_week_data=}")

        for i in range(len(using_ids)):
            event_id = using_ids[i]
            translated = DICTIONARY.get(event_id)
            value_from_week_with_id = functions.find_in_array_with_id(
                actual_week_data, event_id, "id"
            )
            if value_from_week_with_id is not None:

                value_from_week_with_id = value_from_week_with_id.get("data")
            value_to_display = functions.db_times_to_user_format(
                value_from_week_with_id
            )

            self.add_item(
                discord.ui.InputText(
                    label=f"{translated}  |{event_id}",
                    required=False,
                    placeholder="Vnesi čase / Enter times",
                    value=value_to_display,
                )
            )  # value = what already typed

    async def callback(self, interaction: discord.Interaction):

        user_id = interaction.user.id

        l_fields = len(self.children)  # len_field

        '''
        self.childer[i].label 
         .value
        '''
        
        event_ids = []
        data = []

        for i in range(l_fields):
            l = self.children[i].label
            l = l.split("|")[1]
            d = self.children[i].value
            dat = functions.parse_times(d, l)
            if not dat in [-1, "dnf"]:
                data.append({"id": l, "data": dat})

        user_data = db.get_user_data(user_id)
        solves_data = user_data["data"]["solves"]

        week_time = functions.find_in_array_with_id(
            solves_data, functions.this_week(), "week"
        )
        print("A" * 10)
        print(solves_data)
        print(week_time)

        if week_time is None:
            week_time = {"data": None}
            week_time["data"] = None
            
        print(data)
        comb_data = functions.combine_two(week_time["data"], data)

        #comb_data = functions.sort_weeky_data(comb_data)
        print(comb_data)

        print(".")
        packaged_data = {"week": functions.this_week(), "data": comb_data}

        print(packaged_data)
        print("before")
        print(user_data["data"]["solves"])
        print("after")

        got = False
        for i in range(len(user_data["data"]["solves"])):
            if user_data["data"]["solves"][i]["week"] == packaged_data["week"]:
                x = i
                print("found")
                got = True
                break

        if got:
            user_data["data"]["solves"][i] = packaged_data
        else:
            x = i
            user_data["data"]["solves"].append(packaged_data)

        # print(user_data["data"]["solves"])
        db.save_user_data(user_data)
        print("saving", user_data)

        c_week = functions.this_week()
        # YYYY-WN week num

        f = False
        for i in range(len(user_data["data"]["solves"])):
            if user_data["data"]["solves"][i]["week"] == c_week:
                x = i
                f = True
                break

        if not f:
            #! Error
            print("Not founddd")
            week_time = []
        else:
            week_data = user_data["data"]["solves"][x]["data"]

        print("??" * 5)
        print(week_data)
        print("??" * 5)

        userObj = interaction.user

        q = discord.Embed(title="Rezultati",color=0xFFFFF)
        q.set_author(name=userObj.display_name, icon_url=userObj.avatar)

        if week_time == []:
            q.add_field(
                name="No data found", value="Plase submit (ask user to) send solves."
            )
            q.set_footer(text="If you believe this is an error please report it.")

        else:
            for elem in week_data:
                # {'id': '333', 'data': ['1', '1', '1', '1', '1']}

                # *print(f"elem - {elem}")
                # *print(elem["id"])
                # *print(elem["data"])
                # *print("=" * 10)

                q.add_field(
                    name=f"Disciplina: **{DICTIONARY.get(elem['id'])}**, id: {elem['id']}",
                    value=f"```{functions.arry_to_human_frm(elem['data'],elem['id'])}```",
                    inline=False,
                )

        await interaction.response.send_message(embed=q)


class solvesCog(commands.Cog, name="solves command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="solves",
        usage="",
        description="Submit solves to database",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def solves(self, ctx):
        userObj = ctx.author

        q = discord.Embed(title="Vnesite čase", description="Enter your solves",color=0xFFFFF)
        q.set_footer(text="Če ne dela v prvo, bo šlo v drugo :) .")
        dview = MyView(userObj.id)

        await ctx.respond(embed=q, view=dview, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(solvesCog(bot))
