# Gmail OAuth-Authentifizierung - Anleitung für Ubuntu Server

## Problem
Auf einem Server ohne GUI kann kein Browser für die OAuth-Authentifizierung geöffnet werden.

## Lösung: Token lokal erstellen und auf Server kopieren

### Schritt 1: Auf Ihrem lokalen Windows-Rechner

1. **Terminal öffnen** im Projektverzeichnis `C:\TMLSTUDIO\ERP_TML`

2. **Option A: Execution Policy umgehen (empfohlen):**
   ```powershell
   powershell -ExecutionPolicy Bypass -Command ".\venv\Scripts\Activate.ps1; python scripts\setup_gmail_auth.py"
   ```

   **Option B: Python direkt aus venv verwenden:**
   ```powershell
   .\venv\Scripts\python.exe scripts\setup_gmail_auth.py
   ```
   
   **Option C: Execution Policy dauerhaft ändern (nur einmal nötig):**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   Dann können Sie normal aktivieren:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python scripts\setup_gmail_auth.py
   ```

4. **Authentifizierung durchführen:**
   - Drücken Sie Enter für den Standard-Pfad
   - Browser öffnet sich automatisch
   - Mit Gmail-Account anmelden
   - Berechtigung erteilen
   - Token wird in `credentials\gmail_token.json` gespeichert

### Schritt 2: Token auf Server kopieren

**Option A: Mit SCP (vom lokalen Rechner aus):**
```powershell
scp C:\TMLSTUDIO\ERP_TML\credentials\gmail_token.json root@server-ip:/opt/erp_tml/credentials/gmail_token.json
```

**Option B: Manuell kopieren:**
1. Öffnen Sie `C:\TMLSTUDIO\ERP_TML\credentials\gmail_token.json` in einem Editor
2. Kopieren Sie den gesamten Inhalt
3. Auf dem Server:
   ```bash
   cd /opt/erp_tml/credentials
   nano gmail_token.json
   # Inhalt einfügen, speichern mit Ctrl+O, Enter, Ctrl+X
   ```

### Schritt 3: Berechtigungen setzen (auf dem Server)

```bash
chmod 600 /opt/erp_tml/credentials/gmail_token.json
chown www-data:www-data /opt/erp_tml/credentials/gmail_token.json
```

### Schritt 4: Testen

Auf dem Server die Gmail-Synchronisation über die Web-Oberfläche testen.

---

## Alternative: SSH-Tunnel (wenn lokaler Zugriff nicht möglich)

Falls Sie keinen lokalen Windows-Rechner haben:

1. **SSH-Tunnel erstellen** (vom lokalen Rechner):
   ```bash
   ssh -L 5000:localhost:5000 root@server-ip
   ```

2. **Auf dem Server Flask-App temporär starten:**
   ```bash
   cd /opt/erp_tml
   source venv/bin/activate
   python app.py
   ```

3. **Im Browser:** `http://localhost:5000` öffnen
4. **Gmail synchronisieren** klicken
5. Browser öffnet sich für Authentifizierung
6. Nach erfolgreicher Authentifizierung App stoppen (Ctrl+C)

---

## Wichtige Hinweise

- Das Token ist gültig, bis es widerrufen wird oder abläuft
- Bei Problemen: Token löschen und neu erstellen
- Token-Datei sollte nicht in Git committed werden (steht in .gitignore)

