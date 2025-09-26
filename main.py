import discord
from discord.ext import commands
from discord import ui, ButtonStyle, Interaction
import json
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="?", intents=intents)

# ------------------------------
# FILES & CONSTANTS
# ------------------------------
USERS_FILE = "users.json"
DAILY_COOLDOWN = 86400  # 24h
CARS_POOL = ["Car A", "Car B", "Car C", "Car D"]
CARD_POOL = ["Dragon", "Knight", "Elf", "Wizard"]
RINGS_POOL = ["Fire Ring", "Water Ring", "Earth Ring"]
SLOTS_EMOJIS = ["🍎", "🍌", "🍇", "🍒"]

# ------------------------------
# JSON HELPERS
# ------------------------------
def load_json(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    users = load_json(USERS_FILE)
    if str(user_id) not in users:
        users[str(user_id)] = {
            "balance": 0,
            "last_daily": "1970-01-01 00:00:00",
            "cards": [],
            "cars": [],
        }
        save_json(USERS_FILE, users)
    return users[str(user_id)]

def update_user(user_id, data):
    users = load_json(USERS_FILE)
    users[str(user_id)] = data
    save_json(USERS_FILE, users)

# ------------------------------
# HELP / CMDS
# ------------------------------
@bot.command(name="cmds")
async def cmds(ctx):
    embed = discord.Embed(title="🤖 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="Economy", value="?balance, ?work, ?daily, ?pay", inline=False)
    embed.add_field(name="Mini-Games", value="?cf, ?dice, ?slots, ?roulette", inline=False)
    embed.add_field(name="Collections", value="?collect, ?mycars, ?draw, ?mycards, ?equip", inline=False)
    embed.add_field(name="Shop", value="?shop, ?buy <item>", inline=False)
    embed.add_field(name="Multiplayer", value="?tictactoe <@opponent> <bet>, ?rps_start <@opponent>", inline=False)
    embed.add_field(name="Admin", value="?givecoins, ?removecoins, ?givecard, ?givering, ?givecar, ?removecard, ?removering, ?removecar", inline=False)
    await ctx.send(embed=embed)

# ------------------------------
# ECONOMY COMMANDS
# ------------------------------
@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    user = get_user(member.id)
    embed = discord.Embed(title=f"{member.name}'s Balance", description=f"{user['balance']} coins", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    user = get_user(ctx.author.id)
    earned = random.randint(50, 200)
    user["balance"] += earned
    update_user(ctx.author.id, user)
    embed = discord.Embed(description=f"You worked hard and earned **{earned} coins**!", color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    user = get_user(ctx.author.id)
    last = datetime.strptime(user["last_daily"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    if (now - last).total_seconds() < DAILY_COOLDOWN:
        remaining = timedelta(seconds=int(DAILY_COOLDOWN - (now - last).total_seconds()))
        embed = discord.Embed(description=f"Daily already claimed! Come back in {remaining}", color=discord.Color.red())
        await ctx.send(embed=embed)
    else:
        reward = random.randint(100, 500)
        user["balance"] += reward
        user["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
        update_user(ctx.author.id, user)
        embed = discord.Embed(description=f"Daily claimed! You got **{reward} coins**.", color=discord.Color.green())
        await ctx.send(embed=embed)

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender = get_user(ctx.author.id)
    receiver = get_user(member.id)
    if sender["balance"] < amount:
        embed = discord.Embed(description="Not enough coins!", color=discord.Color.red())
        await ctx.send(embed=embed)
        return
    sender["balance"] -= amount
    receiver["balance"] += amount
    update_user(ctx.author.id, sender)
    update_user(member.id, receiver)
    embed = discord.Embed(description=f"You sent **{amount} coins** to {member.mention}.", color=discord.Color.green())
    await ctx.send(embed=embed)

# ------------------------------
# SHOP & BUTTONS
# ------------------------------
SHOP_ITEMS = {
    "card": {"desc": "Draw a random card"},
    "ring": {"desc": "Equip a ring to a card"},
    "car": {"desc": "Collect a random car"}
}

class ShopView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for item in SHOP_ITEMS.keys():
            self.add_item(ui.Button(label=item.capitalize(), custom_id=f"shop_{item}"))

    @ui.button(label="Close", style=ButtonStyle.red, row=1)
    async def close_button(self, button: ui.Button, interaction: Interaction):
        await interaction.message.delete()

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 Shop", color=discord.Color.blurple())
    for name, data in SHOP_ITEMS.items():
        embed.add_field(name=name.capitalize(), value=data["desc"], inline=False)
    await ctx.send(embed=embed, view=ShopView())

@bot.event
async def on_interaction(interaction: Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    if not interaction.data["custom_id"].startswith("shop_"):
        return
    item = interaction.data["custom_id"][5:]
    user = get_user(interaction.user.id)
    if item == "card":
        card = random.choice(CARD_POOL)
        user["cards"].append({"name": card, "ring": None})
        await interaction.response.send_message(f"You got a card: **{card}**", ephemeral=True)
    elif item == "ring":
        ring = random.choice(RINGS_POOL)
        await interaction.response.send_message(f"You got a ring: **{ring}** (equip it with ?equip)", ephemeral=True)
    elif item == "car":
        car = random.choice(CARS_POOL)
        if car not in user["cars"]:
            user["cars"].append(car)
            await interaction.response.send_message(f"You got a new car: **{car}**", ephemeral=True)
        else:
            await interaction.response.send_message(f"You already have **{car}**", ephemeral=True)
    update_user(interaction.user.id, user)

# ------------------------------
# MULTIPLAYER RPS BUTTONS
# ------------------------------
rps_games = {}

class RPSView(ui.View):
    def __init__(self, player1, player2):
        super().__init__(timeout=None)
        self.player1 = player1
        self.player2 = player2
        for choice in ["Rock", "Paper", "Scissors"]:
            self.add_item(RPSButton(choice.lower(), player1, player2))

class RPSButton(ui.Button):
    def __init__(self, choice, player1, player2):
        super().__init__(label=choice.capitalize(), style=ButtonStyle.primary)
        self.choice = choice
        self.player1 = player1
        self.player2 = player2

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.player1 and interaction.user.id != self.player2:
            await interaction.response.send_message("You're not part of this game.", ephemeral=True)
            return
        if interaction.user.id not in rps_games:
            await interaction.response.send_message("Game expired or not started.", ephemeral=True)
            return
        rps_games[interaction.user.id]["choices"][interaction.user.id] = self.choice
        await interaction.response.send_message(f"Choice **{self.choice}** registered!", ephemeral=True)
        # Check if both players chose
        game = rps_games[interaction.user.id]
        if len(game["choices"]) == 2:
            p1 = self.player1
            p2 = self.player2
            c1 = game["choices"][p1]
            c2 = game["choices"][p2]
            if c1 == c2:
                result = "It's a tie!"
            elif (c1=="rock" and c2=="scissors") or (c1=="paper" and c2=="rock") or (c1=="scissors" and c2=="paper"):
                result = f"<@{p1}> wins!"
            else:
                result = f"<@{p2}> wins!"
            embed = discord.Embed(title="RPS Result", description=f"<@{p1}> chose **{c1}**\n<@{p2}> chose **{c2}**\n{result}", color=discord.Color.green())
            channel = interaction.channel
            await channel.send(embed=embed)
            del rps_games[p1]
            del rps_games[p2]

@bot.command()
async def rps_start(ctx, opponent: discord.Member):
    if ctx.author.id in rps_games or opponent.id in rps_games:
        await ctx.send("One of the players is already in a game!")
        return
    rps_games[ctx.author.id] = {"opponent": opponent.id, "choices": {}}
    rps_games[opponent.id] = {"opponent": ctx.author.id, "choices": {}}
    embed = discord.Embed(title="Rock-Paper-Scissors", description=f"{ctx.author.mention} challenged {opponent.mention}!\nClick your choice below.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=RPSView(ctx.author.id, opponent.id))

# ------------------------------
# RUN BOT
# ------------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
