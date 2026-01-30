#!/usr/bin/env python3
"""Prüfe DTFWorld-Buchungen und deren PDF-Status"""
import os
import sys

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import Buchung, Lieferant, db

with app.app_context():
    # Finde DTFWorld Lieferant
    dtfworld = Lieferant.query.filter_by(name='DTFWorld').first()
    if dtfworld:
        print(f"DTFWorld Lieferant ID: {dtfworld.id}")
        print(f"Label: {dtfworld.gmail_label}")
        print()
        
        # Finde alle Buchungen für DTFWorld
        buchungen = Buchung.query.filter_by(lieferant_id=dtfworld.id).order_by(Buchung.created_at.desc()).all()
        print(f"Anzahl DTFWorld-Buchungen: {len(buchungen)}")
        print()
        
        for buchung in buchungen:
            print(f"Buchung ID: {buchung.id}")
            print(f"Typ: {buchung.typ}")
            print(f"Betrag: {buchung.betrag}")
            print(f"Datum: {buchung.datum}")
            print(f"Rechnungsnummer: {buchung.rechnungsnummer}")
            print(f"Titel: {buchung.titel}")
            print(f"PDF-Pfad: {buchung.pdf_pfad}")
            print(f"Gmail Message ID: {buchung.gmail_message_id}")
            print(f"Quelle: {buchung.quelle}")
            print(f"Erstellt am: {buchung.created_at}")
            
            if buchung.pdf_pfad:
                if os.path.exists(buchung.pdf_pfad):
                    size = os.path.getsize(buchung.pdf_pfad)
                    print(f"PDF existiert: Ja ({size} Bytes)")
                else:
                    print(f"PDF existiert: NEIN!")
            else:
                print("PDF-Pfad: KEINER")
            print("-" * 60)
    else:
        print("DTFWorld Lieferant nicht gefunden!")

