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
        ret = ret + scrambler222.get_WCA_scramble() + "\n"
        ret = ret + scrambler333.get_WCA_scramble() + "\n"
        ret = ret + scrambler444.get_WCA_scramble() + "\n"

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
            title="Weeky scrambles",
            description="Generates using **pyTwistyScrambler**.",
            color=0xFFFFF,
        )

        for category_id in using_ids:
            cat_name = DICTIONARY.get(category_id)
            repeat = hardstorage.category_attempts(category_id)

            scrambles = ""
            for i in range(repeat):
                scramb = generate_scramble(category_id)
                scrambles = f"{scrambles}[E{i+1}] {scramb}\n"
                print(scramb)

            if len(scrambles) < 1024:

                q.add_field(
                    name=f"{category_id}", 
                    value=f"```ini\n{scrambles}```", 
                    inline=False
                )
            else:
                pass

        await ctx.send(embed=q)


def setup(bot: commands.Bot):
    bot.add_cog(scramblesCog(bot))
