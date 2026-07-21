import json, os, re, requests, uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from bs4 import BeautifulSoup
from models import db, Comic, Chapter, Genre, ComicGenre, User, Changelog, Notification, SiteSettings
from werkzeug.utils import secure_filename
from app import save_upload, allowed_file

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    stats = {
        'comics': Comic.query.count(),
        'chapters': Chapter.query.count(),
        'users': User.query.count(),
        'views': sum(c.views for c in Comic.query.all())
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
            author=request.form['author'],
            artist=request.form['artist'],
            cover=cover_url or 'default_cover.png',
            banner=banner_url or '',
            author_id=current_user.id if not current_user.is_admin else None
        )
        db.session.add(comic)
        db.session.commit()

        for gid in request.form.getlist('genres'):
            db.session.add(ComicGenre(comic_id=comic.id, genre_id=int(gid)))
        db.session.commit()
        flash('Comic created!', 'success')
        return redirect(url_for('admin.comics'))
    return render_template('admin/comic_form.html', genres=genres, comic=None)

@admin_bp.route('/comic/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_comic(id):
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
        return redirect(url_for('admin.comics'))
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
                import re as _re
                md_match = _re.search(r'(?:mangadex\.org/(?:title/)?)([a-f0-9\-]{36})', url)
                if md_match:
                    md_id = md_match.group(1)
                elif _re.match(r'^[a-f0-9\-]{36}$', url):
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

                # Try to get chapters list
                try:
                    ch_resp = requests.get(f'https://api.mangadex.org/manga/{md_id}/feed?limit=5&translatedLanguage[]=en&order[chapter]=desc', headers=headers, timeout=10)
                except:
                    pass
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
        rel = f.split('static\\uploads\\')[-1].replace('\\', '/')
        all_imgs.append(f'/static/uploads/{rel}')
    return render_template('admin/upload.html', recent_images=all_imgs)

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
