import requests
from qbittorrentapi import Client
import time
import re
import os

# Setup for TMDb
TMDB_API_KEY = ''  # Replace with your TMDb API Key
TMDB_SEARCH_URL = 'https://api.themoviedb.org/3/search/tv'
TMDB_DETAILS_URL = 'https://api.themoviedb.org/3/tv/{tv_id}'

# Setup for qBittorrent
qb = Client(host='http://127.0.0.1:8080', username='admin', password='')  # Replace with your credentials

# Jackett Configuration
jackett_api_key = ''  # Replace with your Jackett API key
jackett_url = 'http://localhost:9117/api/v2.0/indexers/all/results'

# Folder Configuration
base_download_path = ''  # Base folder for all TV show downloads
os.makedirs(base_download_path, exist_ok=True)  # Ensure base folder exists

# Load the TV show list with UTF-8 encoding from the new path
tv_show_list_path = 'E:\\requests\\Tv-Shows.txt'
with open(tv_show_list_path, 'r', encoding='utf-8') as file:
    tv_show_list = [line.strip() for line in file if line.strip()]  # Remove empty lines and whitespace

# Utility Functions

def normalize_title(title):
    """Normalize title for better matching with TMDb."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', title).strip().lower()

def get_first_letter_folder(title):
    """Determine the correct folder based on title's first letter."""
    cleaned_title = re.sub(r'^(A |An |The )', '', title, flags=re.IGNORECASE).strip()
    first_letter = cleaned_title[0].upper() if cleaned_title else '#'
    return first_letter if first_letter.isalpha() else '#'

def get_tv_show_details(title):
    """Search TMDb for TV show details."""
    params = {
        'api_key': TMDB_API_KEY,
        'query': title,
        'language': 'en-US'
    }
    response = requests.get(TMDB_SEARCH_URL, params=params)
    if response.status_code == 200:
        results = response.json().get("results", [])
        normalized_title = normalize_title(title)
        for tv_show in results:
            if normalize_title(tv_show.get("name", "")) == normalized_title:
                tv_show_id = tv_show.get("id")
                seasons = get_number_of_seasons(tv_show_id)
                if seasons > 0:
                    return {'id': tv_show_id, 'name': tv_show.get('name'), 'seasons': seasons}
    return None

def get_number_of_seasons(tv_show_id):
    """Get the number of seasons for a TV show from TMDb by its ID."""
    response = requests.get(TMDB_DETAILS_URL.format(tv_id=tv_show_id), params={'api_key': TMDB_API_KEY})
    if response.status_code == 200:
        return response.json().get('number_of_seasons', 0)
    return 0

def search_jackett(query):
    """Search Jackett for torrents based on the query."""
    response = requests.get(jackett_url, params={'apikey': jackett_api_key, 'Query': query})
    if response.status_code == 200:
        results = response.json().get('Results')
        if results:
            sorted_results = sorted(results, key=lambda x: x['Seeders'], reverse=True)
            return sorted_results[0].get('MagnetUri')
    return None

# Main Download Logic for TV Show

def download_tv_show(tv_show_name):
    """Download all seasons of a TV show."""
    show_details = get_tv_show_details(tv_show_name)
    if not show_details:
        print(f"No details found for: {tv_show_name}")
        return False

    tv_show_id = show_details['id']
    total_seasons = show_details['seasons']
    folder_letter = get_first_letter_folder(tv_show_name)
    letter_folder = os.path.join(base_download_path, folder_letter)
    os.makedirs(letter_folder, exist_ok=True)

    show_folder = os.path.join(letter_folder, tv_show_name)
    os.makedirs(show_folder, exist_ok=True)

    all_seasons_added = True
    for season_number in range(1, total_seasons + 1):
        season_folder = os.path.join(show_folder, f"Season {season_number}")
        os.makedirs(season_folder, exist_ok=True)

        season_query = f"{tv_show_name} S{season_number:02d}"
        print(f"Searching for torrents for: {season_query}")

        magnet_link = search_jackett(season_query)
        if magnet_link:
            print(f"Adding torrent for: {season_query} to {season_folder}")
            qb.torrents_add(
                urls=magnet_link,
                save_path=season_folder,
            )
        else:
            print(f"No torrent found for: {season_query}")
            all_seasons_added = False

        time.sleep(1)

    return all_seasons_added

# Function to monitor and remove completed torrents
def remove_completed_torrents():
    torrents = qb.torrents_info()
    for torrent in torrents:
        if torrent.state == 'uploading':  # Status 'uploading' means the torrent is seeding
            print(f"Removing torrent: {torrent.name} (Completed Download)")
            qb.torrents_delete(delete_files=False, torrent_hashes=torrent.hash)

# Function to get the current number of downloading torrents
def get_active_download_count():
    torrents = qb.torrents_info(status_filter='downloading')
    return len(torrents)

# Main download process
def process_tv_shows():
    global tv_show_list
    downloaded_shows = []
    active_limit = 10

    for tv_show in tv_show_list:
        while get_active_download_count() >= active_limit:
            print("Max active downloads reached, waiting for a slot...")
            remove_completed_torrents()
            time.sleep(30)

        if download_tv_show(tv_show):
            downloaded_shows.append(tv_show)
        else:
            print(f"No details found for: {tv_show}")

        print("Waiting for current downloads to complete...")
        time.sleep(30)

    if downloaded_shows:
        tv_show_list = [tv_show for tv_show in tv_show_list if tv_show not in downloaded_shows]
        with open(tv_show_list_path, 'w', encoding='utf-8') as file:
            for tv_show in tv_show_list:
                file.write(f"{tv_show}\n")

    print("All TV shows processed.")

# Continuously monitor for seeding torrents and remove them
def continuous_monitoring():
    print("Monitoring for seeding torrents...")
    while True:
        remove_completed_torrents()
        time.sleep(60)

if __name__ == "__main__":
    process_tv_shows()
    continuous_monitoring()
