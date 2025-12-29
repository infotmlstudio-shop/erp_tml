from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Benutzer-Modell"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Passwort hashen"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Passwort überprüfen"""
        return check_password_hash(self.password_hash, password)
    
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

