# 📋 Detaillierte Installationsanleitung - Ubuntu 24.04 Server

Diese Anleitung führt Sie Schritt für Schritt durch die Installation und Einrichtung der TMLSTUDIO Buchhaltungsverwaltung auf einem Ubuntu 24.04 Server.

## ⚡ Schnellübersicht

**Geschätzter Zeitaufwand:** 30-45 Minuten

**Hauptschritte:**
1. ✅ System aktualisieren und Abhängigkeiten installieren
2. ✅ Projekt-Verzeichnis erstellen und Dateien übertragen
3. ✅ Python Virtual Environment einrichten
4. ✅ Konfiguration anpassen (`.env`-Datei)
5. ✅ Datenbank initialisieren
6. ✅ Gmail API einrichten (Google Cloud Console)
7. ✅ Gunicorn Service konfigurieren
8. ✅ Nginx als Reverse Proxy einrichten
9. ✅ SSL-Zertifikat installieren (optional)
10. ✅ Cron-Job für automatische Synchronisation

**Nach der Installation:**
- Web-Interface: `https://deine-domain.de` (oder `http://server-ip`)
- Standard-Login: `admin` / `admin` ⚠️ **SOFORT ÄNDERN!**

---

## 📌 Voraussetzungen

- Ubuntu 24.04 Server (mit SSH-Zugang)
- Root- oder sudo-Berechtigung
- Domain oder IP-Adresse für den Server
- Gmail-Account: `info.tmlstudio@gmail.com`

---

## 🔧 Schritt 1: System aktualisieren

```bash
# Als root oder mit sudo
sudo apt update
sudo apt upgrade -y
```

---

## 🐍 Schritt 2: Python und System-Abhängigkeiten installieren

```bash
# Python 3 und pip installieren
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Weitere benötigte Pakete
sudo apt install -y nginx gunicorn sqlite3

# Optional: Für PDF-OCR (falls gescannte PDFs verarbeitet werden sollen)
sudo apt install -y tesseract-ocr tesseract-ocr-deu
```

**Überprüfung:**
```bash
python3 --version  # Sollte Python 3.12 oder höher zeigen
pip3 --version
```

---

## 📁 Schritt 3: Projekt-Verzeichnis erstellen

```bash
# Projekt-Verzeichnis anlegen
sudo mkdir -p /opt/erp_tml
sudo chown $USER:$USER /opt/erp_tml
cd /opt/erp_tml
```

**Alle Projektdateien hierher kopieren:**
- Entweder per `scp` von Ihrem lokalen Rechner:
  ```bash
  # Vom lokalen Rechner aus:
  scp -r * benutzer@server-ip:/opt/erp_tml/
  ```
- Oder per Git (falls Repository vorhanden)
- Oder manuell per FTP/SFTP

---

## 🎯 Schritt 4: Python Virtual Environment erstellen

```bash
cd /opt/erp_tml

# Virtual Environment erstellen
python3 -m venv venv

# Virtual Environment aktivieren
source venv/bin/activate

# Pip aktualisieren
pip install --upgrade pip

# Alle Abhängigkeiten installieren
pip install -r requirements.txt
```

**Überprüfung:**
```bash
which python  # Sollte /opt/erp_tml/venv/bin/python zeigen
pip list      # Sollte alle installierten Pakete zeigen
```

---

## ⚙️ Schritt 5: Umgebungsvariablen konfigurieren

```bash
cd /opt/erp_tml

# .env-Datei erstellen
cp .env.example .env
nano .env
```

**Inhalt der `.env`-Datei anpassen:**

```bash
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=HIER_EINEN_STARKEN_SCHLÜSSEL_EINFÜGEN

# Database
DATABASE_URL=sqlite:///buchhaltung.db

# Gmail API
GMAIL_CREDENTIALS_PATH=credentials/gmail_credentials.json
GMAIL_TOKEN_PATH=credentials/gmail_token.json

# File Storage
UPLOAD_FOLDER=/data/rechnungen
MAX_UPLOAD_SIZE=10485760

# Server
HOST=0.0.0.0
PORT=5000
```

**Wichtige Anpassungen:**

1. **SECRET_KEY generieren:**
   ```bash
   # Neuen Schlüssel generieren:
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
   Den generierten Schlüssel in `.env` bei `SECRET_KEY=` eintragen.

2. **UPLOAD_FOLDER:** Standard ist `/data/rechnungen` (wird automatisch erstellt)

**Datei speichern:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 💾 Schritt 6: Datenbank-Verzeichnis und Upload-Ordner erstellen

```bash
# Upload-Ordner für PDFs erstellen
sudo mkdir -p /data/rechnungen
sudo chown -R $USER:$USER /data/rechnungen
sudo chmod 755 /data/rechnungen

# Credentials-Ordner erstellen
mkdir -p /opt/erp_tml/credentials
chmod 700 /opt/erp_tml/credentials
```

---

## 🗄️ Schritt 7: Datenbank initialisieren

```bash
cd /opt/erp_tml
source venv/bin/activate

# Datenbank erstellen
python init_db.py
```

**Erwartete Ausgabe:**
```
✓ Datenbank erstellt
✓ Standard-Admin erstellt:
  Benutzername: admin
  Passwort: admin
  ⚠️  BITTE SOFORT DAS PASSWORT ÄNDERN!
```

**⚠️ WICHTIG:** Notieren Sie sich die Zugangsdaten!

---

## 📧 Schritt 8: Gmail API einrichten

### 8.1 Google Cloud Console konfigurieren

1. **Google Cloud Console öffnen:**
   - Gehen Sie zu: https://console.cloud.google.com/
   - Melden Sie sich mit `info.tmlstudio@gmail.com` an

2. **Neues Projekt erstellen:**
   - Klicken Sie auf "Projekt auswählen" → "Neues Projekt"
   - Projektname: `TMLSTUDIO-Buchhaltung`
   - Klicken Sie auf "Erstellen"

3. **Gmail API aktivieren:**
   - Im Menü: "APIs & Dienste" → "Bibliothek"
   - Suchen Sie nach "Gmail API"
   - Klicken Sie auf "Gmail API" → "Aktivieren"

4. **OAuth 2.0 Client-ID erstellen:**
   - Im Menü: "APIs & Dienste" → "Anmeldedaten"
   - Klicken Sie auf "+ ANMELDEDATEN ERSTELLEN" → "OAuth-Client-ID"
   - Falls gefragt: "OAuth-Zustimmungsbildschirm konfigurieren"
     - Benutzertyp: "Extern"
     - App-Name: "TMLSTUDIO Buchhaltung"
     - E-Mail: `info.tmlstudio@gmail.com`
     - Entwicklerkontakt: `info.tmlstudio@gmail.com`
     - Speichern und fortfahren
   - Anwendungstyp: **"Desktop-App"** (wichtig!)
   - Name: "TMLSTUDIO Buchhaltung Server"
   - Klicken Sie auf "Erstellen"

5. **Credentials herunterladen:**
   - Klicken Sie auf das Download-Symbol neben der erstellten Client-ID
   - Die JSON-Datei wird heruntergeladen (z.B. `client_secret_xxxxx.json`)

### 8.2 Credentials auf Server übertragen

```bash
# Vom lokalen Rechner aus (wo die JSON-Datei ist):
scp client_secret_*.json benutzer@server-ip:/opt/erp_tml/credentials/gmail_credentials.json
```

**Oder manuell:**
```bash
# Auf dem Server:
cd /opt/erp_tml/credentials
nano gmail_credentials.json
# JSON-Inhalt hier einfügen
```

**Berechtigungen setzen:**
```bash
chmod 600 /opt/erp_tml/credentials/gmail_credentials.json
```

### 8.3 Erste Gmail-Authentifizierung

**Wichtig:** Die OAuth-Authentifizierung muss auf einem Rechner mit Browser durchgeführt werden (nicht auf dem Server).

**Option 1: Mit Setup-Script (empfohlen)**

1. **Auf Ihrem lokalen Rechner:**
   ```bash
   # Projekt-Verzeichnis öffnen
   cd /pfad/zum/projekt
   
   # Virtual Environment aktivieren (falls vorhanden)
   source venv/bin/activate  # oder: python3 -m venv venv && source venv/bin/activate
   
   # Abhängigkeiten installieren (falls noch nicht geschehen)
   pip install google-auth-oauthlib
   
   # Gmail-Credentials auf lokalen Rechner kopieren
   # (von Server: scp benutzer@server:/opt/erp_tml/credentials/gmail_credentials.json .)
   
   # Setup-Script ausführen
   python scripts/setup_gmail_auth.py
   ```

2. **Folgen Sie den Anweisungen:**
   - Pfad zu `gmail_credentials.json` eingeben
   - Browser öffnet sich automatisch
   - Mit Gmail-Account anmelden
   - Berechtigung erteilen
   - Token wird angezeigt und kann gespeichert werden

3. **Token auf Server kopieren:**
   ```bash
   scp credentials/gmail_token.json benutzer@server:/opt/erp_tml/credentials/
   ```

**Option 2: Manuell mit Python**

1. **Auf lokalem Rechner:**
   ```bash
   python3
   ```
   
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   import json
   
   SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
   flow = InstalledAppFlow.from_client_secrets_file(
       'credentials/gmail_credentials.json', SCOPES)
   creds = flow.run_local_server(port=0)
   
   # Token speichern
   with open('credentials/gmail_token.json', 'w') as f:
       f.write(creds.to_json())
   ```

2. **Token auf Server kopieren:**
   ```bash
   scp credentials/gmail_token.json benutzer@server:/opt/erp_tml/credentials/
   ```

**Option 3: Direkt auf Server (nur wenn X11-Forwarding aktiviert)**

```bash
# SSH mit X11-Forwarding
ssh -X benutzer@server-ip

# Auf Server
cd /opt/erp_tml
source venv/bin/activate
python3
```

```python
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials/gmail_credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

import json
with open('credentials/gmail_token.json', 'w') as f:
    f.write(creds.to_json())
```

---

## 🔄 Schritt 9: Gunicorn konfigurieren

### 9.1 Systemd Service erstellen

```bash
sudo nano /etc/systemd/system/erp-tml.service
```

**Inhalt einfügen:**

```ini
[Unit]
Description=ERP TML Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/erp_tml
Environment="PATH=/opt/erp_tml/venv/bin"
EnvironmentFile=/opt/erp_tml/.env
ExecStart=/opt/erp_tml/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/opt/erp_tml/erp_tml.sock \
    --timeout 120 \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Datei speichern:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 9.2 Berechtigungen setzen

```bash
# www-data Benutzer Zugriff geben
sudo chown -R www-data:www-data /opt/erp_tml
sudo chown -R www-data:www-data /data/rechnungen

# Nur für Datenbank und Credentials: Eigentümer behalten
sudo chown $USER:$USER /opt/erp_tml/buchhaltung.db
sudo chown -R $USER:$USER /opt/erp_tml/credentials
```

### 9.3 Service aktivieren und starten

```bash
# Systemd neu laden
sudo systemctl daemon-reload

# Service aktivieren (startet bei Boot)
sudo systemctl enable erp-tml

# Service starten
sudo systemctl start erp-tml

# Status überprüfen
sudo systemctl status erp-tml
```

**Erwartete Ausgabe:** `active (running)`

**Logs ansehen:**
```bash
sudo journalctl -u erp-tml -f
```

---

## 🌐 Schritt 10: Nginx konfigurieren

### 10.1 Nginx-Konfiguration erstellen

```bash
sudo nano /etc/nginx/sites-available/erp-tml
```

**Inhalt einfügen:**

```nginx
server {
    listen 80;
    server_name deine-domain.de;  # ODER: server_name _; für IP-Zugriff

    # Maximale Upload-Größe
    client_max_body_size 10M;

    # Hauptanwendung
    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/erp_tml/erp_tml.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Statische Dateien (optional, für Performance)
    location /static {
        alias /opt/erp_tml/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # PDF-Rechnungen (geschützt)
    location /rechnungen {
        alias /data/rechnungen;
        internal;  # Nur interne Weiterleitungen erlauben
    }
}
```

**Anpassungen:**
- `server_name`: Ihre Domain eintragen, oder `_` für IP-Zugriff
- Falls Sie eine Domain haben, später SSL einrichten (siehe Schritt 11)

**Datei speichern:** `Ctrl+O`, `Enter`, `Ctrl+X`

### 10.2 Konfiguration aktivieren

```bash
# Symlink erstellen
sudo ln -s /etc/nginx/sites-available/erp-tml /etc/nginx/sites-enabled/

# Standard-Konfiguration deaktivieren (falls vorhanden)
sudo rm -f /etc/nginx/sites-enabled/default

# Konfiguration testen
sudo nginx -t
```

**Erwartete Ausgabe:** `test is successful`

### 10.3 Nginx starten/neu starten

```bash
sudo systemctl restart nginx
sudo systemctl status nginx
```

---

## 🔒 Schritt 11: SSL/TLS einrichten (Optional, aber empfohlen)

### 11.1 Certbot installieren

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 11.2 SSL-Zertifikat erstellen

```bash
# Ersetzen Sie 'deine-domain.de' mit Ihrer tatsächlichen Domain
sudo certbot --nginx -d deine-domain.de
```

**Folgen Sie den Anweisungen:**
- E-Mail-Adresse eingeben
- AGB akzeptieren
- Zertifikat wird automatisch erstellt und Nginx-Konfiguration angepasst

### 11.3 Auto-Renewal testen

```bash
sudo certbot renew --dry-run
```

---

## ⏰ Schritt 12: Cron-Job für Gmail-Synchronisation

```bash
# Crontab öffnen
crontab -e
```

**Eintrag hinzufügen (z.B. stündlich):**

```cron
# Gmail-Synchronisation jede Stunde
0 * * * * cd /opt/erp_tml && /opt/erp_tml/venv/bin/python3 gmail_sync_cron.py >> /var/log/erp_tml_sync.log 2>&1
```

**Oder täglich um 8 Uhr:**
```cron
# Gmail-Synchronisation täglich um 8 Uhr
0 8 * * * cd /opt/erp_tml && /opt/erp_tml/venv/bin/python3 gmail_sync_cron.py >> /var/log/erp_tml_sync.log 2>&1
```

**Log-Verzeichnis erstellen:**
```bash
sudo touch /var/log/erp_tml_sync.log
sudo chmod 666 /var/log/erp_tml_sync.log
```

**Cron-Job testen:**
```bash
# Manuell ausführen
cd /opt/erp_tml
source venv/bin/activate
python gmail_sync_cron.py

# Log ansehen
tail -f /var/log/erp_tml_sync.log
```

---

## ✅ Schritt 13: Installation überprüfen

### 13.1 Service-Status prüfen

```bash
# Gunicorn Service
sudo systemctl status erp-tml

# Nginx Service
sudo systemctl status nginx
```

### 13.2 Web-Interface testen

1. **Im Browser öffnen:**
   - Mit Domain: `https://deine-domain.de`
   - Mit IP: `http://server-ip`

2. **Login:**
   - Benutzername: `admin`
   - Passwort: `admin`

3. **Funktionen testen:**
   - Dashboard öffnen
   - Lieferant hinzufügen
   - Manuelle Buchung erstellen
   - Gmail-Synchronisation testen

### 13.3 Logs überprüfen

```bash
# Gunicorn Logs
sudo journalctl -u erp-tml -n 50

# Nginx Logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Gmail-Sync Logs
tail -f /var/log/erp_tml_sync.log
```

---

## 🔐 Schritt 14: Sicherheit - Passwort ändern

**⚠️ WICHTIG: Standard-Passwort sofort ändern!**

### Option 1: Über die Web-Oberfläche (später implementieren)

### Option 2: Über Python-Script

```bash
cd /opt/erp_tml
source venv/bin/activate
python3
```

```python
from app import app
from models import db, User

with app.app_context():
    user = User.query.filter_by(username='admin').first()
    user.set_password('IHR_NEUES_SICHERES_PASSWORT')
    db.session.commit()
    print("Passwort erfolgreich geändert!")
```

**Exit:** `exit()`

---

## 📊 Schritt 15: Erste Konfiguration

### 15.1 Lieferanten anlegen

1. **Im Browser:** Login → "Lieferanten"
2. **Neuer Lieferant** klicken
3. **Beispiel:**
   - Name: `BuildYourBrand`
   - Typ: `Ausgabe`
   - Gmail-Label: `Buchhaltung-Ausgaben-BuildYourBrand Rechnungen`
   - Aktiv: ✅
   - Speichern

4. **Weitere Lieferanten hinzufügen:**
   - `RalaTeam` (Ausgabe)
   - `Einnahmen` (Einnahme)

### 15.2 Gmail-Labels erstellen

**In Gmail (`info.tmlstudio@gmail.com`):**

1. E-Mail öffnen
2. Label-Symbol klicken → "Neues Label erstellen"
3. Label-Name eingeben (z.B. `Buchhaltung-Ausgaben-BuildYourBrand Rechnungen`)
4. Label auf E-Mail anwenden

**Wichtig:** Label-Namen müssen exakt mit denen in der Lieferanten-Verwaltung übereinstimmen!

### 15.3 Erste Synchronisation

1. **Im Browser:** Dashboard → "Gmail synchronisieren"
2. Oder warten bis Cron-Job läuft
3. Prüfen ob Rechnungen importiert wurden

---

## 🛠️ Wartung und Troubleshooting

### Datenbank-Backup

**Mit Script (empfohlen):**
```bash
cd /opt/erp_tml
source venv/bin/activate
python scripts/backup_db.py
```

**Manuell:**
```bash
# Backup erstellen
cd /opt/erp_tml
sqlite3 buchhaltung.db ".backup backup_$(date +%Y%m%d_%H%M%S).db"

# Backup wiederherstellen
sqlite3 buchhaltung.db ".restore backup_20260101_120000.db"
```

**Automatisches Backup (Cron-Job):**
```bash
crontab -e
# Täglich um 2 Uhr morgens
0 2 * * * cd /opt/erp_tml && /opt/erp_tml/venv/bin/python3 scripts/backup_db.py >> /var/log/erp_tml_backup.log 2>&1
```

### Service neu starten

```bash
# Gunicorn Service
sudo systemctl restart erp-tml

# Nginx
sudo systemctl restart nginx
```

### Logs ansehen

```bash
# Gunicorn Logs (letzte 100 Zeilen)
sudo journalctl -u erp-tml -n 100

# Gunicorn Logs (Live)
sudo journalctl -u erp-tml -f

# Gmail-Sync Logs
tail -f /var/log/erp_tml_sync.log
```

### Häufige Probleme

**Problem: Service startet nicht**
```bash
# Logs prüfen
sudo journalctl -u erp-tml -n 50

# Berechtigungen prüfen
ls -la /opt/erp_tml
sudo chown -R www-data:www-data /opt/erp_tml
```

**Problem: Gmail-Authentifizierung schlägt fehl**
```bash
# Token löschen und neu authentifizieren
rm /opt/erp_tml/credentials/gmail_token.json
# Dann App starten und Gmail-Sync erneut ausführen
```

**Problem: PDF wird nicht erkannt**
- PDF muss Text enthalten (keine gescannten Bilder)
- Für gescannte PDFs: Tesseract OCR installiert?

**Problem: 502 Bad Gateway**
```bash
# Gunicorn Socket prüfen
ls -la /opt/erp_tml/erp_tml.sock
sudo systemctl restart erp-tml
```

---

## 📝 Checkliste

- [ ] System aktualisiert
- [ ] Python und Abhängigkeiten installiert
- [ ] Projekt-Verzeichnis erstellt
- [ ] Virtual Environment erstellt und aktiviert
- [ ] Abhängigkeiten installiert (`pip install -r requirements.txt`)
- [ ] `.env`-Datei konfiguriert (mit starkem SECRET_KEY)
- [ ] Upload-Ordner erstellt (`/data/rechnungen`)
- [ ] Datenbank initialisiert
- [ ] Gmail API eingerichtet (Google Cloud Console)
- [ ] Gmail Credentials auf Server übertragen
- [ ] Erste Gmail-Authentifizierung durchgeführt
- [ ] Gunicorn Service erstellt und gestartet
- [ ] Nginx konfiguriert und gestartet
- [ ] SSL-Zertifikat installiert (optional)
- [ ] Cron-Job für Gmail-Sync eingerichtet
- [ ] Web-Interface getestet
- [ ] Standard-Passwort geändert
- [ ] Lieferanten angelegt
- [ ] Gmail-Labels erstellt
- [ ] Erste Synchronisation erfolgreich

---

## 🎉 Fertig!

Ihre Buchhaltungsverwaltung ist jetzt einsatzbereit!

**Zugriff:**
- URL: `https://deine-domain.de` (oder `http://server-ip`)
- Login: `admin` / `IHR_NEUES_PASSWORT`

**Nächste Schritte:**
1. Weitere Benutzer anlegen (später implementieren)
2. Regelmäßige Backups einrichten
3. Monitoring einrichten (optional)

**Support:**
- Logs: `sudo journalctl -u erp-tml -f`
- Dokumentation: `README.md`

