#!/usr/bin/env python3
"""
Migration: Fügt kunde_id Spalte zur auftrag-Tabelle hinzu
"""

from app import app, db
from sqlalchemy import text

def migrate():
    """Migration ausführen"""
    with app.app_context():
        try:
            # Prüfe ob Spalte bereits existiert
            result = db.session.execute(text("PRAGMA table_info(auftrag)"))
            columns = [row[1] for row in result]
            
            if 'kunde_id' not in columns:
                print("Füge kunde_id Spalte hinzu...")
                db.session.execute(text("ALTER TABLE auftrag ADD COLUMN kunde_id INTEGER"))
                db.session.commit()
                print("✓ kunde_id Spalte hinzugefügt")
            else:
                print("✓ kunde_id Spalte existiert bereits")
            
            # Prüfe ob auftrag_artikel Tabelle existiert
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='auftrag_artikel'"))
            if not result.fetchone():
                print("Erstelle auftrag_artikel Tabelle...")
                db.session.execute(text("""
                    CREATE TABLE auftrag_artikel (
                        auftrag_id INTEGER NOT NULL,
                        artikel_id INTEGER NOT NULL,
                        menge INTEGER NOT NULL DEFAULT 1,
                        created_at DATETIME,
                        PRIMARY KEY (auftrag_id, artikel_id),
                        FOREIGN KEY(auftrag_id) REFERENCES auftrag (id),
                        FOREIGN KEY(artikel_id) REFERENCES artikel (id)
                    )
                """))
                db.session.commit()
                print("✓ auftrag_artikel Tabelle erstellt")
            else:
                print("✓ auftrag_artikel Tabelle existiert bereits")
            
            # Prüfe ob kunde Tabelle existiert
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='kunde'"))
            if not result.fetchone():
                print("Erstelle kunde Tabelle...")
                db.session.execute(text("""
                    CREATE TABLE kunde (
                        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(200) NOT NULL,
                        firma VARCHAR(200),
                        email VARCHAR(200),
                        telefon VARCHAR(50),
                        adresse TEXT,
                        aktiv BOOLEAN NOT NULL DEFAULT 1,
                        created_at DATETIME,
                        updated_at DATETIME
                    )
                """))
                db.session.commit()
                print("✓ kunde Tabelle erstellt")
            else:
                print("✓ kunde Tabelle existiert bereits")
            
            print("\n✓ Migration erfolgreich abgeschlossen!")
            return 0
            
        except Exception as e:
            print(f"❌ Fehler bei Migration: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return 1

if __name__ == '__main__':
    import sys
    sys.exit(migrate())

