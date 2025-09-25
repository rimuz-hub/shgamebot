import discord
from discord.ext import commands
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
# ECONOMY COMMANDS
# ------------------------------
@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    user = get_user(member.id)
    await ctx.send(f"{member.mention} has {user['balance']} coins.")

@bot.command()
async def work(ctx):
    user = get_user(ctx.author.id)
    earned = random.randint(50, 200)
    user["balance"] += earned
    update_user(ctx.author.id, user)
    await ctx.send(f"You worked hard and earned {earned} coins!")

@bot.command()
async def daily(ctx):
    user = get_user(ctx.author.id)
    last = datetime.strptime(user["last_daily"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    if (now - last).total_seconds() < DAILY_COOLDOWN:
        remaining = timedelta(seconds=int(DAILY_COOLDOWN - (now - last).total_seconds()))
        await ctx.send(f"Daily already claimed! Come back in {remaining}.")
    else:
        reward = random.randint(100, 500)
        user["balance"] += reward
        user["last_daily"] = now.strftime("%Y-%m-%d %H:%M:%S")
        update_user(ctx.author.id, user)
        await ctx.send(f"Daily claimed! You got {reward} coins.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender = get_user(ctx.author.id)
    receiver = get_user(member.id)
    if sender["balance"] < amount:
        await ctx.send("Not enough coins!")
        return
    sender["balance"] -= amount
    receiver["balance"] += amount
    update_user(ctx.author.id, sender)
    update_user(member.id, receiver)
    await ctx.send(f"You sent {amount} coins to {member.mention}.")

# ------------------------------
# MINI-GAMES WITH BALANCE
# ------------------------------
@bot.command()
async def cf(ctx, member: discord.Member, bet: int = 50):
    user = get_user(ctx.author.id)
    if bet > user["balance"]:
        await ctx.send("Not enough coins!")
        return
    winner = random.choice([ctx.author, member])
    if winner == ctx.author:
        user["balance"] += bet
        update_user(ctx.author.id, user)
        await ctx.send(f"You won the coinflip against {member.mention}! +{bet} coins")
    else:
        user["balance"] -= bet
        update_user(ctx.author.id, user)
        await ctx.send(f"You lost the coinflip against {member.mention}! -{bet} coins")

@bot.command()
async def dice(ctx, bet: int = 50):
    user = get_user(ctx.author.id)
    if bet > user["balance"]:
        await ctx.send("Not enough coins!")
        return
    roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    result_text = f"You rolled {roll} vs Bot rolled {bot_roll}."
    if roll > bot_roll:
        user["balance"] += bet
        result_text += f" You win {bet} coins!"
    elif roll < bot_roll:
        user["balance"] -= bet
        result_text += f" You lose {bet} coins!"
    else:
        result_text += " Draw!"
    update_user(ctx.author.id, user)
    await ctx.send(result_text)

@bot.command()
async def slots(ctx, bet: int = 50):
    user = get_user(ctx.author.id)
    if bet > user["balance"]:
        await ctx.send("Not enough coins!")
        return
    result = [random.choice(SLOTS_EMOJIS) for _ in range(3)]
    await ctx.send(" | ".join(result))
    if len(set(result)) == 1:
        win = bet * 5
        user["balance"] += win
        await ctx.send(f"Jackpot! You win {win} coins!")
    elif len(set(result)) == 2:
        win = bet * 2
        user["balance"] += win
        await ctx.send(f"You matched two! You win {win} coins!")
    else:
        user["balance"] -= bet
        await ctx.send(f"You lost {bet} coins.")
    update_user(ctx.author.id, user)

@bot.command()
async def roulette(ctx, bet: int, color: str):
    color = color.lower()
    user = get_user(ctx.author.id)
    if bet > user["balance"]:
        await ctx.send("Not enough coins!")
        return
    outcome = random.choice(["red", "black"])
    if color not in ["red", "black"]:
        await ctx.send("Invalid color! Choose red or black.")
        return
    if color == outcome:
        user["balance"] += bet
        await ctx.send(f"The roulette landed {outcome}. You win {bet} coins!")
    else:
        user["balance"] -= bet
        await ctx.send(f"The roulette landed {outcome}. You lose {bet} coins.")
    update_user(ctx.author.id, user)

# ------------------------------
# CAR COLLECTION
# ------------------------------
@bot.command()
async def collect(ctx):
    user = get_user(ctx.author.id)
    car = random.choice(CARS_POOL)
    if car not in user["cars"]:
        user["cars"].append(car)
        update_user(ctx.author.id, user)
        await ctx.send(f"You collected a new car: {car}")
    else:
        await ctx.send(f"You already have {car}.")

@bot.command()
async def mycars(ctx):
    user = get_user(ctx.author.id)
    if not user["cars"]:
        await ctx.send("You have no cars.")
    else:
        await ctx.send(f"Your cars: {', '.join(user['cars'])}")

# ------------------------------
# CARD SYSTEM
# ------------------------------
@bot.command()
async def draw(ctx):
    user = get_user(ctx.author.id)
    card = random.choice(CARD_POOL)
    user["cards"].append({"name": card, "ring": None})
    update_user(ctx.author.id, user)
    await ctx.send(f"You drew a card: {card}")

@bot.command()
async def mycards(ctx):
    user = get_user(ctx.author.id)
    if not user["cards"]:
        await ctx.send("You have no cards.")
        return
    text = ""
    for i, c in enumerate(user["cards"]):
        text += f"{i}. {c['name']}"
        if c["ring"]:
            text += f" + {c['ring']}"
        text += "\n"
    await ctx.send(f"Your cards:\n{text}")

@bot.command()
async def equip(ctx, card_index: int, ring_index: int):
    user = get_user(ctx.author.id)
    if card_index < 0 or card_index >= len(user["cards"]):
        await ctx.send("Invalid card index!")
        return
    if ring_index < 0 or ring_index >= len(RINGS_POOL):
        await ctx.send("Invalid ring index!")
        return
    user["cards"][card_index]["ring"] = RINGS_POOL[ring_index]
    update_user(ctx.author.id, user)
    await ctx.send(f"Equipped {RINGS_POOL[ring_index]} to {user['cards'][card_index]['name']}")

# ------------------------------
# TICTACTOE WITH BETS
# ------------------------------
games = {}

@bot.command()
async def tictactoe(ctx, opponent: discord.Member, bet: int = 50):
    if ctx.author.id in games or opponent.id in games:
        await ctx.send("One of the players is already in a game!")
        return
    user1 = get_user(ctx.author.id)
    user2 = get_user(opponent.id)
    if user1["balance"] < bet or user2["balance"] < bet:
        await ctx.send("Both players need enough coins for the bet!")
        return
    board = [" "] * 9
    games[ctx.author.id] = {"opponent": opponent.id, "board": board, "turn": ctx.author.id, "bet": bet}
    games[opponent.id] = {"opponent": ctx.author.id, "board": board, "turn": ctx.author.id, "bet": bet}
    await ctx.send(f"TicTacToe started between {ctx.author.mention} and {opponent.mention}!\n{display_board(board)}\n{ctx.author.mention}'s turn!")

def display_board(board):
    return f"{board[0]}|{board[1]}|{board[2]}\n-+-+-\n{board[3]}|{board[4]}|{board[5]}\n-+-+-\n{board[6]}|{board[7]}|{board[8]}"

@bot.command()
async def place(ctx, position: int):
    if ctx.author.id not in games:
        await ctx.send("You are not in a game!")
        return
    game = games[ctx.author.id]
    if game["turn"] != ctx.author.id:
        await ctx.send("Not your turn!")
        return
    board = game["board"]
    if position < 1 or position > 9 or board[position-1] != " ":
        await ctx.send("Invalid position!")
        return
    mark = "X" if ctx.author.id < game["opponent"] else "O"
    board[position-1] = mark
    # switch turn
    game["turn"] = game["opponent"]
    games[game["opponent"]]["turn"] = game["opponent"]
    if winner(board, mark):
        bet = game["bet"]
        winner_user = get_user(ctx.author.id)
        loser_user = get_user(game["opponent"])
        winner_user["balance"] += bet
        loser_user["balance"] -= bet
        update_user(ctx.author.id, winner_user)
        update_user(game["opponent"], loser_user)
        await ctx.send(f"{ctx.author.mention} wins {bet} coins!\n{display_board(board)}")
        del games[ctx.author.id]
        del games[game["opponent"]]
    elif " " not in board:
        await ctx.send(f"Draw!\n{display_board(board)}")
        del games[ctx.author.id]
        del games[game["opponent"]]
    else:
        await ctx.send(f"{display_board(board)}\n<@{game['opponent']}>'s turn!")

def winner(b, m):
    lines = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    return any(b[a]==b[b_]==b[c]==m for a,b_,c in lines)

# ------------------------------
# LEADERBOARD
# ------------------------------
@bot.command()
async def leaderboard(ctx):
    users = load_json(USERS_FILE)
    sorted_users = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    msg = "🏆 **Leaderboard:**\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.name if member else f"User {uid}"
        msg += f"{i}. {name} — {data['balance']} coins\n"
    await ctx.send(msg)

# ------------------------------
# INVITE LINK
# ------------------------------
@bot.command()
async def invite(ctx):
    await ctx.send("Invite link: https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot&permissions=8")

# ------------------------------
# RUN BOT
# ------------------------------
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
