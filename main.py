import discord
from discord.ext import commands
import requests
import json
import os
import re
import pythonping
from pythonping import ping as pinger
import datetime
import tempfile
import chardet
import asyncio
import aiofiles
import pathlib
from discord.ext import tasks
import io
import colorama
from colorama import Style, Fore
colorama.init()

# --- CONFIGURATION DU TOKEN ---
# Remplace 'TON_TOKEN_ICI' par ton vrai token si tu n'utilises pas de variables d'environnement
TOKEN = os.getenv('DISCORD_TOKEN') or 'TON_TOKEN_ICI'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

credit_system_user = {}
CREDITS_PER_USE = 2

# --- LOGIQUE DES CREDITS ---

def serialize_datetime(obj): 
    if isinstance(obj, datetime.datetime): 
        return obj.isoformat() 
    raise TypeError("Type not serializable") 

def load_credits():
    try:
        if os.path.exists('credit_system.json'):
            with open('credit_system.json', 'r') as file:
                data = json.load(file)
                # Conversion des dates pour le calcul du daily
                for uid in data:
                    if "last_daily" in data[uid] and isinstance(data[uid]["last_daily"], str):
                        data[uid]["last_daily"] = datetime.datetime.fromisoformat(data[uid]["last_daily"])
                return data
    except Exception as e:
        print(f"Erreur chargement: {e}")
    return {}

def save_credits():
    with open('credit_system.json', 'w') as file:
        json.dump(credit_system, file, default=serialize_datetime)

# Initialisation correcte
credit_system = load_credits()

# --- EVENTS ---

@bot.event
async def on_ready():
    print(f'{Fore.GREEN}{bot.user} est connecté!{Style.RESET_ALL}')
    activity = discord.Activity(type=discord.ActivityType.streaming, url="https://twitch.tv/discord", name=".gg/legionfr")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        await message.reply('Mon prefix est !') # Correction auto ici pour correspondre au prefix
    await bot.process_commands(message)

# --- COMMANDES (STYLE HUD CONSERVÉ) ---

@bot.command()
async def claim(ctx):
    global credit_system
    now = datetime.datetime.now()
    user_id = str(ctx.author.id)
    
    if user_id in credit_system and isinstance(credit_system[user_id]["last_daily"], datetime.datetime):
        if (now - credit_system[user_id]["last_daily"]) < datetime.timedelta(days=1):
            await ctx.send("Vous avez déjà reçu vos crédits quotidiens.")
            return

    if user_id not in credit_system:
        credit_system[user_id] = {"balance": 10, "last_daily": now}
    else:
        credit_system[user_id]["balance"] += 10
        credit_system[user_id]["last_daily"] = now

    embed = discord.Embed(title="Tu a eu tes 10 credits du jour.", description=f"", color=0x1519F0)
    embed.set_footer(text="searchdb")
    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/N9_6kcP4wna8swPbcseyLaldZUKz9ZdISGxBcAeP_d0/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1242828852263387136/182acac7db921b0d479e952625bc3edb.webp?format=webp&width=300&height=300")
    await ctx.send(embed=embed)
    save_credits()

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Commandes", description="", color=0x1519F0)
    embed.set_footer(text="sousdomain")
    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/N9_6kcP4wna8swPbcseyLaldZUKz9ZdISGxBcAeP_d0/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1242828852263387136/182acac7db921b0d479e952625bc3edb.webp?format=webp&width=300&height=300")
    embed.add_field(name="", value="les paramètres mis entre `<>` sont obligatoires. Si tu as besoin d'aide utilise: !help.", inline=False)
    embed.add_field(name="!search <mot-clé>", value="Rechercher une personnes dans les DB FiveM.", inline=False)
    embed.add_field(name="!restorecord <mot-clé>", value="Rechercher une personnes dans les DB restorecord.", inline=False)
    embed.add_field(name="!discordd <mot-clé>", value="Rechercher une personnes dans les DB discord.", inline=False)
    embed.add_field(name="!nazapi <mot-clé>", value="Rechercher une personnes dans les DB nazapi.", inline=False)
    embed.add_field(name="!geoip <mot-clé>", value="Rechercher une personnes avec son ip .", inline=False)
    embed.add_field(name="!balance", value="Voir son Solde de credits.", inline=False)                               
    embed.add_field(name="!addcr <id> <cr>", value="Ajouter des credits a un Utilisateurs. (Admin Only)", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    bal = credit_system.get(user_id, {}).get("balance", 0)
    embed = discord.Embed(title="Vos Credits", description=f"Salut, {ctx.author.mention} \n **Tu as** {bal} **credits.**", color=0x1519F0)
    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/N9_6kcP4wna8swPbcseyLaldZUKz9ZdISGxBcAeP_d0/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1242828852263387136/182acac7db921b0d479e952625bc3edb.webp?format=webp&width=676&height=676")
    await ctx.send(embed=embed)

@bot.command()
async def addcr(ctx, user: discord.Member, amount: int):
    authorized_ids = [1402199337240625193, 1445150036295028787, 1444785390362820853]
    if ctx.author.id not in authorized_ids:  
        await ctx.send("Désolé, vous n'êtes pas autorisé à ajouter des crédits.")
        return
    user_id = str(user.id)
    if user_id not in credit_system:
        credit_system[user_id] = {"balance": 0, "last_daily": None}
    credit_system[user_id]["balance"] += amount
    await ctx.send(f"{user.mention} à maintenant {credit_system[user_id]['balance']} credits.")
    save_credits()

# --- FONCTION DE RECHERCHE GÉNÉRIQUE (POUR TOUTES TES DBS) ---

async def perform_search(ctx, directory, query):
    user_id = str(ctx.author.id)
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        await ctx.send("Vous n'avez pas assez de crédits pour utiliser cette commande merci de ping un Fondateur pour en obtenir.")
        return
      
    await ctx.send(f'Veuillez patienter pendant que je rassemble les informations...')
    if not os.path.exists(directory):
        await ctx.send(f"Dossier {directory} manquant.")
        return

    result = []
    for file in os.listdir(directory):
        try:
            async with aiofiles.open(os.path.join(directory, file), mode='r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    if query in line:
                        result.append(line.strip())
        except: continue

    if result:
        async with aiofiles.open('results.txt', 'w', encoding='utf-8') as f:
            await f.write('\n'.join(result))
        with open('results.txt', 'rb') as f:
            await ctx.send(f'Les resultats a été envoyée à vos DM.')
            await ctx.author.send(file=discord.File(f))
        credit_system[user_id]["balance"] -= CREDITS_PER_USE
        save_credits()
    else:
        await ctx.send(f'Cette personnes est introuvable: {query}')

# --- ASSIGNATION DES COMMANDES AUX DOSSIERS ---

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
    embed = discord.Embed(title=f"Informations sur l'adresse IP : {ip_address}", color=0x1519F0)
    embed.add_field(name="Ip", value=data.get('ip', 'N/A'), inline=False)
    embed.add_field(name="Pays", value=data.get('country', 'N/A'), inline=True)
    embed.add_field(name="Ville", value=data.get('city', 'N/A'), inline=True)
    embed.add_field(name="Opérateurs", value=data.get('org', 'N/A'), inline=False)
    await ctx.send(f'Regarde tes dm !')
    await ctx.author.send(embed=embed)

# --- LANCEMENT ---
if TOKEN and TOKEN != 'TON_TOKEN_ICI':
    bot.run(TOKEN)
else:
    print(f"{Fore.RED}ERREUR: Token manquant. Modifie la ligne 21.{Style.RESET_ALL}")
