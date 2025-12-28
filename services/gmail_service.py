import os
import base64
import email
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import current_app
from models import db, Buchung, Lieferant
from datetime import datetime
from decimal import Decimal
from services.pdf_service import PDFService

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailService:
    """Gmail-Integration für automatische Rechnungserfassung"""
    
    def __init__(self):
        self.service = None
        self.pdf_service = PDFService()
        self._authenticated = False
    
    def _ensure_authenticated(self):
        """Stelle sicher, dass Authentifizierung durchgeführt wurde"""
        if not self._authenticated:
            self._authenticate()
    
    def _authenticate(self):
        """Gmail API authentifizieren"""
        creds = None
        
        if not hasattr(current_app, 'config'):
            # Fallback wenn kein App-Kontext
            credentials_path = os.environ.get('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
            token_path = os.environ.get('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')
        else:
            credentials_path = current_app.config.get('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
            token_path = current_app.config.get('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')
        
        # Pfade absolut machen falls relativ
        if not os.path.isabs(credentials_path):
            # Relativer Pfad - vom Arbeitsverzeichnis oder Projekt-Root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            credentials_path = os.path.join(base_dir, credentials_path)
        if not os.path.isabs(token_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            token_path = os.path.join(base_dir, token_path)
        
        # Token laden falls vorhanden
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        # Wenn keine gültigen Credentials vorhanden, OAuth-Flow starten
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_path):
                    print(f"Warnung: Gmail-Credentials nicht gefunden: {credentials_path}")
                    return
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                
                # Für Server-Umgebungen: Manueller OAuth-Flow
                try:
                    # Versuche Browser zu öffnen (funktioniert nur lokal)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    # Fallback: Manueller Flow für Server
                    print("\n" + "="*60)
                    print("Gmail OAuth-Authentifizierung erforderlich")
                    print("="*60)
                    print("\nBitte führen Sie die Authentifizierung lokal durch:")
                    print("1. Kopieren Sie diese Datei auf Ihren lokalen Rechner:")
                    print(f"   {credentials_path}")
                    print("\n2. Führen Sie lokal aus:")
                    print("   python3 -c \"")
                    print("   from google_auth_oauthlib.flow import InstalledAppFlow;")
                    print("   flow = InstalledAppFlow.from_client_secrets_file(")
                    print(f"       '{credentials_path}',")
                    print("       ['https://www.googleapis.com/auth/gmail.readonly']);")
                    print("   creds = flow.run_local_server(port=0);")
                    print("   import json;")
                    print("   print(json.dumps(creds.to_json()))")
                    print("   \"")
                    print("\n3. Kopieren Sie den ausgegebenen JSON-String")
                    print("4. Speichern Sie ihn in:")
                    print(f"   {token_path}")
                    print("\nODER verwenden Sie das Script: scripts/setup_gmail_auth.py")
                    print("="*60)
                    raise Exception("OAuth-Authentifizierung muss lokal durchgeführt werden. Siehe Anweisungen oben.")
            
            # Token speichern
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"Fehler bei Gmail-Authentifizierung: {e}")
            self.service = None
        finally:
            self._authenticated = True
    
    def get_messages_by_label(self, label_name):
        """E-Mails nach Label abrufen"""
        self._ensure_authenticated()
        if not self.service:
            print("Warnung: Gmail-Service konnte nicht initialisiert werden")
            return []
        
        try:
            # Label-ID finden
            labels = self.service.users().labels().list(userId='me').execute()
            label_id = None
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    label_id = label['id']
                    break
            
            if not label_id:
                return []
            
            # Nachrichten abrufen
            results = self.service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=50
            ).execute()
            
            messages = results.get('messages', [])
            return messages
            
        except HttpError as error:
            print(f'Fehler beim Abrufen der E-Mails: {error}')
            return []
    
    def get_message_details(self, message_id):
        """Details einer E-Mail abrufen"""
        self._ensure_authenticated()
        if not self.service:
            return None
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return message
        except HttpError as error:
            print(f'Fehler beim Abrufen der E-Mail-Details: {error}')
            return None
    
    def download_attachment(self, message_id, attachment_id, filename):
        """PDF-Anhang herunterladen"""
        self._ensure_authenticated()
        if not self.service:
            return None
        
        if hasattr(current_app, 'config'):
            upload_folder = current_app.config['UPLOAD_FOLDER']
        else:
            upload_folder = os.environ.get('UPLOAD_FOLDER', 'data/rechnungen')
        
        try:
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            # Datei speichern
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(file_data)
            
            return filepath
        except HttpError as error:
            print(f'Fehler beim Herunterladen des Anhangs: {error}')
            return None
    
    def extract_pdf_attachments(self, message):
        """PDF-Anhänge aus E-Mail extrahieren"""
        attachments = []
        
        if 'payload' not in message:
            return attachments
        
        payload = message['payload']
        
        # Prüfen ob Anhänge vorhanden
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename', '').lower().endswith('.pdf'):
                    attachments.append({
                        'filename': part['filename'],
                        'attachment_id': part['body']['attachmentId']
                    })
                # Rekursive Suche in verschachtelten Parts
                if 'parts' in part:
                    for subpart in part['parts']:
                        if subpart.get('filename', '').lower().endswith('.pdf'):
                            attachments.append({
                                'filename': subpart['filename'],
                                'attachment_id': subpart['body']['attachmentId']
                            })
        elif payload.get('filename', '').lower().endswith('.pdf'):
            attachments.append({
                'filename': payload['filename'],
                'attachment_id': payload['body']['attachmentId']
            })
        
        return attachments
    
    def sync_rechnungen(self):
        """Rechnungen aus Gmail synchronisieren"""
        self._ensure_authenticated()
        if not self.service:
            print("Warnung: Gmail-Service konnte nicht initialisiert werden")
            return 0
        
        anzahl = 0
        
        # Alle aktiven Lieferanten mit Gmail-Labels abrufen
        lieferanten = Lieferant.query.filter(
            Lieferant.aktiv == True,
            Lieferant.gmail_label.isnot(None),
            Lieferant.gmail_label != ''
        ).all()
        
        for lieferant in lieferanten:
            # Nachrichten für dieses Label abrufen
            messages = self.get_messages_by_label(lieferant.gmail_label)
            
            for msg in messages:
                message_id = msg['id']
                
                # Prüfen ob bereits importiert
                if Buchung.query.filter_by(gmail_message_id=message_id).first():
                    continue
                
                # Nachrichtendetails abrufen
                message_details = self.get_message_details(message_id)
                if not message_details:
                    continue
                
                # PDF-Anhänge finden
                pdf_attachments = self.extract_pdf_attachments(message_details)
                
                if not pdf_attachments:
                    continue
                
                # Ersten PDF-Anhang verarbeiten
                pdf_attachment = pdf_attachments[0]
                filename = pdf_attachment['filename']
                attachment_id = pdf_attachment['attachment_id']
                
                # PDF herunterladen
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = f"{timestamp}_{filename}"
                pdf_path = self.download_attachment(message_id, attachment_id, safe_filename)
                
                if not pdf_path:
                    continue
                
                # PDF analysieren
                pdf_data = self.pdf_service.extract_invoice_data(pdf_path)
                
                if not pdf_data:
                    continue
                
                # Rechnungsnummer aus Dateiname extrahieren falls nicht im PDF gefunden
                rechnungsnummer = pdf_data.get('rechnungsnummer', '')
                
                # Prüfe ob Rechnungsnummer ungültig ist
                def is_valid_date(date_str):
                    """Prüft ob eine 8-stellige Zahl ein gültiges Datum ist"""
                    if len(date_str) != 8 or not date_str.isdigit():
                        return False
                    try:
                        year = int(date_str[:4])
                        month = int(date_str[4:6])
                        day = int(date_str[6:8])
                        from datetime import datetime as dt
                        dt(year, month, day)
                        return 2000 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31
                    except:
                        return False
                
                if not rechnungsnummer or rechnungsnummer.lower() in ['template', 'belegnummer', 'rechnungsnummer', 'nummer'] or is_valid_date(rechnungsnummer):
                    # Versuche aus Dateiname zu extrahieren
                    import re as re_module
                    name_without_ext = filename.replace('.pdf', '').replace('.PDF', '')
                    parts = name_without_ext.split('_')
                    
                    # Verschiedene Formate im Dateinamen suchen
                    invoice_match = re_module.search(r'INVOICE[-/]?(\d+)', filename, re_module.IGNORECASE)
                    if invoice_match:
                        rechnungsnummer = invoice_match.group(1)
                    elif len(parts) >= 3:
                        # Format: 20251228_174528_45184639 - nimm letzten Teil
                        neue_nr = parts[-1]
                        if not is_valid_date(neue_nr):
                            rechnungsnummer = neue_nr
                    elif len(parts) == 2:
                        # Format: 20251228_45184639
                        neue_nr = parts[-1]
                        if not is_valid_date(neue_nr):
                            rechnungsnummer = neue_nr
                    else:
                        # Suche nach Zahlen im Dateinamen
                        number_match = re_module.search(r'(\d{6,})', filename)
                        if number_match:
                            neue_nr = number_match.group(1)
                            if not is_valid_date(neue_nr):
                                rechnungsnummer = neue_nr
                
                # Buchung erstellen
                buchung = Buchung(
                    typ=lieferant.typ,
                    lieferant_id=lieferant.id if lieferant.typ == 'Ausgabe' else None,
                    betrag=Decimal(str(pdf_data.get('betrag', 0))),
                    datum=pdf_data.get('datum') or datetime.now().date(),
                    rechnungsnummer=rechnungsnummer,
                    titel=pdf_data.get('titel', filename),
                    pdf_pfad=pdf_path,
                    jahr=(pdf_data.get('datum') or datetime.now().date()).year,
                    quelle='Gmail',
                    gmail_message_id=message_id
                )
                
                db.session.add(buchung)
                anzahl += 1
        
        db.session.commit()
        return anzahl

