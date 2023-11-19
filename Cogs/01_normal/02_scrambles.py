import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt

import functions
import db
from hardstorage import *
import hardstorage

from pyTwistyScrambler import (
    scrambler222,
    scrambler333,
    scrambler444,
    scrambler555,
    scrambler666,
    scrambler777,
    megaminxScrambler,
    squareOneScrambler,
    pyraminxScrambler,
    clockScrambler,
    skewbScrambler,
)


def generate_scramble(cid):

    if cid == "222":
        return scrambler222.get_WCA_scramble()

    elif cid == "333":
        return scrambler333.get_WCA_scramble()

    elif cid == "444":
        return scrambler444.get_WCA_scramble()

    elif cid == "555":
        return scrambler555.get_WCA_scramble()

    elif cid == "666":
        return scrambler666.get_WCA_scramble()

    elif cid == "777":
        return scrambler777.get_WCA_scramble()

    elif cid == "333oh":
        return scrambler333.get_WCA_scramble()

    elif cid == "333bf":
        return scrambler333.get_WCA_scramble()

    elif cid == "333mbf":
        return "-1"

    elif cid == "333fm":
        return scrambler333.get_WCA_scramble()

    elif cid == "444bf":
        return scrambler444.get_WCA_scramble()

    elif cid == "pyram":
        return pyraminxScrambler.get_WCA_scramble()

    elif cid == "skewb":
        return skewbScrambler.get_WCA_scramble()

    elif cid == "clock":
        return clockScrambler.get_WCA_scramble()
    elif cid == "minx":
        return megaminxScrambler.get_WCA_scramble()

    elif cid == "sq1":
        return squareOneScrambler.get_WCA_scramble()

    elif cid == "234":
        ret = ""
        ret = ret + "[2x2] " + scrambler222.get_WCA_scramble() + "\n"
        ret = ret + "[3x3] " + scrambler333.get_WCA_scramble() + "\n"
        ret = ret + "[4x4] " + scrambler444.get_WCA_scramble() + "\n"

        return ret

    else:
        print("No Scrambler found.")


mod_roles = db.load_second_table_idd(2)  # role
mod_roles = mod_roles["data"]
mod_roles = list(map(int, mod_roles))


def real_week():
    now = dt.now()
    return f"{now.year}-{now.isocalendar()[1]}"


class scramblesCog(commands.Cog, name="scrambles command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="scrambles",
        usage="",
        description="MOD: Gives scrambles for weak",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def scrambles(self, ctx, week: str = None):

        role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids, mod_roles)

        if not passed:
            q = discord.Embed(
                title="no",
                description="You don't have permissions to execute this command",
                color=discord.Colour.blue(),
            )
            await ctx.respond(embed=q, ephemeral=True)
            return

        true_weak_num = functions.true_week_num()

        using_ids = POPULAR_EVENT_IDS + ALL_WEAKS[true_weak_num]

        print(using_ids)

        q = discord.Embed(
            title="Tedenski mešalni algoritmi",
            description="Generates using **pyTwistyScrambler**.",
            color=0xFFFFF,
        )

        for category_id in using_ids:
            cat_name = DICTIONARY.get(category_id)
            repeat = hardstorage.category_attempts(category_id)

            scrambles = ""
            data = []
            for i in range(repeat):
                scramb = generate_scramble(category_id)
                scrambles = f"{scrambles}[{i+1}] {scramb}\n"
                data.append([f"[{i+1}]",scramb])

            scramb = generate_scramble(category_id)
            scrambles = f"{scrambles}[E] {scramb}\n"
            data.append(["[E]",scramb])

    
            if len(scrambles) < 1024:

                q.add_field(
                    name=f"{cat_name}", 
                    value=f"```ini\n{scrambles}```", 
                    inline=False
                )
            else:
                for i in range(len(data)):
                    prefix = data[i][0]
                    actual_data = data[i][1]
                    
                    if i == 0:
                        name_disp = cat_name
                    else:
                        name_disp = "_ _"
                    
                    q.add_field(
                        name=name_disp,
                        value=f"```ini\n{prefix} {actual_data}```", 
                        inline=False
                    )
                    

        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(scramblesCog(bot))
