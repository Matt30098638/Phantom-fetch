from app.extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    profile_text = db.Column(db.Text)
    profile_picture = db.Column(db.String(255))
    role = db.Column(db.Enum('Admin', 'User', 'Guest'), default='User')
    status = db.Column(db.Enum('Active', 'Suspended'), default='Active')
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    last_login = db.Column(db.TIMESTAMP)
    last_activity = db.Column(db.TIMESTAMP)

    # Relationships
    requests = db.relationship('Request', back_populates='user', cascade='all, delete-orphan')
    downloads = db.relationship('Download', back_populates='user', cascade='all, delete-orphan')
    recommendations = db.relationship('Recommendation', back_populates='user', cascade='all, delete-orphan')


class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_type = db.Column(db.Enum('Movie', 'TV Show', 'Music'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum('Pending', 'In Progress', 'Completed', 'Failed'), default='Pending')
    priority = db.Column(db.Enum('Low', 'Medium', 'High'), default='Medium')
    requested_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    last_status_update = db.Column(db.TIMESTAMP, onupdate=db.func.now())

    # Relationships
    user = db.relationship('User', back_populates='requests')


class Download(db.Model):
    __tablename__ = 'downloads'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    media_type = db.Column(db.Enum('Movie', 'TV Show', 'Music'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    download_status = db.Column(db.Enum('Downloading', 'Completed', 'Failed', 'Paused'), default='Downloading')
    download_path = db.Column(db.String(255))
    added_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    completed_at = db.Column(db.TIMESTAMP)

    # Relationships
    user = db.relationship('User', back_populates='downloads')


class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = db.Column(db.Integer, primary_key=True)
    media_title = db.Column(db.String(255), nullable=False)
    related_media_title = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    url = db.Column(db.String(512), nullable=True)  # TMDb URL
    description = db.Column(db.Text, nullable=True)
    thumbnail_url = db.Column(db.String(512), nullable=True)
    overview = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())

    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='recommendations')


class PastRecommendation(db.Model):
    __tablename__ = 'past_recommendations'
    id = db.Column(db.Integer, primary_key=True)
    media_title = db.Column(db.String(255), nullable=False)
    related_media_title = db.Column(db.String(255), nullable=False)
    sent_to_email = db.Column(db.String(120))
    sent_at = db.Column(db.TIMESTAMP, server_default=db.func.now())


class Media(db.Model):
    __tablename__ = 'media'
    id = db.Column(db.Integer, primary_key=True)
    media_type = db.Column(db.Enum('Movie', 'TV Show', 'Music'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    release_date = db.Column(db.Date)
    added_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    description = db.Column(db.Text)
    path = db.Column(db.String(255))
    status = db.Column(db.Enum('Available', 'Unavailable'), default='Available')


class IgnoredRecommendation(db.Model):
    __tablename__ = 'ignored_recommendations'
    id = db.Column(db.Integer, primary_key=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey('recommendations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ignored_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
