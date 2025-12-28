#!/usr/bin/env python3
"""
Datenbank-Backup erstellen
"""

import sys
import os
import shutil
from datetime import datetime

# Pfad zum Projekt hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def backup_database():
    """Datenbank-Backup erstellen"""
    with app.app_context():
        db_path = 'buchhaltung.db'
        
        if not os.path.exists(db_path):
            print(f"❌ Datenbank '{db_path}' nicht gefunden!")
            return 1
        
        # Backup-Verzeichnis erstellen
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup-Dateiname mit Timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'buchhaltung_backup_{timestamp}.db')
        
        # Backup erstellen
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup erstellt: {backup_path}")
            
            # Alte Backups löschen (älter als 30 Tage)
            import time
            current_time = time.time()
            for file in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, file)
                if os.path.isfile(file_path) and file.startswith('buchhaltung_backup_'):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 30 * 24 * 60 * 60:  # 30 Tage
                        os.remove(file_path)
                        print(f"🗑️  Altes Backup gelöscht: {file}")
            
            return 0
        except Exception as e:
            print(f"❌ Fehler beim Backup: {e}")
            return 1

if __name__ == '__main__':
    sys.exit(backup_database())

