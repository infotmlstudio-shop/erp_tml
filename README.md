# 📒 TMLSTUDIO Buchhaltungsverwaltung

Eine webbasierte Buchhaltungsverwaltung für **TMLSTUDIO** mit automatischer Rechnungserfassung aus Gmail.

## 🎯 Features

- **Dashboard** mit Jahresfilter und Kennzahlen (Einnahmen, Ausgaben, Gewinn)
- **Einnahmen-Verwaltung** mit manueller und automatischer Erfassung
- **Ausgaben-Verwaltung** nach Lieferanten gruppiert
- **Automatische Gmail-Integration** für Rechnungserfassung
- **PDF-Verarbeitung** zur Extraktion von Betrag, Datum und Rechnungsnummer
- **Lieferanten-Verwaltung** mit Gmail-Label-Zuordnung
- **Benutzeranmeldung** mit Passwort-Hashing

## 🚀 Installation auf Ubuntu 24.04

### 1. System-Abhängigkeiten installieren

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx gunicorn
```

### 2. Projekt klonen/übertragen

```bash
cd /opt
sudo mkdir -p erp_tml
sudo chown $USER:$USER erp_tml
cd erp_tml
# Dateien hierher kopieren
```

### 3. Python Virtual Environment erstellen

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
nano .env
```

Wichtige Einstellungen:
- `SECRET_KEY`: Starker, zufälliger Schlüssel (z.B. `openssl rand -hex 32`)
- `UPLOAD_FOLDER`: `/data/rechnungen` (oder gewünschter Pfad)
- Gmail-Credentials-Pfade anpassen

### 5. Datenbank initialisieren

```bash
python3 app.py
```

Dies erstellt die Datenbank und einen Standard-Admin-Benutzer:
- **Benutzername:** `admin`
- **Passwort:** `admin` ⚠️ **Bitte sofort ändern!**

### 6. Gmail API einrichten

1. **Google Cloud Console:**
   - Projekt erstellen: https://console.cloud.google.com/
   - Gmail API aktivieren
   - OAuth 2.0 Client-ID erstellen (Desktop App)
   - Credentials als JSON herunterladen

2. **Credentials speichern:**
   ```bash
   mkdir -p credentials
   # JSON-Datei nach credentials/gmail_credentials.json kopieren
   ```

3. **Erste Authentifizierung:**
   - App starten und Gmail-Synchronisation auslösen
   - Browser öffnet sich für OAuth-Authentifizierung
   - Token wird in `credentials/gmail_token.json` gespeichert

### 7. Verzeichnisse erstellen

```bash
sudo mkdir -p /data/rechnungen
sudo chown -R $USER:$USER /data/rechnungen
```

### 8. Gunicorn konfigurieren

Erstelle `/etc/systemd/system/erp-tml.service`:

```ini
[Unit]
Description=ERP TML Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/erp_tml
Environment="PATH=/opt/erp_tml/venv/bin"
ExecStart=/opt/erp_tml/venv/bin/gunicorn --workers 3 --bind unix:/opt/erp_tml/erp_tml.sock app:app

[Install]
WantedBy=multi-user.target
```

Service aktivieren:
```bash
sudo systemctl daemon-reload
sudo systemctl enable erp-tml
sudo systemctl start erp-tml
```

### 9. Nginx konfigurieren

Erstelle `/etc/nginx/sites-available/erp-tml`:

```nginx
server {
    listen 80;
    server_name deine-domain.de;

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/erp_tml/erp_tml.sock;
    }

    location /rechnungen {
        alias /data/rechnungen;
        internal;
    }
}
```

Aktivieren:
```bash
sudo ln -s /etc/nginx/sites-available/erp-tml /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 10. Cron-Job für Gmail-Synchronisation

```bash
crontab -e
```

Eintrag hinzufügen (z.B. stündlich):
```
0 * * * * cd /opt/erp_tml && /opt/erp_tml/venv/bin/python3 gmail_sync_cron.py >> /var/log/erp_tml_sync.log 2>&1
```

## 📋 Verwendung

### Lieferanten anlegen

1. **Einstellungen → Lieferanten**
2. **Neuer Lieferant** klicken
3. Felder ausfüllen:
   - **Name:** z.B. "BuildYourBrand"
   - **Typ:** Ausgabe oder Einnahme
   - **Gmail-Label:** z.B. "Buchhaltung-Ausgaben-BuildYourBrand Rechnungen"
   - **Aktiv:** Häkchen setzen

### Gmail-Labels erstellen

In Gmail:
1. E-Mail öffnen
2. Label hinzufügen (z.B. "Buchhaltung-Ausgaben-BuildYourBrand Rechnungen")
3. System synchronisiert automatisch (oder manuell über Dashboard)

### Manuelle Buchung

1. **Einnahmen** oder **Ausgaben** → **Neu**
2. Formular ausfüllen
3. Optional PDF hochladen
4. **Speichern**

## 🔧 Wartung

### Logs ansehen

```bash
# Gunicorn
sudo journalctl -u erp-tml -f

# Gmail-Sync
tail -f /var/log/erp_tml_sync.log
```

### Datenbank-Backup

```bash
sqlite3 buchhaltung.db ".backup backup_$(date +%Y%m%d).db"
```

### Passwort ändern

```python
from app import app
from models import db, User

with app.app_context():
    user = User.query.filter_by(username='admin').first()
    user.set_password('neues_passwort')
    db.session.commit()
```

## 📁 Projektstruktur

```
ERP_TML/
├── app.py                 # Hauptanwendung
├── models.py              # Datenbankmodelle
├── config.py              # Konfiguration
├── requirements.txt       # Python-Abhängigkeiten
├── gmail_sync_cron.py     # Cron-Job Script
├── services/
│   ├── gmail_service.py   # Gmail-Integration
│   └── pdf_service.py     # PDF-Verarbeitung
├── templates/             # HTML-Templates
├── credentials/           # Gmail API Credentials
├── data/
│   └── rechnungen/        # PDF-Speicher
└── buchhaltung.db         # SQLite-Datenbank
```

## 🔒 Sicherheit

- ⚠️ **Standard-Passwort ändern!**
- Starker `SECRET_KEY` in `.env`
- Nginx mit SSL/TLS (Let's Encrypt)
- Regelmäßige Backups
- Gmail-Token sicher aufbewahren

## 🐛 Fehlerbehebung

### Gmail-Authentifizierung schlägt fehl
- Credentials-Datei prüfen
- Token löschen und neu authentifizieren: `rm credentials/gmail_token.json`

### PDF wird nicht erkannt
- PDF-Format prüfen (muss Text enthalten, keine gescannten Bilder)
- Optional: Tesseract OCR installieren für gescannte PDFs

### Service startet nicht
```bash
sudo systemctl status erp-tml
sudo journalctl -u erp-tml -n 50
```

## 📝 Lizenz

Proprietär - TMLSTUDIO

