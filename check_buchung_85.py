#!/usr/bin/env python3
"""Prüfe Buchung 85 und deren PDF-Status"""
import os
import sys

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Buchung, db

with app.app_context():
    buchung = Buchung.query.get(85)
    if buchung:
        print(f"Buchung ID: {buchung.id}")
        print(f"Typ: {buchung.typ}")
        print(f"Betrag: {buchung.betrag}")
        print(f"Datum: {buchung.datum}")
        print(f"Rechnungsnummer: {buchung.rechnungsnummer}")
        print(f"Titel: {buchung.titel}")
        print(f"PDF-Pfad: {buchung.pdf_pfad}")
        print(f"Gmail Message ID: {buchung.gmail_message_id}")
        print(f"Quelle: {buchung.quelle}")
        
        if buchung.pdf_pfad:
            if os.path.isabs(buchung.pdf_pfad):
                exists = os.path.exists(buchung.pdf_pfad)
                print(f"PDF existiert (absolut): {exists}")
                if exists:
                    size = os.path.getsize(buchung.pdf_pfad)
                    print(f"PDF-Größe: {size} Bytes")
            else:
                upload_folder = app.config.get('UPLOAD_FOLDER', 'data/rechnungen')
                relative_path = os.path.join(upload_folder, buchung.pdf_pfad)
                exists = os.path.exists(relative_path)
                print(f"PDF existiert (relativ): {exists}")
                if exists:
                    size = os.path.getsize(relative_path)
                    print(f"PDF-Größe: {size} Bytes")
        else:
            print("KEIN PDF-PFAD GESPEICHERT!")
    else:
        print("Buchung 85 nicht gefunden!")

