import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import random, os, asyncio, json
from dotenv import load_dotenv
import aiosqlite

# -----------------------------
# Load token
# -----------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# -----------------------------
# Bot setup
# -----------------------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="?", intents=intents)
bot.remove_command("help")

# -----------------------------
# JSON storage
# -----------------------------
BALANCES_FILE = "balances.json"
CARDS_FILE = "cards.json"
PETS_FILE = "pets.json"

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

balances = load_json(BALANCES_FILE)
cards_data = load_json(CARDS_FILE)
pets_data = load_json(PETS_FILE)

def get_balance(user_id):
    return balances.get(str(user_id),0)

def add_balance(user_id,amount):
    balances[str(user_id)] = get_balance(user_id)+amount
    save_json(BALANCES_FILE,balances)

def get_cards(user_id):
    return cards_data.get(str(user_id),[])

def add_card(user_id,card):
    user_cards = get_cards(user_id)
    user_cards.append(card)
    cards_data[str(user_id)] = user_cards
    save_json(CARDS_FILE, cards_data)

def get_pets(user_id):
    return pets_data.get(str(user_id),[])

def add_pet(user_id,pet):
    user_pets = get_pets(user_id)
    user_pets.append(pet)
    pets_data[str(user_id)] = user_pets
    save_json(PETS_FILE, pets_data)

# -----------------------------
# Cooldowns
# -----------------------------
work_cd,daily_cd,card_cd,pet_cd={}, {}, {}, {}

# -----------------------------
# Helper embed
# -----------------------------
async def send_embed(ctx,title,desc,color=discord.Color.green()):
    embed=discord.Embed(title=title,description=desc,color=color)
    await ctx.send(embed=embed)


# -----------------------------
# Economy commands
# -----------------------------
@bot.command()
async def balance(ctx):
    bal=get_balance(ctx.author.id)
    await send_embed(ctx,"💰 Balance",f"{ctx.author.mention}, your balance is **${bal}**")

@bot.command()
async def work(ctx):
    now=asyncio.get_event_loop().time()
    user=ctx.author.id
    if user in work_cd and now-work_cd[user]<30:
        await send_embed(ctx,"⏳ Work Cooldown",f"Wait {int(30-(now-work_cd[user]))}s",discord.Color.orange())
        return
    earn=random.randint(50,150)
    add_balance(user,earn)
    work_cd[user]=now
    await send_embed(ctx,"👷 Work",f"You earned **${earn}**!")

@bot.command()
async def daily(ctx):
    now=asyncio.get_event_loop().time()
    user=ctx.author.id
    if user in daily_cd and now-daily_cd[user]<86400:
        await send_embed(ctx,"⏳ Daily Cooldown",f"Wait {int((86400-(now-daily_cd[user]))/3600)}h",discord.Color.orange())
        return
    reward=500
    add_balance(user,reward)
    daily_cd[user]=now
    await send_embed(ctx,"📅 Daily",f"You claimed your daily reward of **${reward}**!")

@bot.command()
async def pay(ctx,user:discord.Member,amount:int):
    bal=get_balance(ctx.author.id)
    if amount<=0 or amount>bal:
        await send_embed(ctx,"❌ Error","Invalid amount",discord.Color.red())
        return
    add_balance(ctx.author.id,-amount)
    add_balance(user.id,amount)
    await send_embed(ctx,"💸 Payment",f"{ctx.author.mention} paid **${amount}** to {user.mention}")

@bot.command()
@commands.has_permissions(manage_guild=True)
async def give(ctx,user:discord.Member,amount:int):
    if amount<=0:
        await send_embed(ctx,"❌ Error","Amount must be >0",discord.Color.red())
        return
    add_balance(user.id,amount)
    await send_embed(ctx,"💰 Admin Give",f"{ctx.author.mention} gave **${amount}** to {user.mention}")

# -----------------------------
from discord.ext import commands
from discord.ui import View, Button
import discord
import random





# -----------------------------
# Mini-games: Coinflip/Dice/Slots/Roulette
# -----------------------------
@bot.command()
async def cf(ctx,bet:int,choice:str):
    bal=get_balance(ctx.author.id)
    if bet<=0 or bet>bal:
        await send_embed(ctx,"❌ Error","Invalid bet",discord.Color.red())
        return
    if choice.lower() not in ["heads","tails"]:
        await send_embed(ctx,"❌ Error","Choose heads/tails",discord.Color.red())
        return
    result=random.choice(["heads","tails"])
    if choice.lower()==result:
        add_balance(ctx.author.id,bet)
        await send_embed(ctx,"🪙 Coinflip",f"You won! Coin: **{result}**\n+${bet}")
    else:
        add_balance(ctx.author.id,-bet)
        await send_embed(ctx,"🪙 Coinflip",f"You lost! Coin: **{result}**\n-${bet}",discord.Color.red())

@bot.command()
async def dice(ctx,bet:int,guess:int=None):
    bal=get_balance(ctx.author.id)
    if bet<=0 or bet>bal:
        await send_embed(ctx,"❌ Error","Invalid bet",discord.Color.red())
        return
    roll=random.randint(1,6)
    if guess is None:
        await send_embed(ctx,"🎲 Dice",f"Dice rolled **{roll}**")
        return
    if guess==roll:
        winnings=bet*6
        add_balance(ctx.author.id,winnings)
        await send_embed(ctx,"🎲 Dice",f"Rolled {roll}, guessed {guess}, won **${winnings}**")
    else:
        add_balance(ctx.author.id,-bet)
        await send_embed(ctx,"🎲 Dice",f"Rolled {roll}, guessed {guess}, lost **${bet}**",discord.Color.red())

@bot.command()
async def slots(ctx,bet:int):
    bal=get_balance(ctx.author.id)
    if bet<=0 or bet>bal:
        await send_embed(ctx,"❌ Error","Invalid bet",discord.Color.red())
        return
    symbols=["🍒","🍋","🍇","🍉","⭐","7️⃣"]
    res=[random.choice(symbols) for _ in range(3)]
    if len(set(res))==1:
        winnings=bet*5
        add_balance(ctx.author.id,winnings)
        msg=f"JACKPOT! Won **${winnings}**"
        color=discord.Color.green()
    elif len(set(res))==2:
        winnings=int(bet*1.5)
        add_balance(ctx.author.id,winnings)
        msg=f"Two match! Won **${winnings}**"
        color=discord.Color.gold()
    else:
        add_balance(ctx.author.id,-bet)
        msg=f"No match! Lost **${bet}**"
        color=discord.Color.red()
    await send_embed(ctx,"🎰 Slots",f"{' | '.join(res)}\n{msg}",color)

@bot.command()
async def roulette(ctx,bet:int,choice:str):
    bal=get_balance(ctx.author.id)
    if bet<=0 or bet>bal:
        await send_embed(ctx,"❌ Error","Invalid bet",discord.Color.red())
        return
    numbers=list(range(37))
    result=random.choice(numbers)
    win=False
    payout=0
    if choice.isdigit() and int(choice)==result:
        win=True
        payout=bet*35
    elif choice.lower() in ["red","black"]:
        color="red" if result%2==0 else "black"
        if choice.lower()==color:
            win=True
            payout=bet*2
    if win:
        add_balance(ctx.author.id,payout)
        await send_embed(ctx,"🎡 Roulette",f"Result: {result}\nWon **${payout}**")
    else:
        add_balance(ctx.author.id,-bet)
        await send_embed(ctx,"🎡 Roulette",f"Result: {result}\nLost **${bet}**",discord.Color.red())

# -----------------------------
# TicTacToe
# -----------------------------
class TicTacToeButton(Button):
    def __init__(self,x,y):
        super().__init__(style=discord.ButtonStyle.secondary,label="\u200b",row=y)
        self.x=x
        self.y=y
    async def callback(self,interaction):
        view=self.view
        if interaction.user!=view.current:
            await interaction.response.send_message("❌ Not your turn",ephemeral=True)
            return
        mark="X" if view.current==view.p1 else "O"
        self.label=mark
        self.disabled=True
        view.board[self.y][self.x]=mark
        if view.check_win(mark):
            for child in view.children:
                child.disabled=True
            await interaction.response.edit_message(content=f"🎉 {interaction.user.mention} wins!",view=view)
            return
        view.switch_player()
        await interaction.response.edit_message(view=view)

class TicTacToeView(View):
    def __init__(self,p1,p2):
        super().__init__(timeout=180)
        self.p1=p1
        self.p2=p2
        self.current=p1
        self.board=[[None,None,None],[None,None,None],[None,None,None]]
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x,y))
    def switch_player(self):
        self.current=self.p2 if self.current==self.p1 else self.p1
    def check_win(self,mark):
        b=self.board
        for row in b:
            if all([c==mark for c in row]):
                return True
        for col in range(3):
            if all([b[row][col]==mark for row in range(3)]):
                return True
        if b[0][0]==b[1][1]==b[2][2]==mark:
            return True
        if b[0][2]==b[1][1]==b[2][0]==mark:
            return True
        return False

@bot.command()
async def tictactoe(ctx,opponent: discord.Member):
    if opponent==ctx.author:
        await ctx.send("❌ Cannot play yourself")
        return
    view=TicTacToeView(ctx.author,opponent)
    await ctx.send(f"🎮 TicTacToe: {ctx.author.mention} vs {opponent.mention}",view=view)

# -----------------------------
# Blackjack 1v1
# -----------------------------
class Blackjack1v1(View):
    def __init__(self, ctx, p1, p2, bet):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.p1 = p1
        self.p2 = p2
        self.bet = bet
        self.current = p1
        self.deck = [i for i in range(1,12)]*4
        random.shuffle(self.deck)
        self.hands = {p1.id:[self.deck.pop(),self.deck.pop()],p2.id:[self.deck.pop(),self.deck.pop()]}
        self.msg = None

        self.hit_btn = Button(label="Hit", style=discord.ButtonStyle.success)
        self.stand_btn = Button(label="Stand", style=discord.ButtonStyle.danger)
        self.hit_btn.callback = self.hit
        self.stand_btn.callback = self.stand
        self.add_item(self.hit_btn)
        self.add_item(self.stand_btn)

    async def send_hands(self):
        embed=discord.Embed(title="🃏 Blackjack 1v1",color=discord.Color.green())
        for player in [self.p1,self.p2]:
            embed.add_field(name=player.display_name,value=f"{self.hands[player.id]} = {sum(self.hands[player.id])}",inline=False)
        embed.set_footer(text=f"Turn: {self.current.display_name}")
        if self.msg:
            await self.msg.edit(embed=embed, view=self)
        else:
            self.msg = await self.ctx.send(embed=embed, view=self)

    async def switch_turn(self):
        self.current=self.p2 if self.current==self.p1 else self.p1
        await self.send_hands()

    async def hit(self, interaction: discord.Interaction):
        if interaction.user!=self.current:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        self.hands[self.current.id].append(self.deck.pop())
        total=sum(self.hands[self.current.id])
        if total>21:
            add_balance(self.current.id,-self.bet)
            await interaction.response.edit_message(content=f"❌ {self.current.display_name} busted! Lost ${self.bet}", view=None)
            self.stop()
        else:
            await interaction.response.defer()
            await self.send_hands()

    async def stand(self, interaction: discord.Interaction):
        if interaction.user!=self.current:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        if self.current==self.p1:
            await self.switch_turn()
            await interaction.response.defer()
        else:
            p1_total=sum(self.hands[self.p1.id])
            p2_total=sum(self.hands[self.p2.id])
            if p1_total>21 and p2_total>21:
                result="🤝 Both busted! No one wins."
            elif p1_total>21:
                add_balance(self.p2.id,self.bet)
                add_balance(self.p1.id,-self.bet)
                result=f"🎉 {self.p2.display_name} wins! {self.p1.display_name} busted."
            elif p2_total>21:
                add_balance(self.p1.id,self.bet)
                add_balance(self.p2.id,-self.bet)
                result=f"🎉 {self.p1.display_name} wins! {self.p2.display_name} busted."
            elif p1_total>p2_total:
                add_balance(self.p1.id,self.bet)
                add_balance(self.p2.id,-self.bet)
                result=f"🎉 {self.p1.display_name} wins!"
            elif p2_total>p1_total:
                add_balance(self.p2.id,self.bet)
                add_balance(self.p1.id,-self.bet)
                result=f"🎉 {self.p2.display_name} wins!"
            else:
                result="🤝 It's a tie!"
            await interaction.response.edit_message(content=result, view=None)
            self.stop()

@bot.command()
async def blackjack(ctx, opponent: discord.Member, bet: int):
    if opponent==ctx.author:
        await ctx.send("❌ You cannot play yourself!")
        return
    if bet<=0:
        await ctx.send("❌ Bet must be >0")
        return
    if get_balance(ctx.author.id)<bet or get_balance(opponent.id)<bet:
        await ctx.send("❌ Both players must have enough balance!")
        return
    view=Blackjack1v1(ctx,ctx.author,opponent,bet)
    await view.send_hands()

# -----------------------------
import discord
from discord.ext import commands
from discord.ui import View, Button
import random, os, json, asyncio

# ----------------- STORAGE -----------------
CARDS_FILE = "cards.json"

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

cards_data = load_json(CARDS_FILE)

def get_cards(user_id):
    return cards_data.get(str(user_id), [])

def add_card(user_id, card):
    user_cards = get_cards(user_id)
    user_cards.append(card)
    cards_data[str(user_id)] = user_cards
    save_json(CARDS_FILE, cards_data)

def remove_card(user_id, card):
    user_cards = get_cards(user_id)
    if card in user_cards:
        user_cards.remove(card)
        cards_data[str(user_id)] = user_cards
        save_json(CARDS_FILE, cards_data)

# ----------------- CARD POOL -----------------
CARD_POOL = [
    {"name":"Fire Elemental","atk":50,"def":20,"hp":120},
    {"name":"Water Spirit","atk":30,"def":40,"hp":130},
    {"name":"Earth Golem","atk":20,"def":50,"hp":150},
    {"name":"Wind Falcon","atk":40,"def":30,"hp":110},
    {"name":"Lightning Dragon","atk":60,"def":10,"hp":100},
    {"name":"Shadow Assassin","atk":55,"def":15,"hp":90},
    {"name":"Holy Knight","atk":35,"def":45,"hp":140},
    {"name":"Frost Giant","atk":25,"def":55,"hp":160},
    {"name":"Phoenix","atk":45,"def":25,"hp":120},
    {"name":"Dark Sorcerer","atk":70,"def":5,"hp":80}
]

# ----------------- COMMANDS -----------------
@commands.command()
async def drawcard(ctx):
    """Draw a random card (5 min cooldown)."""
    now = asyncio.get_event_loop().time()
    if hasattr(ctx.bot, "card_cd") and ctx.author.id in ctx.bot.card_cd:
        last = ctx.bot.card_cd[ctx.author.id]
        if now - last < 300:
            rem = int(300 - (now - last))
            await ctx.send(f"⏳ Wait {rem//60}m {rem%60}s before drawing again")
            return
    card = random.choice(CARD_POOL)
    add_card(ctx.author.id, card.copy())
    ctx.bot.card_cd = getattr(ctx.bot, "card_cd", {})
    ctx.bot.card_cd[ctx.author.id] = now
    await ctx.send(f"🃏 You drew **{card['name']}** (ATK:{card['atk']} DEF:{card['def']} HP:{card['hp']})")

@commands.command()
async def mycards(ctx):
    """View your collected cards."""
    user_cards = get_cards(ctx.author.id)
    if not user_cards:
        await ctx.send("❌ You don't have any cards yet!")
        return
    desc = "\n".join([f"{i+1}. {c['name']} | ATK:{c['atk']} DEF:{c['def']} HP:{c['hp']}" for i,c in enumerate(user_cards)])
    embed = discord.Embed(title=f"{ctx.author.display_name}'s Cards", description=desc, color=discord.Color.blue())
    await ctx.send(embed=embed)

@commands.command()
async def sellcard(ctx, *, cardname:str):
    """Sell one of your cards for currency (half stats)."""
    user_cards = get_cards(ctx.author.id)
    card = next((c for c in user_cards if c['name'].lower() == cardname.lower()), None)
    if not card:
        await ctx.send(f"❌ You don't have a card named '{cardname}'")
        return
    sell_price = (card['atk'] + card['def'] + card['hp']//10) // 2
    remove_card(ctx.author.id, card)
    # NOTE: integrate add_balance if using economy
    await ctx.send(f"💰 Sold **{card['name']}** for **${sell_price}**")

# ----------------- BATTLE SYSTEM -----------------
class CardActionButton(Button):
    def __init__(self, label, action, game_view):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.action = action
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.game_view.current:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return

        attacker = self.game_view.current
        defender = self.game_view.p2 if attacker == self.game_view.p1 else self.game_view.p1

        attacker_card = self.game_view.cards[attacker.id][self.game_view.active_index[attacker.id]]
        defender_card = self.game_view.cards[defender.id][self.game_view.active_index[defender.id]]

        if self.action == "Attack":
            damage = max(attacker_card['atk'] - defender_card['def']//2, 5)
            defender_card['hp'] = max(defender_card['hp'] - damage, 0)
            desc = f"{attacker.mention}'s **{attacker_card['name']}** attacked {defender.mention}'s **{defender_card['name']}** for {damage} dmg!"


from discord.ui import View, Button
import discord
import random

class RPSButton(Button):
    def __init__(self, choice, game_view):
        super().__init__(label=choice, style=discord.ButtonStyle.primary)
        self.choice = choice
        self.game_view = game_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.game_view.current:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True)
            return
        self.game_view.selections[self.game_view.current.id] = self.choice
        # Switch turn
        if self.game_view.current == self.game_view.p1:
            self.game_view.current = self.game_view.p2
            await interaction.response.edit_message(content=f"🕹️ {self.game_view.current.mention}, it's your turn!", view=self.game_view)
        else:
            # Both players chose, determine winner
            p1_choice = self.game_view.selections[self.game_view.p1.id]
            p2_choice = self.game_view.selections[self.game_view.p2.id]
            result = self.game_view.determine_winner(p1_choice, p2_choice)
            await interaction.response.edit_message(content=result, view=None)
            self.game_view.stop()


class RPSView(View):
    def __init__(self, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=60)
        self.p1 = p1
        self.p2 = p2
        self.current = p1
        self.selections = {}  # user.id -> choice

        # Add buttons
        for choice in ["Rock", "Paper", "Scissors"]:
            self.add_item(RPSButton(choice, self))

    def determine_winner(self, c1, c2):
        if c1 == c2:
            return f"🤝 Tie! Both chose **{c1}**"
        wins = {"Rock":"Scissors","Paper":"Rock","Scissors":"Paper"}
        if wins[c1] == c2:
            return f"🎉 {self.p1.mention} wins! {c1} beats {c2}"
        else:
            return f"🎉 {self.p2.mention} wins! {c2} beats {c1}"


# Command to start the game
@bot.command()
async def rps(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("❌ You cannot play yourself!")
        return
    view = RPSView(ctx.author, opponent)
    await ctx.send(f"🕹️ {ctx.author.mention} vs {opponent.mention} - {ctx.author.mention} goes first!", view=view)

# -----------------------------
# Commands list
# -----------------------------
@bot.command()
async def cmds(ctx):
    embed=discord.Embed(title="🎮 Available Commands",color=discord.Color.green())
    cmds_list=[
        "**Economy:**",
        "?balance - Check your balance",
        "?work - Earn a small random amount",
        "?daily - Claim daily reward",
        "?pay @user amount - Pay another user",
        "?give @user amount - Admin give balance",
        "",
        "**Mini-games:**",
        "?cf <bet> <heads/tails> - Coinflip",
        "?dice <bet> [guess] - Roll dice",
        "?slots <bet> - Slot machine",
        "?roulette <bet> <choice> - Roulette (number or red/black)",
        "?tictactoe @opponent - TicTacToe 1v1",
        "?blackjack @opponent <bet> - Blackjack 1v1",
        "",
        "**Cards & Pets:**",
        "?drawcard - Draw a random card (5 min cooldown)",
        "?mycards - Show your cards",
        "?mypets - Show your pets",
        "?collect - Collect a pet (5 min cooldown)",
        "","?cardbattle @opponent - Challenge another user to a 1v1 card battle using your collected cards",
        "Sincerely, Plat"
    ]
    embed.description="\n".join(cmds_list)
    await ctx.send(embed=embed)

# -----------------------------
# Ready
# -----------------------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# -----------------------------
# Run
# -----------------------------
bot.run(TOKEN)
