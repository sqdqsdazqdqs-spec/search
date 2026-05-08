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

# --- CONFIGURATION (TON TOKEN) ---
TOKEN = os.getenv('DISCORD_TOKEN') or 'TON_TOKEN_ICI'

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# --- VARIABLES ET IDS ---
AUTHORIZED_IDS = [1402199337240625193, 1445150036295028787, 1444785390362820853]
BANNER_URL = "https://io.files.catbox.moe/u96y2u.png"
CREDITS_PER_USE = 2

# --- LOGIQUE DES CREDITS (TON CODE D'ORIGINE) ---

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

# --- FONCTION DE RECHERCHE D'ORIGINE (TON MOTEUR) ---

async def perform_search_logic(interaction, directory, query):
    user_id = str(interaction.user.id)
    
    # Vérification des crédits
    if user_id not in credit_system or credit_system[user_id]["balance"] < CREDITS_PER_USE:
        return await interaction.followup.send("❌ Vous n'avez pas assez de crédits.", ephemeral=True)
      
    if not os.path.exists(directory):
        return await interaction.followup.send(f"❌ Dossier `{directory}` manquant.", ephemeral=True)

    results = []
    for file in os.listdir(directory):
        try:
            async with aiofiles.open(os.path.join(directory, file), mode='r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    if query in line:
                        results.append(line.strip())
        except: continue

    if results:
        # Envoi des résultats en DM comme avant
        content = '\n'.join(results)
        file_data = io.BytesIO(content.encode('utf-8'))
        try:
            await interaction.user.send(content=f"📂 Résultats Legion pour : `{query}`", file=discord.File(file_data, "results.txt"))
            # Déduction des crédits
            credit_system[user_id]["balance"] -= CREDITS_PER_USE
            save_credits()
            await interaction.followup.send("✅ Les résultats ont été envoyés dans tes messages privés.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Impossible de t'envoyer tes DM. Ouvre tes messages privés.", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ Aucune information trouvée pour : `{query}`", ephemeral=True)

# --- INTERFACES : MODALS (FORMULAIRES) ---

class AdvancedSearchModal(ui.Modal, title='Recherche avancée'):
    prenom = ui.TextInput(label='Prénom (optionnel)', placeholder='Jean', required=False)
    nom = ui.TextInput(label='Nom (optionnel)', placeholder='Dupont', required=False)
    dob = ui.TextInput(label='Date de naissance (optionnel)', placeholder='01/01/1990', required=False)
    year = ui.TextInput(label='Année de naissance (optionnel)', placeholder='1990', required=False)
    city = ui.TextInput(label='Ville / Code-Postal (optionnel)', placeholder='Paris 75001', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        query = f"{self.prenom.value} {self.nom.value} {self.city.value}".strip()
        await perform_search_logic(interaction, "database", query)

class FiveMSearchModal(ui.Modal):
    def __init__(self, title, label, placeholder):
        super().__init__(title=title)
        self.input = ui.TextInput(label=label, placeholder=placeholder, required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await perform_search_logic(interaction, "Fivemdb", self.input.value)

class SnusbaseSearchModal(ui.Modal):
    def __init__(self, title, label):
        super().__init__(title=title)
        self.input = ui.TextInput(label=label, placeholder="Entrez la valeur ici...", required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Remplace "snusbase_db" par ton dossier snusbase réel
        await perform_search_logic(interaction, "snusbase_db", self.input.value)

# --- INTERFACES : MENUS DÉROULANTS (VIEWS) ---

class SnusbaseMenuView(ui.View):
    @ui.select(placeholder="Sélectionne un type de recherche...", options=[
        discord.SelectOption(label="Détection auto", emoji="➡️"),
        discord.SelectOption(label="Email", emoji="➡️"),
        discord.SelectOption(label="Pseudo / username", emoji="➡️"),
        discord.SelectOption(label="Adresse IP", emoji="➡️"),
        discord.SelectOption(label="Mot de passe", emoji="➡️"),
        discord.SelectOption(label="Hash", emoji="➡️"),
        discord.SelectOption(label="Nom", emoji="➡️"),
        discord.SelectOption(label="Domaine", emoji="➡️"),
    ])
    async def callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_modal(SnusbaseSearchModal(f"Snusbase : {select.values[0]}", f"Valeur ({select.values[0]})"))

class FiveMMenuView(ui.View):
    @ui.select(placeholder="→ Choisis un type", options=[
        discord.SelectOption(label="Username", emoji="👤"),
        discord.SelectOption(label="Steam", emoji="🎮"),
        discord.SelectOption(label="Discord", emoji="💬"),
        discord.SelectOption(label="License", emoji="🔑"),
        discord.SelectOption(label="Xbox", emoji="💚"),
        discord.SelectOption(label="Live", emoji="📧"),
        discord.SelectOption(label="FiveM ID", emoji="🆔"),
        discord.SelectOption(label="Adresse IP", emoji="🌐"),
    ])
    async def callback(self, interaction: discord.Interaction, select: ui.Select):
        configs = {
            "Username": ("FiveM : Username", "Username (pseudo)", "Gablidotse"),
            "Steam": ("FiveM : Steam", "Steam ID (hex)", "11000010a86a88f"),
            "Discord": ("FiveM : Discord", "Discord ID", "970665717877858364"),
            "License": ("FiveM : License", "License (hex)", "511b2ee9..."),
            "Xbox": ("FiveM : Xbox", "Xbox Live ID", "2535432541599307"),
            "Live": ("FiveM : Live", "Microsoft Live ID", "84425664499926"),
            "FiveM ID": ("FiveM : ID", "FiveM ID", "6821837"),
            "Adresse IP": ("FiveM : IP", "Adresse IP", "1.1.1.1")
        }
        t, l, p = configs[select.values[0]]
        await interaction.response.send_modal(FiveMSearchModal(t, l, p))

class MainMenuSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Advanced", description="Recherche complète", emoji="🚀"),
            discord.SelectOption(label="FiveM", description="8 types de recherche", emoji="🚗"),
            discord.SelectOption(label="Snusbase", description="Base de données Snusbase", emoji="🔑"),
            discord.SelectOption(label="Discord", description="Recherche base Discord", emoji="💬"),
            discord.SelectOption(label="Legion", description="Infos sur le projet", emoji="🪐"),
        ]
        super().__init__(placeholder="Choisis un outil...", options=options)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "Advanced":
            await interaction.response.send_modal(AdvancedSearchModal())
        elif val == "FiveM":
            embed = discord.Embed(title="==============================\n      FIVEM S€ARCHER\n==============================", description="[+] 8 types de recherche\n[+] Username · Steam · Discord\n[+] License · IP\n[+] Xbox · Live · FiveM ID", color=0x2b2d31)
            await interaction.response.send_message(embed=embed, view=FiveMMenuView(), ephemeral=True)
        elif val == "Snusbase":
            embed = discord.Embed(title="==============================\n      Snusbase S€ARCHER\n==============================", description="[+] 8 modes de recherche\n[+] Détection auto disponible\n[+] Multi-sources", color=0x2b2d31)
            await interaction.response.send_message(embed=embed, view=SnusbaseMenuView(), ephemeral=True)
        else:
            await interaction.response.send_message(f"Outil {val} sélectionné.", ephemeral=True)

# --- COMMANDES CLASSIQUES (TON CODE D'ORIGINE) ---

@bot.event
async def on_ready():
    print(f'{Fore.GREEN}Legion Bot connecté !{Style.RESET_ALL}')
    await bot.change_presence(activity=discord.Streaming(name="Legion S€archer", url="https://twitch.tv/discord"))

@bot.event
async def on_message(message):
    if bot.user in message.mentions:
        await message.reply("Salut — pour ouvrir le **panel**, mets `/legion` dans ton **statut**.", mention_author=False)
    await bot.process_commands(message)

@bot.command()
async def panel(ctx):
    embed = discord.Embed(title="🪐 Legion S€archer", description="Legion — Recherche & infos en un clic.\n\n**Accès** — mets `/legion` en statut.", color=0x2b2d31)
    embed.set_image(url=BANNER_URL)
    view = ui.View()
    view.add_item(MainMenuSelect())
    await ctx.send(embed=embed, view=view)

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    bal = credit_system.get(user_id, {}).get("balance", 0)
    await ctx.send(f"💰 {ctx.author.mention}, tu as **{bal}** crédits.")

@bot.command()
async def claim(ctx):
    global credit_system
    now = datetime.datetime.now()
    user_id = str(ctx.author.id)
    if user_id in credit_system and isinstance(credit_system[user_id].get("last_daily"), datetime.datetime):
        if (now - credit_system[user_id]["last_daily"]) < datetime.timedelta(days=1):
            return await ctx.send("❌ Déjà réclamé aujourd'hui.")
    
    if user_id not in credit_system: credit_system[user_id] = {"balance": 10, "last_daily": now}
    else:
        credit_system[user_id]["balance"] += 10
        credit_system[user_id]["last_daily"] = now
    save_credits()
    await ctx.send("🎁 Tu as reçu tes **10 crédits** quotidiens !")

@bot.command()
async def addcr(ctx, user: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_IDS: return
    user_id = str(user.id)
    if user_id not in credit_system: credit_system[user_id] = {"balance": 0, "last_daily": None}
    credit_system[user_id]["balance"] += amount
    save_credits()
    await ctx.send(f"✅ {user.mention} a maintenant **{credit_system[user_id]['balance']}** crédits.")

# --- LANCEMENT ---
bot.run(TOKEN)
