import discord
from discord.ext import commands
from discord.ui import Select, View
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
TOKEN = os.getenv('DISCORD_TOKEN') or 'TON_TOKEN_ICI'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

CREDITS_PER_USE = 2
AUTHORIZED_IDS = [1402199337240625193, 1445150036295028787, 1444785390362820853]
BANNER_URL = "https://io.files.catbox.moe/u96y2u.png" # L'image style Xeyes

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

credit_system = load_credits()

# --- INTERFACE XEYES (HUD) ---

class SearchMenu(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="FiveM", description="Recherche base FiveM", emoji="🚗"),
            discord.SelectOption(label="Discord", description="Recherche base Discord", emoji="💬"),
            discord.SelectOption(label="Restorecord", description="Recherche base Restorecord", emoji="🔗"),
            discord.SelectOption(label="GeoIP", description="Localisation d'IP", emoji="🌐"),
            discord.SelectOption(label="Mon Profil", description="Voir mes crédits", emoji="👤"),
        ]
        super().__init__(placeholder="Choisis un outil...", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        val = self.values[0]

        if val == "Mon Profil":
            bal = credit_system.get(user_id, {}).get("balance", 0)
            await interaction.response.send_message(f"👤 **Profil de {interaction.user.name}**\n💰 Crédits : `{bal}`", ephemeral=True)
        elif val == "GeoIP":
             await interaction.response.send_message(f"Utilise la commande `!geoip <ip>`", ephemeral=True)
        else:
            cmd = val.lower() if val != "FiveM" else "search"
            await interaction.response.send_message(f"Utilise la commande `!{cmd} <mot-clé>` pour lancer l'outil **{val}**.", ephemeral=True)

class MainView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SearchMenu())

# --- EVENTS ---

@bot.event
async def on_ready():
    print(f'{Fore.GREEN}{bot.user} est connecté!{Style.RESET_ALL}')
    activity = discord.Streaming(name="discord.gg/xeyes", url="https://twitch.tv/discord")
    await bot.change_presence(status=discord.Status.dnd, activity=activity)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    if bot.user in message.mentions:
        await message.reply('Mon prefix est !')
    await bot.process_commands(message)

# --- COMMANDES ---

@bot.command()
async def panel(ctx):
    """Affiche le nouveau HUD style Xeyes"""
    embed = discord.Embed(
        title="🪐 Xeyes S€archer",
        description=(
            "xEyes — Recherche & infos en un clic.\n"
            "Choisis un outil dans le menu ci-dessous.\n\n"
            "**Accès** — mets `/xeyes` dans ton **statut personnalisé** et reste **en ligne**."
        ),
        color=0x2b2d31
    )
    embed.add_field(name="🟢 Services", value="```yaml\nEn ligne\n```", inline=True)
    embed.add_field(name="🔗 Outils", value="• Advanced\n• FiveM\n• Snusbase\n• Osint+\n• xEyes", inline=True)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="discord.gg/xeyes")
    await ctx.send(embed=embed, view=MainView())

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
    
    embed = discord.Embed(title="Tu a eu tes 10 credits du jour.", color=0x1519F0)
    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/N9_6kcP4wna8swPbcseyLaldZUKz9ZdISGxBcAeP_d0/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1242828852263387136/182acac7db921b0d479e952625bc3edb.webp?format=webp&width=300&height=300")
    await ctx.send(embed=embed)
    save_credits()

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    bal = credit_system.get(user_id, {}).get("balance", 0)
    embed = discord.Embed(title="Vos Credits", description=f"Salut, {ctx.author.mention} \n **Tu as** {bal} **credits.**", color=0x1519F0)
    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/N9_6kcP4wna8swPbcseyLaldZUKz9ZdISGxBcAeP_d0/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/1242828852263387136/182acac7db921b0d479e952625bc3edb.webp?format=webp&width=676&height=676")
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    await panel(ctx) # On renvoie vers le nouveau HUD

@bot.command()
async def addcr(ctx, user: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_IDS:
        return await ctx.send("Désolé, vous n'êtes pas autorisé.")
    user_id = str(user.id)
    if user_id not in credit_system:
        credit_system[user_id] = {"balance": 0, "last_daily": None}
    credit_system[user_id]["balance"] += amount
    await ctx.send(f"{user.mention} à maintenant {credit_system[user_id]['balance']} credits.")
    save_credits()

# --- LOGIQUE DE RECHERCHE ---

async def perform_search(ctx, directory, query):
    user_id = str(ctx.author.id)
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        return await ctx.send("Vous n'avez pas assez de crédits.")
      
    await ctx.send(f'Veuillez patienter...')
    if not os.path.exists(directory):
        return await ctx.send(f"Dossier {directory} manquant.")

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
async def geoip(ctx, ip_address):
    r = requests.get(f"https://ipinfo.io/{ip_address}/json")
    data = r.json()
    embed = discord.Embed(title=f"IP : {ip_address}", color=0x1519F0)
    embed.add_field(name="Pays", value=data.get('country', 'N/A'), inline=True)
    embed.add_field(name="Ville", value=data.get('city', 'N/A'), inline=True)
    embed.add_field(name="Opérateur", value=data.get('org', 'N/A'), inline=False)
    await ctx.author.send(embed=embed)
    await ctx.send(f'Regarde tes dm !')

if __name__ == "__main__":
    bot.run(TOKEN)
