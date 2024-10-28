import os
import logging
import yaml
from utils.music_helper import SpotifyHelper, download_music

# Load configuration from config.yaml
APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APPLICATION_PATH, 'assets', 'config.yaml')

if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError(f"Configuration file '{CONFIG_FILE}' is missing.")

with open(CONFIG_FILE, 'r') as file:
    config = yaml.safe_load(file)

# Path to Music Request File (updated to new path)
MUSIC_LIST_PATH = 'E:\\requests\\Music-list.txt'

# Initialize SpotifyHelper using Spotify credentials
spotify_config = config.get('Spotify', {})
CLIENT_ID = spotify_config.get('client_id')
CLIENT_SECRET = spotify_config.get('client_secret')

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Missing Spotify credentials in the configuration file.")

spotify_helper = SpotifyHelper(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# Function to load music requests from Music-list.txt
def load_music_requests(file_path):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logging.error(f"Music request file not found at {file_path}")
        return []

# Function to remove a processed music request from the list
def remove_processed_music(title):
    try:
        with open(MUSIC_LIST_PATH, 'r') as file:
            lines = file.readlines()
        with open(MUSIC_LIST_PATH, 'w') as file:
            for line in lines:
                if line.strip().lower() != title.lower():
                    file.write(line)
    except Exception as e:
        logging.error(f"Error while removing processed music from the list: {e}")

# Function to handle the music request
def handle_music_request(title):
    """
    Handles music request and manages the downloading process.

    :param title: Title of the music requested
    """
    logging.info(f"Processing request for: {title}")

    # Step 1: Verify if the request is related to music using Spotify
    if spotify_helper.is_music(title):
        logging.info(f"'{title}' is recognized as music.")

        # Step 2: Retrieve metadata for the title
        metadata = spotify_helper.get_metadata(title)
        if metadata:
            logging.info(f"Metadata found for '{title}': {metadata}")
        else:
            logging.warning(f"No metadata found for '{title}', but proceeding to search Jackett.")

        # Step 3: Initiate the download process using Jackett and qBittorrent
        download_music(title)

        # Step 4: Remove the processed music from the request list
        remove_processed_music(title)
    else:
        logging.warning(f"'{title}' was not found as music in Spotify.")

# Main function to process the music request list
def process_music_list():
    if not os.path.exists(MUSIC_LIST_PATH):
        logging.error(f"Error: Music request file '{MUSIC_LIST_PATH}' does not exist.")
        return

    music_titles = load_music_requests(MUSIC_LIST_PATH)
    if not music_titles:
        logging.info("No music titles found in the list.")
        return

    # Process each music title in the list
    for music_title in music_titles:
        handle_music_request(music_title)

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Process the music list
    process_music_list()
