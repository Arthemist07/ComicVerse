import os, json, boto3, requests, uuid
from datetime import datetime

from flask import Flask, session, request as flask_request
from flask_login import LoginManager
from config import Config
from models import db, User, SiteSettings
from routes.auth import auth_bp
from routes.main import main_bp
from routes.comic import comic_bp
from routes.admin import admin_bp
from routes.api import api_bp
from routes.author import author_bp

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, subfolder='covers'):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        fname = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_FOLDER, subfolder, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        file.save(path)
        return f"/static/uploads/{subfolder}/{fname}"
    return None

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

_translations = {}
def load_translations():
    global _translations
    for lang in ['en', 'id']:
        path = os.path.join(os.path.dirname(__file__), 'translations', f'{lang}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}

load_translations()

def _(text):
    lang = session.get('language', 'en')
    return _translations.get(lang, {}).get(text, _translations.get('en', {}).get(text, text))

app.jinja_env.globals.update(_=_)

def get_r2_client():
    return boto3.client('s3',
        endpoint_url=f"https://{app.config['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=app.config['R2_ACCESS_KEY'],
        aws_secret_access_key=app.config['R2_SECRET_KEY'],
        region_name='auto')

def upload_to_r2(file_obj, filename):
    client = get_r2_client()
    client.upload_fileobj(file_obj, app.config['R2_BUCKET_NAME'], filename, ExtraArgs={'ACL': 'public-read'})
    return f"{app.config['R2_PUBLIC_URL']}/{filename}"

def delete_from_r2(filename):
    client = get_r2_client()
    client.delete_object(Bucket=app.config['R2_BUCKET_NAME'], Key=filename)

def get_setting(key):
    s = SiteSettings.query.filter_by(key=key).first()
    return s.value if s else ''

def set_setting(key, value):
    s = SiteSettings.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = SiteSettings(key=key, value=value)
        db.session.add(s)
    db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(comic_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(author_bp)

app.jinja_env.globals.update(get_setting=get_setting)

@app.template_filter('from_json')
def from_json(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []

@app.template_filter('page_count')
def page_count(value):
    if not value:
        return 0
    try:
        return len(json.loads(value))
    except:
        return 0

def init_db():
    with app.app_context():
        try:
            db.create_all()
            # Migrate existing tables — add columns if missing
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                for table, cols in {
                    'user': [('is_banned', 'BOOLEAN DEFAULT FALSE'), ('is_verified', 'BOOLEAN DEFAULT FALSE'), ('warning_count', 'INTEGER DEFAULT 0'), ('suspension_until', 'TIMESTAMP')],
                    'comic': [('nsfw', 'BOOLEAN DEFAULT FALSE')],
                    'chapter': [('is_draft', 'BOOLEAN DEFAULT FALSE')],
                }.items():
                    existing = [c['name'] for c in inspector.get_columns(table)]
                    for col_name, col_type in cols:
                        if col_name not in existing:
                            db.session.execute(db.text(f'ALTER TABLE "{table}" ADD COLUMN {col_name} {col_type}'))
                db.session.commit()
            except Exception as e2:
                print(f"Migration note (non-fatal): {e2}")
            if not User.query.filter_by(is_admin=True).first():
                admin = User(username='admin', email='admin@comic.com', is_admin=True)
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
        except Exception as e:
            print(f"DB init warning (will retry on first request): {e}")

init_db()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
