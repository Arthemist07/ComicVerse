from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar = db.Column(db.String(500), default='default.png')
    bio = db.Column(db.Text, default='')
    theme = db.Column(db.String(10), default='dark')
    language = db.Column(db.String(5), default='en')
    custom_bg = db.Column(db.String(500), default='')
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    history = db.relationship('ReadHistory', backref='user', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    followed = db.relationship('User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_count(self):
        return self.followed.count()

    def followers_count(self):
        return self.followers.count()


class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(50), unique=True, nullable=False)
    name_id = db.Column(db.String(50), nullable=False)
    comics = db.relationship('ComicGenre', backref='genre', lazy='dynamic')


class Comic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title_en = db.Column(db.String(200), nullable=False)
    title_id = db.Column(db.String(200), nullable=False)
    description_en = db.Column(db.Text, default='')
    description_id = db.Column(db.Text, default='')
    cover = db.Column(db.String(500), default='default_cover.png')
    banner = db.Column(db.String(500), default='')
    type = db.Column(db.String(10), default='manga')
    status = db.Column(db.String(20), default='ongoing')
    author = db.Column(db.String(100), default='')
    artist = db.Column(db.String(100), default='')
    rating = db.Column(db.Float, default=0.0)
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    genres = db.relationship('ComicGenre', backref='comic', lazy='dynamic')
    chapters = db.relationship('Chapter', backref='comic', lazy='dynamic', order_by='Chapter.number.desc()')


class ComicGenre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comic_id = db.Column(db.Integer, db.ForeignKey('comic.id'))
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'))


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comic_id = db.Column(db.Integer, db.ForeignKey('comic.id'))
    number = db.Column(db.Float, nullable=False)
    title_en = db.Column(db.String(200), default='')
    title_id = db.Column(db.String(200), default='')
    pages = db.Column(db.Text, default='[]')
    views = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('comic_id', 'number'),)


class ReadHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comic_id = db.Column(db.Integer, db.ForeignKey('comic.id'))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    page = db.Column(db.Integer, default=0)
    read_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    comic_id = db.Column(db.Integer, db.ForeignKey('comic.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('user_id', 'comic_id'),)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(20))
    message_en = db.Column(db.String(500))
    message_id = db.Column(db.String(500))
    link = db.Column(db.String(500), default='#')
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Changelog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False)
    content_en = db.Column(db.Text, nullable=False)
    content_id = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, default='')
