from flask import Blueprint, jsonify, request
from app.helpers.jellyfin_helper import JellyfinHelper
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create a Blueprint for Jellyfin routes
jellyfin_bp = Blueprint('jellyfin_routes', __name__)

# Initialize JellyfinHelper
jellyfin_helper = JellyfinHelper()

@jellyfin_bp.route('/sync-jellyfin', methods=['GET'])
def sync_jellyfin():
    """Route to sync Jellyfin media with the database."""
    try:
        jellyfin_helper.save_items_to_db()
        return jsonify({"message": "Jellyfin media sync completed."}), 200
    except Exception as e:
        logging.error(f"Error during Jellyfin sync: {e}")
        return jsonify({"error": "Failed to sync Jellyfin media."}), 500


@jellyfin_bp.route('/check-library', methods=['GET'])
def check_jellyfin_library():
    """Route to check if a title exists in the Jellyfin library."""
    title = request.args.get('title')

    if not title:
        return jsonify({'error': 'Title is required'}), 400

    if jellyfin_helper.item_exists(title):
        logging.info(f"{title} exists in the Jellyfin library")
        return jsonify({'message': f"{title} exists in the Jellyfin library"}), 200
    logging.info(f"{title} not found in the Jellyfin library")
    return jsonify({'message': f"{title} not found in the Jellyfin library"}), 404
