#!/usr/bin/env python3
"""
Neuen Benutzer erstellen
"""

import sys
import os
import getpass

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, User

def create_user():
    """Neuen Benutzer erstellen"""
    with app.app_context():
        username = input("Benutzername: ").strip()
        
        if not username:
            print("❌ Benutzername darf nicht leer sein!")
            return 1
        
        # Prüfen ob Benutzer bereits existiert
        if User.query.filter_by(username=username).first():
            print(f"❌ Benutzer '{username}' existiert bereits!")
            return 1
        
        password = getpass.getpass("Passwort: ")
        confirm_password = getpass.getpass("Passwort bestätigen: ")
        
        if password != confirm_password:
            print("❌ Passwörter stimmen nicht überein!")
            return 1
        
        if len(password) < 6:
            print("❌ Passwort muss mindestens 6 Zeichen lang sein!")
            return 1
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ Benutzer '{username}' erfolgreich erstellt!")
        return 0

if __name__ == '__main__':
    sys.exit(create_user())

