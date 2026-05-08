import discord
from discord.ext import commands
from discord import ui
import os
import datetime
import json
import aiofiles

# --- CONFIGURATION (GARDÉE) ---
TOKEN = os.getenv('DISCORD_TOKEN') or 'TON_TOKEN_ICI'
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

AUTHORIZED_IDS = [1402199337240625193, 1445150036295028787, 1444785390362820853]
BANNER_URL = "https://files.catbox.moe/4za0fc.png"

# --- SYSTÈME DE CRÉDITS (GARDÉ) ---
def load_credits():
    if os.path.exists('credit_system.json'):
        with open('credit_system.json', 'r') as f: return json.load(f)
    return {}

credit_system = load_credits()

# --- 1. MODALS FIVEM (IMAGE 10 À 16) ---
class FiveMSearchModal(ui.Modal):
    def __init__(self, title, label, placeholder, directory):
        super().__init__(title=title)
        self.directory = directory
        self.input = ui.TextInput(label=label, placeholder=placeholder, required=True)
        self.add_item(self.input)

    async def on_submit(self, interaction: discord.Interaction):
        # On appelle ta fonction de recherche d'origine
        await interaction.response.defer(ephemeral=True)
        await perform_search_logic(interaction, self.directory, self.input.value)

# --- 2. MENU DÉROULANT FIVEM (IMAGE 8 & 9) ---
class FiveMMenuView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.select(
        placeholder="→ Username",
        options=[
            discord.SelectOption(label="Username", emoji="👤"),
            discord.SelectOption(label="Steam", emoji="🎮"),
            discord.SelectOption(label="Discord", emoji="💬"),
            discord.SelectOption(label="License", emoji="🔑"),
            discord.SelectOption(label="Xbox", emoji="💚"),
            discord.SelectOption(label="Live", emoji="📧"),
            discord.SelectOption(label="FiveM ID", emoji="🆔"),
            discord.SelectOption(label="Adresse IP", emoji="🌐"),
        ]
    )
    async def callback(self, interaction: discord.Interaction, select: ui.Select):
        choice = select.values[0]
        # Configuration des champs selon ton interface
        config = {
            "Username": ("FiveM : Username", "Username (pseudo)", "Gablidotse"),
            "Steam": ("FiveM : Steam", "Steam ID (hex)", "11000010a86a88f"),
            "Discord": ("FiveM : Discord", "Discord ID", "970665717877858364"),
            "License": ("FiveM : License", "License (hex)", "511b2ee9..."),
            "Xbox": ("FiveM : Xbox", "Xbox Live ID", "2535432541599307"),
            "Live": ("FiveM : Live", "Microsoft Live ID", "84425664499926"),
            "FiveM ID": ("FiveM : ID", "FiveM ID", "6821837"),
            "Adresse IP": ("FiveM : IP", "Adresse IP", "1.1.1.1")
        }
        title, label, placeholder = config[choice]
        await interaction.response.send_modal(FiveMSearchModal(title, label, placeholder, "Fivemdb"))

# --- 3. MENU PRINCIPAL (IMAGE 2 & 3) ---
class MainMenuSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Advanced", description="Recherche avancée", emoji="🚀"),
            discord.SelectOption(label="FiveM", description="8 types de recherche", emoji="🚗"),
            discord.SelectOption(label="Discord", description="Base Discord", emoji="💬"),
            discord.SelectOption(label="Restorecord", description="Base Restorecord", emoji="🔗"),
            discord.SelectOption(label="Legion", description="Infos Legion", emoji="🪐"),
        ]
        super().__init__(placeholder="Choisis un outil...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "FiveM":
            # Affichage de l'embed FiveM (Image 7)
            embed = discord.Embed(
                title="==============================\n      FIVEM S€ARCHER\n==============================",
                description="[+] 8 types de recherche\n[+] Username · Steam · Discord\n[+] License · IP\n[+] Xbox · Live · FiveM ID",
                color=0x2b2d31
            )
            embed.set_thumbnail(url="https://io.files.catbox.moe/u96y2u.png") # Ton logo
            embed.set_footer(text="discord.gg/legion")
            await interaction.response.send_message(embed=embed, view=FiveMMenuView(), ephemeral=True)
        else:
            await interaction.response.send_message("Outil en cours d'intégration.", ephemeral=True)

# --- FONCTION DE RECHERCHE (TON CODE D'AVANT) ---
async def perform_search_logic(interaction, directory, query):
    # Logique de recherche exacte de ton ancien code
    if not os.path.exists(directory):
        return await interaction.followup.send(f"Dossier {directory} manquant.")

    result = []
    for file in os.listdir(directory):
        try:
            async with aiofiles.open(os.path.join(directory, file), mode='r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    if query in line: result.append(line.strip())
        except: continue

    if result:
        # Envoi en DM comme avant
        content = '\n'.join(result)
        file_data = io.BytesIO(content.encode())
        await interaction.user.send(content="Voici tes résultats :", file=discord.File(file_data, "results.txt"))
        await interaction.followup.send("✅ Résultats envoyés en DM.")
    else:
        await interaction.followup.send(f"❌ Aucun résultat pour : {query}")

# --- EVENTS & COMMANDES ---
@bot.event
async def on_message(message):
    if bot.user in message.mentions:
        await message.reply("Salut — pour ouvrir le **panel**, mets `/legion` dans ton **statut** et reste **en ligne**.", mention_author=False)
    await bot.process_commands(message)

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🪐 Legion S€archer",
        description="Legion — Recherche & infos en un clic.\nChoisis un outil dans le menu.\n\n**Accès** — mets `/legion` en statut.",
        color=0x2b2d31
    )
    embed.set_image(url=BANNER_URL)
    view = ui.View()
    view.add_item(MainMenuSelect())
    await ctx.send(embed=embed, view=view)

bot.run(TOKEN)
