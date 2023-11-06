import discord
from discord.ext import commands


from datetime import datetime as dt

import db
import functions


from hardstorage import *


REVERSE_DICT = reverse_dict = {v: k for k, v in DICTIONARY.items()}


class MyView(discord.ui.View):
    def __init__(self, idd):
        super().__init__()
        self.id = int(idd)

    @discord.ui.button(label="Classic", row=0, style=discord.ButtonStyle.primary)
    async def button1(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id == self.id:
            await interaction.response.send_modal(
                MyModal(id="classic", user_id=interaction.user.id)
            )

    @discord.ui.button(label="Wut", row=2, style=discord.ButtonStyle.secondary)
    async def button2(
        self, select: discord.ui.Select, interaction: discord.Interaction
    ):
        if interaction.user.id == self.id:
            await interaction.response.send_modal(
                MyModal(id="special", user_id=interaction.user.id)
            )


class MyModal(discord.ui.Modal):
    def __init__(self, id, user_id) -> None:
        super().__init__(title="a")
        self.id = id
        self.user_id = user_id

        user_data = db.get_user_data(user_id)
        solves_data = user_data["data"]["solves"]

        weak_times = functions.find_in_array_with_id(
            solves_data, functions.this_weak(), "weak"
        )
        # none if first inp
        print(f"this weak:\n{weak_times}")

        used_ids = []

        if id == "classic":
            # normal catgories
            using_ids = POPULAR_EVENT_IDS
        elif id == "special":
            using_ids = SECONDARY_IDS
        else:
            return 1

        if weak_times is not None:

            actual_weak_data = weak_times["data"]
        else:
            actual_weak_data = []

        print(f"{actual_weak_data=}")

        for i in range(len(using_ids)):
            event_id = using_ids[i]
            translated = DICTIONARY.get(event_id)
            value_from_weak_with_id = functions.find_in_array_with_id(
                actual_weak_data, event_id, "id"
            )
            if value_from_weak_with_id is not None:

                value_from_weak_with_id = value_from_weak_with_id.get("data")
            value_to_display = functions.db_times_to_user_format(
                value_from_weak_with_id
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

        weak_time = functions.find_in_array_with_id(
            solves_data, functions.this_weak(), "weak"
        )
        print("A" * 10)
        print(solves_data)
        print(weak_time)

        if weak_time is None:
            weak_time = {"data": None}
            weak_time["data"] = None

        comb_data = functions.combine_two(weak_time["data"], data)

        print(comb_data)

        print(".")
        packaged_data = {"weak": functions.this_weak(), "data": comb_data}

        print(packaged_data)
        print("before")
        print(user_data["data"]["solves"])
        print("after")

        got = False
        for i in range(len(user_data["data"]["solves"])):
            if user_data["data"]["solves"][i]["weak"] == packaged_data["weak"]:
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
            weak_data = user_data["data"]["solves"][x]["data"]

        print("??" * 5)
        print(weak_data)
        print("??" * 5)

        userObj = interaction.user

        q = discord.Embed(title="Solves")
        q.set_author(name=userObj.display_name, icon_url=userObj.avatar)

        if weak_time == []:
            q.add_field(
                name="No data found", value="Plase submit (ask user to) send solves."
            )
            q.set_footer(text="If you believe this is an error please report it.")

        else:
            for elem in weak_data:
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

        await interaction.response.send_message(embed=q)


class solvesCog(commands.Cog, name="solves command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="solves",
        usage="",
        description="Able to submit solves to database",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def solves(self, ctx):
        userObj = ctx.author

        q = discord.Embed(title="Vnesite čase", description="Enter your solves")
        q.set_footer(text="Če ne dela v prvo, bo šlo v drugo :) .")
        dview = MyView(userObj.id)

        await ctx.respond(embed=q, view=dview, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(solvesCog(bot))
