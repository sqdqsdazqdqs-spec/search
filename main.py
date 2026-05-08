import discord
from discord.ext import commands
from discord import ui
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
intents.presences = True # IMPORTANT : Requis pour lire les statuts
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# --- VARIABLES ET IDS ---
AUTHORIZED_IDS = [1402199337240625193, 1445150036295028787, 1444785390362820853]
BANNER_URL = "https://files.catbox.moe/4za0fc.png"
CREDITS_PER_USE = 2
REQUIRED_STATUS = "/legionfr"

# Configuration API Snusbase
SNUSBASE_AUTH = 'sbyjthkoft4yaimbwcjqpmxs8huovd'
SNUSBASE_API_URL = 'https://api-experimental.snusbase.com/data/search'

# --- LOGIQUE DE VÉRIFICATION DU STATUT ---

async def check_legion_status(interaction: discord.Interaction):
    """Vérifie si l'utilisateur a le statut requis."""
    user = interaction.guild.get_member(interaction.user.id)
    has_status = False
    
    if user and user.activities:
        for activity in user.activities:
            if isinstance(activity, discord.CustomActivity):
                if activity.name and REQUIRED_STATUS in activity.name:
                    has_status = True
                    break
    
    if not has_status:
        embed = discord.Embed(
            title="❌ Accès Refusé",
            description=f"Vous devez avoir `{REQUIRED_STATUS}` dans votre statut Discord pour utiliser Legion.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return True

# --- LOGIQUE DES CREDITS ---

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

# --- RECHERCHE LOCALE ---

async def perform_search_logic(interaction, directory, query):
    user_id = str(interaction.user.id)
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        return await interaction.followup.send("❌ Vous n'avez pas assez de crédits.", ephemeral=True)
      
    if not os.path.exists(directory):
        return await interaction.followup.send(f"❌ Dossier `{directory}` manquant sur le VPS.", ephemeral=True)

    results = []
    for file in os.listdir(directory):
        try:
            async with aiofiles.open(os.path.join(directory, file), mode='r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    if query.lower() in line.lower():
                        results.append(line.strip())
        except: continue

    if results:
        content = '\n'.join(results)
        file_data = io.BytesIO(content.encode('utf-8'))
        try:
            await interaction.user.send(content=f"📂 **Résultats Legion**\nCible : `{query}`", file=discord.File(file_data, "results.txt"))
            credit_system[user_id]["balance"] -= CREDITS_PER_USE
            save_credits()
            await interaction.followup.send("✅ Les résultats ont été envoyés dans tes messages privés.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Impossible de t'envoyer tes DM. Ouvre tes messages privés.", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Aucune information trouvée pour : `{query}`", ephemeral=True)

# --- RECHERCHE API SNUSBASE ---

async def perform_snusbase_api_search(interaction, search_type, query):
    user_id = str(interaction.user.id)
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        return await interaction.followup.send("❌ Vous n'avez pas assez de crédits.", ephemeral=True)

    type_map = {
        "Email": "email", "Pseudo / username": "username", "Adresse IP": "lastip",
        "Mot de passe": "password", "Hash": "hash", "Nom": "name",
        "Domaine": "domain", "Détection auto": "email"
    }
    
    api_type = type_map.get(search_type, "email")
    headers = {'auth': SNUSBASE_AUTH, 'Content-Type': 'application/json'}
    body = {'terms': [query], 'types': [api_type], 'wildcard': False}

    try:
        response = requests.post(SNUSBASE_API_URL, headers=headers, json=body)
        if response.status_code == 200:
            data = response.json()
            if data.get("results") and any(data["results"].values()):
                file_data = io.BytesIO(json.dumps(data, indent=2).encode('utf-8'))
                await interaction.user.send(
                    content=f"🔑 **Résultats Snusbase**\n**Type**: `{search_type}`\n**Cible**: `{query}`", 
                    file=discord.File(file_data, "snusbase_results.txt")
                )
                credit_system[user_id]["balance"] -= CREDITS_PER_USE
                save_credits()
                await interaction.followup.send("✅ Résultats Snusbase envoyés en DM.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Aucun résultat trouvé sur Snusbase.", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Erreur API Snusbase.", ephemeral=True)
    except:
        await interaction.followup.send("❌ Erreur de connexion API.", ephemeral=True)

# --- INTERFACES : MODALS ---

class AdvancedSearchModal(ui.Modal, title='Recherche avancée'):
    prenom = ui.TextInput(label='Prénom', placeholder='Jean', required=False)
    nom = ui.TextInput(label='Nom', placeholder='Dupont', required=False)
    city = ui.TextInput(label='Ville / Code-Postal', placeholder='Paris 75001', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = f"{self.prenom.value} {self.nom.value} {self.city.value}".strip()
        await perform_search_logic(interaction, "database", query)

class FiveMSearchModal(ui.Modal):
    def __init__(self, title, label, placeholder, directory="Fivemdb"):
        super().__init__(title=title)
        self.directory = directory
        self.input = ui.TextInput(label=label, placeholder=placeholder, required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await perform_search_logic(interaction, self.directory, self.input.value)

class SnusbaseSearchModal(ui.Modal):
    def __init__(self, title, search_type):
        super().__init__(title=title)
        self.search_type = search_type
        self.input = ui.TextInput(label=f"Valeur ({search_type})", placeholder="Entrez la recherche ici...", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await perform_snusbase_api_search(interaction, self.search_type, self.input.value)

# --- INTERFACES : VIEWS ---

class AdvancedMenuView(ui.View):
    @ui.button(label="Lancer la recherche", style=discord.ButtonStyle.grey, emoji="🚀")
    async def launch_search(self, interaction: discord.Interaction, button: ui.Button):
        if await check_legion_status(interaction):
            await interaction.response.send_modal(AdvancedSearchModal())

class SnusbaseMenuView(ui.View):
    @ui.select(placeholder="Sélectionne un type de recherche...", options=[
        discord.SelectOption(label="Détection auto", emoji="➡️"),
        discord.SelectOption(label="Email", emoji="📧"),
        discord.SelectOption(label="Pseudo / username", emoji="👤"),
        discord.SelectOption(label="Adresse IP", emoji="🌐"),
        discord.SelectOption(label="Mot de passe", emoji="🔒"),
        discord.SelectOption(label="Hash", emoji="🔑")
    ])
    async def callback(self, interaction, select):
        if await check_legion_status(interaction):
            await interaction.response.send_modal(SnusbaseSearchModal(f"Snusbase : {select.values[0]}", select.values[0]))

class FiveMMenuView(ui.View):
    @ui.select(placeholder="→ Choisis un type", options=[
        discord.SelectOption(label="Username", emoji="👤"),
        discord.SelectOption(label="Steam", emoji="🎮"),
        discord.SelectOption(label="Discord", emoji="💬"),
        discord.SelectOption(label="License", emoji="🔑"),
        discord.SelectOption(label="Adresse IP", emoji="🌐")
    ])
    async def callback(self, interaction, select):
        if await check_legion_status(interaction):
            configs = {
                "Username": ("FiveM : Username", "Pseudo", "Gablidotse"),
                "Steam": ("FiveM : Steam", "Steam Hex", "1100001..."),
                "Discord": ("FiveM : Discord", "Discord ID", "97066..."),
                "License": ("FiveM : License", "License Hex", "511b..."),
                "Adresse IP": ("FiveM : IP", "IP", "1.1.1.1")
            }
            t, l, p = configs[select.values[0]]
            await interaction.response.send_modal(FiveMSearchModal(t, l, p))

class MainMenuSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Advanced", description="Recherche complète", emoji="🚀"),
            discord.SelectOption(label="FiveM", description="Recherche multi-identifiants", emoji="🚗"),
            discord.SelectOption(label="Snusbase", description="Accès API Snusbase", emoji="🔑"),
            discord.SelectOption(label="Discord", description="Base de données Discord", emoji="💬"),
            discord.SelectOption(label="Legion", description="Infos sur le projet", emoji="🪐"),
        ]
        super().__init__(placeholder="Choisis un outil...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        
        if val == "Advanced":
            emb = discord.Embed(
                title="==============================\n      🚀 ADVANCED S€ARCH\n==============================", 
                description="[+] Recherche locale par filtres\n[+] Prénom · Nom · Ville\n[+] Scan profond des bases de données", 
                color=0x2b2d31
            )
            await interaction.response.send_message(embed=emb, view=AdvancedMenuView(), ephemeral=True)
            
        elif val == "FiveM":
            emb = discord.Embed(title="==============================\n      FIVEM S€ARCHER\n==============================", description="[+] Plusieurs types de recherche\n[+] Username · Steam · Discord\n[+] License · IP", color=0x2b2d31)
            await interaction.response.send_message(embed=emb, view=FiveMMenuView(), ephemeral=True)
            
        elif val == "Snusbase":
            emb = discord.Embed(title="==============================\n      Snusbase S€ARCHER\n==============================", description="[+] API SNUSBASE CONNECTÉE\n[+] Multi-sources & Instantané", color=0x2b2d31)
            await interaction.response.send_message(embed=emb, view=SnusbaseMenuView(), ephemeral=True)
            
        elif val == "Discord":
            if await check_legion_status(interaction):
                await interaction.response.send_modal(FiveMSearchModal("Discord Search", "Valeur Discord", "ID ou Pseudo", "discord_db"))
                
        elif val == "Legion":
            user_id = str(interaction.user.id)
            user_credits = credit_system.get(user_id, {}).get("balance", 0)
            embed = discord.Embed(
                title="==============================\n      🪐 PROJECT LEGION\n==============================",
                description=(
                    f"**Utilisateur** : {interaction.user.mention}\n"
                    f"**ID** : `{user_id}`\n"
                    f"**Crédits** : `{user_credits}`\n\n"
                    "**Status** : `Opérationnel` 🟢\n"
                    "**Version** : `2.4.1` (Stable)\n\n"
                    f"**Requis** : Avoir `{REQUIRED_STATUS}` en statut Discord."
                ),
                color=0x2b2d31
            )
            embed.set_footer(text="Legion S€archer • OSINT Protection")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

# --- COMMANDES BOT ---

@bot.event
async def on_ready():
    print(f'{Fore.CYAN}Legion Bot est en ligne !{Style.RESET_ALL}')

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🪐 Legion S€archer", 
        description=f"Legion — Recherche & infos en un clic.\n\n**Accès** — mets `{REQUIRED_STATUS}` en statut.", 
        color=0x2b2d31
    )
    embed.set_image(url=BANNER_URL)
    view = ui.View()
    view.add_item(MainMenuSelect())
    await ctx.send(embed=embed, view=view)

@bot.command()
async def claim(ctx):
    uid = str(ctx.author.id)
    now = datetime.datetime.now()
    if uid in credit_system and isinstance(credit_system[uid].get("last_daily"), datetime.datetime):
        if (now - credit_system[uid]["last_daily"]) < datetime.timedelta(days=1):
            return await ctx.send("❌ Déjà réclamé aujourd'hui.")
    
    credit_system[uid] = {"balance": credit_system.get(uid, {}).get("balance", 0) + 10, "last_daily": now}
    save_credits()
    await ctx.send("🎁 Tu as reçu tes **10 crédits** quotidiens !")

bot.run(TOKEN)
