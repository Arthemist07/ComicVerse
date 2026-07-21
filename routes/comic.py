import json
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from models import db, Comic, Chapter, Genre, ComicGenre, ReadHistory, Favorite

comic_bp = Blueprint('comic', __name__)

@comic_bp.route('/comic/<int:comic_id>')
def comic_detail(comic_id):
    comic = Comic.query.get_or_404(comic_id)
    comic.views += 1
    db.session.commit()
    chapters = Chapter.query.filter_by(comic_id=comic_id).order_by(Chapter.number.desc()).all()
    related = ComicGenre.query.filter_by(genre_id=comic.genres.first().genre_id if comic.genres.first() else 0).all()
    related_ids = [g.comic_id for g in related if g.comic_id != comic_id][:6]
    related_comics = Comic.query.filter(Comic.id.in_(related_ids)).all() if related_ids else []
    return render_template('comic.html', comic=comic, chapters=chapters, related_comics=related_comics)

@comic_bp.route('/read/<int:comic_id>/<int:chapter_id>')
def reader(comic_id, chapter_id):
    comic = Comic.query.get_or_404(comic_id)
    chapter = Chapter.query.get_or_404(chapter_id)
    pages = json.loads(chapter.pages) if chapter.pages else []
    chapter.views += 1
    db.session.commit()

    if current_user.is_authenticated:
        hist = ReadHistory.query.filter_by(user_id=current_user.id, comic_id=comic_id, chapter_id=chapter_id).first()
        if hist:
            hist.read_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        else:
            db.session.add(ReadHistory(user_id=current_user.id, comic_id=comic_id, chapter_id=chapter_id))
        db.session.commit()

    chapters = Chapter.query.filter_by(comic_id=comic_id).order_by(Chapter.number).all()
    prev_ch = next((c for c in chapters if c.number < chapter.number), None)
    next_ch = next((c for c in reversed(chapters) if c.number > chapter.number), None)

    return render_template('reader.html', comic=comic, chapter=chapter,
                         pages=pages, prev_ch=prev_ch, next_ch=next_ch)

@comic_bp.route('/comic/<int:comic_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(comic_id):
    fav = Favorite.query.filter_by(user_id=current_user.id, comic_id=comic_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({'favorited': False})
    else:
        db.session.add(Favorite(user_id=current_user.id, comic_id=comic_id))
        db.session.commit()
        return jsonify({'favorited': True})

@comic_bp.route('/genres')
def genres():
    all_genres = Genre.query.all()
    return render_template('genres.html', genres=all_genres)
