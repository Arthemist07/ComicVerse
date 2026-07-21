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

@api_bp.route('/chapter/complete', methods=['POST'])
@login_required
def complete_chapter():
    data = request.get_json() or {}
    comic_id = data.get('comic_id')
    chapter_id = data.get('chapter_id')
    if not comic_id or not chapter_id:
        return jsonify({'error': 'Missing comic_id or chapter_id'}), 400
    chapter = Chapter.query.get_or_404(chapter_id)
    comic = Comic.query.get_or_404(comic_id)
    existing = ReadHistory.query.filter_by(user_id=current_user.id, chapter_id=chapter_id).first()
    if not existing:
        ReadHistory.query.filter_by(user_id=current_user.id, comic_id=comic_id, chapter_id=chapter_id).delete()
        db.session.add(ReadHistory(user_id=current_user.id, comic_id=comic_id, chapter_id=chapter_id))
        current_user.add_xp(10)
        current_user.update_streak()
        db.session.commit()
    return jsonify({
        'ok': True,
        'xp': current_user.xp,
        'level': current_user.level,
        'streak': current_user.streak
    })

@api_bp.route('/comic/<int:comic_id>/comments', methods=['GET'])
def get_comments(comic_id):
    from models import Comment
    comments = Comment.query.filter_by(comic_id=comic_id, parent_id=None).order_by(Comment.is_pinned.desc(), Comment.created_at.desc()).all()
    result = []
    for c in comments:
        result.append({
            'id': c.id,
            'user': c.user.username,
            'avatar': c.user.avatar,
            'content': c.content,
            'is_spoiler': c.is_spoiler,
            'is_pinned': c.is_pinned,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M') if c.created_at else '',
            'replies': [{
                'id': r.id,
                'user': r.user.username,
                'avatar': r.user.avatar,
                'content': r.content,
                'is_spoiler': r.is_spoiler,
                'created_at': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else ''
            } for r in c.replies]
        })
    return jsonify(result)

@api_bp.route('/comic/<int:comic_id>/comment', methods=['POST'])
@login_required
def add_comment(comic_id):
    from models import Comment
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    parent_id = data.get('parent_id')
    is_spoiler = data.get('is_spoiler', False)
    if not content:
        return jsonify({'error': 'Content required'}), 400
    c = Comment(user_id=current_user.id, comic_id=comic_id, content=content,
                parent_id=parent_id, is_spoiler=is_spoiler)
    db.session.add(c)
    db.session.commit()
    return jsonify({'ok': True, 'id': c.id})

@api_bp.route('/comment/<int:id>/pin', methods=['POST'])
@login_required
def pin_comment(id):
    from models import Comment
    c = Comment.query.get_or_404(id)
    if not current_user.is_admin and not current_user.is_author:
        return jsonify({'error': 'Unauthorized'}), 403
    c.is_pinned = not c.is_pinned
    db.session.commit()
    return jsonify({'pinned': c.is_pinned})

@api_bp.route('/comment/<int:id>/delete', methods=['POST'])
@login_required
def delete_comment(id):
    from models import Comment
    c = Comment.query.get_or_404(id)
    if c.user_id != current_user.id and not current_user.is_admin and not current_user.is_author:
        return jsonify({'error': 'Unauthorized'}), 403
    Comment.query.filter_by(parent_id=id).delete()
    db.session.delete(c)
    db.session.commit()
    return jsonify({'ok': True})

@api_bp.route('/comic/<int:comic_id>/upload-cover', methods=['POST'])
@login_required
def upload_comic_cover(comic_id):
    from app import save_upload, allowed_file
    comic = Comic.query.get_or_404(comic_id)
    if not current_user.is_admin and (not current_user.is_author or comic.author_id != current_user.id):
        return jsonify({'error': 'Unauthorized'}), 403
    file = request.files.get('cover_file')
    if file and allowed_file(file.filename):
        url = save_upload(file, 'covers')
        if url:
            comic.cover = url
            db.session.commit()
            return jsonify({'url': url})
    return jsonify({'error': 'Upload failed'}), 400

@api_bp.route('/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    from app import save_upload, allowed_file
    file = request.files.get('file')
    if file and allowed_file(file.filename):
        url = save_upload(file, 'covers')
        if url:
            current_user.avatar = url
            db.session.commit()
            return jsonify({'url': url})
    return jsonify({'error': 'Upload failed'}), 400

@api_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    from app import save_upload, allowed_file
    current_user.bio = request.form.get('bio', current_user.bio)
    current_user.theme = request.form.get('theme', current_user.theme)
    current_user.language = request.form.get('language', current_user.language)
    current_user.custom_title = request.form.get('custom_title', current_user.custom_title)
    avatar_file = request.files.get('avatar_file')
    if avatar_file and allowed_file(avatar_file.filename):
        url = save_upload(avatar_file, 'covers')
        if url:
            current_user.avatar = url
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
