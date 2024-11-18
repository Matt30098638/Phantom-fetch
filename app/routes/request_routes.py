from flask import Blueprint, request, jsonify
from app.models import db, Request
from flask_login import login_required, current_user
from app.helpers.qbittorrent_helper import QBittorrentHelper
from app.helpers.tmdb_helper import TMDbHelper
from app.helpers.jackett_helper import JackettHelper
from config import Config
import logging

bp = Blueprint('request_routes', __name__)

# Initialize the configuration
config = Config()

@bp.route('/create-request', methods=['POST'])
@login_required
def create_request():
    data = request.get_json()
    title = data.get('title')
    media_type = data.get('media_type')

    if not title or not media_type:
        return jsonify({'error': 'Title and media type are required'}), 400

    # Check if the media exists using TMDb and classify it
    tmdb_helper = TMDbHelper()
    classification = tmdb_helper.classify_title(title)
    if not classification:
        return jsonify({'message': f"Failed to classify the title: {title}"}), 404

    # Add request to the database
    new_request = Request(
        user_id=current_user.id,
        media_type=classification,
        title=title
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({'message': f"Request for {title} created successfully"}), 201
