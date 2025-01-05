import requests
import aiohttp
import re
from db_utils import *

def get_roblox_user_id(username):
    # url = f"https://users.roblox.com/v1/users/search?keyword={username}"
    # response = requests.get(url)
    
    # if response.status_code == 200:
    #     data = response.json()
        
    #     if data.get('data'):
    #         user_id = data['data'][0]['id']
    #         return user_id
    #     else:
    #         print("User not found.")
    #         return None
    # elif response.status_code == 429:
    #     return 429
    # else:
    #     print(f"Error: {response.status_code}")
    #     return None

    try:
        # Send the GET request to the Roblox profile URL
        response = requests.get(f"https://www.roblox.com/users/profile?username={username}")
        
        # Check if the response is successful
        if response.status_code != 200:
            raise Exception("Invalid response")

        # Use regex to extract the user ID from the URL
        user_id = re.search(r'\d+', response.url).group(0)

        # Return the user ID
        print(user_id)
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