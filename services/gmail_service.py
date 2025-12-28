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
        if not hasattr(current_app, 'config'):
            # Fallback wenn kein App-Kontext
            import os
            credentials_path = os.environ.get('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
            token_path = os.environ.get('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')
        else:
            credentials_path = current_app.config.get('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
            token_path = current_app.config.get('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')
        
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
                creds = flow.run_local_server(port=0)
            
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
            import os
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
                
                # Buchung erstellen
                buchung = Buchung(
                    typ=lieferant.typ,
                    lieferant_id=lieferant.id if lieferant.typ == 'Ausgabe' else None,
                    betrag=Decimal(str(pdf_data.get('betrag', 0))),
                    datum=pdf_data.get('datum') or datetime.now().date(),
                    rechnungsnummer=pdf_data.get('rechnungsnummer', ''),
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

