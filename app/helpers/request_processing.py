import logging
from app.models import Request, db
from app.helpers.jackett_helper import JackettHelper, normalize_media_type
from app.helpers.qbittorrent_helper import QBittorrentHelper
from app.helpers.tmdb_helper import TMDbHelper
from app.routes.web_routes import get_download_path  # Adjust import based on its location

class RequestProcessor:
    @staticmethod
    def process_pending_requests():
        """Process pending requests using TMDb, Jackett, and qBittorrent."""
        logging.info("Starting request processing.")
        jackett_helper = JackettHelper()
        qb_helper = QBittorrentHelper()
        tmdb_helper = TMDbHelper()

        pending_requests = Request.query.filter_by(status='Pending').all()
        logging.info(f"Found {len(pending_requests)} pending requests.")

        for req in pending_requests:
            try:
                # Validate title
                validated_media = tmdb_helper.get_media_details(req.title, req.media_type.lower())
                if not validated_media:
                    logging.warning(f"TMDb validation failed for {req.title}")
                    continue

                validated_title = validated_media.get('title') if req.media_type == 'Movie' else validated_media.get('name')
                release_year = validated_media.get('release_date', '')[:4]
                search_query = f"{validated_title} {release_year}"
                logging.info(f"Searching Jackett with query: {search_query}")

                magnet_link = jackett_helper.search_jackett(query=search_query, category=normalize_media_type(req.media_type))
                if not magnet_link:
                    logging.warning(f"No torrents found for {search_query}")
                    continue

                download_path = get_download_path(req.title, req.media_type)
                qb_helper.add_torrent(magnet_link, save_path=download_path)

                req.status = 'In Progress'
                db.session.commit()
                logging.info(f"Download started for: {validated_title}")
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error processing {req.title}: {e}")

        logging.info("Request processing completed.")
