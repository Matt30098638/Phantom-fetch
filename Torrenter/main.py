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
from utils.qbittorrent_helper import QBittorrentHelper
from utils.jackett_helper import JackettHelper
from PyQt5.QtWidgets import QInputDialog

# Initialize qBittorrent helper
qb_helper = QBittorrentHelper()
jackett_helper = JackettHelper()

if getattr(sys, 'frozen', False):  # PyInstaller context
    APPLICATION_PATH = sys._MEIPASS
else:
    APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))

# Reference config.yaml using APPLICATION_PATH
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
MAX_ACTIVE_DOWNLOADS = 30

# Jellyfin Configuration
JELLYFIN_SERVER_URL = config['Jellyfin']['server_url']
JELLYFIN_API_KEY = config['Jellyfin']['api_key']

# Setting up Helpers
jellyfin_helper = JellyfinHelper(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY)
tmdb_helper = TMDbHelper(config_path=CONFIG_FILE)
spotify_helper = SpotifyHelper(client_id=config['Spotify']['client_id'], client_secret=config['Spotify']['client_secret'])

# Log function with size restriction
def log_message(message):
    if os.path.exists(LOG_FILE_PATH) and os.path.getsize(LOG_FILE_PATH) > 10 * 1024 * 1024:  # Limit 10 MB
        os.remove(LOG_FILE_PATH)
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Function to manage continuous monitoring and cleanup for qBittorrent
def continuous_monitoring(helper):
    while True:
        helper.remove_completed_torrents()  # Check and clean up completed torrents
        time.sleep(60)  # Check every minute

# Function to retrieve and monitor current downloads continuously
def get_current_downloads():
    try:
        downloading_torrents = qb_helper.qb.torrents_info(status_filter='downloading')
        download_list = []
        for torrent in downloading_torrents:
            progress = round(torrent.progress * 100, 2)
            download_list.append(f"{torrent.name} - {progress}% complete at {torrent.dlspeed / (1024**2):.2f} MB/s")
        return download_list
    except Exception as e:
        log_message(f"Error fetching current downloads: {e}")
        return ["Error retrieving downloads"]

def get_request_lists():
    """Retrieve current requests for movies, TV shows, and music from their respective lists."""
    def read_file(file_path):
        print(f"Attempting to read file: {file_path}")  # Debug: Check which file path is accessed
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = [line.strip() for line in file if line.strip()]
                print(f"Successfully read {len(lines)} items from {file_path}")  # Debug: Check number of lines read
                return lines
        else:
            print(f"File does not exist: {file_path}")  # Debug: Notify if file path is incorrect
        return []
    
    # Paths assumed to be defined elsewhere in the codebase
    movies = read_file(FILMS_LIST_PATH)
    tv_shows = read_file(TV_SHOWS_LIST_PATH)
    music = read_file(MUSIC_LIST_PATH)
    
    print("Movies:", movies)       # Debug: Display movie list
    print("TV Shows:", tv_shows)    # Debug: Display TV show list
    print("Music:", music)          # Debug: Display music list
    
    return movies, tv_shows, music

# Ensure directories and files exist
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
for file_path in [FILMS_LIST_PATH, TV_SHOWS_LIST_PATH, MUSIC_LIST_PATH]:
    if not os.path.exists(file_path):
        open(file_path, 'w').close()

def detect_category(title):
    """
    Detects the category of a title based on keywords or patterns.
    Returns the corresponding file path for Movies, TV Shows, or Music.
    """
    # Define keywords for each category
    movie_keywords = ["movie", "film", "cinema", "episode", "saga", "part", "trilogy"]
    tv_show_keywords = ["season", "series", "episode", "tv show", "show"]
    music_keywords = ["album", "song", "music", "track", "single", "band", "concert"]

    # Convert title to lowercase for easier matching
    title_lower = title.lower()

    # Check for keywords in title
    if any(keyword in title_lower for keyword in movie_keywords):
        return FILMS_LIST_PATH
    elif any(keyword in title_lower for keyword in tv_show_keywords):
        return TV_SHOWS_LIST_PATH
    elif any(keyword in title_lower for keyword in music_keywords):
        return MUSIC_LIST_PATH
    else:
        # If no keywords match, return None (unclassified)
        return None

def get_category_name(file_path):
    """
    Returns the category name (Movies, TV Shows, or Music) based on the file path.
    """
    if file_path == FILMS_LIST_PATH:
        return "Movies"
    elif file_path == TV_SHOWS_LIST_PATH:
        return "TV Shows"
    elif file_path == MUSIC_LIST_PATH:
        return "Music"
    else:
        return "Unknown"

def add_request(title):
    """
    Adds a request to the appropriate category file based on title.
    """
    # Determine the category based on the title
    list_path = detect_category(title)

    # If no category is detected, prompt the user to choose
    if not list_path:
        category, ok = QInputDialog.getItem(
            None, "Select Category", 
            f"Could not categorize '{title}'. Please select a category:", 
            ["Movies", "TV Shows", "Music"], 0, False
        )
        if not ok or not category:
            return f"Request for '{title}' was canceled."

        # Map the selected category to its file path
        if category == "Movies":
            list_path = FILMS_LIST_PATH
        elif category == "TV Shows":
            list_path = TV_SHOWS_LIST_PATH
        elif category == "Music":
            list_path = MUSIC_LIST_PATH

    # Append to the appropriate list
    with open(list_path, 'a', encoding='utf-8') as file:
        file.write(title + "\n")

    return f"Added '{title}' to {get_category_name(list_path)} requests."

# Backend function to delete a request from the list
def edit_request(old_title, new_title, list_path):
    try:
        if os.path.exists(list_path):
            with open(list_path, 'r', encoding='utf-8') as file:
                requests = [line.strip() for line in file]

            # Update the title if it matches the old title
            updated_requests = [new_title if req.lower() == old_title.lower() else req for req in requests]

            # Write back the updated requests to the file
            with open(list_path, 'w', encoding='utf-8') as file:
                file.write("\n".join(updated_requests) + "\n")

            return True
    except Exception as e:
        print(f"Error editing request from '{old_title}' to '{new_title}' in list '{list_path}': {e}")
    return False

def delete_request(title, list_path):
    try:
        if os.path.exists(list_path):
            with open(list_path, 'r', encoding='utf-8') as file:
                requests = [line.strip() for line in file]

            # Remove the request with the matching title
            updated_requests = [req for req in requests if req.lower() != title.lower()]

            # Write back the updated requests to the file
            with open(list_path, 'w', encoding='utf-8') as file:
                file.write("\n".join(updated_requests) + "\n")

            return True
    except Exception as e:
        print(f"Error deleting '{title}' from '{list_path}': {e}")
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
            time.sleep(30)
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
