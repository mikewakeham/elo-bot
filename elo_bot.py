from db_utils import *
from utils import *
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import threading
from sheets import *

DC_VERIFIED_ROLE_ID = 1323577921981648906
VERIFIED_ROLE_ID = 1323577899894181888
PRIVILEGED_ROLE_ID = 1323578013887238194
ROBLOX_GROUP_ID = 35383229
LOGS_CHANNEL_ID = 1324866568609595413

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

connect_db()

sheet = authenticate_google_sheets()

thread = threading.Thread(target=update_google_sheet, args=(sheet,))
thread.daemon = True
thread.start()



# COMMANDS

@bot.event
async def on_ready():
    await bot.tree.sync() 
    print(f'Logged in as {bot.user}')


@bot.tree.command(name="verify", description="Verify a player by checking their roles and group membership")
async def verify(interaction: discord.Interaction):
    member = interaction.user

    has_dc_verified = any(role.id == DC_VERIFIED_ROLE_ID for role in member.roles)
    has_verified = any(role.id == VERIFIED_ROLE_ID for role in member.roles)

    nickname = member.nick
    if nickname is None:
        await interaction.response.send_message("Verify with Bloxlink")
        return
    
    match = re.search(r'\((.*?)\)', nickname)
    if match is None:
        await interaction.response.send_message("There is no username surrounded by parentheses")
        return
    roblox_name = match.group(1)
    if roblox_name is None:
        await interaction.response.send_message("There is no username surrounded by parentheses")
        return

    roblox_id = get_roblox_user_id(roblox_name)
    if roblox_id is None:
        await interaction.response.send_message(f"Can't find Roblox ID for username {roblox_name}")
        return
    elif roblox_id == 429:
        await interaction.response.send_message("Currently on cooldown")
        return

    in_roblox_group = await is_in_roblox_group(roblox_id, ROBLOX_GROUP_ID)

    if has_dc_verified and has_verified and in_roblox_group:
        existing_player_by_roblox_id = get_player(roblox_id)
        existing_player_by_discord_id = get_player(member.id)

        if existing_player_by_roblox_id is not None:
            await interaction.response.send_message("You are already verified in the database")
        elif existing_player_by_discord_id is not None:
            await interaction.response.send_message("Discord account is already registered in the database, contact staff to update username")
        else:
            if add_player(member.id, roblox_id, roblox_name):
                await interaction.response.send_message("You have been verified and added to the database")
            else:
                await interaction.response.send_message("An error occurred while adding you to the database")
    else:
        missing = []
        if not has_dc_verified:
            missing.append("DC Verified role")
        if not has_verified:
            missing.append("Verified role")
        if not in_roblox_group:
            missing.append("Roblox group member")

        await interaction.response.send_message(f"You are missing the following requirements: {', '.join(missing)}")


@bot.tree.command(name="add", description="Add elo to the designated player")
@app_commands.describe(member="The player to add points to", points="The amount of elo to add")
async def add(interaction: discord.Interaction, member: discord.Member, points: int):
    if PRIVILEGED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("You do not have permission to use this command")
        return

    if points <= 0:
        await interaction.response.send_message("Points must be a positive integer")
        return

    current_elo = get_player_attribute(member.id, "elo")
    if current_elo is None:
        await interaction.response.send_message(f"{member.mention} is not in the database, have them verify first")
        return
    
    new_elo = max(0, current_elo + points)
    updated_season_elo = await update_elo(member.id, new_elo, points, member.guild)
    await interaction.response.send_message(f"Added {points} points to {member.mention} | New ELO: {updated_season_elo} ({new_elo} total)")
    

@bot.tree.command(name="subtract", description="Subtract elo from the designated player")
@app_commands.describe(member="The player to subtract points from", points="The amount of elo to subtract")
async def add(interaction: discord.Interaction, member: discord.Member, points: int):
    if PRIVILEGED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("You do not have permission to use this command")
        return

    if points <= 0:
        await interaction.response.send_message("Points must be a positive integer")
        return

    current_elo = get_player_attribute(member.id, "elo")
    if current_elo is None:
        await interaction.response.send_message(f"{member.mention} is not in the database, have them verify first")
        return
    
    new_elo = max(0, current_elo - points)

    updated_season_elo = await update_elo(member.id, new_elo, -points, member.guild)
    await interaction.response.send_message(f"Subtracted {points} points from {member.mention} | New ELO: {updated_season_elo} ({new_elo} total)")


@bot.tree.command(name="leaderboard", description="View the top players on the leaderboard.")
@app_commands.describe(top_n="The number of players to display")
async def leaderboard(interaction: discord.Interaction, top_n: int = 10):
    if top_n < 1 or top_n > 50:
        await interaction.response.send_message('top_n must be between 1 and 50')
        return

    leaderboard = get_leaderboard(top_n)
    if leaderboard:
        leaderboard_message = "**Season Leaderboard:**\n"
        for rank, (player, season_elo, elo) in enumerate(leaderboard, start=1):
            leaderboard_message += f"{rank}. {player} - ELO: {season_elo} ({elo} total)\n"
        await interaction.response.send_message(leaderboard_message)
    else:
        await interaction.response.send_message("The leaderboard is empty")


@bot.tree.command(name="view", description="View a player's elo")
@app_commands.describe(member="The player to view")
async def view(interaction: discord.Interaction, member: discord.Member):
    if get_player(member.id) is None:
        await interaction.response.send_message(f"{member.mention} is not in the database, have them verify first.")
    else:
        elo = get_player_attribute(member.id, "elo")
        season_elo = get_player_attribute(member.id, "season_elo")
        most_recent_action = get_player_attribute(member.id, "most_recent_action")
        await interaction.response.send_message(f"{member.mention} ELO: {season_elo} ({elo} total) | Latest change: {most_recent_action}")


@bot.tree.context_menu(name="match elo update")
async def update_match_elo(interaction: discord.Interaction, message: discord.Message):
    if PRIVILEGED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("You do not have permission to use this command")
        return
    
    if not message.content:
        await interaction.response.send_message("This message does not contain match elo")
        return

    await interaction.response.defer(ephemeral=True)

    try:
        response_message = await asyncio.wait_for(process_match_elo_update(interaction, message), timeout=5.0)
        if response_message is None:
            return
    except asyncio.TimeoutError:
        await interaction.followup.send("The operation is taking too long, please try again later or contact staff if the issue persists")
        return

    log_channel = bot.get_channel(LOGS_CHANNEL_ID)

    if log_channel:
        await log_channel.send(response_message)
    else:
        await interaction.followup.send("The log channel could not be found")

    await interaction.followup.send("Success")


@bot.tree.command(name="reset", description="Reset season leaderboard")
async def reset_leaderboard(interaction: discord.Interaction):
    if interaction.user.id != 720504770720301096 and interaction.user.id != 786078512846471168:
        await interaction.response.send_message("Nice try... heh")
        return
    
    reset_seasonal_elo()

    await interaction.response.send_message("Season leaderboard has been reset")
    

bot.run("DISCORD API TOKEN HERE")
