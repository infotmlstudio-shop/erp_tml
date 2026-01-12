# Gmail Token Setup - Kurzanleitung

## Schritt 1: Token lokal erstellen (Windows)

**PowerShell als Administrator öffnen** und ins Projektverzeichnis wechseln:

```powershell
cd C:\TMLSTUDIO\ERP_TML
```

**Setup-Script ausführen:**

```powershell
venv\Scripts\python.exe scripts\setup_gmail_auth.py
```

**Authentifizierung durchführen:**
- Enter drücken für Standard-Pfad
- Browser öffnet sich automatisch
- Mit Gmail-Account anmelden und Berechtigung erteilen
- Token wird in `credentials\gmail_token.json` gespeichert

---

## Schritt 2: Token auf Server kopieren

**Option A: Mit SCP (vom Windows-Rechner aus):**

```powershell
scp C:\TMLSTUDIO\ERP_TML\credentials\gmail_token.json root@SERVER-IP:/opt/erp_tml/credentials/gmail_token.json
```

**Option B: Manuell kopieren:**
1. Datei öffnen: `C:\TMLSTUDIO\ERP_TML\credentials\gmail_token.json`
2. Gesamten Inhalt kopieren
3. Auf Server: `nano /opt/erp_tml/credentials/gmail_token.json`
4. Inhalt einfügen, speichern (Ctrl+O, Enter, Ctrl+X)

---

## Schritt 3: Berechtigungen auf Server setzen

**SSH zum Server** und ausführen:

```bash
chmod 600 /opt/erp_tml/credentials/gmail_token.json
chown www-data:www-data /opt/erp_tml/credentials/gmail_token.json
```

---

## Schritt 4: Fertig!

Token ist jetzt auf dem Server. Gmail-Synchronisation sollte funktionieren.

**Hinweis:** Falls das Token abläuft, einfach Schritt 1-3 wiederholen.

