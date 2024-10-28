import os
import yaml
from qbittorrentapi import Client

class QBittorrentHelper:
    def __init__(self, config_path= '' 'assets' 'config.yaml'):
        # Load configuration from YAML
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' is missing.")

        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        qb_config = config.get('qBittorrent', {})

        try:
            # Initialize qBittorrent client with settings from the configuration
            self.qb = Client(
                host=qb_config.get('host', 'http://127.0.0.1:8080'),
                username=qb_config.get('username', 'admin'),
                password=qb_config.get('password', '')
            )
            print("Connected to qBittorrent successfully.")
        except Exception as e:
            print(f"Error connecting to qBittorrent: {e}")

    def get_active_downloads(self):
        try:
            torrents = self.qb.torrents_info(status_filter='downloading')
            return len(torrents)
        except Exception as e:
            print(f"Error getting active downloads: {e}")
            return 0

    def add_torrent(self, magnet_link, save_path, rename=None):
        try:
            self.qb.torrents_add(
                urls=magnet_link,
                save_path=save_path,
                rename=rename
            )
            print(f"Added torrent for: {rename} to {save_path}")
        except Exception as e:
            print(f"Error adding torrent: {e}")

    def remove_completed_torrents(self):
        try:
            torrents = self.qb.torrents_info()
            for torrent in torrents:
                if torrent.state == 'uploading':
                    print(f"Removing completed torrent: {torrent.name}")
                    self.qb.torrents_delete(delete_files=False, torrent_hashes=torrent.hash)
        except Exception as e:
            print(f"Error removing completed torrents: {e}")
