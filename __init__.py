from flask import Flask, current_app
from flask_migrate import Migrate  # Import Flask-Migrate for database migrations
from config import Config  # Ensure this imports the Config class you created
from app.extensions import db, login_manager  # Import db and login_manager from extensions
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler  # Import APScheduler
from app.routes.web_routes import generate_recommendations, process_requests  # Adjust import paths if needed
from app.routes.request_processing_routes import request_processing_bp
import logging
from logging.handlers import RotatingFileHandler
import os

csrf = CSRFProtect()
migrate = Migrate()  # Initialize Flask-Migrate

def create_app():
    app = Flask(__name__)

    # Initialize CSRF protection after app creation
    csrf.init_app(app)

    # Instantiate and load the configuration
    config = Config()
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = config.SECRET_KEY

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)  # Attach Flask-Migrate to the app
    login_manager.init_app(app)
    login_manager.login_view = 'user_routes.login'

    # Add the user_loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  # Import User here to avoid circular import issues
        return User.query.get(int(user_id))

    # Initialize the scheduler
    scheduler = BackgroundScheduler()

    # Define the task functions
    def daily_recommendations_task():
        with app.app_context():  # Ensure the task runs within the app context
            try:
                generate_recommendations()
            except Exception as e:
                current_app.logger.error(f"Error running daily_recommendations_task: {e}")

    def process_pending_requests_task():
        with app.app_context():  # Ensure the task runs within the app context
            try:
                # Call the processing function directly (imported at the top of this file)
                from app.routes.request_processing_routes import process_requests_with_jackett_and_qbittorrent
                process_requests_with_jackett_and_qbittorrent()
            except Exception as e:
                current_app.logger.error(f"Error running process_pending_requests_task: {e}")

    # Schedule the tasks
    scheduler.add_job(daily_recommendations_task, 'interval', days=1)
    scheduler.add_job(process_pending_requests_task, 'interval', minutes=5)
    scheduler.start()

    with app.app_context():
        # Import and register your blueprints/routes here
        from .routes import media_routes, user_routes, request_routes, notification_routes, web_routes, auth_routes
        from app.routes.jellyfin_routes import jellyfin_bp
        app.register_blueprint(auth_routes.auth_bp)
        app.register_blueprint(media_routes.bp)
        app.register_blueprint(user_routes.bp)
        app.register_blueprint(request_routes.bp)
        app.register_blueprint(notification_routes.bp)
        app.register_blueprint(web_routes.bp)
        app.register_blueprint(jellyfin_bp)
        app.register_blueprint(request_processing_bp)

        # Create database tables if they don't exist
        db.create_all()

    return app

def configure_logging():
    LOG_DIR = "./logs"
    os.makedirs(LOG_DIR, exist_ok=True)

    LOG_FILE = os.path.join(LOG_DIR, "app.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Console
            RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5),  # Rotating logs
        ],
    )
