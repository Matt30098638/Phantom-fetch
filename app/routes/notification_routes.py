from flask import Blueprint, jsonify, request
from app.helpers.qbittorrent_helper import QBittorrentHelper
from app.helpers.jackett_helper import JackettHelper
from app.helpers.jellyfin_helper import JellyfinHelper
from app.helpers.tmdb_helper import TMDbHelper
from app.helpers.spotify_helper import SpotifyHelper
from app.helpers.outlook_helper import OutlookHelper
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create a Blueprint for the notification routes
bp = Blueprint('notification_routes', __name__)

# Instantiate helpers with configuration
config = Config()
qb_helper = QBittorrentHelper()
jackett_helper = JackettHelper()
jellyfin_helper = JellyfinHelper()
spotify_helper = SpotifyHelper()
outlook_helper = OutlookHelper()

# Route to get notifications (placeholder for actual logic)
@bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Endpoint to fetch notifications."""
    return jsonify({"message": "Notifications retrieved successfully"})

# Route for testing Outlook email fetching and processing
@bp.route('/notifications/outlook', methods=['GET'])
def check_outlook_emails():
    """Fetch and process unread Outlook emails."""
    access_token = outlook_helper.get_access_token()
    if not access_token:
        logging.error("Failed to acquire Outlook access token")
        return jsonify({"error": "Failed to acquire access token"}), 500

    emails = outlook_helper.get_filtered_emails(access_token)
    if not emails:
        logging.info("No new emails found in Outlook")
        return jsonify({"message": "No new emails found"})

    outlook_helper.process_requests(emails, access_token)
    logging.info("Outlook emails processed successfully")
    return jsonify({"message": "Processed Outlook emails successfully"})

# Route for fetching current downloads from qBittorrent
@bp.route('/notifications/qbittorrent', methods=['GET'])
def get_qbittorrent_downloads():
    """Fetch active downloads from qBittorrent."""
    try:
        active_downloads = qb_helper.get_active_downloads()
        logging.info("Fetched active downloads from qBittorrent")
        return jsonify({"active_downloads": active_downloads})
    except Exception as e:
        logging.error(f"Error fetching active downloads: {e}")
        return jsonify({"error": str(e)}), 500

# Route for checking if a title exists in the Jellyfin library
@bp.route('/notifications/jellyfin', methods=['GET'])
def check_jellyfin_library():
    """Check if a title exists in the Jellyfin library."""
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title is required"}), 400

    if jellyfin_helper.item_exists(title):
        logging.info(f"{title} exists in the Jellyfin library")
        return jsonify({"message": f"{title} exists in the Jellyfin library"}), 200
    logging.info(f"{title} not found in the Jellyfin library")
    return jsonify({"message": f"{title} not found in the Jellyfin library"}), 404

@bp.route('/start-download', methods=['POST'])
def start_download():
    """Start a media download using Jackett and qBittorrent."""
    data = request.get_json()
    title = data.get('title')
    category = data.get('category', 'Movies')

    if not title:
        return jsonify({"error": "Title is required"}), 400

    magnet_link = jackett_helper.search_jackett(title, category=category)
    if not magnet_link:
        logging.info(f"No torrent found for {title}")
        return jsonify({"message": f"No torrent found for {title}"}), 404

    qb_helper.add_torrent(magnet_link, save_path="/downloads")
    logging.info(f"Download started for {title}")
    return jsonify({"message": f"Download started for {title}"}), 200

# Route to search for music on Spotify
@bp.route('/search-music', methods=['GET'])
def search_music():
    """Search for a song, album, or artist on Spotify."""
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title is required"}), 400

    is_music = spotify_helper.is_music(title)
    if is_music:
        logging.info(f"{title} found on Spotify")
        return jsonify({"message": f"{title} found on Spotify"}), 200
    logging.info(f"{title} not found on Spotify")
    return jsonify({"message": f"{title} not found on Spotify"}), 404

# Route to classify a media title using TMDb
@bp.route('/classify-media', methods=['GET'])
def classify_media():
    """Classify a media title as a movie or TV show using TMDb."""
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title is required"}), 400

    media_type = TMDbHelper.classify_title(title)
    if media_type:
        logging.info(f"{title} classified as {media_type}")
        return jsonify({"title": title, "media_type": media_type}), 200
    logging.info(f"Failed to classify {title}")
    return jsonify({"message": f"Failed to classify {title}"}), 404

# Route to retrieve franchise information from TMDb
@bp.route('/get-franchise-info', methods=['GET'])
def get_franchise_info():
    """Get franchise information for a movie using TMDb."""
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title is required"}), 400

    media_type = TMDbHelper.classify_title(title)
    if media_type == 'movie':
        details = TMDbHelper.get_media_details(title, media_type)
        if details and TMDbHelper.is_part_of_franchise(details):
            franchise_movies = TMDbHelper.get_franchise_movies(details)
            logging.info(f"Franchise information found for {title}")
            return jsonify({"franchise_movies": franchise_movies}), 200
        logging.info(f"No franchise information available for {title}")
        return jsonify({"message": f"No franchise information available for {title}"}), 404
    logging.info(f"{title} is not a movie or has no franchise")
    return jsonify({"message": f"{title} is not a movie or has no franchise"}), 404

# Route to check download status in qBittorrent
@bp.route('/download-status', methods=['GET'])
def download_status():
    """Check the status of active downloads in qBittorrent."""
    try:
        active_downloads = qb_helper.get_active_downloads()
        logging.info("Fetched active download status")
        return jsonify({"active_downloads": active_downloads}), 200
    except Exception as e:
        logging.error(f"Error checking download status: {e}")
        return jsonify({"error": str(e)}), 500
    
@bp.route('/media-details', methods=['GET'])
def media_details():
    """Fetch details of a media item from the Jellyfin library."""
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        items = jellyfin_helper.get_existing_items()
        matched_items = [item for item in items if item.get('Name').lower() == title.lower()]
        if matched_items:
            logging.info(f"Details found for {title} in Jellyfin")
            return jsonify({"media_details": matched_items}), 200
        logging.info(f"No details found for {title} in Jellyfin")
        return jsonify({"message": f"No details found for {title} in Jellyfin"}), 404
    except Exception as e:
        logging.error(f"Error fetching media details: {e}")
        return jsonify({"error": str(e)}), 500

# Route to get recent requests from the database
@bp.route('/recent-requests', methods=['GET'])
def recent_requests():
    """Fetch recent media requests from the database."""
    try:
        recent_requests = request.query.order_by(request.requested_at.desc()).limit(10).all()
        requests_list = [{
            "id": request.id,
            "title": request.title,
            "media_type": request.media_type,
            "status": request.status,
            "priority": request.priority,
            "requested_at": request.requested_at
        } for request in recent_requests]
        logging.info("Fetched recent media requests")
        return jsonify({"recent_requests": requests_list}), 200
    except Exception as e:
        logging.error(f"Error fetching recent requests: {e}")
        return jsonify({"error": str(e)}), 500

# Route to update the status of a media request
@bp.route('/update-request-status', methods=['POST'])
def update_request_status():
    """Update the status of a media request."""
    data = request.get_json()
    request_id = data.get('request_id')
    new_status = data.get('status')

    if not request_id or not new_status:
        return jsonify({"error": "request ID and new status are required"}), 400

    try:
        media_request = request.query.get(request_id)
        if media_request:
            media_request.status = new_status
            db.session.commit()
            logging.info(f"Updated status of request ID {request_id} to {new_status}")
            return jsonify({"message": f"request status updated to {new_status}"}), 200
        logging.info(f"request ID {request_id} not found")
        return jsonify({"message": "request not found"}), 404
    except Exception as e:
        logging.error(f"Error updating request status: {e}")
        return jsonify({"error": str(e)}), 500

# Route to check if a title exists in Jellyfin before adding a request
@bp.route('/check-title-existence', methods=['POST'])
def check_title_existence():
    """Check if a media title already exists in the Jellyfin library before adding a request."""
    data = request.get_json()
    title = data.get('title')

    if not title:
        return jsonify({"error": "Title is required"}), 400

    exists = jellyfin_helper.item_exists(title)
    if exists:
        logging.info(f"{title} already exists in the Jellyfin library")
        return jsonify({"message": f"{title} already exists in the Jellyfin library"}), 200
    logging.info(f"{title} not found in the Jellyfin library")
    return jsonify({"message": f"{title} not found in the Jellyfin library"}), 404

# Route to fetch Spotify metadata for a media title
@bp.route('/spotify-metadata', methods=['GET'])
def get_spotify_metadata():
    """Fetch metadata for a media title from Spotify."""
    title = request.args.get('title')
    if not title:
        return jsonify({"error": "Title is required"}), 400

    metadata = spotify_helper.get_metadata(title)
    if metadata:
        logging.info(f"Metadata found for {title} on Spotify")
        return jsonify({"metadata": metadata}), 200
    logging.info(f"No metadata found for {title} on Spotify")
    return jsonify({"message": f"No metadata found for {title} on Spotify"}), 404

# Route to handle bulk download requests
@bp.route('/bulk-download', methods=['POST'])
def bulk_download():
    """Handle bulk download requests."""
    data = request.get_json()
    titles = data.get('titles', [])
    category = data.get('category', 'Movies')

    if not titles or not isinstance(titles, list):
        return jsonify({"error": "A list of titles is required"}), 400

    download_results = []
    for title in titles:
        try:
            magnet_link = jackett_helper.search_jackett(title, category=category)
            if magnet_link:
                qb_helper.add_torrent(magnet_link, save_path="/downloads")
                download_results.append({"title": title, "status": "Download started"})
                logging.info(f"Download started for {title}")
            else:
                download_results.append({"title": title, "status": "No torrent found"})
                logging.info(f"No torrent found for {title}")
        except Exception as e:
            download_results.append({"title": title, "status": f"Error: {str(e)}"})
            logging.error(f"Error downloading {title}: {e}")

    return jsonify({"results": download_results}), 200

# Route to pause all active downloads in qBittorrent
@bp.route('/pause-all-downloads', methods=['POST'])
def pause_all_downloads():
    """Pause all active downloads in qBittorrent."""
    try:
        qb_helper.pause_all_downloads()
        logging.info("All downloads paused")
        return jsonify({"message": "All downloads paused"}), 200
    except Exception as e:
        logging.error(f"Error pausing all downloads: {e}")
        return jsonify({"error": str(e)}), 500

# Route to resume all paused downloads in qBittorrent
@bp.route('/resume-all-downloads', methods=['POST'])
def resume_all_downloads():
    """Resume all paused downloads in qBittorrent."""
    try:
        qb_helper.resume_all_downloads()
        logging.info("All downloads resumed")
        return jsonify({"message": "All downloads resumed"}), 200
    except Exception as e:
        logging.error(f"Error resuming all downloads: {e}")
        return jsonify({"error": str(e)}), 500
