import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Use PostgreSQL on Render, SQLite locally
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        # Fix for Render's postgres:// URL (SQLAlchemy needs postgresql://)
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///prospector.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Production settings for Render
    if os.environ.get('FLASK_ENV') == 'production':
        DEBUG = False
        TESTING = False
    else:
        DEBUG = True
        TESTING = False
