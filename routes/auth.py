from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            session['language'] = user.language
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('register.html')
        user = User(username=username, email=email, is_author=('is_author' in request.form))
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        session['language'] = user.language
        return redirect(url_for('main.index'))
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
