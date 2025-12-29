from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Rolle(db.Model):
    """Rollen-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    beschreibung = db.Column(db.String(200), nullable=True)
    
    # Berechtigungen (als JSON-String gespeichert)
    berechtigungen = db.Column(db.Text, nullable=False, default='{}')  # JSON: {"dashboard": True, "einnahmen": True, ...}
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Beziehung zu Benutzern
    benutzer = db.relationship('User', backref='rolle', lazy=True)
    
    def __repr__(self):
        return f'<Rolle {self.name}>'
    
    def hat_berechtigung(self, bereich):
        """Prüft ob Rolle Berechtigung für einen Bereich hat"""
        import json
        try:
            perms = json.loads(self.berechtigungen)
            return perms.get(bereich, False)
        except:
            return False


class User(UserMixin, db.Model):
    """Benutzer-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rolle_id = db.Column(db.Integer, db.ForeignKey('rolle.id'), nullable=True)
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """Passwort hashen"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Passwort überprüfen"""
        return check_password_hash(self.password_hash, password)
    
    def hat_berechtigung(self, bereich):
        """Prüft ob Benutzer Berechtigung für einen Bereich hat"""
        # Admin hat immer alle Berechtigungen
        if self.username == 'admin':
            return True
        if not self.rolle or not self.aktiv:
            return False
        return self.rolle.hat_berechtigung(bereich)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Lieferant(db.Model):
    """Lieferant-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    gmail_label = db.Column(db.String(200), nullable=True)
    typ = db.Column(db.String(20), nullable=False)  # 'Einnahme' oder 'Ausgabe'
    aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Beziehungen
    buchungen = db.relationship('Buchung', backref='lieferant', lazy=True)
    
    def __repr__(self):
        return f'<Lieferant {self.name}>'


class Buchung(db.Model):
    """Buchung-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    typ = db.Column(db.String(20), nullable=False)  # 'Einnahme' oder 'Ausgabe'
    lieferant_id = db.Column(db.Integer, db.ForeignKey('lieferant.id'), nullable=True)
    betrag = db.Column(db.Numeric(10, 2), nullable=False)
    datum = db.Column(db.Date, nullable=False)
    rechnungsnummer = db.Column(db.String(100), nullable=True)
    titel = db.Column(db.String(500), nullable=True)
    pdf_pfad = db.Column(db.String(500), nullable=True)
    jahr = db.Column(db.Integer, nullable=False)
    quelle = db.Column(db.String(20), nullable=False, default='Manuell')  # 'Gmail' oder 'Manuell'
    gmail_message_id = db.Column(db.String(200), nullable=True)  # Zur Vermeidung von Duplikaten
    von_zielkonto_abgebucht = db.Column(db.Boolean, default=False, nullable=False)
    ueberwiesen_am = db.Column(db.Date, nullable=True)  # Datum der Überweisung (nur für Einnahmen)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Buchung {self.typ} {self.betrag} {self.datum}>'


class Lager(db.Model):
    """Lager-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    beschreibung = db.Column(db.String(500), nullable=True)
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Beziehung zu Artikeln
    artikel = db.relationship('Artikel', backref='lager', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Lager {self.name}>'


class Artikel(db.Model):
    """Artikel-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    artikelnummer = db.Column(db.String(50), nullable=False, unique=True)  # SKU
    name = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    bestand = db.Column(db.Integer, default=0, nullable=False)
    mindestbestand = db.Column(db.Integer, default=0, nullable=False)
    einkaufspreis = db.Column(db.Numeric(10, 2), nullable=True)
    lager_id = db.Column(db.Integer, db.ForeignKey('lager.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Artikel {self.artikelnummer} {self.name}>'
    
    def ist_niedrig(self):
        """Prüft ob Bestand unter Mindestbestand ist"""
        return self.bestand <= self.mindestbestand

