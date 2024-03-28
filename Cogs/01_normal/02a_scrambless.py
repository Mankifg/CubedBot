import discord
from discord.ext import commands
import requests, json

from datetime import datetime as dt

import functions
import db
from hardstorage import *
import hardstorage



mod_roles = db.load_second_table_idd(2)  # role
mod_roles = mod_roles["data"]
mod_roles = list(map(int, mod_roles))


def real_week():
    now = dt.now()
    return f"{now.year}-{now.isocalendar()[1]}"


class s(commands.Cog, name="s command"):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @discord.command(
        name="s",
        usage="",
        description="MOD: Gives scrambles for week",
    )
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def s(self, ctx):

        '''role_ids = [role.id for role in ctx.author.roles]
        passed = functions.any_object_same(role_ids, mod_roles)'''

        passed = ctx.author.id in [732917883591589920,650756055390879757]

        if not passed:
            q = discord.Embed(
                title="no",
                description="You don't have permissions to execute this command",
                color=discord.Colour.blue(),
            )
            await ctx.respond(embed=q, ephemeral=True)
            return

        true_week_num = functions.true_week_num()

        using_ids = POPULAR_EVENT_IDS + ALL_WEEKS[true_week_num]

        print(using_ids)

        q = discord.Embed(
            title="Tedenski mešalni algoritmi",
            description="Generates using **pyTwistyScrambler**.",
            color=0xFFFFF,
        )

        stor = [
"""[1] B2 D' L2 D L2 R2 U' F2 D2 F2 U L' U R2 D L' F U' L' R D'
[2] U R2 F B R B2 R U2 L B2 R U’ D’ R2 F R’ L B2 U2 F2
[3] L' B2 U2 M D2 U2 F2 M' U2 S D F R E' R2 S2 B' E2 R2
[4] L2 R' U R' U' R' F R2 U' R' U' R U R' F' R2 L2 (scramble with feet)
[5] U2 L2 U R2 L F2 R L' U2 R' D2 R D2 R U2 L R' F2 L' R2 U' L2 U2 R'
[E] R U R U' R U R U2 R' U R U R U' R U2 R2 U2 R2 U' R2 U R2 U2 R'""",
"""[1] R2 U2 F U' U F' U2 R2 U
[2] F U F U F U F U F U F
[3] R U2 L' M2 R R' U2 F2
[4] R R' R R' R R' R R' R
[5] M U U U U U U U U U U
[E] Rw Uw2 Lw' Rw Fw2 Rw' Fw""",
"""[1] (0, 5)/(-5, -2)/(5, -4)/(3, 0)/(4, -5)/(3, 0)/(0, -1)/(-3, -3)/(5, 0)/(0, -2)/(6, 0)/(-2, -4)/(0, -2)
[2] UR2- DR1- DL1- UL1- U1- R1- D3- L0+ ALL5+ y2 U5- R5+ D5- L4- ALL2- UR DR UL
[3] Dw2 Uw2 Rw Lw' 3Fw2 Dw Bw 3Lw' Lw2 3Bw Rw' 3Fw' Uw2 3Uw B' L2 3Fw Dw' 3Bw' U' L' Bw2 3Uw 3Lw Bw 3Fw' Dw2 3Dw2 3Lw' 3Rw' B' Bw' R Bw2 Rw' 3Lw' Uw Dw2 U R' 3Dw' Lw2 3Bw2 Uw 3Bw2 F2 U' Dw2
[4] U R' F R' U R' U R F
[5] UR2- DR3+ DL3- UL1- U3- R1- D1- L3- ALL5+ y2 U0+ R2- D0+ L4- ALL3+ DL UL
[E] U B' R' L R U' L B l'  r'  b'  u""",
            """[1] U L' U L R U' B U' B' R'
[2] R' L R L' U L' U' L
[3] F' R U M B2 F r u b
[4] Rw Uw2 Lw' Rw Fw2 Rw' Fw
[5] U R2 F B R B2 R U2 L B2
[E] L 4 E x y z """,
"""[1] Turn the back face counterclockwise by 90 degrees, turn the front face clockwise by 90 degrees, turn the right face counterclockwise by 90 degrees, turn the back face by 180 degrees, turn the front face counterclockwise by 90 degrees
[2] R2 R' R R2 R2 R2 R' R2 R' R2 R' R' R2 R R' R2 R2 R2 R R2 R R' R2 R R
[3] B E E E E E E E E E E E E E E E 
[4] H A H A H A H A H A H A H A H A H A H A H A H A 
[5] (0, 5)/(-5, -2)/(5, -4)/(3, 0)/(4, -5)/(3, 0)/(0, -1)/(-3, -3)/(5, 0)/(0, -2)/(6, 0)/(-2, -4)/(0, -2)
[E] LOL!!! XD!!! WOW YEEEEEEEEEEEES XD HAHA WOW!!! LOL!!! XD!!! WOW YEEEEEEEEEEEES XD HAHA WOW!!!""",
        ]
        

        for i in range(len(stor)):
            q.add_field(

                name=f"{DICTIONARY.get(using_ids[i])}", 
                value=f"```ini\n{stor[i]}```", 
                inline=False
            )
                
                    
        await ctx.send(embed=q)
            

def setup(bot: commands.Bot):
    bot.add_cog(s(bot))
