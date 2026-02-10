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
    
    # Versuche interaktive Eingabe, falls nicht möglich verwende Standard
    try:
        credentials_path = input("Pfad zu gmail_credentials.json (Enter für Standard): ").strip()
        if not credentials_path:
            credentials_path = default_credentials
    except (EOFError, KeyboardInterrupt):
        # Nicht-interaktiver Modus: Verwende Standard-Pfad
        print("\n[INFO] Nicht-interaktiver Modus: Verwende Standard-Pfad")
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
        
        # WICHTIG: access_type='offline' und prompt='consent' sind notwendig,
        # um einen Refresh-Token zu erhalten!
        # InstalledAppFlow verwendet standardmäßig 'offline', aber wir müssen sicherstellen,
        # dass der Consent-Screen angezeigt wird
        print("\n[INFO] Browser oeffnet sich fuer Authentifizierung...")
        print("Bitte folgen Sie den Anweisungen im Browser.")
        print("\n[WICHTIG] Stellen Sie sicher, dass Sie 'Zugriff gewähren' klicken!")
        print("          Nur so wird ein Refresh-Token erstellt, der für automatische Erneuerung benötigt wird.")
        print("\n[INFO] Falls Sie bereits autorisiert haben, wird möglicherweise kein neuer")
        print("       Refresh-Token erstellt. In diesem Fall:")
        print("       1. Gehen Sie zu: https://myaccount.google.com/permissions")
        print("       2. Entfernen Sie die Berechtigung für diese App")
        print("       3. Führen Sie dieses Script erneut aus")
        
        # OAuth-Flow durchführen
        # run_local_server() verwendet standardmäßig access_type='offline' für Desktop-Apps
        creds = flow.run_local_server(
            port=0,
            authorization_prompt_message='Bitte öffnen Sie diese URL in Ihrem Browser: {url}',
            success_message='Authentifizierung erfolgreich! Sie können dieses Fenster schließen.',
            open_browser=True
        )
        
        # Prüfe ob Refresh-Token vorhanden ist
        token_data = json.loads(creds.to_json())
        if not token_data.get('refresh_token'):
            print("\n" + "="*60)
            print("[WARNUNG] Kein Refresh-Token erhalten!")
            print("="*60)
            print("\nMögliche Ursachen:")
            print("1. Sie haben bereits einmal autorisiert - Google gibt dann keinen neuen Refresh-Token")
            print("2. Die OAuth-App ist nicht als 'Desktop-App' konfiguriert")
            print("\nLösung:")
            print("1. Gehen Sie zu: https://myaccount.google.com/permissions")
            print("2. Entfernen Sie die Berechtigung für 'TMLSTUDIO Buchhaltung'")
            print("3. Führen Sie dieses Script erneut aus")
            print("\nODER:")
            print("1. In Google Cloud Console: OAuth-Zustimmungsbildschirm → Testbenutzer hinzufügen")
            print("2. Script erneut ausführen")
            print("\n" + "="*60)
            return 1
        
        # Token speichern
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
        
        print("\n" + "="*60)
        print("[ERFOLG] Authentifizierung erfolgreich!")
        print("="*60)
        print(f"\n[OK] Token gespeichert: {token_path}")
        print(f"[OK] Refresh-Token vorhanden: Ja")
        print(f"[OK] Token-Ablaufzeit: {token_data.get('expiry', 'Unbekannt')}")
        print("\nSie koennen jetzt die Gmail-Synchronisation verwenden.")
        print("\n[INFO] Kopieren Sie die Token-Datei auf den Server:")
        print(f"       scp {token_path} root@server-ip:/opt/erp_tml/credentials/gmail_token.json")
        
        return 0
        
    except Exception as e:
        print(f"\n[FEHLER] Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

