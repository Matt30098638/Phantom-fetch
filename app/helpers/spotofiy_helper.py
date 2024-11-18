import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app.helpers.jackett_helper import JackettHelper  # Corrected absolute import
from app.helpers.qbittorrent_helper import QBittorrentHelper  # Corrected absolute import
import logging
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load configuration details for helper classes
jackett_helper = JackettHelper()
qb_helper = QBittorrentHelper()

class SpotifyHelper:
    def __init__(self):
        # Load configuration using the Config class
        config = Config()
        self.client_id = config.SPOTIFY_CLIENT_ID
        self.client_secret = config.SPOTIFY_CLIENT_SECRET

        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify configuration is missing 'client_id' or 'client_secret'.")

        # Initialize Spotipy with the credentials
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=self.client_id, client_secret=self.client_secret))

    def is_music(self, title):
        """Check if the given title exists as music in Spotify."""
        try:
            results = self.spotify.search(q=title, type='track,album,artist', limit=1)
            return len(results['tracks']['items']) > 0 or len(results['albums']['items']) > 0 or len(results['artists']['items']) > 0
        except Exception as e:
            logging.error(f"Error checking music for title '{title}': {e}")
            return False

    def get_metadata(self, title):
        """Retrieve metadata for the given title from Spotify."""
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
    """Search for a music torrent using Jackett and add it to qBittorrent for downloading."""
    try:
        # Search for the torrent using Jackett
        magnet_link = jackett_helper.search_jackett(title, category='Music')
        if not magnet_link:
            logging.error(f"No torrents found for music title: {title}")
            return

        # Add the torrent to qBittorrent for downloading
        qb_helper.add_torrent(magnet_link, save_path="E:\\Music\\Downloads")  # Update with the desired save path
        logging.info(f"Started download for: {title}")
    except Exception as e:
        logging.error(f"Error during music download process for '{title}': {e}")
