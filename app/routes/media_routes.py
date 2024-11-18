from flask import Blueprint, request, jsonify
from app.helpers.qbittorrent_helper import QBittorrentHelper
from app.helpers.jackett_helper import JackettHelper
from app.helpers.jellyfin_helper import JellyfinHelper
from app.helpers.tmdb_helper import TMDbHelper
from app.helpers.spotify_helper import SpotifyHelper
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create a Blueprint for media routes
bp = Blueprint('media_routes', __name__)

# Initialize configuration
config = Config()

# Initialize helper instances with appropriate configurations
qb_helper = QBittorrentHelper(max_retries=3, retry_delay=5)
jackett_helper = JackettHelper()
jellyfin_helper = JellyfinHelper()
tmdb_helper = TMDbHelper()
spotify_helper = SpotifyHelper()

@bp.route('/download', methods=['POST'])
def download_media():
    """
    Route to handle media download requests. It uses Jackett to search for torrents
    and qBittorrent to start the download.
    """
    data = request.get_json()
    title = data.get('title')
    category = data.get('category', 'TV')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    # Search for torrent using Jackett
    magnet_link = jackett_helper.search_jackett(query=title, category=category)
    if not magnet_link:
        logging.info(f"No torrent found for {title}")
        return jsonify({'message': f"No torrent found for {title}"}), 404

    # Add torrent to qBittorrent
    try:
        qb_helper.add_torrent(magnet_link, save_path="/downloads")
        logging.info(f"Download started for {title}")
        return jsonify({'message': f"Download started for {title}"}), 200
    except Exception as e:
        logging.error(f"Error starting download for {title}: {e}")
        return jsonify({'error': f"Failed to start download for {title}"}), 500

@bp.route('/check-library', methods=['GET'])
def check_jellyfin_library():
    """
    Route to check if a title exists in the Jellyfin library.
    """
    title = request.args.get('title')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    if jellyfin_helper.item_exists(title):
        logging.info(f"{title} exists in the Jellyfin library")
        return jsonify({'message': f"{title} exists in the Jellyfin library"}), 200
    logging.info(f"{title} not found in the Jellyfin library")
    return jsonify({'message': f"{title} not found in the Jellyfin library"}), 404

@bp.route('/classify-title', methods=['GET'])
def classify_title():
    """
    Route to classify a title as either 'movie' or 'tv' using TMDb.
    """
    title = request.args.get('title')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    media_type = tmdb_helper.classify_title(title)
    if media_type:
        logging.info(f"Classified {title} as {media_type}")
        return jsonify({'title': title, 'media_type': media_type}), 200
    logging.info(f"Title classification failed for {title}")
    return jsonify({'message': f"Title classification failed for {title}"}), 404

@bp.route('/search-music', methods=['GET'])
def search_music():
    """
    Route to check if a music title exists using Spotify.
    """
    title = request.args.get('title')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    is_music = spotify_helper.is_music(title)
    if is_music:
        logging.info(f"{title} is found as a music item on Spotify")
        return jsonify({'message': f"{title} is found as a music item on Spotify"}), 200
    logging.info(f"{title} is not found as a music item on Spotify")
    return jsonify({'message': f"{title} is not found as a music item on Spotify"}), 404

@bp.route('/search-and-confirm', methods=['POST'])
def search_and_confirm():
    """
    Route to search TMDB and confirm result with user before adding to requests.
    """
    data = request.get_json()
    title = data.get('title')
    media_type = data.get('media_type')
    exclude_ids = data.get('exclude_ids', [])

    if not title or not media_type:
        return jsonify({'error': 'Title and media type are required'}), 400

    # Check if title already exists in Jellyfin
    if jellyfin_helper.item_exists(title):
        return jsonify({'message': f"{title} already exists in Jellyfin library"}), 200

    # Search TMDB
    result = tmdb_helper.get_media_details(title, media_type, exclude_ids)
    if not result:
        return jsonify({'message': 'No suitable TMDB results found.'}), 404

    return jsonify({
        'tmdb_id': result.get('id'),
        'title': result.get('title') or result.get('name'),
        'description': result.get('overview'),
        'release_date': result.get('release_date') or result.get('first_air_date')
    }), 200

@bp.route('/confirm-tmdb', methods=['POST'])
def confirm_tmdb():
    """
    Route to confirm and add a TMDB result to the requests table.
    """
    data = request.get_json()
    tmdb_id = data.get('tmdb_id')
    title = data.get('title')
    media_type = data.get('media_type')
    user_id = data.get('user_id')  # Pass the user ID from the session if available

    # Create a new request entry in the database
    new_request = Request(
        user_id=user_id,
        media_type=media_type,
        title=title,
        status='Pending'
    )
    db.session.add(new_request)
    db.session.commit()

    return jsonify({'message': f"{title} has been added to your requests"}), 200
