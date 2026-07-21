import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://...')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
    R2_ACCESS_KEY = os.environ.get('R2_ACCESS_KEY')
    R2_SECRET_KEY = os.environ.get('R2_SECRET_KEY')
    R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'comic-site')
    R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', 'https://pub-xxxxx.r2.dev')

    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_SUPPORTED_LOCALES = ['en', 'id']
    LANGUAGES = {
        'en': 'English',
        'id': 'Bahasa Indonesia'
    }
