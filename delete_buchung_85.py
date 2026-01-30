#!/usr/bin/env python3
"""Lösche Buchung 85, damit die DTFWorld-Rechnung erneut verarbeitet wird"""
import os
import sys

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Buchung, db

with app.app_context():
    buchung = Buchung.query.get(85)
    if buchung:
        print(f"Lösche Buchung ID: {buchung.id}")
        print(f"PDF-Pfad: {buchung.pdf_pfad}")
        print(f"Gmail Message ID: {buchung.gmail_message_id}")
        
        # Lösche auch das PDF, falls vorhanden
        if buchung.pdf_pfad and os.path.exists(buchung.pdf_pfad):
            try:
                os.remove(buchung.pdf_pfad)
                print(f"PDF-Datei gelöscht: {buchung.pdf_pfad}")
            except Exception as e:
                print(f"Fehler beim Löschen der PDF-Datei: {e}")
        
        # Lösche die Buchung
        db.session.delete(buchung)
        db.session.commit()
        print("Buchung erfolgreich gelöscht!")
        print("Beim nächsten Gmail-Sync wird die E-Mail erneut verarbeitet und die Rechnung vom Link heruntergeladen.")
    else:
        print("Buchung 85 nicht gefunden!")

