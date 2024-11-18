from flask_wtf.csrf import validate_csrf, generate_csrf
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.models import Request, User, Download, Media, Recommendation, db, PastRecommendation, IgnoredRecommendation
from app.helpers.jackett_helper import JackettHelper, normalize_media_type
from app.helpers.qbittorrent_helper import QBittorrentHelper
from app.helpers.tmdb_helper import TMDbHelper
import re
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
import hashlib
import requests
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import send_from_directory

# Configure logging
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)  # Ensure the logs directory exists
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)  # Rotate logs
    ]
)

bp = Blueprint('web_routes', __name__)

def get_download_path(title, media_type):
    """Determine the correct directory path for the torrent download."""
    title_for_path = re.sub(r'^(The|A|An)\s+', '', title, flags=re.IGNORECASE).strip()
    first_letter = title_for_path[0].upper() if title_for_path else 'Misc'
    media_type = media_type.lower() if media_type else None

    if media_type == 'movie':
        return f"E:\\Movies\\{first_letter}\\"
    elif media_type == 'tv show':
        return f"E:\\Tv Shows\\{first_letter}\\"
    elif media_type == 'music':
        return f"E:\\Music\\{first_letter}\\"
    else:
        raise ValueError(f"Unsupported media type: {media_type}. Cannot determine download path.")

@bp.route('/')
@login_required
def home():
    return render_template('home.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@bp.route('/downloads')
@login_required
def downloads():
    try:
        qb_helper = QBittorrentHelper()
        active_downloads = qb_helper.get_active_downloads()
        return render_template('downloads.html', downloads=active_downloads)
    except Exception as e:
        logging.error(f"Error fetching downloads: {e}", exc_info=True)
        flash('Error fetching downloads.', 'danger')
        return redirect(url_for('web_routes.dashboard'))
# Route to view the user's library
@bp.route('/library')
@login_required
def library():
    try:
        all_items = Media.query.order_by(Media.title.asc()).all()
        movies = [item for item in all_items if item.media_type == 'Movie']
        tv_shows = [item for item in all_items if item.media_type == 'TV Show']
        music = [item for item in all_items if item.media_type == 'Music']
        return render_template('library.html', movies=movies, tv_shows=tv_shows, music=music)
    except Exception as e:
        current_app.logger.error(f"Error in /library route: {e}")
        flash('Error loading your library.', 'danger')
        return redirect(url_for('web_routes.dashboard'))

# Route for user profile
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        profile_text = request.form.get('profile_text')

        if email:
            current_user.email = email
        current_user.profile_text = profile_text

        try:
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            current_app.logger.error(f"Error updating profile: {e}")
            flash('An error occurred while updating your profile.', 'danger')
        return redirect(url_for('web_routes.profile'))

    return render_template('profile.html', user=current_user)

@bp.route('/process-requests', methods=['GET'])
@login_required
def process_requests():
    try:
        tmdb_helper = TMDbHelper()
        jackett_helper = JackettHelper()
        qb_helper = QBittorrentHelper()
        pending_requests = Request.query.filter_by(status='Pending').all()

        if not pending_requests:
            flash('No pending requests to process.', 'info')
            return redirect(url_for('web_routes.downloads'))

        for req in pending_requests:
            try:
                validated_media = tmdb_helper.get_media_details(req.title, req.media_type.lower())
                if not validated_media:
                    flash(f"No valid media found for {req.title} on TMDB.", 'warning')
                    continue

                validated_title = validated_media['title'] if req.media_type == 'Movie' else validated_media['name']
                release_year = validated_media.get('release_date', '')[:4]
                search_query = f"{validated_title} {release_year}"
                search_results = jackett_helper.search_jackett(query=search_query, category=normalize_media_type(req.media_type))

                # Handle case where search_results is None
                if not search_results:
                    flash(f"No results found for {validated_title}.", 'info')
                    continue

                # Fix: Access the magnet link correctly from the dictionary
                magnet_link = next(
                    (result['magnet'] for result in search_results if result.get('magnet', '').startswith("magnet:?")),
                    None
                )
                if not magnet_link:
                    flash(f"No valid magnet link found for {validated_title}.", 'warning')
                    continue

                download_path = get_download_path(req.title, req.media_type)
                qb_helper.add_torrent(magnet_link, save_path=download_path)
                req.status = 'In Progress'
                db.session.commit()
                flash(f"Started download for {req.title}.", 'success')
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error processing request {req.title}: {e}", exc_info=True)
                flash(f"Error processing {req.title}: {e}", 'danger')

        return redirect(url_for('web_routes.downloads'))
    except Exception as e:
        logging.error(f"Error in process_requests: {e}", exc_info=True)
        flash('An error occurred while processing requests.', 'danger')
        return redirect(url_for('web_routes.dashboard'))

@bp.route('/pause-download/<hash>', methods=['POST'])
@login_required
def pause_download(hash):
    try:
        qb_helper = QBittorrentHelper()
        qb_helper.qb.torrents_pause(torrent_hashes=hash)
        return jsonify({"message": "Download paused successfully."}), 200
    except Exception as e:
        logging.error(f"Error pausing download: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/resume-download/<hash>', methods=['POST'])
@login_required
def resume_download(hash):
    try:
        qb_helper = QBittorrentHelper()
        qb_helper.qb.torrents_resume(torrent_hashes=hash)
        return jsonify({"message": "Download resumed successfully."}), 200
    except Exception as e:
        logging.error(f"Error resuming download: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/remove-download/<hash>', methods=['POST'])
@login_required
def remove_download(hash):
    try:
        qb_helper = QBittorrentHelper()
        qb_helper.qb.torrents_delete(torrent_hashes=hash)
        return jsonify({"message": "Download removed successfully."}), 200
    except Exception as e:
        logging.error(f"Error removing download: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@bp.route('/recommendations')
@login_required
def recommendations():
    try:
        tmdb_helper = TMDbHelper()
        recommendations = []
        for media in Media.query.all():
            media_recommendations = tmdb_helper.get_recommendations(media.title, media.media_type.lower())
            recommendations.extend(media_recommendations)
        return render_template('recommendations.html', recommendations=recommendations)
    except Exception as e:
        logging.error(f"Error fetching recommendations: {e}", exc_info=True)
        flash('Error loading recommendations.', 'danger')
        return redirect(url_for('web_routes.dashboard'))
@bp.route('/mark-as-past-recommendation', methods=['POST'])
@login_required
def mark_as_past_recommendation():
    original_title = request.form.get('original_title')
    related_title = request.form.get('related_title')

    if original_title and related_title:
        past_rec = PastRecommendation(
            media_title=original_title,
            related_media_title=related_title,
            sent_to_email=current_user.email
        )
        try:
            db.session.add(past_rec)
            db.session.commit()
            flash(f'Recommendation "{related_title}" marked as past successfully!', 'success')
        except Exception as e:
            logging.error(f"Error adding past recommendation: {e}", exc_info=True)
            flash('Error marking as past.', 'danger')
            db.session.rollback()

    return redirect(url_for('web_routes.recommendations'))


@bp.route('/generate-recommendations', methods=['GET'])
@login_required
def generate_recommendations():
    tmdb_helper = TMDbHelper()
    media_items = Media.query.all()
    generated_recommendations = []

    for item in media_items:
        recommendations = tmdb_helper.get_recommendations(title=item.title, media_type=item.media_type)
        for rec in recommendations:
            exists = Recommendation.query.filter_by(
                user_id=current_user.id,
                title=rec['title']
            ).first()

            if not exists:
                new_recommendation = Recommendation(
                    user_id=current_user.id,
                    title=rec['title'],
                    media_type=item.media_type,
                    description=rec.get('overview', 'No description available.')
                )
                db.session.add(new_recommendation)
                generated_recommendations.append({
                    'original_title': item.title,
                    'recommended_title': rec['title'],
                    'media_type': item.media_type
                })

    try:
        db.session.commit()
        flash('Recommendations generated successfully!', 'success')
    except Exception as e:
        logging.error(f"Error storing recommendations: {e}", exc_info=True)
        db.session.rollback()
        flash('Error storing recommendations.', 'danger')

    if not generated_recommendations:
        flash("No recommendations were found.", "info")
        return redirect(url_for('web_routes.dashboard'))

    return render_template('recommendations.html', recommendations=generated_recommendations)


@bp.route('/bulk_action', methods=['POST'])
@login_required
def bulk_action():
    selected_ids = request.form.getlist("selected_recommendations")
    action = request.form.get("action")

    if not selected_ids:
        flash("No recommendations selected.", "info")
        return redirect(url_for('web_routes.recommendations'))

    try:
        if action == "add_request":
            for recommendation_id in selected_ids:
                recommendation = Recommendation.query.get(recommendation_id)
                if recommendation:
                    new_request = Request(
                        user_id=current_user.id,
                        media_type=recommendation.media_type,
                        title=recommendation.related_media_title,
                        status='Pending',
                        priority='Medium'
                    )
                    db.session.add(new_request)

        elif action == "ignore":
            for recommendation_id in selected_ids:
                recommendation = Recommendation.query.get(recommendation_id)
                if recommendation:
                    ignored = IgnoredRecommendation(
                        recommendation_id=recommendation.id,
                        user_id=current_user.id
                    )
                    db.session.add(ignored)

        db.session.commit()
        flash(f"Bulk action '{action}' completed successfully.", "success")
    except Exception as e:
        logging.error(f"Error in bulk_action: {e}", exc_info=True)
        db.session.rollback()
        flash("Error performing bulk action.", "danger")

    return redirect(url_for('web_routes.recommendations'))


@bp.route('/previous-recommendations')
@login_required
def previous_recommendations():
    past_recommendations = PastRecommendation.query.order_by(PastRecommendation.sent_at.desc()).all()
    return render_template('previous_recommendations.html', past_recommendations=past_recommendations)


@bp.route('/add-recommendation', methods=['GET', 'POST'])
@login_required
def add_recommendation():
    if request.method == 'POST':
        title = request.form.get('title')
        media_type = request.form.get('media_type')
        description = request.form.get('description')

        if not title or not media_type:
            flash('Title and media type are required.', 'danger')
            return redirect(url_for('web_routes.add_recommendation'))

        new_recommendation = Recommendation(
            user_id=current_user.id,
            title=title,
            media_type=media_type,
            is_new=True,
            recommended_at=datetime.utcnow(),
            description=description
        )

        try:
            db.session.add(new_recommendation)
            db.session.commit()
            flash('Recommendation added successfully!', 'success')
        except Exception as e:
            logging.error(f"Error adding recommendation: {e}", exc_info=True)
            flash('Error adding recommendation.', 'danger')
            db.session.rollback()

        return redirect(url_for('web_routes.recommendations'))

    return render_template('add-recommendation.html')


@bp.route('/requests')
@login_required
def recent_requests():
    try:
        recent_requests = Request.query.order_by(Request.requested_at.desc()).limit(10).all()
        return render_template('requests.html', requests=recent_requests)
    except Exception as e:
        logging.error(f"Error in /requests: {e}", exc_info=True)
        flash('Error loading requests.', 'danger')
        return redirect(url_for('web_routes.dashboard'))


@bp.route('/add-request', methods=['GET', 'POST'])
@login_required
def add_request():
    if request.method == 'POST':
        title = request.form.get('title')
        media_type = request.form.get('type')

        if not title or not media_type:
            flash('Title and media type are required.', 'danger')
            return redirect(url_for('web_routes.add_request'))

        new_request = Request(
            user_id=current_user.id,
            media_type=media_type,
            title=title,
            status='Pending',
            priority='Medium'
        )

        try:
            db.session.add(new_request)
            db.session.commit()
            flash('Request added successfully!', 'success')
        except Exception as e:
            logging.error(f"Error adding request: {e}", exc_info=True)
            flash('Error adding request.', 'danger')
            db.session.rollback()

        return redirect(url_for('web_routes.add_request'))

    current_requests = Request.query.all()
    return render_template('add-request.html', requests=current_requests)


@bp.route('/edit-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
def edit_request(request_id):
    try:
        media_request = Request.query.get_or_404(request_id)
        if request.method == 'POST':
            new_title = request.form.get('title')
            new_type = request.form.get('type')
            new_status = request.form.get('status')

            if new_title:
                media_request.title = new_title
            if new_type:
                media_request.media_type = new_type
            if new_status:
                media_request.status = new_status

            db.session.commit()
            flash('Request updated successfully!', 'success')

            return redirect(url_for('web_routes.add_request'))
        return render_template('edit-request.html', request=media_request)
    except Exception as e:
        logging.error(f"Error in edit_request: {e}", exc_info=True)
        flash('Error loading request for editing.', 'danger')
        return redirect(url_for('web_routes.add_request'))


@bp.route('/delete-request/<int:request_id>', methods=['POST'])
@login_required
def delete_request(request_id):
    try:
        request_to_delete = Request.query.get_or_404(request_id)
        db.session.delete(request_to_delete)
        db.session.commit()
        flash('Request deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Error deleting request: {e}", exc_info=True)
        flash('Error deleting request.', 'danger')
        db.session.rollback()

    return redirect(url_for('web_routes.add_request'))

@bp.route('/add-to-requests', methods=['POST'])
@login_required
def add_to_requests():
    data = request.get_json()
    title = data.get('title')
    media_type = data.get('media_type')

    if not title or not media_type:
        return jsonify({"message": "Title and media type are required."}), 400

    try:
        existing_request = Request.query.filter_by(title=title, user_id=current_user.id).first()
        if existing_request:
            return jsonify({"message": f"Request for '{title}' already exists."}), 400

        new_request = Request(
            user_id=current_user.id,
            title=title,
            media_type=media_type,
            status='Pending',
            priority='Medium'
        )
        db.session.add(new_request)
        db.session.commit()

        return jsonify({"message": f"Request for '{title}' added successfully."}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error adding request: {e}", exc_info=True)
        return jsonify({"message": "An error occurred while adding the request."}), 500


@bp.route('/future_releases')
@login_required
def future_releases():
    try:
        tmdb_helper = TMDbHelper()
        us_movies = tmdb_helper.get_upcoming_movies(region="US")
        gb_movies = tmdb_helper.get_upcoming_movies(region="GB")
        us_tv_shows = tmdb_helper.get_upcoming_tv_shows()
        gb_tv_shows = tmdb_helper.get_upcoming_tv_shows()

        def filter_english_shows(tv_shows):
            return [show for show in tv_shows if show.get('original_language') in ['en', 'en-US']]

        us_tv_shows = filter_english_shows(us_tv_shows)
        gb_tv_shows = filter_english_shows(gb_tv_shows)

        def format_results(results, is_movie=True):
            return [
                {
                    'title': item['title'] if is_movie else item['name'],
                    'release_date': item.get('release_date') if is_movie else item.get('first_air_date'),
                    'thumbnail_url': item.get('poster_path'),
                    'overview': item.get('overview', 'No description available.'),
                    'url': f"https://www.themoviedb.org/movie/{item['id']}" if is_movie else f"https://www.themoviedb.org/tv/{item['id']}"
                }
                for item in results
            ]

        us_movies = format_results(us_movies, is_movie=True)
        gb_movies = format_results(gb_movies, is_movie=True)
        us_tv_shows = format_results(us_tv_shows, is_movie=False)
        gb_tv_shows = format_results(gb_tv_shows, is_movie=False)

        return render_template(
            'future_releases.html',
            us_movies=us_movies,
            gb_movies=gb_movies,
            us_tv_shows=us_tv_shows,
            gb_tv_shows=gb_tv_shows
        )
    except Exception as e:
        logging.error(f"Error in /future_releases route: {e}", exc_info=True)
        flash('Error loading future releases.', 'danger')
        return redirect(url_for('web_routes.dashboard'))


@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search_torrents():
    try:
        jackett_helper = JackettHelper()
        results = None

        if request.method == 'POST':
            csrf_token = request.form.get('csrf_token')
            try:
                validate_csrf(csrf_token)
            except Exception as e:
                flash('Invalid or missing CSRF token. Please try again.', 'danger')
                logging.error(f"CSRF validation failed: {e}")
                return redirect(url_for('web_routes.search_torrents'))

            query = request.form.get('query')
            if not query:
                flash('Search query is required.', 'danger')
                return redirect(url_for('web_routes.search_torrents'))

            logging.info(f"Searching for torrents with query: {query}")
            results = jackett_helper.search_jackett(query=query)

            if not results:
                flash(f"No torrents found for query: {query}", 'info')

        csrf_token = generate_csrf()
        return render_template('search.html', csrf_token=csrf_token, results=results)
    except Exception as e:
        logging.error(f"Error in search_torrents: {e}", exc_info=True)
        flash('An error occurred while performing the search.', 'danger')
        return redirect(url_for('web_routes.dashboard'))


def is_valid_magnet_uri(magnet_uri):
    """Validate magnet URI structure."""
    return magnet_uri and magnet_uri.startswith("magnet:?xt=urn:btih:")


@bp.route('/add_to_downloads', methods=['POST'])
@login_required
def add_to_downloads():
    try:
        magnet_uri = request.form.get('magnet_uri')
        title = request.form.get('title')
        media_type = request.form.get('media_type')

        logging.info(f"Attempting to add torrent to downloads: {title}")

        if not is_valid_magnet_uri(magnet_uri):
            logging.warning("Invalid magnet URI.")
            flash("Invalid magnet URI. Cannot add to downloads.", "danger")
            return redirect(url_for('web_routes.search_torrents'))

        try:
            download_path = get_download_path(title, media_type)
            logging.info(f"Resolved download path: {download_path}")
        except ValueError as e:
            logging.error(f"Error determining download path: {e}")
            flash(str(e), "danger")
            return redirect(url_for('web_routes.search_torrents'))

        qb_helper = QBittorrentHelper()
        qb_helper.add_torrent(magnet_uri, save_path=download_path)
        logging.info(f"Successfully added torrent '{title}' to path '{download_path}'.")
        flash(f"Torrent '{title}' added to downloads successfully.", "success")
    except Exception as e:
        logging.error(f"Error in add_to_downloads: {e}", exc_info=True)
        flash("An error occurred while adding the torrent to downloads.", "danger")

    return redirect(url_for('web_routes.search_torrents'))


@bp.route('/cached_image/<filename>')
def cached_image(filename):
    file_path = os.path.join('/cached_image', filename)
    logging.info(f"Attempting to serve cached image at: {file_path}")
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        return "File not found", 404
    return send_from_directory('/cached_image', filename)
