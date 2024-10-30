import os
import sys
import time
import threading
import requests
import yaml
from qbittorrentapi import Client
from msal import PublicClientApplication, SerializableTokenCache
from utils.tmdb_helper import TMDbHelper
from utils.jellyfin_helper import JellyfinHelper
from Movies import download_movie
from TV import download_tv_show
from Teams_Requests import get_access_token, get_filtered_emails, process_requests
from utils.music_helper import SpotifyHelper, download_music

# Determine the correct path for config.yaml
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

# Jellyfin Configuration
JELLYFIN_SERVER_URL = config['Jellyfin']['server_url']
JELLYFIN_API_KEY = config['Jellyfin']['api_key']

# Setting up Helpers
jellyfin_helper = JellyfinHelper(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY)
tmdb_helper = TMDbHelper(config_path=CONFIG_FILE)
spotify_helper = SpotifyHelper(client_id=config['Spotify']['client_id'], client_secret=config['Spotify']['client_secret'])

# qBittorrent Configuration
qb = Client(
    host=config['qBittorrent']['host'],
    username=config['qBittorrent']['username'],
    password=config['qBittorrent']['password']
)

# Log function with size restriction
def log_message(message):
    if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > 10 * 1024 * 1024:  # Limit 10 MB
        os.remove(LOG_FILE_PATH)
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")


def get_request_lists():
    """Retrieve current requests for movies, TV shows, and music from their respective lists."""
    def read_file(file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return [line.strip() for line in file if line.strip()]
        return []
    
    movies = read_file(FILMS_LIST_PATH)
    tv_shows = read_file(TV_SHOWS_LIST_PATH)
    music = read_file(MUSIC_LIST_PATH)
    
    return movies, tv_shows, music


# Ensure directories and files exist
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
for file_path in [FILMS_LIST_PATH, TV_SHOWS_LIST_PATH, MUSIC_LIST_PATH]:
    if not os.path.exists(file_path):
        open(file_path, 'w').close()

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


# Verification functions for downloaded content using Jellyfin
def verify_movie(title):
    return jellyfin_helper.item_exists(title, type="Movie")

def verify_tv_show(title):
    return jellyfin_helper.item_exists(title, type="Series")

def verify_music(title):
    return jellyfin_helper.item_exists(title, type="Audio")


# Function to retrieve Outlook messages
def get_outlook_messages():
    access_token = get_access_token()
    if not access_token:
        log_message("Unable to fetch Outlook messages: No valid access token.")
        return []

    emails = get_filtered_emails(access_token)
    messages = [f"Subject: {email.get('subject', 'No Subject')}\nPreview: {email.get('bodyPreview', 'No Body Preview')}" for email in emails]
    return messages

# Function to retrieve current downloads
def get_current_downloads():
    try:
        # Retrieve a list of torrents with 'downloading' status
        downloading_torrents = qb.torrents_info(status_filter='downloading')
        download_list = []
        for torrent in downloading_torrents:
            progress = round(torrent.progress * 100, 2)  # Format progress as a percentage
            download_list.append(f"{torrent.name} - {progress}% complete at {torrent.dlspeed / (1024**2):.2f} MB/s")
        return download_list
    except Exception as e:
        log_message(f"Error fetching current downloads: {e}")
        return ["Error retrieving downloads"]

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

# Function to continuously monitor Teams for new requests
def monitor_teams():
    while True:
        access_token = get_access_token()
        if not access_token:
            log_message("Unable to retrieve Teams access token.")
            time.sleep(300)
            continue

        # Get emails from Teams
        emails = get_filtered_emails(access_token)
        process_requests(emails, 
                         FILMS_LIST_PATH, 
                         TV_SHOWS_LIST_PATH, 
                         MUSIC_LIST_PATH,
                         access_token)

        time.sleep(60)  # Monitor every 1 minute

# Start the Teams monitor thread
teams_monitor_thread = threading.Thread(target=monitor_teams, daemon=True)
teams_monitor_thread.start()
