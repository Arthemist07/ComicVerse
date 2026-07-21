from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import db, Comic, Genre, ComicGenre, User, Changelog, Notification, ReadHistory, Announcement
from sqlalchemy import desc

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('splash.html')
    page = request.args.get('page', 1, type=int)
    genre_filter = request.args.get('genre', '')
    sort = request.args.get('sort', 'latest')
    search = request.args.get('q', '')

    query = Comic.query

    if search:
        query = query.filter(
            Comic.title_en.contains(search) |
            Comic.title_id.contains(search)
        )

    if genre_filter:
        query = query.join(ComicGenre).filter(ComicGenre.genre_id == int(genre_filter))

    if sort == 'popular':
        query = query.order_by(desc(Comic.views))
    elif sort == 'rating':
        query = query.order_by(desc(Comic.rating))
    else:
        query = query.order_by(desc(Comic.updated_at))

    comics = query.paginate(page=page, per_page=24, error_out=False)
    genres = Genre.query.all()

    latest_updates = Comic.query.order_by(desc(Comic.updated_at)).limit(10).all()
    popular = Comic.query.order_by(desc(Comic.views)).limit(5).all()

    announcements = Announcement.query.filter_by(pinned=True).order_by(Announcement.created_at.desc()).all()
    return render_template('index.html', comics=comics, genres=genres,
                         latest_updates=latest_updates, popular=popular, announcements=announcements)

@main_bp.route('/language/<lang>')
def set_language(lang):
    if lang in ['en', 'id']:
        session['language'] = lang
        if current_user.is_authenticated:
            current_user.language = lang
            db.session.commit()
    return redirect(request.referrer or url_for('main.index'))

@main_bp.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', profile_user=user)

@main_bp.route('/profile')
@login_required
def my_profile():
    return redirect(url_for('main.profile', username=current_user.username))

@main_bp.route('/history')
@login_required
def history():
    history = ReadHistory.query.filter_by(user_id=current_user.id).order_by(ReadHistory.read_at.desc()).all()
    return render_template('history.html', history=history)

@main_bp.route('/api/search')
def api_search():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    comics = Comic.query.filter(
        Comic.title_en.contains(q) | Comic.title_id.contains(q)
    ).order_by(Comic.views.desc()).limit(10).all()
    return jsonify([{
        'id': c.id,
        'title_en': c.title_en,
        'cover': c.cover,
        'type': c.type,
        'rating': c.rating
    } for c in comics])

@main_bp.route('/changelog')
def changelog():
    logs = Changelog.query.order_by(desc(Changelog.created_at)).all()
    return render_template('changelog.html', logs=logs)
