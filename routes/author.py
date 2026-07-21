import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import db, Comic, Chapter, Genre, ComicGenre
author_bp = Blueprint('author', __name__, url_prefix='/author')

def author_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not (current_user.is_admin or current_user.is_author):
            flash('Author access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@author_bp.route('/')
@login_required
@author_required
def dashboard():
    if current_user.is_admin:
        comics = Comic.query.order_by(Comic.updated_at.desc()).all()
    else:
        comics = Comic.query.filter_by(author_id=current_user.id).order_by(Comic.updated_at.desc()).all()
    total_chapters = sum(c.chapters.count() for c in comics)
    total_views = sum(c.views for c in comics)
    total_followers = 0
    from models import Favorite
    for c in comics:
        total_followers += Favorite.query.filter_by(comic_id=c.id).count()
    stats = {
        'comics': len(comics),
        'chapters': total_chapters,
        'views': total_views,
        'followers': total_followers,
    }
    return render_template('author/dashboard.html', comics=comics, stats=stats)

@author_bp.route('/comic/create', methods=['GET', 'POST'])
@login_required
@author_required
def create_comic():
    from app import save_upload, allowed_file
    genres = Genre.query.all()
    if request.method == 'POST':
        cover_url = 'default_cover.png'
        cover_file = request.files.get('cover_file')
        if cover_file and allowed_file(cover_file.filename):
            cover_url = save_upload(cover_file, 'covers') or cover_url

        banner_url = ''
        banner_file = request.files.get('banner_file')
        if banner_file and allowed_file(banner_file.filename):
            banner_url = save_upload(banner_file, 'covers') or banner_url

        comic = Comic(
            title_en=request.form['title_en'],
            title_id=request.form['title_id'],
            description_en=request.form.get('description_en', ''),
            description_id=request.form.get('description_id', ''),
            type=request.form['type'],
            status=request.form['status'],
            author=request.form.get('author', current_user.username),
            artist=request.form.get('artist', ''),
            rating=float(request.form.get('rating', 0)),
            cover=cover_url,
            banner=banner_url,
            author_id=current_user.id
        )
        db.session.add(comic)
        db.session.commit()
        for gid in request.form.getlist('genres'):
            db.session.add(ComicGenre(comic_id=comic.id, genre_id=int(gid)))
        db.session.commit()
        flash('Comic created! Add chapters now.', 'success')
        return redirect(url_for('author.edit_comic', id=comic.id))
    return render_template('author/comic_form.html', genres=genres, comic=None)

@author_bp.route('/comic/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@author_required
def edit_comic(id):
    from app import save_upload, allowed_file
    comic = Comic.query.get_or_404(id)
    if comic.author_id != current_user.id and not current_user.is_admin:
        flash('Not your comic', 'error')
        return redirect(url_for('author.dashboard'))
    genres = Genre.query.all()
    if request.method == 'POST':
        comic.title_en = request.form['title_en']
        comic.title_id = request.form['title_id']
        comic.description_en = request.form.get('description_en', '')
        comic.description_id = request.form.get('description_id', '')
        comic.type = request.form['type']
        comic.status = request.form['status']
        comic.rating = float(request.form.get('rating', 0))

        cover_file = request.files.get('cover_file')
        if cover_file and allowed_file(cover_file.filename):
            comic.cover = save_upload(cover_file, 'covers') or comic.cover

        banner_file = request.files.get('banner_file')
        if banner_file and allowed_file(banner_file.filename):
            comic.banner = save_upload(banner_file, 'covers') or comic.banner

        ComicGenre.query.filter_by(comic_id=comic.id).delete()
        for gid in request.form.getlist('genres'):
            db.session.add(ComicGenre(comic_id=comic.id, genre_id=int(gid)))
        db.session.commit()
        flash('Comic updated!', 'success')
        return redirect(url_for('author.dashboard'))
    return render_template('author/comic_form.html', genres=genres, comic=comic)

@author_bp.route('/comic/delete/<int:id>', methods=['POST'])
@login_required
@author_required
def delete_comic(id):
    comic = Comic.query.get_or_404(id)
    if comic.author_id != current_user.id and not current_user.is_admin:
        flash('Not your comic', 'error')
        return redirect(url_for('author.dashboard'))
    Chapter.query.filter_by(comic_id=id).delete()
    ComicGenre.query.filter_by(comic_id=id).delete()
    db.session.delete(comic)
    db.session.commit()
    flash('Comic deleted', 'success')
    return redirect(url_for('author.dashboard'))

@author_bp.route('/chapters/<int:comic_id>')
@login_required
@author_required
def chapters(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    if comic.author_id != current_user.id and not current_user.is_admin:
        flash('Not your comic', 'error')
        return redirect(url_for('author.dashboard'))
    chs = Chapter.query.filter_by(comic_id=comic_id).order_by(Chapter.number.desc()).all()
    return render_template('author/chapters.html', comic=comic, chapters=chs)

@author_bp.route('/chapter/create/<int:comic_id>', methods=['GET', 'POST'])
@login_required
@author_required
def create_chapter(comic_id):
    from app import save_upload, allowed_file
    comic = Comic.query.get_or_404(comic_id)
    if comic.author_id != current_user.id and not current_user.is_admin:
        flash('Not your comic', 'error')
        return redirect(url_for('author.dashboard'))
    if request.method == 'POST':
        pages = []
        page_files = request.files.getlist('page_files')
        for pf in page_files:
            if pf and allowed_file(pf.filename):
                url = save_upload(pf, 'pages')
                if url:
                    pages.append(url)
        chapter = Chapter(
            comic_id=comic_id,
            number=float(request.form['number']),
            title_en=request.form['title_en'],
            title_id=request.form['title_id'],
            pages=json.dumps(pages) if pages else '[]',
            is_draft='is_draft' in request.form
        )
        db.session.add(chapter)
        db.session.commit()
        flash('Chapter created!' + (' (Draft)' if chapter.is_draft else ''), 'success')
        return redirect(url_for('author.chapters', comic_id=comic_id))
    return render_template('author/chapter_form.html', comic=comic, chapter=None)

@author_bp.route('/chapter/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@author_required
def edit_chapter(id):
    from app import save_upload, allowed_file
    chapter = Chapter.query.get_or_404(id)
    comic = chapter.comic
    if comic.author_id != current_user.id and not current_user.is_admin:
        flash('Not your comic', 'error')
        return redirect(url_for('author.dashboard'))
    if request.method == 'POST':
        chapter.number = float(request.form['number'])
        chapter.title_en = request.form['title_en']
        chapter.title_id = request.form['title_id']
        chapter.is_draft = 'is_draft' in request.form
        page_files = request.files.getlist('page_files')
        new_pages = []
        for pf in page_files:
            if pf and allowed_file(pf.filename):
                url = save_upload(pf, 'pages')
                if url:
                    new_pages.append(url)
        if new_pages:
            chapter.pages = json.dumps(new_pages)
        db.session.commit()
        flash('Chapter updated!', 'success')
        return redirect(url_for('author.chapters', comic_id=comic.id))
    return render_template('author/chapter_form.html', comic=comic, chapter=chapter)

@author_bp.route('/chapter/delete/<int:id>', methods=['POST'])
@login_required
@author_required
def delete_chapter(id):
    chapter = Chapter.query.get_or_404(id)
    comic = chapter.comic
    if comic.author_id != current_user.id and not current_user.is_admin:
        flash('Not your comic', 'error')
        return redirect(url_for('author.dashboard'))
    cid = chapter.comic_id
    db.session.delete(chapter)
    db.session.commit()
    flash('Chapter deleted', 'success')
    return redirect(url_for('author.chapters', comic_id=cid))

@author_bp.route('/genres')
@login_required
@author_required
def manage_genres():
    genres = Genre.query.order_by(Genre.name_en).all()
    return render_template('author/genres.html', genres=genres)

@author_bp.route('/genre/create', methods=['POST'])
@login_required
@author_required
def create_genre():
    name_en = request.form.get('name_en', '').strip()
    name_id = request.form.get('name_id', '').strip()
    if not name_en or not name_id:
        flash('Both English and Indonesian names required', 'error')
        return redirect(url_for('author.manage_genres'))
    if Genre.query.filter_by(name_en=name_en).first():
        flash('Genre already exists', 'error')
        return redirect(url_for('author.manage_genres'))
    g = Genre(name_en=name_en, name_id=name_id)
    db.session.add(g)
    db.session.commit()
    flash(f'Genre "{name_en}" created!', 'success')
    return redirect(url_for('author.manage_genres'))

@author_bp.route('/genre/delete/<int:id>', methods=['POST'])
@login_required
@author_required
def delete_genre(id):
    genre = Genre.query.get_or_404(id)
    ComicGenre.query.filter_by(genre_id=id).delete()
    db.session.delete(genre)
    db.session.commit()
    flash('Genre deleted', 'success')
    return redirect(url_for('author.manage_genres'))

@author_bp.route('/genre/inline-add', methods=['POST'])
@login_required
@author_required
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
