from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, current_user, logout_user
from app.models import User
from werkzeug.security import check_password_hash
from flask_wtf import CSRFProtect

# Initialize CSRF protection if not done globally in __init__.py
csrf = CSRFProtect()

auth_bp = Blueprint('auth_routes', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@csrf.exempt  # Add this if using CSRFProtect at the blueprint level or app level
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web_routes.home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        # Check CSRF token
        if 'csrf_token' not in request.form or not request.form.get('csrf_token'):
            flash('CSRF token missing or incorrect.', 'danger')
            return redirect(url_for('auth_routes.login'))

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('web_routes.home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth_routes.login'))
