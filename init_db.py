#!/usr/bin/env python3
"""
Datenbank initialisieren und Standard-Benutzer erstellen
"""

from app import app, init_db
from models import db, User, Auftrag, Todo, Kunde

if __name__ == '__main__':
    with app.app_context():
        # Datenbank erstellen
        db.create_all()
        print("✓ Datenbank erstellt")
        
        # Standard-Admin-Benutzer erstellen (falls nicht vorhanden)
        if User.query.count() == 0:
            admin = User(username='admin')
            admin.set_password('admin')  # Bitte in Produktion ändern!
            db.session.add(admin)
            db.session.commit()
            print("✓ Standard-Admin erstellt:")
            print("  Benutzername: admin")
            print("  Passwort: admin")
            print("  ⚠️  BITTE SOFORT DAS PASSWORT ÄNDERN!")
        else:
            print("✓ Benutzer bereits vorhanden")
        
        print("\nDatenbank-Initialisierung abgeschlossen!")

