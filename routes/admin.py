import json, os, re, requests, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from bs4 import BeautifulSoup
from models import db, Comic, Chapter, Genre, ComicGenre, User, Changelog, Notification, SiteSettings, LevelConfig, UserRole, UserRoleAssignment
from werkzeug.utils import secure_filename
admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

from datetime import datetime, date, timedelta

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    from sqlalchemy import func
    total_views = db.session.query(func.sum(Comic.views)).scalar() or 0
    total_users = User.query.count()
    total_authors = User.query.filter_by(is_author=True).count()
    recent_comics = Comic.query.order_by(Comic.updated_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    pending_authors = User.query.filter_by(is_author=True, is_verified=False).count()
    stats = {
        'comics': Comic.query.count(),
        'chapters': Chapter.query.count(),
        'users': total_users,
        'authors': total_authors,
        'views': total_views,
        'pending_authors': pending_authors,
        'recent_comics': recent_comics,
        'recent_users': recent_users,
    }
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/comics')
@login_required
@admin_required
def comics():
    all_comics = Comic.query.order_by(Comic.updated_at.desc()).all()
    return render_template('admin/comics.html', comics=all_comics)

@admin_bp.route('/comic/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_comic():
    from app import save_upload, allowed_file
    genres = Genre.query.all()
    if request.method == 'POST':
        cover_url = request.form.get('cover', '')
        cover_file = request.files.get('cover_file')
        if cover_file and allowed_file(cover_file.filename):
            cover_url = save_upload(cover_file, 'covers') or cover_url

        banner_url = request.form.get('banner', '')
        banner_file = request.files.get('banner_file')
        if banner_file and allowed_file(banner_file.filename):
            banner_url = save_upload(banner_file, 'covers') or banner_url

        comic = Comic(
            title_en=request.form['title_en'],
            title_id=request.form['title_id'],
            description_en=request.form['description_en'],
            description_id=request.form['description_id'],
            type=request.form['type'],
            status=request.form['status'],
            author=request.form.get('author', ''),
            artist=request.form.get('artist', ''),
            rating=float(request.form.get('rating', 0)),
            cover=cover_url or 'default_cover.png',
            banner=banner_url or '',
            author_id=current_user.id if not current_user.is_admin else None
        )
        db.session.add(comic)
        db.session.commit()

        for gid in request.form.getlist('genres'):
            db.session.add(ComicGenre(comic_id=comic.id, genre_id=int(gid)))
        db.session.commit()
        flash('Comic created! Add chapters now.', 'success')
        return redirect(url_for('admin.edit_comic', id=comic.id))
    return render_template('admin/comic_form.html', genres=genres, comic=None)

@admin_bp.route('/comic/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_comic(id):
    from app import save_upload, allowed_file
    comic = Comic.query.get_or_404(id)
    genres = Genre.query.all()
    if request.method == 'POST':
        comic.title_en = request.form['title_en']
        comic.title_id = request.form['title_id']
        comic.description_en = request.form['description_en']
        comic.description_id = request.form['description_id']
        comic.type = request.form['type']
        comic.status = request.form['status']
        comic.author = request.form['author']
        comic.artist = request.form['artist']
        comic.rating = float(request.form.get('rating', 0))

        cover_url = request.form.get('cover', comic.cover)
        cover_file = request.files.get('cover_file')
        if cover_file and allowed_file(cover_file.filename):
            cover_url = save_upload(cover_file, 'covers') or cover_url
        comic.cover = cover_url

        banner_url = request.form.get('banner', comic.banner)
        banner_file = request.files.get('banner_file')
        if banner_file and allowed_file(banner_file.filename):
            banner_url = save_upload(banner_file, 'covers') or banner_url
        comic.banner = banner_url

        ComicGenre.query.filter_by(comic_id=comic.id).delete()
        for gid in request.form.getlist('genres'):
            db.session.add(ComicGenre(comic_id=comic.id, genre_id=int(gid)))
        db.session.commit()
        flash('Comic updated!', 'success')
        return redirect(url_for('admin.edit_comic', id=comic.id))
    return render_template('admin/comic_form.html', genres=genres, comic=comic)

@admin_bp.route('/comic/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_comic(id):
    comic = Comic.query.get_or_404(id)
    Chapter.query.filter_by(comic_id=id).delete()
    ComicGenre.query.filter_by(comic_id=id).delete()
    db.session.delete(comic)
    db.session.commit()
    flash('Comic deleted', 'success')
    return redirect(url_for('admin.comics'))

@admin_bp.route('/chapters/<int:comic_id>')
@login_required
@admin_required
def chapters(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    chs = Chapter.query.filter_by(comic_id=comic_id).order_by(Chapter.number.desc()).all()
    return render_template('admin/chapters.html', comic=comic, chapters=chs)

@admin_bp.route('/chapter/create/<int:comic_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def create_chapter(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    if request.method == 'POST':
        chapter = Chapter(
            comic_id=comic_id,
            number=float(request.form['number']),
            title_en=request.form['title_en'],
            title_id=request.form['title_id'],
            pages=request.form.get('pages', '[]')
        )
        db.session.add(chapter)
        db.session.commit()
        flash('Chapter created!', 'success')
        return redirect(url_for('admin.chapters', comic_id=comic_id))
    return render_template('admin/chapter_form.html', comic=comic, chapter=None)

@admin_bp.route('/chapter/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    if request.method == 'POST':
        chapter.number = float(request.form['number'])
        chapter.title_en = request.form['title_en']
        chapter.title_id = request.form['title_id']
        chapter.pages = request.form.get('pages', '[]')
        db.session.commit()
        flash('Chapter updated!', 'success')
        return redirect(url_for('admin.chapters', comic_id=chapter.comic_id))
    return render_template('admin/chapter_form.html', comic=chapter.comic, chapter=chapter)

@admin_bp.route('/chapter/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    comic_id = chapter.comic_id
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted', 'success')
    return redirect(url_for('admin.chapters', comic_id=comic_id))

@admin_bp.route('/genres')
@login_required
@admin_required
def manage_genres():
    all_genres = Genre.query.all()
    return render_template('admin/genres.html', genres=all_genres)

@admin_bp.route('/genre/create', methods=['POST'])
@login_required
@admin_required
def create_genre():
    g = Genre(name_en=request.form['name_en'], name_id=request.form['name_id'])
    db.session.add(g)
    db.session.commit()
    flash('Genre created!', 'success')
    return redirect(url_for('admin.manage_genres'))

@admin_bp.route('/genre/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_genre(id):
    Genre.query.filter_by(id=id).delete()
    db.session.commit()
    flash('Genre deleted', 'success')
    return redirect(url_for('admin.manage_genres'))

@admin_bp.route('/genre/inline-add', methods=['POST'])
@login_required
@admin_required
def inline_add_genre():
    name_en = request.form.get('name_en', '').strip()
    name_id = request.form.get('name_id', '').strip()
    if not name_en or not name_id:
        return {'error': 'Both names required'}, 400
    existing = Genre.query.filter_by(name_en=name_en).first()
    if existing:
        return {'id': existing.id, 'name_en': existing.name_en}
    g = Genre(name_en=name_en, name_id=name_id)
    db.session.add(g)
    db.session.commit()
    return {'id': g.id, 'name_en': g.name_en}

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    if request.method == 'POST':
        for key in ['site_name_en', 'site_name_id', 'site_description', 'custom_css', 'custom_js', 'custom_bg', 'footer_text']:
            if key in request.form:
                s = SiteSettings.query.filter_by(key=key).first()
                if s:
                    s.value = request.form[key]
                else:
                    db.session.add(SiteSettings(key=key, value=request.form[key]))
        db.session.commit()
        flash('Settings saved!', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html')

@admin_bp.route('/changelog', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_changelog():
    if request.method == 'POST':
        log = Changelog(
            version=request.form['version'],
            content_en=request.form['content_en'],
            content_id=request.form['content_id']
        )
        db.session.add(log)
        db.session.commit()
        flash('Changelog added!', 'success')
        return redirect(url_for('admin.manage_changelog'))
    logs = Changelog.query.order_by(Changelog.created_at.desc()).all()
    return render_template('admin/changelog.html', logs=logs)

@admin_bp.route('/changelog/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_changelog(id):
    Changelog.query.filter_by(id=id).delete()
    db.session.commit()
    flash('Changelog deleted', 'success')
    return redirect(url_for('admin.manage_changelog'))

@admin_bp.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_comic():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        source = request.form.get('source', '').strip().lower()
        if not url:
            flash('URL is required', 'error')
            return render_template('admin/import.html')
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            title_en = 'Imported Comic'
            title_id = title_en
            desc_en = ''
            desc_id = ''
            cover = ''

            # MangaDex API import
            if 'mangadex' in url or source == 'mangadex':
                md_match = re.search(r'(?:mangadex\.org/(?:title/)?)([a-f0-9\-]{36})', url)
                if md_match:
                    md_id = md_match.group(1)
                elif re.match(r'^[a-f0-9\-]{36}$', url):
                    md_id = url
                else:
                    raise Exception('Could not extract MangaDex ID from URL')

                # Fetch manga details from MangaDex API
                md_resp = requests.get(f'https://api.mangadex.org/manga/{md_id}', headers=headers, timeout=15)
                if md_resp.status_code != 200:
                    raise Exception(f'MangaDex API returned {md_resp.status_code}')
                md_data = md_resp.json().get('data', {})
                attrs = md_data.get('attributes', {})

                title_en = attrs.get('title', {}).get('en', '')
                alt_titles = attrs.get('altTitles', [])
                for at in alt_titles:
                    if 'id' in at:
                        title_id = at['id']
                        break
                if not title_id:
                    title_id = title_en
                desc_en = attrs.get('description', {}).get('en', '')
                desc_id = attrs.get('description', {}).get('id', '')

                # Get cover from MangaDex
                cover_resp = requests.get(f'https://api.mangadex.org/cover?manga[]={md_id}', headers=headers, timeout=10)
                if cover_resp.status_code == 200:
                    cover_data = cover_resp.json().get('data', [])
                    if cover_data:
                        cv_attrs = cover_data[0].get('attributes', {})
                        cv_file = cv_attrs.get('fileName', '')
                        if cv_file:
                            cover = f'https://uploads.mangadex.org/covers/{md_id}/{cv_file}'

            else:
                # Generic import via HTML scraping
                resp = requests.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(resp.text, 'lxml')
                title_en = soup.title.string if soup.title else 'Imported Comic'
                title_id = title_en
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    desc_en = meta_desc.get('content', '')
                og_img = soup.find('meta', property='og:image')
                if og_img:
                    cover = og_img.get('content', '')

            comic = Comic(
                title_en=title_en or 'Imported Comic',
                title_id=title_id or title_en or 'Imported Comic',
                description_en=desc_en,
                description_id=desc_id or desc_en,
                cover=cover or '/static/uploads/covers/default_cover.png'
            )
            db.session.add(comic)
            db.session.commit()
            flash(f'Imported: {title_en}', 'success')
            return redirect(url_for('admin.edit_comic', id=comic.id))
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
    return render_template('admin/import.html')

@admin_bp.route('/upload')
@login_required
@admin_required
def upload():
    import glob
    covers = glob.glob(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'covers', '*'))
    pages = glob.glob(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'pages', '*'))
    all_imgs = []
    for f in sorted(covers + pages, key=os.path.getmtime, reverse=True)[:24]:
        rel = f.split(os.path.sep + 'static' + os.path.sep + 'uploads' + os.path.sep)[-1].replace(os.path.sep, '/')
        all_imgs.append(f'/static/uploads/{rel}')
    return render_template('admin/upload.html', recent_images=all_imgs)

@admin_bp.route('/comic/toggle-nsfw/<int:id>')
@login_required
@admin_required
def toggle_nsfw(id):
    comic = Comic.query.get_or_404(id)
    comic.nsfw = not comic.nsfw
    db.session.commit()
    flash(f'NSFW: {comic.nsfw}', 'success')
    return redirect(url_for('admin.comics'))

@admin_bp.route('/comic/transfer/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def transfer_comic(id):
    comic = Comic.query.get_or_404(id)
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.transfer_comic', id=id))
        comic.author_id = user.id
        db.session.commit()
        flash(f'Comic transferred to {username}', 'success')
        return redirect(url_for('admin.comics'))
    return render_template('admin/transfer.html', comic=comic)

@admin_bp.route('/upload-image', methods=['POST'])
@login_required
@admin_required
def upload_image():
    from app import save_upload
    img_type = request.form.get('type', 'covers')
    if img_type not in ['covers', 'pages']:
        img_type = 'covers'
    file = request.files.get('file')
    if file:
        url = save_upload(file, img_type)
        if url:
            flash(f'Uploaded! URL: {url}', 'success')
        else:
            flash('Invalid file type', 'error')
    return redirect(url_for('admin.upload'))

@admin_bp.route('/toggle-author/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_author(user_id):
    user = User.query.get_or_404(user_id)
    user.is_author = not user.is_author
    db.session.commit()
    flash(f'User {user.username} author status: {user.is_author}', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/ban/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    if user_id == current_user.id:
        flash('Cannot ban yourself', 'error')
        return redirect(url_for('admin.manage_users'))
    user = User.query.get_or_404(user_id)
    user.is_banned = not user.is_banned
    db.session.commit()
    flash(f'{user.username} banned: {user.is_banned}', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/warn/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def warn_user(user_id):
    user = User.query.get_or_404(user_id)
    user.warning_count = (user.warning_count or 0) + 1
    db.session.commit()
    flash(f'Warning issued to {user.username} ({user.warning_count}/3)', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    new_pass = request.form.get('new_password', 'changeme123')
    user.set_password(new_pass)
    db.session.commit()
    flash(f'Password for {user.username} reset to: {new_pass}', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Cannot delete yourself', 'error')
        return redirect(url_for('admin.manage_users'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    if user_id == current_user.id:
        flash('Cannot revoke your own admin', 'error')
        return redirect(url_for('admin.manage_users'))
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'User {user.username} admin status: {user.is_admin}', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/levels', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_levels():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            lv = int(request.form['level'])
            xp = int(request.form['xp_required'])
            title = request.form.get('title', '')
            existing = LevelConfig.query.filter_by(level=lv).first()
            if existing:
                existing.xp_required = xp
                existing.title = title
            else:
                db.session.add(LevelConfig(level=lv, xp_required=xp, title=title))
            flash(f'Level {lv} saved', 'success')
        elif action == 'delete':
            LevelConfig.query.filter_by(id=int(request.form['id'])).delete()
            flash('Level deleted', 'success')
        elif action == 'defaults':
            LevelConfig.query.delete()
            defaults = [(1, 0), (2, 100), (3, 300), (4, 600), (5, 1000), (6, 1600), (7, 2400), (8, 3400), (9, 4600), (10, 6000)]
            for lv, xp in defaults:
                db.session.add(LevelConfig(level=lv, xp_required=xp))
            flash('Default levels restored', 'success')
        db.session.commit()
        return redirect(url_for('admin.manage_levels'))
    levels = LevelConfig.query.order_by(LevelConfig.level).all()
    return render_template('admin/levels.html', levels=levels)

@admin_bp.route('/roles', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_roles():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            r = UserRole(name=request.form['name'], color=request.form.get('color', '#6c5ce7'), icon=request.form.get('icon', '🏅'))
            db.session.add(r)
            flash(f'Role "{r.name}" created', 'success')
        elif action == 'edit':
            role = UserRole.query.get_or_404(int(request.form['id']))
            role.name = request.form['name']
            role.color = request.form.get('color', role.color)
            role.icon = request.form.get('icon', role.icon)
            flash('Role updated', 'success')
        elif action == 'delete':
            UserRoleAssignment.query.filter_by(role_id=int(request.form['id'])).delete()
            UserRole.query.filter_by(id=int(request.form['id'])).delete()
            flash('Role deleted', 'success')
        elif action == 'assign':
            role = UserRole.query.get_or_404(int(request.form['role_id']))
            user = User.query.get_or_404(int(request.form['user_id']))
            existing = UserRoleAssignment.query.filter_by(user_id=user.id, role_id=role.id).first()
            if existing:
                db.session.delete(existing)
                flash(f'Removed role from {user.username}', 'success')
            else:
                db.session.add(UserRoleAssignment(user_id=user.id, role_id=role.id))
                flash(f'Assigned role to {user.username}', 'success')
        db.session.commit()
        return redirect(url_for('admin.manage_roles'))
    roles = UserRole.query.all()
    users = User.query.order_by(User.username).all()
    return render_template('admin/roles.html', roles=roles, users=users)

@admin_bp.route('/authors')
@login_required
@admin_required
def authors():
    from datetime import datetime
    authors_list = User.query.filter_by(is_author=True).all()
    for a in authors_list:
        a.comics = Comic.query.filter_by(author_id=a.id).count()
    return render_template('admin/authors.html', authors=authors_list, now=datetime.utcnow())

@admin_bp.route('/author/toggle-verify/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_verify(user_id):
    user = User.query.get_or_404(user_id)
    user.is_verified = not user.is_verified
    db.session.commit()
    flash(f'{user.username} verified: {user.is_verified}', 'success')
    return redirect(url_for('admin.authors'))

@admin_bp.route('/author/suspend/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def suspend_author(user_id):
    user = User.query.get_or_404(user_id)
    days = int(request.form.get('days', 7))
    user.suspension_until = datetime.utcnow() + timedelta(days=days)
    db.session.commit()
    flash(f'{user.username} suspended for {days} days', 'success')
    return redirect(url_for('admin.authors'))

@admin_bp.route('/author/unsuspend/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def unsuspend_author(user_id):
    user = User.query.get_or_404(user_id)
    user.suspension_until = None
    db.session.commit()
    flash(f'{user.username} unsuspended', 'success')
    return redirect(url_for('admin.authors'))

@admin_bp.route('/announcements')
@login_required
@admin_required
def announcements():
    from models import Announcement
    anns = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=anns)

@admin_bp.route('/announcement/create', methods=['POST'])
@login_required
@admin_required
def create_announcement():
    from models import Announcement
    a = Announcement(
        title_en=request.form['title_en'],
        title_id=request.form.get('title_id', request.form['title_en']),
        content_en=request.form['content_en'],
        content_id=request.form.get('content_id', request.form['content_en']),
        type=request.form.get('type', 'info'),
        pinned='pinned' in request.form,
        link=request.form.get('link', ''),
    )
    db.session.add(a)
    db.session.commit()
    flash('Announcement created', 'success')
    return redirect(url_for('admin.announcements'))

@admin_bp.route('/announcement/delete/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_announcement(id):
    from models import Announcement
    Announcement.query.filter_by(id=id).delete()
    db.session.commit()
    flash('Announcement deleted', 'success')
    return redirect(url_for('admin.announcements'))

@admin_bp.route('/send-notification', methods=['POST'])
@login_required
@admin_required
def send_notification():
    msg_en = request.form.get('message_en', '')
    msg_id = request.form.get('message_id', '')
    link = request.form.get('link', '#')
    users = User.query.all()
    for u in users:
        db.session.add(Notification(
            user_id=u.id,
            type='update',
            message_en=msg_en or 'New update available!',
            message_id=msg_id or 'Pembaruan baru tersedia!',
            link=link
        ))
    db.session.commit()
    flash('Notification sent to all users!', 'success')
    return redirect(url_for('admin.dashboard'))
