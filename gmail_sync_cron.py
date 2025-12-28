#!/usr/bin/env python3
"""
Cron-Job für automatische Gmail-Synchronisation
Dieses Script sollte regelmäßig (z.B. stündlich) ausgeführt werden.
"""

import sys
import os

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from services.gmail_service import GmailService
from models import db

def sync_gmail():
    """Gmail synchronisieren"""
    with app.app_context():
        try:
            # Prüfen ob Gmail-Credentials vorhanden
            credentials_path = app.config.get('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
            if not os.path.exists(credentials_path):
                print(f"Gmail-Credentials nicht gefunden: {credentials_path}")
                return 0  # Nicht als Fehler behandeln
            
            gmail_service = GmailService()
            anzahl = gmail_service.sync_rechnungen()
            print(f"Gmail-Synchronisation erfolgreich: {anzahl} neue Rechnungen importiert.")
            return 0
        except Exception as e:
            print(f"Fehler bei Gmail-Synchronisation: {e}", file=sys.stderr)
            return 1

if __name__ == '__main__':
    sys.exit(sync_gmail())

