import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta
import asyncio
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def fetch_leetcode_potd():
    url = "https://leetcode.com/graphql"

    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          title
          difficulty
        }
      }
    }
    """

    response = requests.post(url, json={"query": query})
    data = response.json()

    q = data["data"]["activeDailyCodingChallengeQuestion"]

    return {
        "date": q["date"],
        "title": q["question"]["title"],
        "difficulty": q["question"]["difficulty"],
        "link": "https://leetcode.com" + q["link"]
    }

async def potd_scheduler():
    await bot.wait_until_ready()

    while not bot.is_closed():

        now = datetime.now()
        target = now.replace(hour=12, minute=46, second=0, microsecond=0)

        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        potd = fetch_leetcode_potd()

        requests.post(WEBHOOK_URL, json={
            "type": "potd_add",
            "date": potd["date"],
            "platform": "LeetCode",
            "difficulty": potd["difficulty"],
            "link": potd["link"]
        })

        channel = bot.get_channel(CHANNEL_ID)

        await channel.send(
            f"🔥 **LeetCode POTD**\n\n"
            f"📅 {potd['date']}\n"
            f"📌 {potd['title']}\n"
            f"📊 {potd['difficulty']}\n"
            f"🔗 {potd['link']}"
        )


@bot.command()
async def solve(ctx, platform, difficulty, link, time):
    today = datetime.today().strftime("%Y-%m-%d")

    r = requests.post(WEBHOOK_URL, json={
        "type": "solve",
        "date": today,
        "platform": platform,
        "difficulty": difficulty,
        "link": link,
        "time": time
    })

    data = r.json()

    await ctx.send(
        f"✅ Logged\n"
        f"🔥 Streak: {data['streak']}\n"
        f"📈 Total Solved: {data['total']}"
    )

@bot.command()
async def streak(ctx):
    r = requests.post(WEBHOOK_URL, json={
        "type": "normal_streak"
    })

    data = r.json()

    await ctx.send(f"🔥 Current Streak: {data['streak']}")

@bot.command()
async def potd_done(ctx):
    today = datetime.today().strftime("%Y-%m-%d")

    r = requests.post(WEBHOOK_URL, json={
        "type": "potd_done",
        "date": today
    })

    data = r.json()

    await ctx.send(f"✅ POTD marked solved\n🔥 POTD Streak: {data['streak']}")

@bot.command()
async def potd_streak(ctx):
    r = requests.post(WEBHOOK_URL, json={
        "type": "potd_streak"
    })

    data = r.json()

    await ctx.send(f"🔥 POTD Streak: {data['streak']}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.loop.create_task(potd_scheduler())

bot.run(DISCORD_TOKEN)
