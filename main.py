import discord
from discord.ext import commands
from discord import ui
import requests
import json
import os
import datetime
import asyncio
import aiofiles
import colorama
from colorama import Style, Fore

colorama.init()

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN') or 'TON_TOKEN_ICI'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

CREDITS_PER_USE = 2
AUTHORIZED_IDS = [1402199337240625193, 1445150036295028787, 1444785390362820853]
BANNER_URL = "https://files.catbox.moe/4za0fc.png"

# --- LOGIQUE DES CREDITS (GARDÉE À L'IDENTIQUE) ---
def serialize_datetime(obj): 
    if isinstance(obj, datetime.datetime): return obj.isoformat() 
    raise TypeError("Type not serializable") 

def load_credits():
    try:
        if os.path.exists('credit_system.json'):
            with open('credit_system.json', 'r') as file:
                data = json.load(file)
                for uid in data:
                    if "last_daily" in data[uid] and isinstance(data[uid]["last_daily"], str):
                        data[uid]["last_daily"] = datetime.datetime.fromisoformat(data[uid]["last_daily"])
                return data
    except: pass
    return {}

def save_credits():
    with open('credit_system.json', 'w') as file:
        json.dump(credit_system, file, default=serialize_datetime)

credit_system = load_credits()

# --- NOUVELLE INTERFACE : FORMULAIRE (MODAL) ---
class AdvancedSearchModal(ui.Modal, title='Recherche avancée Legion'):
    prenom = ui.TextInput(label='Prénom (optionnel)', placeholder='Jean', required=False)
    nom = ui.TextInput(label='Nom (optionnel)', placeholder='Dupont', required=False)
    dob = ui.TextInput(label='Date de naissance (optionnel)', placeholder='01/01/1990', required=False)
    year = ui.TextInput(label='Année de naissance (optionnel)', placeholder='1990', required=False)
    city = ui.TextInput(label='Ville / Code-Postal (optionnel)', placeholder='Paris 75001', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔍 Recherche lancée pour : `{self.prenom} {self.nom}`. (Fonctionnalité en cours de liaison)", ephemeral=True)

# --- NOUVELLE INTERFACE : MENU DÉROULANT ---
class SearchMenu(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Advanced", description="Ouvrir le formulaire Legion", emoji="🚀"),
            discord.SelectOption(label="FiveM", description="Recherche base FiveM", emoji="🚗"),
            discord.SelectOption(label="Discord", description="Recherche base Discord", emoji="💬"),
            discord.SelectOption(label="Restorecord", description="Recherche base Restorecord", emoji="🔗"),
            discord.SelectOption(label="GeoIP", description="Localisation d'IP", emoji="🌐"),
        ]
        super().__init__(placeholder="Choisis un outil...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "Advanced":
            await interaction.response.send_modal(AdvancedSearchModal())
        elif val == "GeoIP":
            await interaction.response.send_message("Utilise `!geoip <ip>`", ephemeral=True)
        else:
            cmd_map = {"FiveM": "search", "Discord": "discordd", "Restorecord": "restorecord"}
            cmd = cmd_map.get(val, val.lower())
            await interaction.response.send_message(f"Utilise la commande `!{cmd} <mot-clé>`", ephemeral=True)

class MainView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SearchMenu())

# --- EVENTS ---
@bot.event
async def on_ready():
    print(f'{Fore.GREEN}Legion Bot connecté !{Style.RESET_ALL}')
    activity = discord.Streaming(name="Legion S€archer", url="https://twitch.tv/discord")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if bot.user in message.mentions:
        await message.reply("Salut — pour ouvrir le **panel**, mets `/legion` dans ton **statut** et reste **en ligne**.", mention_author=False)
    await bot.process_commands(message)

# --- COMMANDES D'INTERFACE ---

@bot.command()
async def panel(ctx):
    """Affiche le nouveau HUD Legion"""
    embed = discord.Embed(
        title="🪐 Legion S€archer",
        description=(
            "Legion — Recherche & infos en un clic.\n"
            "Choisis un outil dans le menu ci-dessous.\n\n"
            "**Accès** — mets `/legion` dans ton **statut personnalisé** et reste **en ligne**."
        ),
        color=0x2b2d31
    )
    embed.add_field(name="🟢 Services", value="```yaml\nEn ligne\n```", inline=True)
    embed.add_field(name="🔗 Outils", value="• Advanced\n• FiveM\n• Discord\n• Restorecord\n• GeoIP", inline=True)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="discord.gg/legion")
    await ctx.send(embed=embed, view=MainView())

@bot.command()
async def help(ctx):
    await panel(ctx)

# --- COMMANDES DE LOGIQUE (TES COMMANDES D'AVANT) ---

async def perform_search(ctx, directory, query):
    user_id = str(ctx.author.id)
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        await ctx.send("Vous n'avez pas assez de crédits.")
        return
      
    await ctx.send(f'Recherche en cours...')
    if not os.path.exists(directory):
        await ctx.send(f"Dossier {directory} manquant.")
        return

    result = []
    for file in os.listdir(directory):
        try:
            async with aiofiles.open(os.path.join(directory, file), mode='r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    if query in line: result.append(line.strip())
        except: continue

    if result:
        async with aiofiles.open('results.txt', 'w', encoding='utf-8') as f:
            await f.write('\n'.join(result))
        with open('results.txt', 'rb') as f:
            await ctx.send(f'Résultats envoyés en DM.')
            await ctx.author.send(file=discord.File(f))
        credit_system[user_id]["balance"] -= CREDITS_PER_USE
        save_credits()
    else:
        await ctx.send(f'Introuvable: {query}')

@bot.command()
async def search(ctx, *, query): await perform_search(ctx, "database", query)

@bot.command()
async def discordd(ctx, *, query): await perform_search(ctx, "discordd", query)

@bot.command()
async def restorecord(ctx, *, query): await perform_search(ctx, "restorecord", query)

@bot.command()
async def fivem_vip(ctx, *, query): await perform_search(ctx, "Fivemdb", query)

@bot.command()
async def geoip(ctx, ip_address):
    r = requests.get(f"https://ipinfo.io/{ip_address}/json")
    data = r.json()
    embed = discord.Embed(title=f"IP : {ip_address}", color=0x1519F0)
    embed.add_field(name="Pays", value=data.get('country', 'N/A'), inline=True)
    embed.add_field(name="Ville", value=data.get('city', 'N/A'), inline=True)
    embed.add_field(name="Opérateur", value=data.get('org', 'N/A'), inline=False)
    await ctx.author.send(embed=embed)
    await ctx.send(f'Regarde tes dm !')

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    bal = credit_system.get(user_id, {}).get("balance", 0)
    await ctx.send(f"💰 Tu as **{bal}** crédits.")

@bot.command()
async def addcr(ctx, user: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_IDS:
        return await ctx.send("Non autorisé.")
    user_id = str(user.id)
    if user_id not in credit_system: credit_system[user_id] = {"balance": 0, "last_daily": None}
    credit_system[user_id]["balance"] += amount
    await ctx.send(f"{user.mention} a maintenant {credit_system[user_id]['balance']} crédits.")
    save_credits()

@bot.command()
async def claim(ctx):
    global credit_system
    now = datetime.datetime.now()
    user_id = str(ctx.author.id)
    if user_id in credit_system and isinstance(credit_system[user_id]["last_daily"], datetime.datetime):
        if (now - credit_system[user_id]["last_daily"]) < datetime.timedelta(days=1):
            await ctx.send("Déjà réclamé aujourd'hui.")
            return
    if user_id not in credit_system: credit_system[user_id] = {"balance": 10, "last_daily": now}
    else:
        credit_system[user_id]["balance"] += 10
        credit_system[user_id]["last_daily"] = now
    await ctx.send("🎁 +10 crédits ajoutés !")
    save_credits()

if __name__ == "__main__":
    bot.run(TOKEN)
