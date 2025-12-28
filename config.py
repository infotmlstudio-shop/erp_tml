import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///buchhaltung.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Gmail API
    GMAIL_CREDENTIALS_PATH = os.environ.get('GMAIL_CREDENTIALS_PATH') or 'credentials/gmail_credentials.json'
    GMAIL_TOKEN_PATH = os.environ.get('GMAIL_TOKEN_PATH') or 'credentials/gmail_token.json'
    
    # File uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'rechnungen')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE', 10485760))  # 10MB
    
    # Server
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    
    # Ensure upload folder exists
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

