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
        
        # Migration für bestehende Datenbanken
        try:
            from sqlalchemy import text
            # Prüfe ob kunde_id Spalte fehlt
            result = db.session.execute(text("PRAGMA table_info(auftrag)"))
            columns = [row[1] for row in result]
            
            if 'kunde_id' not in columns:
                print("Führe Migration aus: Füge kunde_id Spalte hinzu...")
                db.session.execute(text("ALTER TABLE auftrag ADD COLUMN kunde_id INTEGER"))
                db.session.commit()
                print("✓ Migration: kunde_id Spalte hinzugefügt")
        except Exception as e:
            print(f"⚠️  Migration-Warnung: {e}")
            # Ignoriere Fehler, falls Tabelle noch nicht existiert
        
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

