import sqlite3
import re
from utils import *


DB_FILE = 'elo.sqlite'
ROLE_IDS = {
    'iron': 1325332328070910085,
    'bronze': 1325332371150737408,
    'silver': 1325332351525589064,
    'gold': 1325332602462273556,
    'platinum': 1325332615456100415,
    'diamond': 1325332631230873620,
    'emerald': 1325332656074002462,
    'ascendant': 1325332739217555477,
}
ELO_RANGES = {
    'iron': (0, 399),
    'bronze': (400, 899),
    'silver': (900, 1399),
    'gold': (1400, 1899),
    'platinum': (1900, 2399),
    'diamond': (2400, 3250),
    'emerald': (3250, float('inf'))
}


def connect_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        discord_id TEXT,
                        roblox_id TEXT,
                        roblox_name TEXT,
                        season_elo INTEGER DEFAULT 0,
                        elo INTEGER DEFAULT 0,
                        most_recent_action INTEGER DEFAULT 0
                      )''')
    conn.commit()
    conn.close()

def fetch_data_from_sqlite():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players")
    rows = cursor.fetchall()
    conn.close()
    return rows





def add_player(discord_id, roblox_id, roblox_name):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO players (discord_id, roblox_id, roblox_name, elo)
                          VALUES (?, ?, ?, ?)''', (discord_id, roblox_id, roblox_name, 0))
        conn.commit()
        conn.close()
        return True  
    except sqlite3.Error as e:
        print(f"Error adding player {e}")  
        return None  


async def update_elo(discord_id, new_elo, elo_change, guild):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        await update_rank(guild, discord_id, new_elo)

        cursor.execute('''UPDATE players 
                          SET elo = ?, most_recent_action = ? 
                          WHERE discord_id = ?''', 
                          (new_elo, elo_change, discord_id))
        
        cursor.execute('''SELECT season_elo FROM players WHERE discord_id = ?''', (discord_id,))
        current_season_elo = cursor.fetchone()[0]

        updated_season_elo = max(0, current_season_elo + elo_change)
        cursor.execute('''UPDATE players 
                          SET season_elo = ?, most_recent_action = ? 
                          WHERE discord_id = ?''', 
                          (updated_season_elo, elo_change, discord_id))
        conn.commit()
        conn.close()
        return updated_season_elo 
    except sqlite3.Error as e:
        print(f"Error updating Elo {e}")
        return None


async def update_rank(guild, discord_id, player_elo):
    member = guild.get_member(int(discord_id))
    
    for rank, (min_elo, max_elo) in ELO_RANGES.items():
        if min_elo <= player_elo <= max_elo:
            if ROLE_IDS[rank] not in [role.id for role in member.roles]:
                role = guild.get_role(ROLE_IDS[rank])
                if role:
                    await member.remove_roles(*[role for role in member.roles if role.id in ROLE_IDS.values()])
                    await member.add_roles(role)  
                    print(f"Assigned {role.name} role to {member.name}")
                else:
                    print(f"Role {rank} not found in the server")
            break

    top_25 = get_leaderboard(25)
    ascendant_role = guild.get_role(ROLE_IDS['ascendant'])

    for rank, (player_name, _, _) in enumerate(top_25, start=1):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''SELECT discord_id FROM players WHERE roblox_name = ?''', (player_name,))
        player_id = cursor.fetchone()
        conn.close()

        if not player_id:
            print(f"No Discord ID found for player: {player_name}")
            continue

        player_member = guild.get_member(int(player_id[0]))
        if not player_member:
            print(f"Member with ID {player_id[0]} is not in the server")
            continue

        if rank <= 10:
            if ascendant_role not in player_member.roles:
                await player_member.add_roles(ascendant_role)
                print(f"Assigned ascendant role to {player_member.name}")
        else:
            if ascendant_role in player_member.roles:
                await player_member.remove_roles(ascendant_role)
                print(f"Removed ascendant role from {player_member.name}")


def get_player(discord_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''SELECT * FROM players WHERE discord_id = ?''', (discord_id,))
        player = cursor.fetchone()
        conn.close()
        return player 
    except sqlite3.Error as e:
        print(f"Error retrieving player {e}")
        return None  


def get_leaderboard(top_n):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(f'''SELECT roblox_name, season_elo, elo 
                            FROM players 
                            ORDER BY season_elo DESC, elo DESC 
                            LIMIT {top_n}''')
        leaderboard = cursor.fetchall()
        conn.close()
        return leaderboard  
    except sqlite3.Error as e:
        print(f"Error retrieving leaderboard {e}")
        return None 


def get_player_attribute(discord_id, attribute):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(players)")  
    columns = cursor.fetchall()
    conn.close()

    column_names = [column[1] for column in columns]

    if attribute not in column_names:
        raise ValueError(f"Invalid attribute: {attribute}")

    player = get_player(discord_id)

    if player:
        attribute_index = column_names.index(attribute)  

        return player[attribute_index]
    else:
        return None 


async def process_match_elo_update(interaction, message):
    message_lines = message.content.split("\n")
    updates = []

    first_line = message.content.split("\n")[0]
    match_num = re.search(r"(\d+)", first_line)

    if match_num:
        match_num = match_num.group(1)
    else:
        await interaction.followup.send("Could not find the game number in the message")
        return
    
    for line in message_lines:
        match = re.match(r"<@(\d+)>.*?([+-]\s*\d+)", line.strip())
        if match:
            user_id = match.group(1)
            elo_change = match.group(2).replace(" ", "")
            elo_change = int(elo_change)
            
            if elo_change == 0:
                continue

            updates.append((user_id, elo_change))
        else:
            continue
    
    if len(updates) > 14:
        await interaction.followup.send(f"Invalid number of mentions with elo change, there should be at most 14")
        return
    
    if len(updates) < 12:
        await interaction.followup.send(f"Invalid number of mentions with elo change, there should be at least 12")
        return
    
    response_message = f"Match {match_num} elo update: [message]({message.jump_url})" + "\n\n"
    print(updates)
    for discord_id, elo_change in updates:
        player_data = get_player(discord_id)

        if player_data:
            current_elo = get_player_attribute(discord_id, "elo")
            new_elo = max(0, current_elo + elo_change)

            await update_elo(discord_id, new_elo, elo_change, message.guild)
            if elo_change > 0:
                response_message += f"<@{discord_id}>: +{elo_change} elo. New ELO: {new_elo}" + "\n"
            else:
                response_message += f"<@{discord_id}>: {elo_change} elo. New ELO: {new_elo}" + "\n"
        else:
            response_message += f"<@{discord_id}> is not in the database" + "\n"

    return response_message


def reset_seasonal_elo():
    conn = sqlite3.connect('elo.sqlite')
    cursor = conn.cursor()
    cursor.execute("UPDATE players SET season_elo = 0")
    conn.commit()
    print("Seasonal Elo scores reset to 0 for all players.")
    conn.close()