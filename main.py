import discord
from discord.ext import commands
import requests
import json
import os
import datetime
import asyncio
import aiofiles
import io
import colorama
from colorama import Style, Fore

colorama.init()

# --- CONFIGURATION ---
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

CREDITS_PER_USE = 2
AUTHORIZED_IDS = [1402199337240625193, 1445150036295028787, 1444785390362820853]

# --- SYSTEME DE CREDITS ---

def serialize_datetime(obj): 
    if isinstance(obj, datetime.datetime): 
        return obj.isoformat() 
    raise TypeError("Type not serializable")

def load_credits():
    try:
        if os.path.exists('credit_system.json'):
            with open('credit_system.json', 'r') as file:
                data = json.load(file)
                # Conversion des dates string en objets datetime pour les calculs
                for user_id in data:
                    if "last_daily" in data[user_id] and data[user_id]["last_daily"]:
                        data[user_id]["last_daily"] = datetime.datetime.fromisoformat(data[user_id]["last_daily"])
                return data
    except Exception as e:
        print(f"Erreur chargement JSON: {e}")
    return {}

def save_credits():
    try:
        with open('credit_system.json', 'w') as file:
            # On convertit en dictionnaire simple pour le JSON
            json.dump(credit_system, file, default=serialize_datetime, indent=4)
    except Exception as e:
        print(f"Erreur sauvegarde JSON: {e}")

# Initialisation des données
credit_system = load_credits()

# --- EVENTS ---

@bot.event
async def on_ready():
    print(f'{Fore.GREEN}{bot.user} est connecté!{Style.RESET_ALL}')
    activity = discord.Streaming(name=".gg/legionfr", url="https://twitch.tv/discord")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if bot.user in message.mentions:
        await message.reply('Mon prefix est !')
    await bot.process_commands(message)

# --- COMMANDES ---

@bot.command()
async def claim(ctx):
    user_id = str(ctx.author.id)
    now = datetime.datetime.now()

    if user_id in credit_system:
        last_daily = credit_system[user_id].get("last_daily")
        if last_daily and (now - last_daily) < datetime.timedelta(days=1):
            await ctx.send("❌ Vous avez déjà reçu vos crédits quotidiens.")
            return

    # Attribution des crédits
    if user_id not in credit_system:
        credit_system[user_id] = {"balance": 10, "last_daily": now}
    else:
        credit_system[user_id]["balance"] += 10
        credit_system[user_id]["last_daily"] = now

    embed = discord.Embed(title="Crédits récupérés !", description="Tu as reçu tes **10 crédits** du jour.", color=0x1519F0)
    embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/1242828852263387136/182acac7db921b0d479e952625bc3edb.webp")
    await ctx.send(embed=embed)
    save_credits()

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    bal = credit_system.get(user_id, {}).get("balance", 0)
    
    embed = discord.Embed(title="Vos Crédits", description=f"Salut {ctx.author.mention}, tu as **{bal}** crédits.", color=0x1519F0)
    await ctx.send(embed=embed)

@bot.command()
async def addcr(ctx, user: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_IDS:  
        return await ctx.send("Désolé, vous n'êtes pas autorisé.")

    user_id = str(user.id)
    if user_id not in credit_system:
        credit_system[user_id] = {"balance": 0, "last_daily": None}
    
    credit_system[user_id]["balance"] += amount
    save_credits()
    await ctx.send(f"✅ {user.mention} a maintenant **{credit_system[user_id]['balance']}** crédits.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 Liste des Commandes", color=0x1519F0)
    embed.add_field(name="!claim", value="Récupérer tes 10 crédits journaliers", inline=False)
    embed.add_field(name="!balance", value="Voir ton solde", inline=False)
    embed.add_field(name="!search <clé>", value="Recherche FiveM (2 cr)", inline=True)
    embed.add_field(name="!geoip <ip>", value="Infos sur une IP", inline=True)
    embed.add_field(name="!discordd <clé>", value="Recherche Discord", inline=True)
    embed.set_footer(text="Prefix: !")
    await ctx.send(embed=embed)

# --- FONCTION DE RECHERCHE GENERIQUE ---

async def perform_search(ctx, directory, query):
    user_id = str(ctx.author.id)
    
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        return await ctx.send("⚠️ Crédits insuffisants (2 requis).")

    if not os.path.exists(directory):
        return await ctx.send(f"Erreur : Dossier `{directory}` introuvable sur le serveur.")

    await ctx.send(f'🔍 Recherche en cours dans `{directory}`...')
    results = []

    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        try:
            async with aiofiles.open(file_path, mode='r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    if query.lower() in line.lower():
                        results.append(line.strip())
        except Exception as e:
            print(f"Erreur lecture {file}: {e}")

    if results:
        content = "\n".join(results)
        file_data = io.BytesIO(content.encode('utf-8'))
        
        credit_system[user_id]["balance"] -= CREDITS_PER_USE
        save_credits()

        await ctx.author.send(content=f"Résultats pour `{query}` :", file=discord.File(file_data, filename="results.txt"))
        await ctx.send("✅ Résultats envoyés en MP !")
    else:
        await ctx.send(f"❌ Aucune information trouvée pour : `{query}`")

# --- COMMANDES DE RECHERCHE ---

@bot.command()
async def search(ctx, *, query): await perform_search(ctx, "database", query)

@bot.command()
async def discordd(ctx, *, query): await perform_search(ctx, "discordd", query)

@bot.command()
async def fivem_vip(ctx, *, query): await perform_search(ctx, "Fivemdb", query)

@bot.command()
async def restorecord(ctx, *, query): await perform_search(ctx, "restorecord", query)

@bot.command()
async def geoip(ctx, ip_address):
    try:
        r = requests.get(f"https://ipinfo.io/{ip_address}/json")
        data = r.json()
        embed = discord.Embed(title=f"IP Info: {ip_address}", color=0x1519F0)
        embed.add_field(name="Ville/Pays", value=f"{data.get('city')}, {data.get('country')}")
        embed.add_field(name="Org", value=data.get('org', 'N/A'))
        await ctx.author.send(embed=embed)
        await ctx.send("Infos IP envoyées en MP.")
    except:
        await ctx.send("Erreur lors de la récupération de l'IP.")

# --- LANCEMENT ---

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print(f"{Fore.RED}ERREUR : DISCORD_TOKEN manquant dans les variables d'environnement.{Style.RESET_ALL}")
