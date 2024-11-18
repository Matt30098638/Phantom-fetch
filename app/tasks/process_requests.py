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
    jackett_helper = JackettHelper()
    qb_helper = QBittorrentHelper()
    tmdb_helper = TMDbHelper()

    # Query for pending requests
    pending_requests = Request.query.filter_by(status='Pending').all()

    for request in pending_requests:
        # Validate the title with TMDb to get the correct title and release year
        validated_media = tmdb_helper.get_media_details(request.title, request.media_type.lower())
        
        if not validated_media:
            logging.warning(f"No valid TMDb data found for {request.title}")
            continue  # Skip if no valid media data is found on TMDb

        # Use TMDb title and release year for torrent search
        validated_title = validated_media.get('title') if request.media_type == 'Movie' else validated_media.get('name')
        release_year = validated_media.get('release_date', '')[:4]  # Extract year if available

        # Build the search query with the validated title and year
        search_query = f"{validated_title} {release_year}"
        logging.info(f"Searching Jackett for: {search_query} in category: {request.media_type}")

        # Search for a torrent using Jackett
        magnet_link = jackett_helper.search_jackett(query=search_query, category=request.media_type)
        
        if magnet_link:
            try:
                # Determine the save path based on media type
                download_path = f"/downloads/{request.media_type}/{validated_title}"

                # Add the torrent to qBittorrent
                qb_helper.add_torrent(magnet_link, save_path=download_path, rename=validated_title)
                
                # Update the request status to 'In Progress' in the database
                request.status = 'In Progress'
                db.session.commit()
                
                logging.info(f"Started download for request: {validated_title}")
            except Exception as e:
                logging.error(f"Failed to start download for {validated_title}: {e}")
                db.session.rollback()  # Roll back the session in case of an error
        else:
            logging.info(f"No torrent found for validated title: {validated_title}")
