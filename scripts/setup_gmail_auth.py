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
    print("❌ google-auth-oauthlib nicht installiert!")
    print("Installieren Sie es mit: pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    print("="*60)
    print("Gmail OAuth-Authentifizierung")
    print("="*60)
    print()
    
    # Credentials-Pfad abfragen
    credentials_path = input("Pfad zu gmail_credentials.json: ").strip()
    if not credentials_path:
        credentials_path = "credentials/gmail_credentials.json"
    
    if not os.path.exists(credentials_path):
        print(f"❌ Datei nicht gefunden: {credentials_path}")
        sys.exit(1)
    
    # OAuth-Flow starten
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        print("\n🔐 Browser öffnet sich für Authentifizierung...")
        creds = flow.run_local_server(port=0)
        
        # Token als JSON ausgeben
        token_json = creds.to_json()
        
        print("\n" + "="*60)
        print("✅ Authentifizierung erfolgreich!")
        print("="*60)
        print("\nToken (kopieren und auf Server speichern):")
        print("-"*60)
        print(token_json)
        print("-"*60)
        
        # Optional: Direkt speichern
        save = input("\nToken lokal speichern? (j/n): ").strip().lower()
        if save == 'j':
            token_path = input("Pfad (Enter für credentials/gmail_token.json): ").strip()
            if not token_path:
                token_path = "credentials/gmail_token.json"
            
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as f:
                f.write(token_json)
            print(f"✅ Token gespeichert: {token_path}")
            print("\n📋 Kopieren Sie diese Datei auf den Server:")
            print(f"   scp {token_path} benutzer@server:/opt/erp_tml/credentials/gmail_token.json")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

