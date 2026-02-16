import discord
from discord.ext import commands, tasks
import requests
from datetime import datetime
import os
import re
from html import unescape

# --------------------------
# ENV VARIABLES
# --------------------------

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# --------------------------
# BOT SETUP
# --------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --------------------------
# HTML CLEANER
# --------------------------

def clean_html(raw_html):
    clean = re.sub('<.*?>', '', raw_html)
    return unescape(clean)

def split_message(text, limit=1900):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

# --------------------------
# LEETCODE POTD FETCH
# --------------------------

def fetch_leetcode_potd():
    url = "https://leetcode.com/graphql"

    daily_query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          title
          difficulty
          titleSlug
        }
      }
    }
    """

    response = requests.post(url, json={"query": daily_query})
    data = response.json()

    q = data["data"]["activeDailyCodingChallengeQuestion"]
    slug = q["question"]["titleSlug"]

    detail_query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        content
        exampleTestcases
        topicTags {
          name
        }
      }
    }
    """

    variables = {"titleSlug": slug}

    response2 = requests.post(url, json={
        "query": detail_query,
        "variables": variables
    })

    detail_data = response2.json()
    question = detail_data["data"]["question"]

    return {
        "date": q["date"],
        "title": q["question"]["title"],
        "difficulty": q["question"]["difficulty"],
        "content": question["content"],
        "examples": question["exampleTestcases"],
        "tags": [tag["name"] for tag in question["topicTags"]]
    }

# --------------------------
# SCHEDULED TASKS
# --------------------------

@tasks.loop(time=datetime.strptime("19:44", "%H:%M").time())
async def potd_task():
    channel = bot.get_channel(CHANNEL_ID)
    potd = fetch_leetcode_potd()

    # Send to sheet
    requests.post(WEBHOOK_URL, json={
        "type": "potd_add",
        "date": potd["date"],
        "platform": "LeetCode",
        "difficulty": potd["difficulty"],
        "link": "Auto-Fetched"
    })

    description = clean_html(potd["content"])
    tags = ", ".join(potd["tags"])

    header = (
        f"🔥 **LeetCode Problem of the Day**\n\n"
        f"📅 {potd['date']}\n"
        f"📌 **{potd['title']}**\n"
        f"📊 Difficulty: {potd['difficulty']}\n"
        f"🏷 Tags: {tags}\n\n"
        f"📝 **Problem Statement:**\n"
    )

    full_message = header + description

    for chunk in split_message(full_message):
        await channel.send(chunk)


@tasks.loop(time=datetime.strptime("19:00", "%H:%M").time())
async def reminder_7pm():
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(
        "⚠️ Reminder: Solve at least one DSA problem today.\n"
        "Your streak will break if you skip."
    )


@tasks.loop(time=datetime.strptime("21:00", "%H:%M").time())
async def reminder_9pm():
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(
        "⚠️ Still time left. Solve one problem to protect your streak."
    )


@tasks.loop(time=datetime.strptime("22:00", "%H:%M").time())
async def reminder_10pm():
    channel = bot.get_channel(CHANNEL_ID)
    await channel.send(
        "⚠️ Don't forget to solve today's LeetCode POTD."
    )

# --------------------------
# COMMANDS
# --------------------------

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
    r = requests.post(WEBHOOK_URL, json={"type": "normal_streak"})
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

    await ctx.send(
        f"✅ POTD marked solved\n"
        f"🔥 POTD Streak: {data['streak']}"
    )


@bot.command()
async def potd_streak(ctx):
    r = requests.post(WEBHOOK_URL, json={"type": "potd_streak"})
    data = r.json()
    await ctx.send(f"🔥 POTD Streak: {data['streak']}")

# --------------------------
# START TASKS
# --------------------------

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    potd_task.start()
    reminder_7pm.start()
    reminder_9pm.start()
    reminder_10pm.start()

# --------------------------
# RUN BOT
# --------------------------

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
