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
base_download_path = 'E:\\Shows'  # Base folder for all TV show downloads
os.makedirs(base_download_path, exist_ok=True)  # Ensure base folder exists

# Load the TV show list with UTF-8 encoding from the new path
tv_show_list_path = 'E:\\requests\\Tv-Shows.txt'
with open(tv_show_list_path, 'r', encoding='utf-8') as file:
    tv_show_list = [line.strip() for line in file if line.strip()]  # Remove empty lines and whitespace

# Function to normalize title for better matching with TMDb
def normalize_title(title):
    return re.sub(r'[^a-zA-Z0-9\s]', '', title).strip().lower()

# Function to determine the correct folder based on title
def get_first_letter_folder(title):
    cleaned_title = re.sub(r'^(A |An |The )', '', title, flags=re.IGNORECASE).strip()
    first_letter = cleaned_title[0].upper() if cleaned_title else '#'
    if first_letter.isalpha():
        return first_letter
    else:
        return '#'

# Function to search TV show on TMDb and get details
def get_tv_show_details(title):
    try:
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
                    else:
                        print(f"No seasons found for: {title} (ID: {tv_show_id})")
                        return None
        else:
            print(f"Failed to search TMDb for: {title}. Status Code: {response.status_code}")
        return None
    except Exception as e:
        print(f"Error fetching details for {title}: {e}")
        return None

# Function to get the number of seasons for a TV show by its ID
def get_number_of_seasons(tv_show_id):
    try:
        response = requests.get(TMDB_DETAILS_URL.format(tv_id=tv_show_id), params={'api_key': TMDB_API_KEY})
        if response.status_code == 200:
            tv_show_details = response.json()
            return tv_show_details.get('number_of_seasons', 0)
        else:
            print(f"Failed to get details for TV show ID {tv_show_id}. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching number of seasons for show ID {tv_show_id}: {e}")
    return 0

# Function to search Jackett for torrents
def search_jackett(query):
    try:
        response = requests.get(jackett_url, params={'apikey': jackett_api_key, 'Query': query})
        if response.status_code == 200:
            results = response.json().get('Results')
            if results:
                sorted_results = sorted(results, key=lambda x: x['Seeders'], reverse=True)
                return sorted_results[0].get('MagnetUri')
        print(f"No results found on Jackett for: {query}")
        return None
    except Exception as e:
        print(f"Error searching Jackett for {query}: {e}")
        return None

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
    global tv_show_list  # Declare as global to modify the variable
    downloaded_shows = []
    active_limit = 10  # Limit the number of active downloads to 10

    for tv_show in tv_show_list:
        while get_active_download_count() >= active_limit:
            print("Max active downloads reached, waiting for a slot...")
            remove_completed_torrents()  # Remove completed torrents if any
            time.sleep(30)  # Check every 30 seconds

        show_details = get_tv_show_details(tv_show)
        if show_details:
            tv_show_name = show_details['name']
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

            if all_seasons_added:
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
        time.sleep(60)  # Check every minute for torrents that have finished downloading and are seeding

if __name__ == "__main__":
    process_tv_shows()
    continuous_monitoring()
