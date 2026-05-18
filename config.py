import os
import logging
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

def _require(var):
    val = os.getenv(var, '').strip()
    if not val:
        raise RuntimeError(f"Missing required environment variable: '{var}'. Please set it in your .env file.")
    return val

def get_db_url():
    db_url = _require('DATABASE_URL').strip()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url

class Config:
    SECRET_KEY = _require('SECRET_KEY')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    SQLALCHEMY_DATABASE_URI = get_db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(_require('DB_POOL_SIZE')),
        'max_overflow': int(_require('DB_MAX_OVERFLOW')),
        'pool_timeout': int(_require('DB_POOL_TIMEOUT')),
        'pool_recycle': int(_require('DB_POOL_RECYCLE')),
        'pool_pre_ping': True,
    }

    GEMINI_API_KEY = _require('GEMINI_API_KEY')
    GEMINI_MODEL = _require('GEMINI_MODEL')
    GEMINI_MAX_TOKENS = int(_require('GEMINI_MAX_TOKENS'))

    BREVO_API_KEY = _require('BREVO_API_KEY')
    BREVO_SENDER_EMAIL = _require('BREVO_SENDER_EMAIL')
    BREVO_SENDER_NAME = os.getenv('BREVO_SENDER_NAME', 'EduVerse AI Chatbot')

    SESSION_TYPE = _require('SESSION_TYPE')
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(_require('SESSION_LIFETIME_DAYS')))
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = _require('SESSION_COOKIE_SAMESITE')
    SESSION_REFRESH_EACH_REQUEST = True

    RATELIMIT_DEFAULT = _require('RATELIMIT_DEFAULT')
    RATELIMIT_STORAGE_URL = _require('RATELIMIT_STORAGE_URL')

    LOG_LEVEL = _require('LOG_LEVEL')

    @classmethod
    def configure_logging(cls):
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL, logging.INFO),
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

def get_config():
    return Config