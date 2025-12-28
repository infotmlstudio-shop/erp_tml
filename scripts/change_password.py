#!/usr/bin/env python3
"""
Passwort für einen Benutzer ändern
"""

import sys
import os
import getpass

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, User

def change_password():
    """Passwort ändern"""
    with app.app_context():
        username = input("Benutzername: ").strip()
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"❌ Benutzer '{username}' nicht gefunden!")
            return 1
        
        print(f"Passwort für Benutzer '{username}' ändern:")
        new_password = getpass.getpass("Neues Passwort: ")
        confirm_password = getpass.getpass("Passwort bestätigen: ")
        
        if new_password != confirm_password:
            print("❌ Passwörter stimmen nicht überein!")
            return 1
        
        if len(new_password) < 6:
            print("❌ Passwort muss mindestens 6 Zeichen lang sein!")
            return 1
        
        user.set_password(new_password)
        db.session.commit()
        
        print(f"✅ Passwort für '{username}' erfolgreich geändert!")
        return 0

if __name__ == '__main__':
    sys.exit(change_password())

