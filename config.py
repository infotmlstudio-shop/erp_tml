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
    # Verwende absolute Pfade für bessere Kompatibilität
    # Prüfe zuerst Umgebungsvariable, dann Standard-Pfad
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _default_creds = os.path.join(_base_dir, 'credentials', 'gmail_credentials.json')
    _default_token = os.path.join(_base_dir, 'credentials', 'gmail_token.json')
    
    # Verwende Umgebungsvariable oder absoluten Pfad
    if os.environ.get('GMAIL_CREDENTIALS_PATH'):
        GMAIL_CREDENTIALS_PATH = os.environ.get('GMAIL_CREDENTIALS_PATH')
    elif os.path.exists(_default_creds):
        GMAIL_CREDENTIALS_PATH = _default_creds
    else:
        # Fallback auf absoluten Pfad
        GMAIL_CREDENTIALS_PATH = '/opt/erp_tml/credentials/gmail_credentials.json'
    
    if os.environ.get('GMAIL_TOKEN_PATH'):
        GMAIL_TOKEN_PATH = os.environ.get('GMAIL_TOKEN_PATH')
    elif os.path.exists(_default_token):
        GMAIL_TOKEN_PATH = _default_token
    else:
        # Fallback auf absoluten Pfad
        GMAIL_TOKEN_PATH = '/opt/erp_tml/credentials/gmail_token.json'
    
    # File uploads
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'rechnungen')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE', 10485760))  # 10MB
    
    # Server
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    
    # Ensure upload folder exists
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

