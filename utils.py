import requests
import aiohttp
import re
from db_utils import *

def get_roblox_user_id(username):
    try:
        response = requests.get(f"https://www.roblox.com/users/profile?username={username}")
        
        if response.status_code != 200:
            raise Exception("Invalid response")

        user_id = re.search(r'\d+', response.url).group(0)
        return user_id

    except Exception as e:
        print(f"Error: {e}")
        return None

    
async def is_in_roblox_group(roblox_id, group_id):
    url = f"https://groups.roblox.com/v2/users/{roblox_id}/groups/roles"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for group in data.get("data", []):
                        if group["group"]["id"] == group_id:
                            return True
                    
                    return False
                else:
                    print(f"Failed to fetch group data: {response.status}")
                    return False
        except Exception as e:
            print(f"An error occurred: {e}")
            return False
