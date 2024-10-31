import os
import yaml

class Config:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'config.yaml')

    def __init__(self):
        if not os.path.exists(self.CONFIG_PATH):
            raise FileNotFoundError(f"Configuration file '{self.CONFIG_PATH}' is missing.")
        
        with open(self.CONFIG_PATH, 'r') as file:
            self.config = yaml.safe_load(file)

    def get_jackett_config(self):
        return self.config.get('Jackett', {})

    def get_qbittorrent_config(self):
        return self.config.get('qBittorrent', {})

    def get_tmdb_config(self):
        return self.config.get('TMDb', {})

    def get_jellyfin_config(self):
        return self.config.get('Jellyfin', {})

    def get_media_paths(self):
        return {
            'movies': self.config['Paths']['movies'],
            'tv_shows': self.config['Paths']['tv_shows'],
            'music': self.config['Paths']['music']
        }
        
config = Config()
