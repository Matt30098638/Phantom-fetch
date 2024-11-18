import os
import yaml

# Load configuration from the YAML file
CONFIG_PATH = 'config.yaml'
WTF_CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:5000', 'http://10.252.0.4:5000']
WTF_CSRF_ENABLED = True

class Config:
    def __init__(self):
        with open(CONFIG_PATH, 'r') as file:
            config = yaml.safe_load(file)
        
        self.QB_API_URL = config['qBittorrent']['host']
        self.QB_USERNAME = config['qBittorrent']['username']
        self.QB_PASSWORD = config['qBittorrent']['password']
        
        self.JACKETT_API_URL = config['Jackett']['server_url']
        self.JACKETT_API_KEY = config['Jackett']['api_key']
        self.JACKETT_CATEGORIES = config['Jackett']['categories']
        
        self.JELLYFIN_API_KEY = config['Jellyfin']['api_key']
        self.JELLYFIN_SERVER_URL = config['Jellyfin']['server_url']
        
        self.SPOTIFY_CLIENT_ID = config['Spotify']['client_id']
        self.SPOTIFY_CLIENT_SECRET = config['Spotify']['client_secret']
        
        self.OUTLOOK_CLIENT_ID = config['MicrosoftGraph']['client_id']
        self.OUTLOOK_TENANT_ID = config['MicrosoftGraph']['tenant_id']
        self.OUTLOOK_SCOPES = config['MicrosoftGraph']['scopes']
        self.OUTLOOK_CACHE_FILE_PATH = config['MicrosoftGraph']['cache_file_path']
        
        self.TMDB_API_KEY = config['TMDb']['api_key']
        
        # Database Configuration
        self.SQLALCHEMY_DATABASE_URI = config['Database']['uri']
        self.SQLALCHEMY_TRACK_MODIFICATIONS = config['Database']['track_modifications']
        
        # Ensure the correct key casing for SECRET_KEY
        self.SECRET_KEY = config['Secret_key']  # Correctly matches the YAML key
