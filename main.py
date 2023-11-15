from pathlib import Path
from itertools import cycle
from discord.ext import commands, tasks
import json
import os
from itertools import cycle
from dotenv import load_dotenv
import time
import discord
from discord.ext import commands

start_time = time.time()

load_dotenv()
token = os.getenv("TOKEN")

unwanted_files = ["exam.txt"]

with open("settings.json", "r") as config:
    data = json.load(config)
    prefix = data["prefix"]
    owner_id = data["owner_id"]

status = cycle(
    [
        "Made by Mankifg",
        "Some commands are used, because we can't trust the calendar.",
        "Tudi slepa kura kocko zloži. :)",
    ]
)


@tasks.loop(seconds=10)
async def status_swap():
    await bot.change_presence(activity=discord.Game(next(status)))


class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("m!"),
    help_command=None,
    description="Mankifg's discord bot.",
    intents=intents,
    owner_id=owner_id,
)

setup_time = time.time()

'''if __name__ == "__main__":
    for path in Path("./Cogs").rglob("*.py"):

        p = str(path)
        p = p.replace("\\", ".")
        p = p.replace("/", ".")
        print(p)
        bot.load_extension(f"{p[:-3]}")'''
        
import asyncio
from pathlib import Path
from discord.ext import commands

async def load_extensions():
    for path in Path("./Cogs").rglob("*.py"):
        p = str(path)
        p = p.replace("\\", ".")
        p = p.replace("/", ".")
        print(p)
        try:
            await bot.load_extension(f"{p[:-3]}")
        except Exception  as e:
            print(f"Failed to load extension {p[:-3]}: {e}")

if __name__ == "__main__":
    bot.loop.run_until_complete(load_extensions())
    bot.run(token)

'''boot_time = time.time()


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}, id: {bot.user.id}")
    print(
        f"Setup time: {round((setup_time-start_time),4)} s,Start time: {round((boot_time-setup_time),4)} s"
    )
    status_swap.start()


bot.run(token)'''
