#!/usr/bin/env python3
"""
Gmail OAuth-Authentifizierung lokal durchführen
Dieses Script sollte auf Ihrem lokalen Rechner ausgeführt werden.
"""

import sys
import os
import json

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("[FEHLER] google-auth-oauthlib nicht installiert!")
    print("Installieren Sie es mit: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    print("="*60)
    print("Gmail OAuth-Authentifizierung")
    print("="*60)
    print()
    
    # Projekt-Root finden (wo app.py liegt)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Standard-Pfade
    default_credentials = os.path.join(project_root, "credentials", "gmail_credentials.json")
    default_token = os.path.join(project_root, "credentials", "gmail_token.json")
    
    # Credentials-Pfad abfragen oder Standard verwenden
    print(f"Standard-Pfad: {default_credentials}")
    credentials_path = input("Pfad zu gmail_credentials.json (Enter für Standard): ").strip()
    if not credentials_path:
        credentials_path = default_credentials
    
    if not os.path.exists(credentials_path):
        print(f"[FEHLER] Datei nicht gefunden: {credentials_path}")
        sys.exit(1)
    
    # Token-Pfad bestimmen
    token_path = default_token
    print(f"\nToken wird gespeichert in: {token_path}")
    
    # OAuth-Flow starten
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        print("\n[INFO] Browser oeffnet sich fuer Authentifizierung...")
        print("Bitte folgen Sie den Anweisungen im Browser.")
        creds = flow.run_local_server(port=0)
        
        # Token speichern
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        
        print("\n" + "="*60)
        print("[ERFOLG] Authentifizierung erfolgreich!")
        print("="*60)
        print(f"\n[OK] Token gespeichert: {token_path}")
        print("\nSie koennen jetzt die Gmail-Synchronisation verwenden.")
        
        return 0
        
    except Exception as e:
        print(f"\n[FEHLER] Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

