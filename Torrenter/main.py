import os
import sys
import time
import threading
import requests
import yaml
from qbittorrentapi import Client
from msal import PublicClientApplication, SerializableTokenCache
from utils.tmdb_helper import TMDbHelper
from Movies import download_movie  # Assuming `Movies.py` contains the function download_movie(title)
from TV import download_tv_show  # Assuming `TV.py` contains the function download_tv_show(title)
from Teams_Requests import get_access_token, get_messages_from_chat
from utils.music_helper import SpotifyHelper, download_music

# Determine the correct path for config.yaml, both for development and packaged runs
APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APPLICATION_PATH, 'assets', 'config.yaml')
if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError("Configuration file 'config.yaml' is missing.")

with open(CONFIG_FILE, 'r') as config_file:
    config = yaml.safe_load(config_file)

# Configurations
TMDB_API_KEY = config['TMDb']['api_key']
FILMS_LIST_PATH = 'E:\\requests\\Film-list.txt'
TV_SHOWS_LIST_PATH = 'E:\\requests\\Tv-Shows.txt'
MUSIC_LIST_PATH = 'E:\\requests\\Music-list.txt'
LOG_FILE_PATH = os.path.join(APPLICATION_PATH, 'logs', 'app_log.txt')
MAX_ACTIVE_DOWNLOADS = 15  # Maximum number of concurrent downloads allowed

# Ensure directories and files exist
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
for file_path in [FILMS_LIST_PATH, TV_SHOWS_LIST_PATH, MUSIC_LIST_PATH]:
    if not os.path.exists(file_path):
        open(file_path, 'w').close()

# qBittorrent Configuration
qb = Client(
    host=config['qBittorrent']['host'],
    username=config['qBittorrent']['username'],
    password=config['qBittorrent']['password']
)

# Setting up Helpers
tmdb_helper = TMDbHelper(config_path=CONFIG_FILE)
spotify_helper = SpotifyHelper(client_id=config['Spotify']['client_id'], client_secret=config['Spotify']['client_secret'])

# Log function with size restriction
def log_message(message):
    if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > 10 * 1024 * 1024:  # Limit 10 MB
        os.remove(LOG_FILE_PATH)
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Backend function to delete a request from the list
def delete_request(title, list_path):
    try:
        if os.path.exists(list_path):
            with open(list_path, 'r', encoding='utf-8') as file:
                requests = [line.strip() for line in file.readlines()]
            updated_requests = [req for req in requests if req.lower() != title.lower()]
            with open(list_path, 'w', encoding='utf-8') as file:
                for req in updated_requests:
                    file.write(f"{req}\n")
            log_message(f"Removed completed request: {title}")
            return True
    except Exception as e:
        log_message(f"Error removing completed title '{title}' from request list '{list_path}': {e}")
    return False

# Verification functions for downloaded content
def verify_movie(title):
    return tmdb_helper.verify_movie_in_jellyfin(title)

def verify_tv_show(title):
    return tmdb_helper.verify_tv_show_in_jellyfin(title)

def verify_music(title):
    return spotify_helper.verify_music_in_jellyfin(title)

# Function to manage the round-robin downloading of TV shows, movies, and music
def manage_downloads():
    round_robin = ["tv", "movie", "music"]
    list_paths = {
        "tv": TV_SHOWS_LIST_PATH,
        "movie": FILMS_LIST_PATH,
        "music": MUSIC_LIST_PATH
    }
    current_index = 0

    while True:
        active_downloads = len([t for t in qb.torrents_info() if t.state == 'downloading'])
        if active_downloads >= MAX_ACTIVE_DOWNLOADS:
            log_message(f"Max active downloads reached: {active_downloads}. Waiting for slots to free up...")
            time.sleep(10)
            continue

        content_type = round_robin[current_index]
        list_path = list_paths[content_type]

        # Read the first line (next title to process) from the list file
        title = None
        if os.path.exists(list_path) and os.path.getsize(list_path) > 0:
            with open(list_path, 'r', encoding='utf-8') as file:
                title = file.readline().strip()

        if title:
            log_message(f"Processing {content_type} request: {title}")
            
            # Start the download process based on content type
            if content_type == "movie":
                if download_movie(title):  # Assume download_movie returns True if download started
                    if verify_movie(title):
                        delete_request(title, FILMS_LIST_PATH)
            elif content_type == "tv":
                if download_tv_show(title):  # Assume download_tv_show returns True if download started
                    if verify_tv_show(title):
                        delete_request(title, TV_SHOWS_LIST_PATH)
            elif content_type == "music":
                if download_music(title):  # Assume download_music returns True if download started
                    if verify_music(title):
                        delete_request(title, MUSIC_LIST_PATH)

        # Move to the next content type in the round-robin order
        current_index = (current_index + 1) % len(round_robin)
        time.sleep(1)  # Small delay to avoid overwhelming requests

# Start threads for managing downloads and monitoring Teams
download_management_thread = threading.Thread(target=manage_downloads, daemon=True)
download_management_thread.start()

def monitor_teams():
    while True:
        access_token = get_access_token()
        if not access_token:
            log_message("Unable to retrieve Teams access token.")
            time.sleep(300)
            continue

        chat_ids = config['MicrosoftGraph'].get('chat_ids', [])
        for chat_id in chat_ids:
            messages = get_messages_from_chat(chat_id, access_token)
            for message in messages:
                title = message.get('body', {}).get('content', '').strip()
                if title:
                    result_message = add_request(title)
                    log_message(result_message)
        time.sleep(60)  # Monitor every 1 minute

teams_monitor_thread = threading.Thread(target=monitor_teams, daemon=True)
teams_monitor_thread.start()
