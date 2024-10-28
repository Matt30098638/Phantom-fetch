# utils/jellyfin_helper.py
import requests

class JellyfinHelper:
    def __init__(self, server_url, api_key):
        self.server_url = server_url
        self.api_key = api_key

    def get_existing_items(self):
        """Fetch all existing items from Jellyfin"""
        url = f"{self.server_url}/Users/Public/Items"
        headers = {
            "X-Emby-Token": self.api_key
        }
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json().get('Items', [])
            else:
                print(f"Failed to fetch existing items from Jellyfin: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error fetching existing items from Jellyfin: {e}")
            return []

    def item_exists(self, title, release_year=None, type=None):
        """Check if an item already exists in the Jellyfin library"""
        items = self.get_existing_items()
        for item in items:
            if item.get('Name').lower() == title.lower():
                if release_year and str(item.get('ProductionYear')) == str(release_year):
                    return True
                elif not release_year:  # If year is not specified, just check the name
                    return True
        return False
