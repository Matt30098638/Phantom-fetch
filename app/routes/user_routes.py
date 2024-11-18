from flask import Blueprint, request, jsonify
from app.models import db, User
from flask_login import login_user, logout_user, login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user


bp = Blueprint('user_routes', __name__)

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and user.verify_password(data['password']):  # Assume verify_password is implemented
        login_user(user)
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'message': 'Invalid credentials'}), 401

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        email = request.form.get('email')
        profile_text = request.form.get('profile_text')

        # Validate and update user information
        if email:
            current_user.email = email
        current_user.profile_text = profile_text

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('web_routes.profile'))

    return render_template('profile.html', user=current_user)
