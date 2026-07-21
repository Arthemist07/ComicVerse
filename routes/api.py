from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Comic, Chapter, User, Favorite, ReadHistory, Notification

api_bp = Blueprint('api', __name__)

@api_bp.route('/history')
@login_required
def get_history():
    history = ReadHistory.query.filter_by(user_id=current_user.id).order_by(ReadHistory.read_at.desc()).limit(20).all()
    data = [{
        'comic_id': h.comic_id,
        'chapter_id': h.chapter_id,
        'comic_title': h.comic.title_en if hasattr(h.comic, 'title_en') else '',
        'chapter_number': h.chapter.number if hasattr(h.chapter, 'number') else 0,
        'read_at': h.read_at.isoformat() if h.read_at else ''
    } for h in history if h.comic and h.chapter]
    return jsonify(data)

@api_bp.route('/favorites')
@login_required
def get_favorites():
    favs = Favorite.query.filter_by(user_id=current_user.id).all()
    data = [{
        'comic_id': f.comic_id,
        'title': f.comic.title_en if hasattr(f.comic, 'title_en') else '',
        'cover': f.comic.cover if hasattr(f.comic, 'cover') else ''
    } for f in favs if f.comic]
    return jsonify(data)

@api_bp.route('/notifications')
@login_required
def get_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(50).all()
    lang = current_user.language
    data = [{
        'id': n.id,
        'message': n.message_id if lang == 'id' else n.message_en,
        'link': n.link,
        'is_read': n.is_read,
        'created_at': n.created_at.isoformat() if n.created_at else ''
    } for n in notifs]
    return jsonify(data)

@api_bp.route('/notifications/read/<int:id>', methods=['POST'])
@login_required
def mark_read(id):
    n = Notification.query.filter_by(id=id, user_id=current_user.id).first()
    if n:
        n.is_read = True
        db.session.commit()
    return jsonify({'ok': True})

@api_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'ok': True})

@api_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    current_user.bio = request.form.get('bio', current_user.bio)
    current_user.theme = request.form.get('theme', current_user.theme)
    current_user.language = request.form.get('language', current_user.language)
    avatar = request.form.get('avatar', '')
    if avatar:
        current_user.avatar = avatar
    db.session.commit()
    return jsonify({'ok': True})

@api_bp.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def toggle_follow(user_id):
    target = User.query.get_or_404(user_id)
    if target == current_user:
        return jsonify({'error': 'Cannot follow yourself'}), 400
    if current_user.is_following(target):
        current_user.unfollow(target)
        return jsonify({'following': False})
    else:
        current_user.follow(target)
        db.session.add(Notification(
            user_id=target.id,
            type='follow',
            message_en=f'{current_user.username} started following you!',
            message_id=f'{current_user.username} mulai mengikuti Anda!',
            link=f'/profile/{current_user.username}'
        ))
        db.session.commit()
        return jsonify({'following': True})
