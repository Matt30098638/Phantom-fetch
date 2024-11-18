from qbittorrentapi import Client
from config import Config
import logging
import time

logging.basicConfig(level=logging.INFO)


class QBittorrentHelper:
    def __init__(self, max_retries=3, retry_delay=5):
        config = Config()
        qb_config = {
            'host': config.QB_API_URL,
            'username': config.QB_USERNAME,
            'password': config.QB_PASSWORD
        }
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        try:
            self.qb = Client(
                host=qb_config['host'],
                username=qb_config['username'],
                password=qb_config['password']
            )
            self.qb.auth_log_in()
            logging.info("Connected to qBittorrent successfully.")
        except Exception as e:
            logging.error(f"Error connecting to qBittorrent: {e}")
            raise e

    def retry_operation(method):
        """Decorator to retry a method on failure."""
        def wrapper(self, *args, **kwargs):
            for attempt in range(1, self.max_retries + 1):
                try:
                    return method(self, *args, **kwargs)
                except Exception as e:
                    logging.warning(f"Attempt {attempt} for {method.__name__} failed: {e}")
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)
                    else:
                        logging.error(f"Operation {method.__name__} failed after {self.max_retries} attempts.")
                        raise e
        return wrapper

    @retry_operation
    def get_active_downloads(self):
        """Retrieve active torrents and return details."""
        try:
            torrents = self.qb.torrents_info(status_filter='downloading')
            logging.info(f"Retrieved {len(torrents)} active downloads.")
            return torrents
        except Exception as e:
            logging.error(f"Error fetching active downloads: {e}")
            raise e

    @retry_operation
    def add_torrent(self, magnet_link, save_path):
        """Add a torrent using a magnet link."""
        try:
            # Validate magnet link
            if not magnet_link.startswith("magnet:?xt=urn:btih:"):
                raise ValueError("Invalid magnet link format.")

            # Add the torrent
            self.qb.torrents_add(urls=magnet_link, save_path=save_path)
            logging.info(f"Torrent added successfully. Magnet link: {magnet_link}, Save path: {save_path}")

        except Exception as e:
            logging.error(f"Error in add_torrent: {e}")
            raise e

    @retry_operation
    def remove_completed_torrents(self, delete_files=False):
        """Remove torrents that are completed."""
        try:
            torrents = self.qb.torrents_info()
            for torrent in torrents:
                if torrent.state in ['seeding', 'pausedUP', 'completed']:
                    logging.info(f"Removing completed torrent: {torrent.name}")
                    self.qb.torrents_delete(delete_files=delete_files, torrent_hashes=torrent.hash)
        except Exception as e:
            logging.error(f"Error removing completed torrents: {e}")
            raise e

    @retry_operation
    def get_stalled_torrents(self):
        """Retrieve stalled torrents."""
        try:
            stalled_torrents = [t for t in self.qb.torrents_info() if t.state == 'stalledDL']
            logging.info(f"Retrieved {len(stalled_torrents)} stalled torrents.")
            return stalled_torrents
        except Exception as e:
            logging.error(f"Error fetching stalled torrents: {e}")
            raise e

    @retry_operation
    def pause_all_downloads(self):
        """Pause all active downloads."""
        try:
            self.qb.torrents_pause(torrent_hashes="all")
            logging.info("All downloads paused.")
        except Exception as e:
            logging.error(f"Error pausing all downloads: {e}")
            raise e

    @retry_operation
    def resume_all_downloads(self):
        """Resume all paused downloads."""
        try:
            self.qb.torrents_resume(torrent_hashes="all")
            logging.info("All downloads resumed.")
        except Exception as e:
            logging.error(f"Error resuming all downloads: {e}")
            raise e
