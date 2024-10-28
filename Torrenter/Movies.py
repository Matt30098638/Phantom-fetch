import re
import sys
import requests
import os
import yaml
from utils.qbittorrent_helper import QBittorrentHelper
from utils.tmdb_helper import TMDbHelper
from utils.jackett_helper import JackettHelper
from utils.jellyfin_helper import JellyfinHelper

# Load configuration from config.yaml
APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APPLICATION_PATH, 'assets', 'config.yaml')

if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError(f"Configuration file '{CONFIG_FILE}' is missing.")

with open(CONFIG_FILE, 'r') as file:
    config = yaml.safe_load(file)

# Path to Movies Request File (updated to new path)
FILMS_LIST_PATH = 'E:\\requests\\Film-list.txt'

# Initialize Helper Objects using the correct path to config.yaml
qb_helper = QBittorrentHelper(config_path=CONFIG_FILE)
tmdb_helper = TMDbHelper(config_path=CONFIG_FILE)
jackett_helper = JackettHelper(config_path=CONFIG_FILE)
jellyfin_helper = JellyfinHelper(
    server_url=config['Jellyfin']['server_url'],
    api_key=config['Jellyfin']['api_key']
)

# Function to determine the correct directory based on the title
def get_directory_for_title(title):
    corrected_title = re.sub(r"^(A|An|The)\s+", "", title, flags=re.IGNORECASE).strip()
    first_char = corrected_title[0].upper()
    if first_char.isdigit():
        folder_name = "#"
    elif first_char.isalpha():
        folder_name = first_char
    else:
        folder_name = "Misc"

    folder_path = os.path.join("E:\\Movies", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

# Function to sanitize folder names
def sanitize_folder_name(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

# Function to download a movie based on the given title
def download_movie(title):
    movie_details = tmdb_helper.get_media_details(title, media_type='movie')
    if not movie_details:
        print(f"No movie details found for: {title}")
        return

    movie_name = f"{movie_details['title']} ({movie_details['release_date'][:4]})"
    sanitized_movie_name = sanitize_folder_name(movie_name)
    release_year = movie_details.get('release_date', '')[:4]

    if jellyfin_helper.item_exists(movie_name, release_year, type='movie'):
        print(f"Movie '{movie_name}' already exists in Jellyfin. Skipping download.")
        remove_processed_film(title)
        return

    if tmdb_helper.is_part_of_franchise(movie_details):
        print(f"'{movie_name}' is part of a series or franchise. Checking all related movies...")
        franchise_movies = tmdb_helper.get_franchise_movies(movie_details)
        for franchise_movie in franchise_movies:
            franchise_movie_name = f"{franchise_movie['title']} ({franchise_movie['release_date'][:4]})"
            if jellyfin_helper.item_exists(franchise_movie_name, release_year, type='movie'):
                print(f"Related movie '{franchise_movie_name}' already exists in Jellyfin. Skipping download.")
                remove_processed_film(title)
                return

    print(f"Searching for torrents for: {movie_name}")

    magnet_link = jackett_helper.search_jackett(movie_name)
    if not magnet_link:
        print(f"No torrent found for: {movie_name}")
        return

    download_folder = get_directory_for_title(movie_name)
    download_folder = os.path.join(download_folder, sanitized_movie_name)
    os.makedirs(download_folder, exist_ok=True)

    print(f"Adding torrent for: {movie_name} to {download_folder}")
    qb_helper.add_torrent(magnet_link, save_path=download_folder, rename=sanitized_movie_name)

    force_jellyfin_library_scan()
    remove_processed_film(title)

# Function to force Jellyfin library scan
def force_jellyfin_library_scan():
    url = f"{config['Jellyfin']['server_url']}/Library/Refresh"
    headers = {"X-Emby-Token": config['Jellyfin']['api_key']}
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 204:
            print("Jellyfin library scan triggered successfully.")
        else:
            print(f"Failed to trigger Jellyfin library scan: {response.status_code}")
    except Exception as e:
        print(f"Error triggering Jellyfin library scan: {e}")

# Function to remove a processed movie from the request list
def remove_processed_film(title):
    try:
        with open(FILMS_LIST_PATH, 'r') as file:
            lines = file.readlines()
        with open(FILMS_LIST_PATH, 'w') as file:
            for line in lines:
                if line.strip().lower() != title.lower():
                    file.write(line)
    except Exception as e:
        print(f"Error while removing processed movie from the list: {e}")

# Main function to read movies from the request list and start downloading
def process_films_list():
    if not os.path.exists(FILMS_LIST_PATH):
        print(f"Error: Films list file '{FILMS_LIST_PATH}' does not exist.")
        sys.exit(1)

    with open(FILMS_LIST_PATH, 'r') as file:
        film_titles = [line.strip() for line in file.readlines() if line.strip()]

    if not film_titles:
        print("No movie titles found in the list.")
        return

    for film_title in film_titles:
        download_movie(film_title)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        movie_title = sys.argv[1]
        download_movie(movie_title)
    else:
        process_films_list()
