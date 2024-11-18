import requests
import logging
from config import Config
from app.models import db, Media
from datetime import datetime

logging.basicConfig(level=logging.INFO)

class JellyfinHelper:
    def __init__(self):
        config = Config()
        self.server_url = config.JELLYFIN_SERVER_URL
        self.api_key = config.JELLYFIN_API_KEY

        if not self.server_url or not self.api_key:
            raise ValueError("Jellyfin configuration is missing 'server_url' or 'api_key'.")

    def get_media_items(self, media_type='Movie'):
        """Fetch all media items of a specific type from Jellyfin."""
        url = f"{self.server_url}/Items"
        headers = {
            "X-Emby-Token": self.api_key
        }
        params = {
            "IncludeItemTypes": media_type,
            "Recursive": "true"
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            items = response.json().get('Items', [])
            logging.info(f"Fetched {len(items)} {media_type.lower()} items from Jellyfin.")
            return items
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch {media_type.lower()} items from Jellyfin: {e}")
            return []

    def save_items_to_db(self):
        """Fetch movies and TV shows from Jellyfin and save them to the MySQL database."""
        movie_items = self.get_media_items(media_type='Movie')
        show_items = self.get_media_items(media_type='Series')

        all_items = movie_items + show_items
        if not all_items:
            logging.info("No items to save to the database.")
            return

        # Clear the Media table to avoid duplicates (or use your preferred duplicate handling method)
        db.session.query(Media).delete()
        db.session.commit()

        new_media_count = 0

        for item in all_items:
            title = item.get('Name')
            media_type = item.get('Type')
            release_date = item.get('ProductionYear')
            path = item.get('Path', '')
            description = item.get('Overview', '')

            # Convert Jellyfin's type to custom media type
            if media_type == 'Movie':
                media_type = 'Movie'
            elif media_type == 'Series':
                media_type = 'TV Show'

            # Check if the item already exists in the database
            existing_media = Media.query.filter_by(title=title, media_type=media_type).first()
            if not existing_media:
                try:
                    new_media = Media(
                        title=title,
                        media_type=media_type,
                        release_date=datetime.strptime(str(release_date), '%Y') if release_date else None,
                        path=path,
                        description=description
                    )
                    db.session.add(new_media)
                    new_media_count += 1
                except ValueError as date_error:
                    logging.error(f"Error parsing release date for {title}: {date_error}")

        try:
            db.session.commit()
            logging.info(f"Added {new_media_count} new items to the database.")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Failed to commit items to the database: {e}")
