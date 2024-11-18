from flask import Blueprint, jsonify, current_app
from app.models import Request, db
from app.helpers.jackett_helper import JackettHelper
from app.helpers.qbittorrent_helper import QBittorrentHelper
from app.helpers.tmdb_helper import TMDbHelper
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create a Blueprint for request processing
request_processing_bp = Blueprint('request_processing', __name__)

@request_processing_bp.route('/process-requests', methods=['GET'])
def process_requests():
    """Trigger processing of pending requests."""
    try:
        with current_app.app_context():  # Ensure the app context is used
            process_requests_with_jackett_and_qbittorrent()
        return jsonify({"message": "Request processing completed"}), 200
    except Exception as e:
        logging.error(f"Error processing requests: {e}")
        return jsonify({"error": "Failed to process requests"}), 500

def process_requests_with_jackett_and_qbittorrent():
    """Check pending requests, validate titles with TMDb, and process them with Jackett and qBittorrent."""
    logging.info("Starting Jackett and qBittorrent request processing.")
    jackett_helper = JackettHelper()
    qb_helper = QBittorrentHelper()
    tmdb_helper = TMDbHelper()

    # Query for pending requests
    pending_requests = Request.query.filter_by(status='Pending').all()
    logging.info(f"Found {len(pending_requests)} pending requests.")

    for request in pending_requests:
        logging.info(f"Processing request: {request.title}, type: {request.media_type}")

        # Validate the title with TMDb
        validated_media = tmdb_helper.get_media_details(request.title, request.media_type.lower())
        if not validated_media:
            logging.warning(f"No valid TMDb data found for {request.title}, skipping...")
            continue

        validated_title = validated_media.get('title') if request.media_type == 'Movie' else validated_media.get('name')
        release_year = validated_media.get('release_date', '')[:4]
        logging.info(f"Validated title: {validated_title}, Year: {release_year}")

        # Search for torrents on Jackett
        search_query = f"{validated_title} {release_year}"
        logging.info(f"Searching Jackett for: {search_query}")
        magnet_link = jackett_helper.search_jackett(query=search_query, category=request.media_type)

        if not magnet_link:
            logging.warning(f"No torrents found for: {search_query}, skipping...")
            continue

        # Add the torrent to qBittorrent
        try:
            download_path = f"/downloads/{request.media_type}/{validated_title}"
            qb_helper.add_torrent(magnet_link, save_path=download_path, rename=validated_title)

            # Update request status
            request.status = 'In Progress'
            db.session.commit()
            logging.info(f"Download started for: {validated_title}")
        except Exception as e:
            logging.error(f"Failed to start download for {validated_title}: {e}")
            db.session.rollback()

        else:
            logging.info(f"No torrent found for validated title: {validated_title}")

def process_pending_requests_task():
    """Scheduled task to process pending requests."""
    with current_app.app_context():
        try:
            logging.info("Starting scheduled task to process pending requests.")
            process_requests_with_jackett_and_qbittorrent()
            logging.info("Scheduled task completed successfully.")
        except Exception as e:
            logging.error(f"Error running process_pending_requests_task: {e}")

@request_processing_bp.route('/pause-download/<hash>', methods=['POST'])
def pause_download(hash):
    jackett_helper = JackettHelper()
    qb_helper = QBittorrentHelper()
    tmdb_helper = TMDbHelper()
    try:
        qb_helper.pause_download(hash)
        return jsonify({"message": f"Download {hash} paused"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@request_processing_bp.route('/resume-download/<hash>', methods=['POST'])
def resume_download(hash):
    jackett_helper = JackettHelper()
    qb_helper = QBittorrentHelper()
    tmdb_helper = TMDbHelper()
    try:
        qb_helper.resume_download(hash)
        return jsonify({"message": f"Download {hash} resumed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@request_processing_bp.route('/remove-download/<hash>', methods=['POST'])
def remove_download(hash):
    jackett_helper = JackettHelper()
    qb_helper = QBittorrentHelper()
    tmdb_helper = TMDbHelper()
    try:
        qb_helper.remove_download(hash)
        return jsonify({"message": f"Download {hash} removed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
