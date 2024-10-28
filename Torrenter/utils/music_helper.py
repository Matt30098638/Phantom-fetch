import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from utils.jackett_helper import JackettHelper
from utils.qbittorrent_helper import QBittorrentHelper
import logging

# Load the configuration
CONFIG_FILE = 'assets/config.yaml'
jackett_helper = JackettHelper(config_path=CONFIG_FILE)
qb_helper = QBittorrentHelper(config_path=CONFIG_FILE)

class SpotifyHelper:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

    def is_music(self, title):
        try:
            results = self.spotify.search(q=title, type='track,album,artist', limit=1)
            return len(results['tracks']['items']) > 0 or len(results['albums']['items']) > 0 or len(results['artists']['items']) > 0
        except Exception as e:
            logging.error(f"Error checking music for title '{title}': {e}")
            return False

    def get_metadata(self, title):
        try:
            results = self.spotify.search(q=title, type='track,album,artist', limit=1)
            if results['tracks']['items']:
                return results['tracks']['items'][0]
            elif results['albums']['items']:
                return results['albums']['items'][0]
            elif results['artists']['items']:
                return results['artists']['items'][0]
            else:
                return None
        except Exception as e:
            logging.error(f"Error retrieving metadata for '{title}': {e}")
            return None

# Function to download music using Jackett and qBittorrent
def download_music(title):
    try:
        # Search for the torrent using Jackett
        magnet_link = jackett_helper.search_jackett(title, category='Music')
        if not magnet_link:
            logging.error(f"No torrents found for music title: {title}")
            return

        # Add the torrent to qBittorrent for downloading
        if magnet_link:
            qb_helper.add_torrent(magnet_link, save_path="E:\\Music\\Downloads")  # Update with the desired save path
            logging.info(f"Started download for: {title}")
        else:
            logging.error(f"Failed to find magnet link for: {title}")
    except Exception as e:
        logging.error(f"Error during music download process for '{title}': {e}")
