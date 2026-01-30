#!/usr/bin/env python3
"""Lösche DTFWorld-Buchungen mit falschen PDFs (AGB, Widerrufsrecht), damit die Rechnung erneut verarbeitet wird"""
import os
import sys

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Buchung, Lieferant, db

with app.app_context():
    # Finde DTFWorld Lieferant
    dtfworld = Lieferant.query.filter_by(name='DTFWorld').first()
    if not dtfworld:
        print("DTFWorld Lieferant nicht gefunden!")
        sys.exit(1)
    
    # Finde alle DTFWorld-Buchungen mit Gmail Message ID 19b9a51e6f551393
    buchungen = Buchung.query.filter_by(
        lieferant_id=dtfworld.id,
        gmail_message_id='19b9a51e6f551393'
    ).all()
    
    if not buchungen:
        print("Keine DTFWorld-Buchungen mit dieser Gmail Message ID gefunden!")
        sys.exit(1)
    
    print(f"Gefundene Buchungen: {len(buchungen)}")
    
    for buchung in buchungen:
        print(f"\nLösche Buchung ID: {buchung.id}")
        print(f"PDF-Pfad: {buchung.pdf_pfad}")
        print(f"Titel: {buchung.titel}")
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
    print(f"\n{len(buchungen)} Buchung(en) erfolgreich gelöscht!")
    print("Beim nächsten Gmail-Sync wird die E-Mail erneut verarbeitet und die Rechnung vom Link heruntergeladen.")

