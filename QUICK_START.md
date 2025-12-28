# 🚀 Quick Start - Schnelleinstieg

Kurzanleitung für erfahrene Linux-Administratoren.

## Voraussetzungen

- Ubuntu 24.04 Server
- Root/Sudo-Zugriff
- Domain oder IP-Adresse

## Installation (Kurzfassung)

```bash
# 1. System-Abhängigkeiten
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx gunicorn

# 2. Projekt-Verzeichnis
sudo mkdir -p /opt/erp_tml /data/rechnungen
sudo chown $USER:$USER /opt/erp_tml /data/rechnungen
cd /opt/erp_tml
# Dateien hierher kopieren

# 3. Python Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Konfiguration
cp .env.example .env
nano .env  # SECRET_KEY generieren: python3 -c "import secrets; print(secrets.token_hex(32))"

# 5. Datenbank
python init_db.py

# 6. Gmail API (siehe INSTALLATION.md Schritt 8)
# Credentials nach credentials/gmail_credentials.json kopieren

# 7. Gunicorn Service
sudo nano /etc/systemd/system/erp-tml.service
# Inhalt siehe INSTALLATION.md Schritt 9
sudo systemctl daemon-reload
sudo systemctl enable erp-tml
sudo systemctl start erp-tml

# 8. Nginx
sudo nano /etc/nginx/sites-available/erp-tml
# Inhalt siehe INSTALLATION.md Schritt 10
sudo ln -s /etc/nginx/sites-available/erp-tml /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 9. SSL (optional)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d deine-domain.de

# 10. Cron-Job
crontab -e
# 0 * * * * cd /opt/erp_tml && /opt/erp_tml/venv/bin/python3 gmail_sync_cron.py >> /var/log/erp_tml_sync.log 2>&1

# 11. Passwort ändern
python scripts/change_password.py
```

## Wichtige Dateien

- **Konfiguration:** `/opt/erp_tml/.env`
- **Datenbank:** `/opt/erp_tml/buchhaltung.db`
- **Logs:** `sudo journalctl -u erp-tml -f`
- **Backup:** `python scripts/backup_db.py`

## Nützliche Befehle

```bash
# Service neu starten
sudo systemctl restart erp-tml

# Logs ansehen
sudo journalctl -u erp-tml -f

# Gmail-Sync manuell
cd /opt/erp_tml && source venv/bin/activate && python gmail_sync_cron.py

# Backup erstellen
cd /opt/erp_tml && source venv/bin/activate && python scripts/backup_db.py
```

**Detaillierte Anleitung:** Siehe `INSTALLATION.md`

