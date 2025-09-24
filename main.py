# bot.py
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import random, os, asyncio, json
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# ---------------- CONFIG ----------------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in .env")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

BALANCES_FILE = os.path.join(DATA_DIR, "balances.json")
CARDS_FILE = os.path.join(DATA_DIR, "cards.json")
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

PREFIX = "?"
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
# remove default help if present
try:
    bot.remove_command("help")
except Exception:
    pass

# ---------------- JSON UTIL (thread-safe) ----------------
file_lock = asyncio.Lock()

def safe_load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        try:
            os.rename(path, path + ".bak")
        except Exception:
            pass
        return {}

async def safe_save(path: str, data: Dict[str, Any]):
    async with file_lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

# load data
balances: Dict[str,int] = safe_load(BALANCES_FILE)
cards_db: Dict[str, List[Dict[str,int]]] = safe_load(CARDS_FILE)
pets_db: Dict[str, List[Dict[str,Any]]] = safe_load(PETS_FILE)

# ---------------- HELPERS ----------------
def get_balance(uid:int) -> int:
    return balances.get(str(uid), 0)

async def add_balance(uid:int, amount:int):
    balances[str(uid)] = get_balance(uid) + amount
    await safe_save(BALANCES_FILE, balances)

def get_cards(uid:int) -> List[Dict[str,int]]:
    return cards_db.get(str(uid), [])

async def add_card(uid:int, card:Dict[str,int]):
    cards_db.setdefault(str(uid), []).append(card)
    await safe_save(CARDS_FILE, cards_db)

async def remove_card_by_obj(uid:int, card:Dict[str,int]) -> bool:
    arr = cards_db.get(str(uid), [])
    try:
        arr.remove(card)
        if arr:
            cards_db[str(uid)] = arr
        else:
            cards_db.pop(str(uid), None)
        await safe_save(CARDS_FILE, cards_db)
        return True
    except ValueError:
        return False

def get_pets(uid:int) -> List[Dict[str,Any]]:
    return pets_db.get(str(uid), [])

async def add_pet(uid:int, pet:Dict[str,Any]):
    pets_db.setdefault(str(uid), []).append(pet)
    await safe_save(PETS_FILE, pets_db)

async def remove_pet_by_index(uid:int, index:int) -> Optional[Dict[str,Any]]:
    arr = pets_db.get(str(uid), [])
    if 0 <= index < len(arr):
        pet = arr.pop(index)
        if arr:
            pets_db[str(uid)] = arr
        else:
            pets_db.pop(str(uid), None)
        await safe_save(PETS_FILE, pets_db)
        return pet
    return None

async def send_embed(dest, title:str, desc:str, color=discord.Color.green()):
    embed = discord.Embed(title=title, description=desc, color=color)
    await dest.send(embed=embed)

# ---------------- GAME COOLDOWNS ----------------
work_cd: Dict[int, float] = {}
daily_cd: Dict[int, float] = {}
card_draw_cd: Dict[int, float] = {}
pet_collect_cd: Dict[int, float] = {}

# ---------------- CARD POOL ----------------
CARD_POOL = [
    {"name":"Fire Elemental","atk":50,"def":20},
    {"name":"Water Spirit","atk":30,"def":40},
    {"name":"Earth Golem","atk":20,"def":50},
    {"name":"Wind Falcon","atk":40,"def":30},
    {"name":"Lightning Dragon","atk":60,"def":10},
    {"name":"Shadow Assassin","atk":55,"def":15},
    {"name":"Holy Knight","atk":35,"def":45},
    {"name":"Ice Wizard","atk":45,"def":30},
    {"name":"Thunder Titan","atk":70,"def":20},
    {"name":"Nature Dryad","atk":25,"def":45},
    {"name":"Fire Phoenix","atk":65,"def":25},
    {"name":"Dark Reaper","atk":60,"def":15},
    {"name":"Crystal Guardian","atk":40,"def":40},
    {"name":"Spirit Archer","atk":33,"def":22},
    {"name":"Stone Titan","atk":48,"def":48},
    {"name":"Swift Panther","atk":42,"def":18},
]

# ---------------- PET POOL (simple) ----------------
PET_POOL = [
    {"name":"Mini Fire Elemental","rarity":"Common","bonus":5},
    {"name":"Water Sprite","rarity":"Common","bonus":5},
    {"name":"Earth Pup","rarity":"Uncommon","bonus":10},
    {"name":"Wind Hawk","rarity":"Uncommon","bonus":10},
    {"name":"Lightning Dragonling","rarity":"Rare","bonus":15},
    {"name":"Mystic Phoenix","rarity":"Epic","bonus":25}
]

# ---------------- ECONOMY COMMANDS ----------------
@bot.command()
async def balance(ctx):
    bal = get_balance(ctx.author.id)
    await send_embed(ctx, "💰 Balance", f"{ctx.author.mention}, your balance is **${bal}**")

@bot.command()
async def work(ctx):
    now = asyncio.get_event_loop().time()
    uid = ctx.author.id
    if uid in work_cd and now - work_cd[uid] < 30:
        await send_embed(ctx, "⏳ Work Cooldown", f"Wait {int(30-(now-work_cd[uid]))}s", discord.Color.orange()); return
    earn = random.randint(50,150)
    await add_balance(uid, earn)
    work_cd[uid] = now
    await send_embed(ctx, "👷 Work", f"You earned **${earn}**!")

@bot.command()
async def daily(ctx):
    now = asyncio.get_event_loop().time()
    uid = ctx.author.id
    if uid in daily_cd and now - daily_cd[uid] < 86400:
        rem_h = int((86400-(now-daily_cd[uid]))/3600)
        await send_embed(ctx, "⏳ Daily Cooldown", f"Wait {rem_h}h", discord.Color.orange()); return
    reward = 500
    await add_balance(uid, reward)
    daily_cd[uid] = now
    await send_embed(ctx, "📅 Daily", f"You claimed your daily reward of **${reward}**!")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    bal = get_balance(ctx.author.id)
    if amount <= 0 or amount > bal:
        await send_embed(ctx, "❌ Error", "Invalid amount", discord.Color.red()); return
    await add_balance(ctx.author.id, -amount)
    await add_balance(member.id, amount)
    await send_embed(ctx, "💸 Payment", f"{ctx.author.mention} paid **${amount}** to {member.mention}")

@bot.command()
@commands.has_guild_permissions(manage_guild=True)
async def give(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await send_embed(ctx, "❌ Error", "Amount must be >0", discord.Color.red()); return
    await add_balance(member.id, amount)
    await send_embed(ctx, "💰 Admin Give", f"{ctx.author.mention} gave **${amount}** to {member.mention}")

# ---------------- CASINO GAMES ----------------
@bot.command()
async def cf(ctx, bet: int, choice: str):
    bal = get_balance(ctx.author.id)
    if bet <= 0 or bet > bal:
        await send_embed(ctx, "❌ Error", "Invalid bet", discord.Color.red()); return
    choice = choice.lower()
    if choice not in ("heads","tails"):
        await send_embed(ctx, "❌ Error", "Choose heads or tails", discord.Color.red()); return
    result = random.choice(["heads","tails"])
    if choice == result:
        await add_balance(ctx.author.id, bet)
        await send_embed(ctx, "🪙 Coinflip", f"You won! Coin: **{result}**\n+${bet}", discord.Color.green())
    else:
        await add_balance(ctx.author.id, -bet)
        await send_embed(ctx, "🪙 Coinflip", f"You lost! Coin: **{result}**\n-${bet}", discord.Color.red())

@bot.command()
async def dice(ctx, bet: int, guess: Optional[int] = None):
    bal = get_balance(ctx.author.id)
    if bet <= 0 or bet > bal:
        await send_embed(ctx, "❌ Error", "Invalid bet", discord.Color.red()); return
    roll = random.randint(1,6)
    if guess is None:
        await send_embed(ctx, "🎲 Dice", f"Dice rolled **{roll}**"); return
    if guess == roll:
        winnings = bet * 6
        await add_balance(ctx.author.id, winnings)
        await send_embed(ctx, "🎲 Dice", f"You guessed **{guess}**, dice rolled **{roll}**\nYou won **${winnings}**", discord.Color.green())
    else:
        await add_balance(ctx.author.id, -bet)
        await send_embed(ctx, "🎲 Dice", f"You guessed **{guess}**, dice rolled **{roll}**\nYou lost **${bet}**", discord.Color.red())

@bot.command()
async def slots(ctx, bet: int):
    bal = get_balance(ctx.author.id)
    if bet <= 0 or bet > bal:
        await send_embed(ctx, "❌ Error", "Invalid bet", discord.Color.red()); return
    symbols = ["🍒","🍋","🍇","🍉","⭐","7️⃣"]
    res = [random.choice(symbols) for _ in range(3)]
    # payout rules: 3 same = 5x, 2 same = 1.5x (rounded down), else lose
    if len(set(res)) == 1:
        winnings = bet * 5
        await add_balance(ctx.author.id, winnings)
        msg = f"🎉 JACKPOT! You won **${winnings}**"
        color = discord.Color.green()
    elif len(set(res)) == 2:
        winnings = int(bet * 1.5)
        await add_balance(ctx.author.id, winnings)
        msg = f"✨ Two match! Won **${winnings}**"
        color = discord.Color.gold()
    else:
        await add_balance(ctx.author.id, -bet)
        msg = f"❌ No match! Lost **${bet}**"
        color = discord.Color.red()
    await send_embed(ctx, "🎰 Slots", f"{' | '.join(res)}\n{msg}", color)

@bot.command()
async def roulette(ctx, bet: int, choice: str):
    bal = get_balance(ctx.author.id)
    if bet <= 0 or bet > bal:
        await send_embed(ctx, "❌ Error", "Invalid bet", discord.Color.red()); return
    result = random.randint(0,36)
    win = False
    payout = 0
    if choice.isdigit() and int(choice) == result:
        win = True; payout = bet * 35
    elif choice.lower() in ("red","black"):
        color_res = "red" if result % 2 == 0 else "black"
        if choice.lower() == color_res:
            win = True; payout = bet * 2
    if win:
        await add_balance(ctx.author.id, payout)
        await send_embed(ctx, "🎡 Roulette", f"Result: **{result}**\nYou won **${payout}**", discord.Color.green())
    else:
        await add_balance(ctx.author.id, -bet)
        await send_embed(ctx, "🎡 Roulette", f"Result: **{result}**\nYou lost **${bet}**", discord.Color.red())

# ---------------- TIC TAC TOE ----------------
class TicTacToeButton(Button):
    def __init__(self,x,y):
        super().__init__(style=discord.ButtonStyle.secondary,label="\u200b",row=y)
        self.x=x; self.y=y
    async def callback(self,interaction):
        view: TicTacToeView = self.view
        if interaction.user != view.current:
            await interaction.response.send_message("❌ Not your turn", ephemeral=True); return
        mark = "X" if view.current == view.p1 else "O"
        self.label = mark; self.disabled = True
        view.board[self.y][self.x] = mark
        if view.check_win(mark):
            for child in view.children:
                child.disabled = True
            await interaction.response.edit_message(content=f"🎉 {interaction.user.mention} wins!", view=view)
            view.stop()
            return
        view.switch_player()
        await interaction.response.edit_message(view=view)

class TicTacToeView(View):
    def __init__(self,p1,p2):
        super().__init__(timeout=180)
        self.p1=p1; self.p2=p2; self.current=p1
        self.board=[[None]*3 for _ in range(3)]
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x,y))
    def switch_player(self):
        self.current = self.p2 if self.current == self.p1 else self.p1
    def check_win(self,mark):
        b=self.board
        for row in b:
            if all(c==mark for c in row): return True
        for col in range(3):
            if all(b[r][col]==mark for r in range(3)): return True
        if b[0][0]==b[1][1]==b[2][2]==mark: return True
        if b[0][2]==b[1][1]==b[2][0]==mark: return True
        return False

@bot.command()
async def tictactoe(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("❌ Cannot play yourself"); return
    view = TicTacToeView(ctx.author, opponent)
    await ctx.send(f"🎮 TicTacToe: {ctx.author.mention} vs {opponent.mention}", view=view)

# ---------------- BLACKJACK 1v1 ----------------
class Blackjack1v1(View):
    def __init__(self, ctx, p1, p2, bet):
        super().__init__(timeout=120)
        self.ctx=ctx; self.p1=p1; self.p2=p2; self.bet=bet; self.current=p1
        self.deck=[i for i in range(1,12)]*4; random.shuffle(self.deck)
        self.hands={p1.id:[self.deck.pop(),self.deck.pop()], p2.id:[self.deck.pop(),self.deck.pop()]}
        self.msg=None
        self.hit_btn=Button(label="Hit", style=discord.ButtonStyle.success)
        self.stand_btn=Button(label="Stand", style=discord.ButtonStyle.danger)
        self.hit_btn.callback=self.hit; self.stand_btn.callback=self.stand
        self.add_item(self.hit_btn); self.add_item(self.stand_btn)
    async def send_hands(self):
        embed=discord.Embed(title="🃏 Blackjack 1v1", color=discord.Color.green())
        for player in (self.p1, self.p2):
            embed.add_field(name=player.display_name, value=f"{self.hands[player.id]} = {sum(self.hands[player.id])}", inline=False)
        embed.set_footer(text=f"Turn: {self.current.display_name}")
        if self.msg:
            await self.msg.edit(embed=embed, view=self)
        else:
            self.msg = await self.ctx.send(embed=embed, view=self)
    async def switch_turn(self):
        self.current = self.p2 if self.current==self.p1 else self.p1
        await self.send_hands()
    async def hit(self, interaction):
        if interaction.user != self.current:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True); return
        self.hands[self.current.id].append(self.deck.pop())
        total = sum(self.hands[self.current.id])
        if total > 21:
            await add_balance(self.current.id, -self.bet)
            await interaction.response.edit_message(content=f"❌ {self.current.display_name} busted! Lost ${self.bet}", view=None)
            self.stop(); return
        await interaction.response.defer(); await self.send_hands()
    async def stand(self, interaction):
        if interaction.user != self.current:
            await interaction.response.send_message("❌ Not your turn!", ephemeral=True); return
        if self.current == self.p1:
            await self.switch_turn(); await interaction.response.defer(); return
        # both stood, evaluate
        p1_total = sum(self.hands[self.p1.id]); p2_total = sum(self.hands[self.p2.id])
        if p1_total>21 and p2_total>21:
            result="🤝 Both busted! No one wins."
        elif p1_total>21:
            await add_balance(self.p2.id, self.bet); await add_balance(self.p1.id, -self.bet)
            result=f"🎉 {self.p2.display_name} wins! {self.p1.display_name} busted."
        elif p2_total>21:
            await add_balance(self.p1.id, self.bet); await add_balance(self.p2.id, -self.bet)
            result=f"🎉 {self.p1.display_name} wins! {self.p2.display_name} busted."
        elif p1_total>p2_total:
            await add_balance(self.p1.id, self.bet); await add_balance(self.p2.id, -self.bet)
            result=f"🎉 {self.p1.display_name} wins!"
        elif p2_total>p1_total:
            await add_balance(self.p2.id, self.bet); await add_balance(self.p1.id, -self.bet)
            result=f"🎉 {self.p2.display_name} wins!"
        else:
            result="🤝 It's a tie!"
        await interaction.response.edit_message(content=result, view=None)
        self.stop()

@bot.command()
async def blackjack(ctx, opponent: discord.Member, bet: int):
    if opponent == ctx.author:
        await ctx.send("❌ You cannot play yourself!"); return
    if bet <= 0:
        await ctx.send("❌ Bet must be >0"); return
    if get_balance(ctx.author.id) < bet or get_balance(opponent.id) < bet:
        await ctx.send("❌ Both players must have enough balance!"); return
    view = Blackjack1v1(ctx, ctx.author, opponent, bet)
    await view.send_hands()

# ---------------- RPS ----------------
class RPSButton(Button):
    def __init__(self, label, view_obj):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.choice = label
        self.view_obj = view_obj
    async def callback(self, interaction):
        gv: RPSView = self.view
        if interaction.user not in (gv.p1, gv.p2):
            await interaction.response.send_message("❌ Not part of this game", ephemeral=True); return
        if interaction.user.id in gv.selections:
            await interaction.response.send_message("❌ You already chose", ephemeral=True); return
        gv.selections[interaction.user.id] = self.choice
        await interaction.response.send_message(f"You chose **{self.choice}**", ephemeral=True)
        if len(gv.selections) == 2:
            p1_choice = gv.selections[gv.p1.id]; p2_choice = gv.selections[gv.p2.id]
            wins = {"Rock":"Scissors","Paper":"Rock","Scissors":"Paper"}
            if p1_choice == p2_choice:
                res = f"🤝 Tie! Both chose **{p1_choice}**"
            elif wins[p1_choice] == p2_choice:
                res = f"🎉 {gv.p1.mention} wins! {p1_choice} beats {p2_choice}"
            else:
                res = f"🎉 {gv.p2.mention} wins! {p2_choice} beats {p1_choice}"
            await gv.msg.edit(content=res, view=None)
            gv.stop()

class RPSView(View):
    def __init__(self, p1, p2):
        super().__init__(timeout=60)
        self.p1 = p1; self.p2 = p2; self.selections = {}; self.msg = None
        for choice in ["Rock","Paper","Scissors"]:
            self.add_item(RPSButton(choice, self))

@bot.command()
async def rps(ctx, opponent: discord.Member):
    if opponent == ctx.author:
        await ctx.send("❌ You cannot play yourself!"); return
    view = RPSView(ctx.author, opponent)
    msg = await ctx.send(f"🕹️ {ctx.author.mention} vs {opponent.mention} — pick a choice", view=view)
    view.msg = msg

# ---------------- CARD SYSTEM (draw/mycards/sell) ----------------
@bot.command()
async def drawcard(ctx):
    now = asyncio.get_event_loop().time()
    uid = ctx.author.id
    if uid in card_draw_cd and now - card_draw_cd[uid] < 300:
        rem = int(300 - (now - card_draw_cd[uid])); await ctx.send(f"⏳ Wait {rem//60}m {rem%60}s to draw again"); return
    card_template = random.choice(CARD_POOL)
    # create owned card instance with hp and temp_def
    owned = {"name": card_template["name"], "atk": card_template["atk"], "def": card_template["def"], "hp": random.randint(40,80), "temp_def": 0}
    await add_card(uid, owned)
    card_draw_cd[uid] = now
    await send_embed(ctx, "🃏 Card Drawn!", f"You drew **{owned['name']}**\nATK: {owned['atk']} DEF: {owned['def']} HP: {owned['hp']}", discord.Color.purple())

@bot.command()
async def mycards(ctx):
    arr = get_cards(ctx.author.id)
    if not arr:
        await ctx.send("❌ You have no cards. Use `?drawcard` to get one."); return
    lines = [f"{i+1}. {c['name']} — ATK:{c['atk']} DEF:{c['def']} HP:{c.get('hp','?')}" for i,c in enumerate(arr)]
    await send_embed(ctx, f"{ctx.author.display_name}'s Cards", "\n".join(lines), discord.Color.blue())

@bot.command()
async def sellcard(ctx, *, cardname: str):
    arr = get_cards(ctx.author.id)
    card = next((c for c in arr if c["name"].lower() == cardname.lower()), None)
    if not card:
        await ctx.send(f"❌ You don't own a card named `{cardname}`"); return
    # price formula: half of (atk + def) + small hp factor
    sell_price = (card["atk"] + card["def"]) // 2 + card.get("hp", 0)//20
    success = await remove_card_by_obj(ctx.author.id, card)
    if not success:
        await ctx.send("❌ Could not remove card (concurrency). Try again."); return
    await add_balance(ctx.author.id, sell_price)
    await send_embed(ctx, "💰 Card Sold", f"You sold **{card['name']}** for **${sell_price}**.", discord.Color.gold())

# ---------------- PETS (simple collect/mypets/release) ----------------
@bot.command()
async def collect(ctx):
    uid = ctx.author.id
    now = asyncio.get_event_loop().time()
    if uid in pet_collect_cd and now - pet_collect_cd[uid] < 300:
        rem = int(300 - (now - pet_collect_cd[uid])); await ctx.send(f"⏳ Wait {rem//60}m {rem%60}s to collect again"); return
    pet = random.choice(PET_POOL)
    await add_pet(uid, pet)
    pet_collect_cd[uid] = now
    await send_embed(ctx, "🎉 Pet Collected", f"You got **{pet['name']}** ({pet['rarity']}) — Bonus: {pet['bonus']}", discord.Color.orange())

@bot.command()
async def mypets(ctx):
    p = get_pets(ctx.author.id)
    if not p:
        await ctx.send("❌ You have no pets."); return
    lines = [f"{i+1}. {pet['name']} ({pet['rarity']}) Bonus:{pet['bonus']}" for i,pet in enumerate(p)]
    await send_embed(ctx, f"{ctx.author.display_name}'s Pets", "\n".join(lines), discord.Color.orange())

@bot.command()
async def release(ctx, index: int):
    pet = await remove_pet_by_index(ctx.author.id, index-1)
    if not pet:
        await ctx.send("❌ Invalid index"); return
    await send_embed(ctx, "Released", f"You released **{pet['name']}**", discord.Color.green())

# ---------------- ADVANCED CARD BATTLE ----------------
# A full implementation that shows all cards, lets the acting player choose which owned card to use,
# choose action (Attack or Defend), then choose target (if Attack). Temporary defense applied for next incoming hit.

class SelectCardButton(Button):
    def __init__(self, idx:int):
        super().__init__(label=str(idx+1), style=discord.ButtonStyle.secondary)
        self.idx = idx
    async def callback(self, interaction):
        view: AdvancedBattleView = self.view
        if interaction.user != view.current:
            await interaction.response.send_message("❌ Not your turn.", ephemeral=True); return
        # can't select a dead card
        card = view.cards[view.current.id][self.idx]
        if card["hp"] <= 0:
            await interaction.response.send_message("❌ That card is defeated.", ephemeral=True); return
        view.selected_attacker_idx = self.idx
        await view.show_action_stage(interaction)

class ActionButton(Button):
    def __init__(self, action:str):
        super().__init__(label=action, style=discord.ButtonStyle.primary)
        self.action = action
    async def callback(self, interaction):
        view: AdvancedBattleView = self.view
        if interaction.user != view.current:
            await interaction.response.send_message("❌ Not your turn.", ephemeral=True); return
        view.selected_action = self.action
        if self.action == "Defend":
            # apply temp_def to the selected attacker card
            attacker_card = view.cards[view.current.id][view.selected_attacker_idx]
            attacker_card["temp_def"] = attacker_card.get("temp_def", 0) + view.defend_bonus
            view.log.append(f"🛡️ {view.current.display_name}'s **{attacker_card['name']}** defends (+{view.defend_bonus} DEF for next hit).")
            await view.end_turn(interaction)
        else:
            await view.show_target_stage(interaction)

class TargetButton(Button):
    def __init__(self, idx:int):
        super().__init__(label=str(idx+1), style=discord.ButtonStyle.danger)
        self.idx = idx
    async def callback(self, interaction):
        view: AdvancedBattleView = self.view
        if interaction.user != view.current:
            await interaction.response.send_message("❌ Not your turn.", ephemeral=True); return
        attacker = view.current
        defender = view.p2 if attacker == view.p1 else view.p1
        atk_card = view.cards[attacker.id][view.selected_attacker_idx]
        def_card = view.cards[defender.id][self.idx]
        if def_card["hp"] <= 0:
            await interaction.response.send_message("❌ Target is already defeated.", ephemeral=True); return
        total_def = def_card.get("def", 0) + def_card.get("temp_def", 0)
        damage = max(atk_card.get("atk", 0) - total_def, 0)
        def_card["hp"] = max(def_card["hp"] - damage, 0)
        # consume temp_def
        def_card["temp_def"] = 0
        view.log.append(f"💥 {attacker.display_name}'s **{atk_card['name']}** attacked {defender.display_name}'s **{def_card['name']}** for **{damage}** damage.")
        if def_card["hp"] <= 0:
            view.log.append(f"❌ {defender.display_name}'s **{def_card['name']}** was defeated!")
        await view.end_turn(interaction)

class AdvancedBattleView(View):
    def __init__(self, ctx, p1:discord.Member, p2:discord.Member, cards_each:int=3):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.p1 = p1; self.p2 = p2
        self.cards_each = cards_each
        self.current = p1
        self.defend_bonus = 8
        self.log: List[str] = []
        # load copies of cards (don't mutate stored user cards)
        self.cards: Dict[int, List[Dict[str,int]]] = {}
        for player in (p1, p2):
            owned = [dict(c) for c in get_cards(player.id)]
            # ensure hp/temp_def exist
            for c in owned:
                c.setdefault("hp", random.randint(40,80))
                c.setdefault("temp_def", 0)
            # if not enough, fill from pool
            while len(owned) < cards_each:
                template = random.choice(CARD_POOL)
                owned.append({"name": template["name"], "atk": template["atk"], "def": template["def"], "hp": random.randint(40,80), "temp_def": 0})
            self.cards[player.id] = owned[:cards_each]
        self.stage = "select_attacker"
        self.selected_attacker_idx: Optional[int] = None
        self.selected_action: Optional[str] = None
        self.msg: Optional[discord.Message] = None

    def create_embed(self, header=""):
        embed = discord.Embed(title="⚔️ Card Battle", description=header or "Battle ongoing", color=discord.Color.blurple())
        for player in (self.p1, self.p2):
            lines = []
            for i,c in enumerate(self.cards[player.id]):
                alive = "🟢" if c["hp"] > 0 else "❌"
                lines.append(f"{i+1}. {alive} **{c['name']}** — HP:{c['hp']} | ATK:{c['atk']} | DEF:{c['def']} (+{c.get('temp_def',0)})")
            embed.add_field(name=player.display_name, value="\n".join(lines), inline=False)
        if self.log:
            embed.add_field(name="Battle Log (recent)", value="\n".join(self.log[-6:]), inline=False)
        embed.set_footer(text=f"Turn: {self.current.display_name} | Stage: {self.stage}")
        return embed

    async def start(self):
        self.clear_items()
        self.stage = "select_attacker"
        # create select buttons for current player's alive cards
        for idx, c in enumerate(self.cards[self.current.id]):
            btn = SelectCardButton(idx)
            btn.disabled = (c["hp"] <= 0)
            btn.label = f"{idx+1}. {c['name']}" if c["hp"]>0 else f"{idx+1}. (dead)"
            self.add_item(btn)
        self.msg = await self.ctx.send(embed=self.create_embed(f"🎮 {self.p1.mention} vs {self.p2.mention} — {self.p1.mention} starts. Choose a card."), view=self)

    async def show_action_stage(self, interaction):
        self.stage = "select_action"
        self.clear_items()
        self.add_item(ActionButton("Attack"))
        self.add_item(ActionButton("Defend"))
        embed = self.create_embed(f"{self.current.mention} selected **{self.cards[self.current.id][self.selected_attacker_idx]['name']}** — choose action.")
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_target_stage(self, interaction):
        self.stage = "select_target"
        self.clear_items()
        opponent = self.p2 if self.current == self.p1 else self.p1
        for idx, c in enumerate(self.cards[opponent.id]):
            btn = TargetButton(idx)
            btn.disabled = (c["hp"] <= 0)
            btn.label = f"{idx+1}. {c['name']}" if c["hp"]>0 else f"{idx+1}. (dead)"
            self.add_item(btn)
        embed = self.create_embed(f"{self.current.mention} chose Attack with **{self.cards[self.current.id][self.selected_attacker_idx]['name']}**. Pick a target.")
        await interaction.response.edit_message(embed=embed, view=self)

    async def end_turn(self, interaction):
        # check victory
        p1_alive = any(c["hp"]>0 for c in self.cards[self.p1.id])
        p2_alive = any(c["hp"]>0 for c in self.cards[self.p2.id])
        if not p1_alive or not p2_alive:
            winner = self.p1 if p1_alive else self.p2
            loser = self.p2 if winner == self.p1 else self.p1
            await add_balance(winner.id, 200)
            await add_balance(loser.id, -100)
            embed = self.create_embed(f"🏆 {winner.display_name} wins the battle!")
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            return
        # switch
        self.current = self.p2 if self.current == self.p1 else self.p1
        # reset stage
        self.stage = "select_attacker"
        self.selected_attacker_idx = None
        self.selected_action = None
        # rebuild attacker selection
        self.clear_items()
        for idx, c in enumerate(self.cards[self.current.id]):
            btn = SelectCardButton(idx)
            btn.disabled = (c["hp"] <= 0)
            btn.label = f"{idx+1}. {c['name']}" if c["hp"]>0 else f"{idx+1}. (dead)"
            self.add_item(btn)
        embed = self.create_embed(f"Turn: {self.current.mention}. Choose a card to act with.")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command()
@commands.has_permissions(manage_guild=True)
async def remove(ctx, user: discord.Member, amount: int):
    if amount <= 0:
        await send_embed(ctx, "❌ Error", "Amount must be >0", discord.Color.red())
        return
    bal = get_balance(user.id)
    if amount > bal:
        amount = bal  # prevent negative balance
    add_balance(user.id, -amount)
    await send_embed(ctx, "💸 Admin Remove", f"{ctx.author.mention} removed **${amount}** from {user.mention}")

@bot.command()
async def leaderboard(ctx, top:int=10):
    """Show top users by balance."""
    if not balances:
        await ctx.send("No data available.")
        return

    # Sort balances descending
    sorted_bal = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:top]

    desc = ""
    for i, (user_id, bal) in enumerate(sorted_bal, start=1):
        user = ctx.guild.get_member(int(user_id))
        if user:
            desc += f"**{i}. {user.display_name}** - ${bal}\n"
        else:
            desc += f"**{i}. Unknown User ({user_id})** - ${bal}\n"

    embed = discord.Embed(title=f"💰 Top {top} Balances", description=desc, color=discord.Color.gold())
    await ctx.send(embed=embed)

# command to start a card battle
@bot.command()
async def cardbattle(ctx, opponent: discord.Member):
    if opponent.bot:
        await ctx.send("❌ Can't battle a bot."); return
    if opponent == ctx.author:
        await ctx.send("❌ You cannot battle yourself."); return
    p1_cards = get_cards(ctx.author.id)
    p2_cards = get_cards(opponent.id)
    if not p1_cards and not p2_cards:
        await ctx.send("❌ Neither player has cards. Draw some with ?drawcard."); return
    view = AdvancedBattleView(ctx, ctx.author, opponent, cards_each=3)
    await view.start()

# ---------------- COMMANDS LIST ----------------
@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🎮 Available Commands", color=discord.Color.green())
    cmds_list = [
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
        "?rps @opponent - Rock Paper Scissors PvP",
        "",
        "**Cards & Pets:**",
        "?drawcard - Draw a random card (5 min cooldown)",
        "?mycards - Show your cards",
        "?sellcard <cardname> - Sell a card for money",
        "?mypets - Show your pets",
        "?collect - Collect a pet (5 min cooldown)",
        "?cardbattle @opponent - Challenge another user to a 1v1 card battle using your collected cards",
        "",
        "Sincerely, Plat"
    ]
    embed.description = "\n".join(cmds_list)
    await ctx.send(embed=embed)

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ---------------- RUN ----------------
bot.run(TOKEN)
