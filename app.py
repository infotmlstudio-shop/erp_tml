from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Lieferant, Buchung, Lager, Artikel, Rolle
from config import Config
from datetime import datetime, date
from decimal import Decimal
from functools import wraps
import os
from werkzeug.utils import secure_filename

# Import Gmail und PDF Services
from services.gmail_service import GmailService
from services.pdf_service import PDFService

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bitte melden Sie sich an, um diese Seite zu sehen.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Services werden bei Bedarf initialisiert (nicht global, da Flask-Kontext benötigt wird)

# Routes
@app.route('/')
@login_required
def index():
    """Dashboard mit Jahresfilter"""
    if not current_user.hat_berechtigung('dashboard'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('login'))
    jahr = request.args.get('jahr', type=int)
    if not jahr:
        jahr = datetime.now().year
        if jahr < 2025:
            jahr = 2025
    
    # Kennzahlen für das ausgewählte Jahr
    einnahmen = db.session.query(db.func.sum(Buchung.betrag)).filter(
        Buchung.typ == 'Einnahme',
        Buchung.jahr == jahr
    ).scalar() or Decimal('0.00')
    
    ausgaben = db.session.query(db.func.sum(Buchung.betrag)).filter(
        Buchung.typ == 'Ausgabe',
        Buchung.jahr == jahr
    ).scalar() or Decimal('0.00')
    
    gewinn = einnahmen - ausgaben
    
    # Monatsübersicht für Diagramm
    monatsdaten = db.session.query(
        db.func.strftime('%m', Buchung.datum).label('monat'),
        db.func.sum(Buchung.betrag).label('betrag')
    ).filter(
        Buchung.jahr == jahr
    ).group_by('monat').all()
    
    monats_einnahmen = {}
    monats_ausgaben = {}
    
    for monat, betrag in monatsdaten:
        buchungen = Buchung.query.filter(
            db.func.strftime('%m', Buchung.datum) == monat,
            Buchung.jahr == jahr
        ).all()
        
        for b in buchungen:
            if b.typ == 'Einnahme':
                monats_einnahmen[monat] = monats_einnahmen.get(monat, Decimal('0.00')) + b.betrag
            else:
                monats_ausgaben[monat] = monats_ausgaben.get(monat, Decimal('0.00')) + b.betrag
    
    # Jahre für Dropdown generieren
    current_year = datetime.now().year
    start_year = 2025
    end_year = current_year + 2
    jahre = list(range(start_year, end_year + 1))
    
    return render_template('dashboard.html', 
                         jahr=jahr,
                         jahre=jahre,
                         einnahmen=einnahmen,
                         ausgaben=ausgaben,
                         gewinn=gewinn,
                         monats_einnahmen=monats_einnahmen,
                         monats_ausgaben=monats_ausgaben)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'success')
    return redirect(url_for('login'))

@app.route('/einnahmen')
@login_required
def einnahmen():
    """Einnahmen-Übersicht"""
    jahr = request.args.get('jahr', type=int)
    if not jahr:
        current_year = datetime.now().year
        jahr = current_year if current_year >= 2025 else 2025
    
    buchungen = Buchung.query.filter(
        Buchung.typ == 'Einnahme',
        Buchung.jahr == jahr
    ).order_by(Buchung.datum.desc()).all()
    
    # Jahre für Dropdown
    current_year = datetime.now().year
    start_year = 2025
    end_year = current_year + 2
    jahre = list(range(start_year, end_year + 1))
    
    return render_template('einnahmen.html', buchungen=buchungen, jahr=jahr, jahre=jahre)

@app.route('/einnahmen/neu', methods=['GET', 'POST'])
@login_required
def einnahmen_neu():
    """Neue Einnahme hinzufügen"""
    if request.method == 'POST':
        betrag = Decimal(request.form.get('betrag'))
        datum = datetime.strptime(request.form.get('datum'), '%Y-%m-%d').date()
        rechnungsnummer = request.form.get('rechnungsnummer', '')
        titel = request.form.get('titel', '')
        ueberwiesen_am = request.form.get('ueberwiesen_am')
        if ueberwiesen_am:
            ueberwiesen_am = datetime.strptime(ueberwiesen_am, '%Y-%m-%d').date()
        else:
            ueberwiesen_am = None
        
        # PDF-Upload
        pdf_pfad = None
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                pdf_pfad = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(pdf_pfad)
        
        buchung = Buchung(
            typ='Einnahme',
            betrag=betrag,
            datum=datum,
            rechnungsnummer=rechnungsnummer,
            titel=titel,
            pdf_pfad=pdf_pfad,
            jahr=datum.year,
            quelle='Manuell',
            ueberwiesen_am=ueberwiesen_am
        )
        
        db.session.add(buchung)
        db.session.commit()
        
        flash('Einnahme erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('einnahmen', jahr=datum.year))
    
    return render_template('einnahmen_form.html', typ='Einnahme')

@app.route('/ausgaben')
@login_required
def ausgaben():
    """Ausgaben-Übersicht"""
    if not current_user.hat_berechtigung('ausgaben'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    """Ausgaben-Übersicht nach Lieferanten gruppiert"""
    jahr = request.args.get('jahr', type=int)
    if not jahr:
        current_year = datetime.now().year
        jahr = current_year if current_year >= 2025 else 2025
    
    # Alle aktiven Ausgaben-Lieferanten
    lieferanten = Lieferant.query.filter_by(typ='Ausgabe', aktiv=True).order_by(Lieferant.name).all()
    
    # Buchungen nach Lieferant gruppiert
    ausgaben_dict = {}
    ausgaben_summens = {}  # Dictionary für Gesamtbeträge
    
    for lieferant in lieferanten:
        buchungen = Buchung.query.filter(
            Buchung.typ == 'Ausgabe',
            Buchung.lieferant_id == lieferant.id,
            Buchung.jahr == jahr
        ).order_by(Buchung.datum.desc()).all()
        if buchungen:
            ausgaben_dict[lieferant] = buchungen
            # Gesamtbetrag berechnen
            gesamtbetrag = sum(float(b.betrag) for b in buchungen)
            ausgaben_summens[lieferant] = gesamtbetrag
    
    # Buchungen ohne Lieferant
    buchungen_ohne_lieferant = Buchung.query.filter(
        Buchung.typ == 'Ausgabe',
        Buchung.lieferant_id.is_(None),
        Buchung.jahr == jahr
    ).order_by(Buchung.datum.desc()).all()
    
    if buchungen_ohne_lieferant:
        ausgaben_dict[None] = buchungen_ohne_lieferant
        # Gesamtbetrag berechnen
        gesamtbetrag = sum(float(b.betrag) for b in buchungen_ohne_lieferant)
        ausgaben_summens[None] = gesamtbetrag
    
    # Jahre für Dropdown
    current_year = datetime.now().year
    start_year = 2025
    end_year = current_year + 2
    jahre = list(range(start_year, end_year + 1))
    
    return render_template('ausgaben.html', ausgaben_dict=ausgaben_dict, ausgaben_summens=ausgaben_summens, jahr=jahr, jahre=jahre)

@app.route('/ausgaben/zielkonto/<int:buchung_id>', methods=['POST'])
@login_required
def ausgaben_zielkonto(buchung_id):
    """Status 'Von Zielkonto abgebucht' aktualisieren"""
    try:
        data = request.get_json()
        abgebucht = data.get('abgebucht', False)
        
        buchung = Buchung.query.get_or_404(buchung_id)
        buchung.von_zielkonto_abgebucht = abgebucht
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/einnahmen/ueberwiesen/<int:buchung_id>', methods=['POST'])
@login_required
def einnahmen_ueberwiesen(buchung_id):
    """Datum 'Überwiesen am' aktualisieren"""
    try:
        data = request.get_json()
        ueberwiesen_am_str = data.get('ueberwiesen_am')
        
        buchung = Buchung.query.get_or_404(buchung_id)
        
        if ueberwiesen_am_str:
            ueberwiesen_am = datetime.strptime(ueberwiesen_am_str, '%Y-%m-%d').date()
        else:
            ueberwiesen_am = None
        
        buchung.ueberwiesen_am = ueberwiesen_am
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ausgaben/neu', methods=['GET', 'POST'])
@login_required
def ausgaben_neu():
    """Neue Ausgabe hinzufügen"""
    lieferanten = Lieferant.query.filter_by(typ='Ausgabe', aktiv=True).order_by(Lieferant.name).all()
    
    if request.method == 'POST':
        lieferant_id = request.form.get('lieferant_id')
        if lieferant_id:
            lieferant_id = int(lieferant_id) if lieferant_id != 'None' else None
        else:
            lieferant_id = None
        
        betrag = Decimal(request.form.get('betrag'))
        datum = datetime.strptime(request.form.get('datum'), '%Y-%m-%d').date()
        rechnungsnummer = request.form.get('rechnungsnummer', '')
        titel = request.form.get('titel', '')
        
        # PDF-Upload
        pdf_pfad = None
        if 'pdf' in request.files:
            file = request.files['pdf']
            if file and file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                pdf_pfad = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(pdf_pfad)
        
        # Prüfe ob DPD-Rechnung (für automatisches Abbuchen)
        von_zielkonto_abgebucht = False
        if lieferant_id:
            lieferant = Lieferant.query.get(lieferant_id)
            if lieferant and lieferant.name and 'DPD' in lieferant.name.upper():
                von_zielkonto_abgebucht = True
        
        buchung = Buchung(
            typ='Ausgabe',
            lieferant_id=lieferant_id,
            betrag=betrag,
            datum=datum,
            rechnungsnummer=rechnungsnummer,
            titel=titel,
            pdf_pfad=pdf_pfad,
            jahr=datum.year,
            quelle='Manuell',
            von_zielkonto_abgebucht=von_zielkonto_abgebucht
        )
        
        db.session.add(buchung)
        db.session.commit()
        
        flash('Ausgabe erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('ausgaben', jahr=datum.year))
    
    return render_template('ausgaben_form.html', typ='Ausgabe', lieferanten=lieferanten)

@app.route('/einstellungen/lieferanten')
@login_required
def lieferanten():
    """Lieferanten-Übersicht"""
    if not current_user.hat_berechtigung('lieferanten'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    """Lieferanten-Verwaltung"""
    lieferanten = Lieferant.query.order_by(Lieferant.typ, Lieferant.name).all()
    return render_template('lieferanten.html', lieferanten=lieferanten)

@app.route('/einstellungen/lieferanten/neu', methods=['GET', 'POST'])
@login_required
def lieferanten_neu():
    """Neuen Lieferanten hinzufügen"""
    if request.method == 'POST':
        name = request.form.get('name')
        gmail_label = request.form.get('gmail_label', '')
        typ = request.form.get('typ')
        aktiv = request.form.get('aktiv') == 'on'
        
        lieferant = Lieferant(
            name=name,
            gmail_label=gmail_label,
            typ=typ,
            aktiv=aktiv
        )
        
        db.session.add(lieferant)
        db.session.commit()
        
        flash('Lieferant erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('lieferanten'))
    
    return render_template('lieferanten_form.html')

@app.route('/einstellungen/lieferanten/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def lieferanten_bearbeiten(id):
    """Lieferant bearbeiten"""
    lieferant = Lieferant.query.get_or_404(id)
    
    if request.method == 'POST':
        lieferant.name = request.form.get('name')
        lieferant.gmail_label = request.form.get('gmail_label', '')
        lieferant.typ = request.form.get('typ')
        lieferant.aktiv = request.form.get('aktiv') == 'on'
        
        db.session.commit()
        
        flash('Lieferant erfolgreich aktualisiert.', 'success')
        return redirect(url_for('lieferanten'))
    
    return render_template('lieferanten_form.html', lieferant=lieferant)

@app.route('/einstellungen/lieferanten/<int:id>/loeschen', methods=['POST'])
@login_required
def lieferanten_loeschen(id):
    """Lieferant löschen"""
    lieferant = Lieferant.query.get_or_404(id)
    
    # Prüfen ob Buchungen existieren
    if Buchung.query.filter_by(lieferant_id=id).count() > 0:
        flash('Lieferant kann nicht gelöscht werden, da Buchungen vorhanden sind.', 'error')
        return redirect(url_for('lieferanten'))
    
    db.session.delete(lieferant)
    db.session.commit()
    
    flash('Lieferant erfolgreich gelöscht.', 'success')
    return redirect(url_for('lieferanten'))

# ==================== LAGERVERWALTUNG ====================

@app.route('/lager')
@login_required
def lager():
    """Lager-Übersicht"""
    if not current_user.hat_berechtigung('lager'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    """Lager-Übersicht"""
    lager_id = request.args.get('lager_id', type=int)
    lager_liste = Lager.query.filter_by(aktiv=True).order_by(Lager.name).all()
    
    if not lager_liste:
        flash('Keine Lager vorhanden. Bitte erstellen Sie zuerst ein Lager.', 'info')
        return redirect(url_for('lager_neu'))
    
    # Standard-Lager auswählen
    if not lager_id:
        lager_id = lager_liste[0].id
    
    aktuelles_lager = Lager.query.get_or_404(lager_id)
    artikel = Artikel.query.filter_by(lager_id=lager_id).order_by(Artikel.name).all()
    
    # Artikelanzahl pro Lager für Template
    artikel_anzahl = {}
    for l in lager_liste:
        artikel_anzahl[l.id] = Artikel.query.filter_by(lager_id=l.id).count()
    
    return render_template('lager.html', 
                         lager_liste=lager_liste,
                         aktuelles_lager=aktuelles_lager,
                         artikel=artikel,
                         lager_id=lager_id,
                         artikel_anzahl=artikel_anzahl)

@app.route('/lager/neu', methods=['GET', 'POST'])
@login_required
def lager_neu():
    """Neues Lager anlegen"""
    if request.method == 'POST':
        name = request.form.get('name')
        beschreibung = request.form.get('beschreibung', '')
        aktiv = request.form.get('aktiv') == 'on'
        
        if Lager.query.filter_by(name=name).first():
            flash('Ein Lager mit diesem Namen existiert bereits.', 'error')
            return render_template('lager_form.html')
        
        lager = Lager(
            name=name,
            beschreibung=beschreibung,
            aktiv=aktiv
        )
        
        db.session.add(lager)
        db.session.commit()
        
        flash('Lager erfolgreich angelegt.', 'success')
        return redirect(url_for('lager', lager_id=lager.id))
    
    return render_template('lager_form.html')

@app.route('/lager/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def lager_bearbeiten(id):
    """Lager bearbeiten"""
    lager = Lager.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        beschreibung = request.form.get('beschreibung', '')
        aktiv = request.form.get('aktiv') == 'on'
        
        # Prüfen ob Name bereits existiert (außer aktuellem Lager)
        existing = Lager.query.filter_by(name=name).first()
        if existing and existing.id != id:
            flash('Ein Lager mit diesem Namen existiert bereits.', 'error')
            return render_template('lager_form.html', lager=lager)
        
        lager.name = name
        lager.beschreibung = beschreibung
        lager.aktiv = aktiv
        db.session.commit()
        
        flash('Lager erfolgreich aktualisiert.', 'success')
        return redirect(url_for('lager', lager_id=lager.id))
    
    return render_template('lager_form.html', lager=lager)

@app.route('/lager/<int:id>/loeschen', methods=['POST'])
@login_required
def lager_loeschen(id):
    """Lager löschen"""
    lager = Lager.query.get_or_404(id)
    
    # Prüfen ob Artikel vorhanden
    if Artikel.query.filter_by(lager_id=id).count() > 0:
        flash('Lager kann nicht gelöscht werden, da noch Artikel vorhanden sind.', 'error')
        return redirect(url_for('lager', lager_id=id))
    
    db.session.delete(lager)
    db.session.commit()
    flash('Lager erfolgreich gelöscht.', 'success')
    return redirect(url_for('lager'))

# ==================== ARTIKELVERWALTUNG ====================

@app.route('/artikel/neu', methods=['GET', 'POST'])
@login_required
def artikel_neu():
    """Neuen Artikel anlegen"""
    lager_id = request.args.get('lager_id', type=int)
    
    if request.method == 'POST':
        lager_id = request.form.get('lager_id', type=int)
        name = request.form.get('name')
        beschreibung = request.form.get('beschreibung', '')
        bestand = request.form.get('bestand', type=int) or 0
        mindestbestand = request.form.get('mindestbestand', type=int) or 0
        einkaufspreis = request.form.get('einkaufspreis')
        einkaufspreis = Decimal(einkaufspreis) if einkaufspreis else None
        
        # Artikelnummer automatisch generieren
        artikelnummer = f"SKU-{datetime.now().strftime('%Y%m%d%H%M%S')}-{db.session.query(Artikel).count() + 1}"
        
        artikel = Artikel(
            artikelnummer=artikelnummer,
            name=name,
            beschreibung=beschreibung,
            bestand=bestand,
            mindestbestand=mindestbestand,
            einkaufspreis=einkaufspreis,
            lager_id=lager_id
        )
        
        db.session.add(artikel)
        db.session.commit()
        
        flash('Artikel erfolgreich angelegt.', 'success')
        return redirect(url_for('lager', lager_id=lager_id))
    
    lager_liste = Lager.query.filter_by(aktiv=True).order_by(Lager.name).all()
    if not lager_liste:
        flash('Bitte erstellen Sie zuerst ein Lager.', 'error')
        return redirect(url_for('lager_neu'))
    
    if not lager_id:
        lager_id = lager_liste[0].id
    
    return render_template('artikel_form.html', lager_liste=lager_liste, lager_id=lager_id)

@app.route('/artikel/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def artikel_bearbeiten(id):
    """Artikel bearbeiten"""
    artikel = Artikel.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        beschreibung = request.form.get('beschreibung', '')
        bestand = request.form.get('bestand', type=int) or 0
        mindestbestand = request.form.get('mindestbestand', type=int) or 0
        einkaufspreis = request.form.get('einkaufspreis')
        einkaufspreis = Decimal(einkaufspreis) if einkaufspreis else None
        lager_id = request.form.get('lager_id', type=int)
        
        artikel.name = name
        artikel.beschreibung = beschreibung
        artikel.bestand = bestand
        artikel.mindestbestand = mindestbestand
        artikel.einkaufspreis = einkaufspreis
        artikel.lager_id = lager_id
        db.session.commit()
        
        flash('Artikel erfolgreich aktualisiert.', 'success')
        return redirect(url_for('lager', lager_id=lager_id))
    
    lager_liste = Lager.query.filter_by(aktiv=True).order_by(Lager.name).all()
    return render_template('artikel_form.html', artikel=artikel, lager_liste=lager_liste, lager_id=artikel.lager_id)

@app.route('/artikel/<int:id>/loeschen', methods=['POST'])
@login_required
def artikel_loeschen(id):
    """Artikel löschen"""
    artikel = Artikel.query.get_or_404(id)
    lager_id = artikel.lager_id
    db.session.delete(artikel)
    db.session.commit()
    flash('Artikel erfolgreich gelöscht.', 'success')
    return redirect(url_for('lager', lager_id=lager_id))

@app.route('/gmail/sync', methods=['POST'])
@login_required
def gmail_sync():
    """Gmail-Synchronisation manuell auslösen"""
    try:
        # Gmail-Service initialisieren
        gmail_service = GmailService()
        
        # Explizit authentifizieren (wichtig im Web-Kontext)
        gmail_service._ensure_authenticated()
        
        # Prüfe ob Service initialisiert wurde
        if not gmail_service.service:
            app.logger.error("Gmail-Service konnte nicht initialisiert werden")
            # Debug-Info - prüfe auch absolute Pfade
            import os
            creds_path = app.config.get('GMAIL_CREDENTIALS_PATH', 'credentials/gmail_credentials.json')
            token_path = app.config.get('GMAIL_TOKEN_PATH', 'credentials/gmail_token.json')
            
            # Prüfe auch absolute Pfade
            abs_creds = '/opt/erp_tml/credentials/gmail_credentials.json'
            abs_token = '/opt/erp_tml/credentials/gmail_token.json'
            
            app.logger.error(f"Config Credentials-Pfad: {creds_path}, existiert: {os.path.exists(creds_path)}")
            app.logger.error(f"Config Token-Pfad: {token_path}, existiert: {os.path.exists(token_path)}")
            app.logger.error(f"Absoluter Credentials-Pfad: {abs_creds}, existiert: {os.path.exists(abs_creds)}")
            app.logger.error(f"Absoluter Token-Pfad: {abs_token}, existiert: {os.path.exists(abs_token)}")
            app.logger.error(f"App root_path: {app.root_path}")
            app.logger.error(f"Working directory: {os.getcwd()}")
            
            # Prüfe ob credentials-Verzeichnis existiert
            creds_dir = '/opt/erp_tml/credentials'
            app.logger.error(f"Credentials-Verzeichnis existiert: {os.path.exists(creds_dir)}")
            if os.path.exists(creds_dir):
                try:
                    files = os.listdir(creds_dir)
                    app.logger.error(f"Dateien im credentials-Verzeichnis: {files}")
                except Exception as e:
                    app.logger.error(f"Fehler beim Lesen des Verzeichnisses: {e}")
            
            flash('Gmail-Service konnte nicht initialisiert werden. Bitte prüfen Sie die Gmail-Credentials.', 'error')
            return redirect(url_for('index'))
        
        # Synchronisation durchführen
        anzahl = gmail_service.sync_rechnungen()
        
        if anzahl > 0:
            flash(f'{anzahl} neue Rechnungen wurden importiert.', 'success')
        else:
            flash('Keine neuen Rechnungen gefunden.', 'info')
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        # Log für Debugging (wird in Gunicorn-Logs sichtbar sein)
        app.logger.error(f"Gmail-Sync Fehler: {error_details}")
        flash(f'Fehler bei Gmail-Synchronisation: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/rechnungen/<path:filename>')
@login_required
def rechnungen(filename):
    """PDF-Dateien ausliefern"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== BENUTZER- UND ROLLENVERWALTUNG ====================

@app.route('/einstellungen/benutzer')
@login_required
def benutzer():
    """Benutzer-Übersicht"""
    try:
        if not current_user.hat_berechtigung('benutzer'):
            flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
            return redirect(url_for('index'))
        
        benutzer_liste = User.query.order_by(User.username).all()
        
        # Prüfe ob Rolle-Tabelle existiert
        try:
            rollen = Rolle.query.order_by(Rolle.name).all()
        except Exception as e:
            app.logger.error(f"Fehler beim Laden der Rollen: {e}")
            rollen = []
        
        # Berechtigungen für Template vorbereiten
        import json
        rollen_mit_berechtigungen = []
        for rolle in rollen:
            try:
                perms = json.loads(rolle.berechtigungen) if rolle.berechtigungen else {}
            except:
                perms = {}
            rollen_mit_berechtigungen.append((rolle, perms))
        
        return render_template('benutzer.html', benutzer_liste=benutzer_liste, rollen=rollen, rollen_mit_berechtigungen=rollen_mit_berechtigungen)
    except Exception as e:
        app.logger.error(f"Fehler in benutzer(): {e}")
        import traceback
        app.logger.error(traceback.format_exc())
        flash(f'Fehler beim Laden der Benutzerverwaltung: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/einstellungen/benutzer/neu', methods=['GET', 'POST'])
@login_required
def benutzer_neu():
    """Neuen Benutzer anlegen"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        rolle_id = request.form.get('rolle_id', type=int)
        aktiv = request.form.get('aktiv') == 'on'
        
        if User.query.filter_by(username=username).first():
            flash('Ein Benutzer mit diesem Namen existiert bereits.', 'error')
            return redirect(url_for('benutzer_neu'))
        
        user = User(
            username=username,
            rolle_id=rolle_id if rolle_id else None,
            aktiv=aktiv
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Benutzer erfolgreich angelegt.', 'success')
        return redirect(url_for('benutzer'))
    
    rollen = Rolle.query.order_by(Rolle.name).all()
    return render_template('benutzer_form.html', rollen=rollen)

@app.route('/einstellungen/benutzer/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def benutzer_bearbeiten(id):
    """Benutzer bearbeiten"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    
    # Admin kann nicht bearbeitet werden (außer Passwort)
    if user.username == 'admin' and current_user.username != 'admin':
        flash('Der Admin-Benutzer kann nicht bearbeitet werden.', 'error')
        return redirect(url_for('benutzer'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        rolle_id = request.form.get('rolle_id', type=int)
        aktiv = request.form.get('aktiv') == 'on'
        
        # Prüfen ob Username bereits existiert (außer aktuellem Benutzer)
        existing = User.query.filter_by(username=username).first()
        if existing and existing.id != id:
            flash('Ein Benutzer mit diesem Namen existiert bereits.', 'error')
            return redirect(url_for('benutzer_bearbeiten', id=id))
        
        user.username = username
        if password:
            user.set_password(password)
        user.rolle_id = rolle_id if rolle_id else None
        user.aktiv = aktiv
        db.session.commit()
        
        flash('Benutzer erfolgreich aktualisiert.', 'success')
        return redirect(url_for('benutzer'))
    
    rollen = Rolle.query.order_by(Rolle.name).all()
    return render_template('benutzer_form.html', user=user, rollen=rollen)

@app.route('/einstellungen/benutzer/<int:id>/loeschen', methods=['POST'])
@login_required
def benutzer_loeschen(id):
    """Benutzer löschen"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    
    # Admin kann nicht gelöscht werden
    if user.username == 'admin':
        flash('Der Admin-Benutzer kann nicht gelöscht werden.', 'error')
        return redirect(url_for('benutzer'))
    
    # Sich selbst kann man nicht löschen
    if user.id == current_user.id:
        flash('Sie können sich nicht selbst löschen.', 'error')
        return redirect(url_for('benutzer'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Benutzer erfolgreich gelöscht.', 'success')
    return redirect(url_for('benutzer'))

@app.route('/einstellungen/rollen')
@login_required
def rollen():
    """Rollen-Übersicht"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    rollen_liste = Rolle.query.order_by(Rolle.name).all()
    benutzer_liste = User.query.all()
    
    # Berechtigungen für Template vorbereiten
    import json
    rollen_mit_berechtigungen = []
    for rolle in rollen_liste:
        try:
            perms = json.loads(rolle.berechtigungen)
        except:
            perms = {}
        rollen_mit_berechtigungen.append((rolle, perms))
    
    return render_template('rollen.html', rollen_liste=rollen_liste, benutzer_liste=benutzer_liste, rollen_mit_berechtigungen=rollen_mit_berechtigungen)

@app.route('/einstellungen/rollen/neu', methods=['GET', 'POST'])
@login_required
def rollen_neu():
    """Neue Rolle anlegen"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        beschreibung = request.form.get('beschreibung', '')
        
        # Berechtigungen sammeln
        import json
        berechtigungen = {}
        for bereich in ['dashboard', 'einnahmen', 'ausgaben', 'lieferanten', 'lager', 'benutzer']:
            berechtigungen[bereich] = request.form.get(f'berechtigung_{bereich}') == 'on'
        
        if Rolle.query.filter_by(name=name).first():
            flash('Eine Rolle mit diesem Namen existiert bereits.', 'error')
            return redirect(url_for('rollen_neu'))
        
        rolle = Rolle(
            name=name,
            beschreibung=beschreibung,
            berechtigungen=json.dumps(berechtigungen)
        )
        
        db.session.add(rolle)
        db.session.commit()
        
        flash('Rolle erfolgreich angelegt.', 'success')
        return redirect(url_for('rollen'))
    
    return render_template('rollen_form.html')

@app.route('/einstellungen/rollen/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
def rollen_bearbeiten(id):
    """Rolle bearbeiten"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    rolle = Rolle.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        beschreibung = request.form.get('beschreibung', '')
        
        # Berechtigungen sammeln
        import json
        berechtigungen = {}
        for bereich in ['dashboard', 'einnahmen', 'ausgaben', 'lieferanten', 'lager', 'benutzer']:
            berechtigungen[bereich] = request.form.get(f'berechtigung_{bereich}') == 'on'
        
        # Prüfen ob Name bereits existiert (außer aktueller Rolle)
        existing = Rolle.query.filter_by(name=name).first()
        if existing and existing.id != id:
            flash('Eine Rolle mit diesem Namen existiert bereits.', 'error')
            return redirect(url_for('rollen_bearbeiten', id=id))
        
        rolle.name = name
        rolle.beschreibung = beschreibung
        rolle.berechtigungen = json.dumps(berechtigungen)
        db.session.commit()
        
        flash('Rolle erfolgreich aktualisiert.', 'success')
        return redirect(url_for('rollen'))
    
    # Berechtigungen für Template vorbereiten
    import json
    try:
        berechtigungen = json.loads(rolle.berechtigungen)
    except:
        berechtigungen = {}
    
    return render_template('rollen_form.html', rolle=rolle, berechtigungen=berechtigungen)

@app.route('/einstellungen/rollen/<int:id>/loeschen', methods=['POST'])
@login_required
def rollen_loeschen(id):
    """Rolle löschen"""
    if not current_user.hat_berechtigung('benutzer'):
        flash('Sie haben keine Berechtigung für diesen Bereich.', 'error')
        return redirect(url_for('index'))
    
    rolle = Rolle.query.get_or_404(id)
    
    # Prüfen ob Benutzer diese Rolle haben
    if User.query.filter_by(rolle_id=id).count() > 0:
        flash('Rolle kann nicht gelöscht werden, da noch Benutzer diese Rolle haben.', 'error')
        return redirect(url_for('rollen'))
    
    db.session.delete(rolle)
    db.session.commit()
    flash('Rolle erfolgreich gelöscht.', 'success')
    return redirect(url_for('rollen'))

# Initialisierung
def init_db():
    """Datenbank initialisieren"""
    with app.app_context():
        db.create_all()
        
        # Standard-Admin-Benutzer erstellen (falls nicht vorhanden)
        if User.query.count() == 0:
            admin = User(username='admin')
            admin.set_password('admin')  # Bitte in Produktion ändern!
            db.session.add(admin)
            db.session.commit()
            print("Standard-Admin erstellt: admin / admin")
            print("⚠️  BITTE SOFORT DAS PASSWORT ÄNDERN!")

if __name__ == '__main__':
    init_db()
    app.run(host=app.config['HOST'], port=app.config['PORT'], debug=True)

