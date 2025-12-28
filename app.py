from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Lieferant, Buchung
from config import Config
from datetime import datetime, date
from decimal import Decimal
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
            quelle='Manuell'
        )
        
        db.session.add(buchung)
        db.session.commit()
        
        flash('Einnahme erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('einnahmen', jahr=datum.year))
    
    return render_template('einnahmen_form.html', typ='Einnahme')

@app.route('/ausgaben')
@login_required
def ausgaben():
    """Ausgaben-Übersicht nach Lieferanten gruppiert"""
    jahr = request.args.get('jahr', type=int)
    if not jahr:
        current_year = datetime.now().year
        jahr = current_year if current_year >= 2025 else 2025
    
    # Alle aktiven Ausgaben-Lieferanten
    lieferanten = Lieferant.query.filter_by(typ='Ausgabe', aktiv=True).order_by(Lieferant.name).all()
    
    # Buchungen nach Lieferant gruppiert
    ausgaben_dict = {}
    for lieferant in lieferanten:
        buchungen = Buchung.query.filter(
            Buchung.typ == 'Ausgabe',
            Buchung.lieferant_id == lieferant.id,
            Buchung.jahr == jahr
        ).order_by(Buchung.datum.desc()).all()
        if buchungen:
            ausgaben_dict[lieferant] = buchungen
    
    # Buchungen ohne Lieferant
    buchungen_ohne_lieferant = Buchung.query.filter(
        Buchung.typ == 'Ausgabe',
        Buchung.lieferant_id.is_(None),
        Buchung.jahr == jahr
    ).order_by(Buchung.datum.desc()).all()
    
    if buchungen_ohne_lieferant:
        ausgaben_dict[None] = buchungen_ohne_lieferant
    
    # Jahre für Dropdown
    current_year = datetime.now().year
    start_year = 2025
    end_year = current_year + 2
    jahre = list(range(start_year, end_year + 1))
    
    return render_template('ausgaben.html', ausgaben_dict=ausgaben_dict, jahr=jahr, jahre=jahre)

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
        
        buchung = Buchung(
            typ='Ausgabe',
            lieferant_id=lieferant_id,
            betrag=betrag,
            datum=datum,
            rechnungsnummer=rechnungsnummer,
            titel=titel,
            pdf_pfad=pdf_pfad,
            jahr=datum.year,
            quelle='Manuell'
        )
        
        db.session.add(buchung)
        db.session.commit()
        
        flash('Ausgabe erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('ausgaben', jahr=datum.year))
    
    return render_template('ausgaben_form.html', typ='Ausgabe', lieferanten=lieferanten)

@app.route('/einstellungen/lieferanten')
@login_required
def lieferanten():
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

