import os
import base64
import email
import json
import re
import requests
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
            # Prüfe ob Service initialisiert wurde
            if not self.service:
                print("Warnung: Service wurde nach _authenticate() nicht initialisiert")
                print(f"  _authenticated: {self._authenticated}")
                print(f"  service: {self.service}")
    
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
        
        # Debug: Logge die Pfade (verwende logging statt print für Gunicorn)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG _authenticate: credentials_path={credentials_path}, isabs={os.path.isabs(credentials_path)}")
        logger.info(f"DEBUG _authenticate: token_path={token_path}, isabs={os.path.isabs(token_path)}")
        
        # Pfade absolut machen falls relativ
        if not os.path.isabs(credentials_path):
            # Relativer Pfad - finde Projekt-Root (wo app.py liegt)
            try:
                if hasattr(current_app, 'root_path'):
                    # Flask root_path ist das Verzeichnis wo app.py liegt
                    base_dir = current_app.root_path
                    logger.info(f"DEBUG: Verwende current_app.root_path: {base_dir}")
                else:
                    # Fallback: vom aktuellen Modul aus
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    logger.info(f"DEBUG: Verwende Modul-Pfad: {base_dir}")
                credentials_path = os.path.join(base_dir, credentials_path)
            except Exception as e:
                # Wenn current_app nicht verfügbar, verwende absoluten Pfad
                logger.info(f"DEBUG: Exception bei Pfad-Auflösung: {e}, verwende /opt/erp_tml")
                credentials_path = os.path.join('/opt/erp_tml', credentials_path.lstrip('/'))
        
        if not os.path.isabs(token_path):
            try:
                if hasattr(current_app, 'root_path'):
                    base_dir = current_app.root_path
                else:
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                token_path = os.path.join(base_dir, token_path)
            except Exception as e:
                logger.info(f"DEBUG: Exception bei Token-Pfad-Auflösung: {e}, verwende /opt/erp_tml")
                token_path = os.path.join('/opt/erp_tml', token_path.lstrip('/'))
        
        logger.info(f"DEBUG nach Pfad-Auflösung: credentials_path={credentials_path}, existiert={os.path.exists(credentials_path)}")
        logger.info(f"DEBUG nach Pfad-Auflösung: token_path={token_path}, existiert={os.path.exists(token_path)}")
        
        # Fallback: Wenn Datei nicht existiert, versuche absoluten Pfad
        if not os.path.exists(credentials_path):
            fallback_credentials = '/opt/erp_tml/credentials/gmail_credentials.json'
            if os.path.exists(fallback_credentials):
                credentials_path = fallback_credentials
            else:
                print(f"Warnung: Gmail-Credentials nicht gefunden: {credentials_path}")
                print(f"  Fallback auch nicht gefunden: {fallback_credentials}")
                # Nicht return, sondern später prüfen
        
        if not os.path.exists(token_path):
            fallback_token = '/opt/erp_tml/credentials/gmail_token.json'
            if os.path.exists(fallback_token):
                token_path = fallback_token
        
        # Token laden falls vorhanden
        token_exists = os.path.exists(token_path)
        logger.info(f"Token-Datei existiert: {token_exists}, Pfad: {token_path}")
        
        if token_exists:
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info(f"Token geladen, gültig: {creds.valid if creds else False}, abgelaufen: {creds.expired if creds else False}")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Tokens: {e}")
                print(f"Fehler beim Laden des Tokens: {e}")
                creds = None
        else:
            logger.warning(f"Token-Datei nicht gefunden: {token_path}")
            print(f"Token-Datei nicht gefunden: {token_path}")
            creds = None
        
        # Wenn keine gültigen Credentials vorhanden, OAuth-Flow starten
        if not creds or not creds.valid:
            # Versuche Token zu refreshen falls abgelaufen
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Token abgelaufen, versuche Refresh...")
                    logger.info(f"Refresh-Token vorhanden: {bool(creds.refresh_token)}")
                    creds.refresh(Request())
                    logger.info("Token erfolgreich aktualisiert")
                    # Aktualisiertes Token speichern - WICHTIG: Refresh-Token beibehalten
                    os.makedirs(os.path.dirname(token_path), exist_ok=True)
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Aktualisiertes Token gespeichert")
                except Exception as e:
                    logger.error(f"Fehler beim Token-Refresh: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    print(f"Fehler beim Token-Refresh: {e}")
                    # Prüfe ob Refresh-Token fehlt oder ungültig ist
                    if 'invalid_grant' in str(e).lower():
                        logger.error("Refresh-Token ist ungültig oder abgelaufen. Neuer OAuth-Flow erforderlich.")
                        print("Refresh-Token ist ungültig. Bitte erstellen Sie ein neues Token.")
                    creds = None
            elif creds and creds.expired and not creds.refresh_token:
                logger.warning("Token abgelaufen, aber kein Refresh-Token vorhanden")
                print("Token abgelaufen, aber kein Refresh-Token vorhanden. Neuer OAuth-Flow erforderlich.")
                creds = None
            
            # Wenn immer noch keine gültigen Credentials, neuen OAuth-Flow starten
            if not creds or not creds.valid:
                if not os.path.exists(credentials_path):
                    print(f"Warnung: Gmail-Credentials nicht gefunden: {credentials_path}")
                    # Prüfe nochmal Fallback
                    fallback_creds = '/opt/erp_tml/credentials/gmail_credentials.json'
                    if os.path.exists(fallback_creds):
                        credentials_path = fallback_creds
                    else:
                        print(f"  Fallback auch nicht gefunden: {fallback_creds}")
                        return
                
                # Prüfe ob wir in einer Server/Web-Umgebung sind
                # In Flask-Request-Kontext können wir keinen Browser öffnen
                try:
                    from flask import has_request_context
                    is_server_env = has_request_context() or os.environ.get('SERVER_SOFTWARE') is not None
                except:
                    # Fallback: Prüfe ob DISPLAY gesetzt ist (für Linux)
                    is_server_env = os.environ.get('DISPLAY') is None
                
                if is_server_env:
                    # In Server-Umgebung kann kein Browser geöffnet werden
                    # Token muss bereits vorhanden sein oder manuell erstellt werden
                    if not token_exists:
                        error_msg = (
                            f"Gmail OAuth-Token nicht gefunden.\n"
                            f"Credentials: {credentials_path}\n"
                            f"Token-Pfad: {token_path}\n"
                            f"Bitte führen Sie 'python scripts/setup_gmail_auth.py' lokal aus und kopieren Sie das Token auf den Server."
                        )
                        logger.error(error_msg)
                        raise Exception("Gmail OAuth-Token nicht gefunden. Bitte führen Sie die Authentifizierung lokal durch: 'python scripts/setup_gmail_auth.py' und kopieren Sie das Token auf den Server.")
                    else:
                        # Token existiert, aber ist ungültig und konnte nicht refreshed werden
                        error_msg = (
                            f"Gmail OAuth-Token ist ungültig und konnte nicht aktualisiert werden.\n"
                            f"Token-Pfad: {token_path}\n"
                            f"Bitte erstellen Sie ein neues Token mit 'python scripts/setup_gmail_auth.py' und kopieren Sie es auf den Server."
                        )
                        logger.error(error_msg)
                        raise Exception("Gmail OAuth-Token ist ungültig. Bitte erstellen Sie ein neues Token mit 'python scripts/setup_gmail_auth.py' und kopieren Sie es auf den Server.")
                
                # Lokale Umgebung: Versuche Browser zu öffnen
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                try:
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    error_msg = (
                        f"Fehler beim OAuth-Flow: {e}\n\n"
                        "Bitte führen Sie die Authentifizierung manuell durch:\n"
                        f"python scripts/setup_gmail_auth.py"
                    )
                    logger.error(error_msg)
                    raise Exception("OAuth-Authentifizierung fehlgeschlagen. Bitte führen Sie 'python scripts/setup_gmail_auth.py' aus.")
            
            # Token speichern - WICHTIG: Refresh-Token beibehalten falls vorhanden
            if creds:
                os.makedirs(os.path.dirname(token_path), exist_ok=True)
                # Stelle sicher, dass Refresh-Token erhalten bleibt
                token_data = creds.to_json()
                # Wenn bereits ein Token existiert, prüfe ob Refresh-Token vorhanden ist
                if os.path.exists(token_path):
                    try:
                        with open(token_path, 'r') as f:
                            old_token_data = json.load(f)
                            # Wenn alter Token einen Refresh-Token hat, aber neuer nicht, behalte den alten
                            if 'refresh_token' in old_token_data and old_token_data['refresh_token']:
                                new_token_data = json.loads(token_data)
                                if not new_token_data.get('refresh_token'):
                                    new_token_data['refresh_token'] = old_token_data['refresh_token']
                                    token_data = json.dumps(new_token_data)
                                    logger.info("Refresh-Token aus altem Token übernommen")
                    except Exception as e:
                        logger.warning(f"Konnte alten Token nicht lesen: {e}")
                
                with open(token_path, 'w') as token:
                    token.write(token_data)
                logger.info("Token gespeichert (inkl. Refresh-Token falls vorhanden)")
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
        except Exception as e:
            print(f"Fehler bei Gmail-Authentifizierung: {e}")
            self.service = None
        finally:
            self._authenticated = True
    
    def get_messages_by_label(self, label_name):
        """E-Mails nach Label abrufen"""
        import logging
        logger = logging.getLogger(__name__)
        
        self._ensure_authenticated()
        if not self.service:
            logger.warning("Gmail-Service konnte nicht initialisiert werden")
            print("Warnung: Gmail-Service konnte nicht initialisiert werden")
            return []
        
        try:
            # Label-ID finden
            labels = self.service.users().labels().list(userId='me').execute()
            logger.info(f"get_messages_by_label: Suche nach Label '{label_name}'")
            logger.info(f"get_messages_by_label: Verfügbare Labels: {[l['name'] for l in labels.get('labels', [])]}")
            
            label_id = None
            for label in labels.get('labels', []):
                if label['name'] == label_name:
                    label_id = label['id']
                    logger.info(f"get_messages_by_label: Label '{label_name}' gefunden (ID: {label_id})")
                    break
            
            if not label_id:
                logger.warning(f"get_messages_by_label: Label '{label_name}' NICHT gefunden!")
                logger.warning(f"get_messages_by_label: Verfügbare Labels: {[l['name'] for l in labels.get('labels', [])]}")
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
    
    def extract_links_from_message(self, message):
        """Links aus E-Mail extrahieren (für DTFWorld etc.)"""
        links = []
        import logging
        logger = logging.getLogger(__name__)
        
        if 'payload' not in message:
            logger.warning("extract_links_from_message: Kein payload in message")
            return links
        
        def extract_text_from_part(part):
            """Text aus einem E-Mail-Part extrahieren"""
            text = ""
            if 'body' in part and 'data' in part['body']:
                try:
                    text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                except Exception as e:
                    logger.debug(f"Fehler beim Dekodieren von Part: {e}")
            if 'parts' in part:
                for subpart in part['parts']:
                    text += extract_text_from_part(subpart)
            return text
        
        payload = message['payload']
        email_text = extract_text_from_part(payload)
        
        logger.info(f"extract_links_from_message: E-Mail-Text extrahiert, Länge: {len(email_text)}")
        
        # Suche nach HTTP/HTTPS-Links - erweiterte Pattern
        # Pattern 1: Standard HTTP/HTTPS Links
        url_pattern1 = r'https?://[^\s<>"{}|\\^`\[\]]+'
        # Pattern 2: Links in HTML href
        url_pattern2 = r'href=["\']?(https?://[^"\'\s<>]+)["\']?'
        # Pattern 3: Links mit möglichen Zeilenumbrüchen
        url_pattern3 = r'https?://[^\s<>"{}|\\^`\[\]]+(?:<[^>]+>)?'
        
        found_links = []
        found_links.extend(re.findall(url_pattern1, email_text, re.IGNORECASE))
        found_links.extend(re.findall(url_pattern2, email_text, re.IGNORECASE))
        
        # Entferne Duplikate
        found_links = list(set(found_links))
        
        logger.info(f"extract_links_from_message: {len(found_links)} Links gefunden")
        
        # Alle Links aufnehmen (nicht nur die mit bestimmten Keywords)
        # Priorisiere aber Links mit relevanten Keywords
        prioritized_links = []
        other_links = []
        
        for link in found_links:
            # Entferne mögliche Anführungszeichen oder Klammern am Ende
            link = link.rstrip('.,;:!?)>"\'<>')
            # Entferne HTML-Tags am Ende
            link = re.sub(r'<[^>]+>$', '', link)
            # Entferne mögliche abschließende HTML-Tags
            link = re.sub(r'</a>.*$', '', link, flags=re.IGNORECASE)
            
            if not link.startswith('http'):
                continue
            
            # Für DTFWorld: Prüfe auch auf dtf-world.de Domain
            link_lower = link.lower()
            is_dtfworld = 'dtf-world.de' in link_lower or 'dtfworld' in link_lower
            
            # Priorisiere Links mit relevanten Keywords oder DTFWorld-Domain
            if ('.pdf' in link_lower or 'download' in link_lower or 'invoice' in link_lower or 
                'rechnung' in link_lower or is_dtfworld or 'bill' in link_lower or
                'receipt' in link_lower or 'document' in link_lower or 'herunterladen' in link_lower):
                prioritized_links.append(link)
                logger.info(f"extract_links_from_message: Priorisierter Link gefunden (Länge: {len(link)}): {link[:100]}...")
            else:
                other_links.append(link)
                logger.debug(f"extract_links_from_message: Anderer Link gefunden: {link[:100]}...")
        
        # Zuerst priorisierte Links, dann andere
        links = prioritized_links + other_links
        
        logger.info(f"extract_links_from_message: {len(prioritized_links)} priorisierte, {len(other_links)} andere Links")
        
        return links
    
    def download_pdf_from_url(self, url, filename):
        """PDF von URL herunterladen"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Lade PDF von URL: {url}")
            
            # Headers setzen, um als Browser zu erscheinen
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Request mit Timeout
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Prüfe ob es wirklich ein PDF ist
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and not url.lower().endswith('.pdf'):
                # Prüfe die ersten Bytes (PDF-Magic-Number: %PDF)
                if not response.content[:4] == b'%PDF':
                    logger.warning(f"URL liefert kein PDF: Content-Type={content_type}")
                    # Versuche trotzdem zu speichern, falls es doch ein PDF ist
            
            # Upload-Ordner bestimmen
            if hasattr(current_app, 'config'):
                upload_folder = current_app.config['UPLOAD_FOLDER']
            else:
                upload_folder = os.environ.get('UPLOAD_FOLDER', 'data/rechnungen')
            
            # Datei speichern
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"PDF erfolgreich heruntergeladen: {filepath}")
            return filepath
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Fehler beim Herunterladen von URL {url}: {e}")
            return None
    
    def sync_rechnungen(self):
        """Rechnungen aus Gmail synchronisieren"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("="*60)
        logger.info("Gmail-Synchronisation gestartet")
        logger.info("="*60)
        
        self._ensure_authenticated()
        if not self.service:
            logger.error("Warnung: Gmail-Service konnte nicht initialisiert werden")
            print("Warnung: Gmail-Service konnte nicht initialisiert werden")
            return 0
        
        anzahl = 0
        
        # Alle aktiven Lieferanten mit Gmail-Labels abrufen
        lieferanten = Lieferant.query.filter(
            Lieferant.aktiv == True,
            Lieferant.gmail_label.isnot(None),
            Lieferant.gmail_label != ''
        ).all()
        
        logger.info(f"Sync: Gefundene Lieferanten mit Labels: {len(lieferanten)}")
        if len(lieferanten) == 0:
            logger.warning("Sync: KEINE Lieferanten mit Gmail-Labels gefunden!")
            logger.warning("Sync: Prüfe ob Lieferanten aktiv sind und gmail_label gesetzt ist")
        for lieferant in lieferanten:
            logger.info(f"Sync: Prüfe Lieferant '{lieferant.name}' (ID: {lieferant.id}, Typ: {lieferant.typ}, Aktiv: {lieferant.aktiv}) mit Label '{lieferant.gmail_label}'")
        
        for lieferant in lieferanten:
            # Nachrichten für dieses Label abrufen
            logger.info(f"Sync: Suche E-Mails für Lieferant '{lieferant.name}' mit Label '{lieferant.gmail_label}'...")
            messages = self.get_messages_by_label(lieferant.gmail_label)
            logger.info(f"Sync: Lieferant '{lieferant.name}' - {len(messages)} E-Mails gefunden")
            
            if len(messages) == 0:
                logger.warning(f"Sync: Keine E-Mails gefunden für Lieferant '{lieferant.name}' mit Label '{lieferant.gmail_label}'")
            
            for idx, msg in enumerate(messages):
                message_id = msg['id']
                logger.info(f"Sync: Verarbeite E-Mail {idx+1}/{len(messages)} (ID: {message_id})")
                
                # Prüfen ob bereits importiert
                existing = Buchung.query.filter_by(gmail_message_id=message_id).first()
                if existing:
                    logger.info(f"Sync: E-Mail {message_id} wurde bereits importiert (Buchung ID: {existing.id})")
                    continue
                
                # Nachrichtendetails abrufen
                message_details = self.get_message_details(message_id)
                if not message_details:
                    continue
                
                # PDF-Anhänge finden
                pdf_attachments = self.extract_pdf_attachments(message_details)
                
                pdf_path = None
                filename = None
                
                # Wenn PDF-Anhänge vorhanden, diese verwenden (NICHT auch Links verarbeiten!)
                if pdf_attachments:
                    logger.info(f"Sync: {len(pdf_attachments)} PDF-Anhänge gefunden, verwende diese")
                    pdf_attachment = pdf_attachments[0]
                    filename = pdf_attachment['filename']
                    attachment_id = pdf_attachment['attachment_id']
                    
                    # PDF herunterladen
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_filename = f"{timestamp}_{filename}"
                    pdf_path = self.download_attachment(message_id, attachment_id, safe_filename)
                    if pdf_path:
                        logger.info(f"Sync: PDF-Anhang erfolgreich heruntergeladen: {pdf_path}")
                else:
                    # Keine PDF-Anhänge - prüfe ob Links vorhanden sind (z.B. für DTFWorld)
                    logger.info(f"Sync: Keine PDF-Anhänge gefunden für Nachricht {message_id}, suche nach Links...")
                    links = self.extract_links_from_message(message_details)
                    logger.info(f"Sync: {len(links)} Links gefunden in Nachricht {message_id}")
                    
                    if links:
                        # Versuche PDF von Links herunterzuladen
                        for idx, link in enumerate(links):
                            logger.info(f"Sync: Versuche PDF von Link {idx+1}/{len(links)} herunterzuladen: {link[:100]}...")
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            # Versuche Dateiname aus URL zu extrahieren
                            # Entferne Query-Parameter für Dateiname
                            link_clean = link.split('?')[0]
                            link_filename = link_clean.split('/')[-1]
                            if not link_filename or len(link_filename) < 3 or len(link_filename) > 200:
                                link_filename = f"rechnung_dtfworld_{timestamp}.pdf"
                            elif not link_filename.endswith('.pdf'):
                                link_filename = f"{link_filename}.pdf"
                            safe_filename = f"{timestamp}_{link_filename}"
                            
                            pdf_path = self.download_pdf_from_url(link, safe_filename)
                            if pdf_path:
                                filename = safe_filename
                                logger.info(f"Sync: PDF erfolgreich von Link heruntergeladen: {pdf_path}")
                                break
                            else:
                                logger.warning(f"Sync: Download von Link fehlgeschlagen: {link[:100]}...")
                    else:
                        logger.warning(f"Sync: Keine Links gefunden in Nachricht {message_id}")
                
                if not pdf_path:
                    logger.warning(f"Sync: Keine PDF gefunden für Nachricht {message_id}")
                    continue
                
                # PDF analysieren
                pdf_data = self.pdf_service.extract_invoice_data(pdf_path)
                
                if not pdf_data:
                    logger.warning(f"Sync: PDF-Analyse fehlgeschlagen für {filename}")
                    continue
                
                logger.info(f"Sync: PDF analysiert - Betrag: {pdf_data.get('betrag')}, Datum: {pdf_data.get('datum')}, Rechnungsnummer: {pdf_data.get('rechnungsnummer')}")
                
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
                
                # Prüfe ob DPD-Rechnung (für automatisches Abbuchen)
                von_zielkonto_abgebucht = False
                if lieferant and lieferant.name and 'DPD' in lieferant.name.upper():
                    von_zielkonto_abgebucht = True
                
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
                    gmail_message_id=message_id,
                    von_zielkonto_abgebucht=von_zielkonto_abgebucht
                )
                
                db.session.add(buchung)
                anzahl += 1
                logger.info(f"Sync: Buchung erstellt für Lieferant '{lieferant.name}' - Betrag: {buchung.betrag}, Rechnungsnummer: {rechnungsnummer}")
        
        db.session.commit()
        logger.info("="*60)
        logger.info(f"Gmail-Synchronisation abgeschlossen: {anzahl} neue Rechnungen importiert")
        logger.info("="*60)
        return anzahl

