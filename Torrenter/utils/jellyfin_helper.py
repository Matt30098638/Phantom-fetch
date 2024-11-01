from qbittorrentapi import Client
from config import config
import os
import time
import subprocess

APPLICATION_PATH = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APPLICATION_PATH, 'assets', 'config.yaml')

class QBittorrentHelper:
    def __init__(self, max_retries=3, retry_delay=5):
        qb_config = config.get_qbittorrent_config()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.qbittorrent_path = qb_config.get('path', '/path/to/qbittorrent')  # Path to qBittorrent executable

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

    def check_running(self):
        """Check if qBittorrent is running by testing the client connection."""
        try:
            self.qb.app_version()
            return True
        except Exception:
            print("qBittorrent is not running or inaccessible.")
            return False

    def start_service(self):
        """Attempt to start qBittorrent service if it's not running."""
        try:
            subprocess.Popen([self.qbittorrent_path])  # Start qBittorrent executable
            time.sleep(5)  # Allow some time for qBittorrent to start
            print("Attempting to start qBittorrent...")
            if self.check_running():
                print("qBittorrent started successfully.")
                return True
            else:
                print("qBittorrent failed to start.")
                return False
        except Exception as e:
            print(f"Failed to start qBittorrent: {e}")
            return False

    def retry_operation(func):
        """Decorator for retrying operations on failure."""
        def wrapper(self, *args, **kwargs):
            for attempt in range(1, self.max_retries + 1):
                try:
                    if not self.check_running():
                        print("qBittorrent is not running. Attempting to start...")
                        if not self.start_service():
                            print("Could not start qBittorrent service.")
                            return None
                    return func(self, *args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempt} failed: {e}")
                    time.sleep(self.retry_delay)
            print(f"Operation failed after {self.max_retries} attempts.")
        return wrapper

    @retry_operation
    def get_active_downloads(self):
        """Retrieve the number of active (downloading) torrents."""
        torrents = self.qb.torrents_info(status_filter='downloading')
        return len(torrents)

    @retry_operation
    def add_torrent(self, magnet_link, save_path, rename=None):
        """Add a new torrent using a magnet link."""
        self.qb.torrents_add(
            urls=magnet_link,
            save_path=save_path,
            rename=rename
        )
        print(f"Added torrent for: {rename} to {save_path}")

    @retry_operation
    def remove_completed_torrents(self, delete_files=False):
        """Remove torrents that have completed (seeding) with optional file deletion."""
        torrents = self.qb.torrents_info()
        for torrent in torrents:
            if torrent.state in ['seeding', 'pausedUP', 'completed']:
                print(f"Removing completed torrent: {torrent.name}")
                self.qb.torrents_delete(delete_files=delete_files, torrent_hashes=torrent.hash)

    @retry_operation
    def get_stalled_torrents(self):
        """Retrieve torrents that are stalled."""
        return [t for t in self.qb.torrents_info() if t.state == 'stalledDL']

    def monitor_and_cleanup(self):
        """Monitor and remove torrents based on their state."""
        try:
            torrents = self.qb.torrents_info()
            for torrent in torrents:
                if torrent.state == 'seeding':
                    print(f"Removing completed torrent: {torrent.name}")
                    self.qb.torrents_delete(delete_files=False, torrent_hashes=torrent.hash)
                elif torrent.state == 'stalledDL':
                    print(f"Removing stalled torrent: {torrent.name}")
                    self.qb.torrents_delete(delete_files=False, torrent_hashes=torrent.hash)
        except Exception as e:
            print(f"Error during monitoring and cleanup: {e}")

    def pause_all_downloads(self):
        """Pause all active downloads."""
        try:
            self.qb.torrents_pause(torrent_hashes="all")
            print("All downloads paused.")
        except Exception as e:
            print(f"Error pausing all downloads: {e}")

    def resume_all_downloads(self):
        """Resume all paused downloads."""
        try:
            self.qb.torrents_resume(torrent_hashes="all")
            print("All downloads resumed.")
        except Exception as e:
            print(f"Error resuming all downloads: {e}")
