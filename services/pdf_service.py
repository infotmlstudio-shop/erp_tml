import pdfplumber
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

class PDFService:
    """PDF-Verarbeitung für Rechnungen"""
    
    def extract_invoice_data(self, pdf_path):
        """Rechnungsdaten aus PDF extrahieren"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Text aus allen Seiten extrahieren
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() or ""
                
                if not full_text:
                    return None
                
                # Daten extrahieren
                data = {
                    'betrag': self._extract_amount(full_text),
                    'datum': self._extract_date(full_text),
                    'rechnungsnummer': self._extract_invoice_number(full_text),
                    'titel': self._extract_title(full_text, pdf_path)
                }
                
                return data if data['betrag'] else None
                
        except Exception as e:
            print(f"Fehler bei PDF-Verarbeitung: {e}")
            return None
    
    def _extract_amount(self, text):
        """Betrag aus Text extrahieren"""
        # Verschiedene Muster für Beträge
        patterns = [
            # Spezielles Format: ##BETRAGBRUTTO=1744,36##
            r'##BETRAGBRUTTO=([\d.,]+)##',
            r'##BETRAGNETTO=([\d.,]+)##',
            # Standard-Muster
            r'(?:Summe|Gesamt|Total|Betrag|Endbetrag|Zu zahlen|Brutto|Netto)[\s:]*([\d.,]+)\s*€',
            r'([\d.,]+)\s*€\s*(?:inkl|MwSt|inkl\.|MwSt\.)',
            r'([\d.,]+)\s*EUR',
            r'([\d.,]+)\s*€',
            r'€\s*([\d.,]+)',
        ]
        
        # Suche nach größtem Betrag (wahrscheinlich Gesamtbetrag)
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Komma/Punkt als Dezimaltrenner behandeln
                    # Prüfen ob es ein deutsches Format ist (Komma als Dezimaltrenner)
                    if ',' in match and '.' in match:
                        # Format: 1.744,36 -> 1744.36
                        amount_str = match.replace('.', '').replace(',', '.')
                    elif ',' in match:
                        # Format: 1744,36 -> 1744.36
                        amount_str = match.replace(',', '.')
                    else:
                        # Format: 1744.36 oder 1744
                        amount_str = match
                    
                    amount = float(amount_str)
                    if amount > 0:
                        amounts.append(amount)
                except (ValueError, InvalidOperation):
                    continue
        
        if amounts:
            # Größten Betrag zurückgeben
            return max(amounts)
        
        return None
    
    def _extract_date(self, text):
        """Datum aus Text extrahieren"""
        # Verschiedene Datumsformate
        patterns = [
            r'(?:Rechnungsdatum|Datum|Date)[\s:]*(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})',
            r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})',
            r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if len(match) == 3:
                        if len(match[2]) == 4:  # YYYY-MM-DD oder DD.MM.YYYY
                            if int(match[0]) > 31:  # YYYY-MM-DD Format
                                year, month, day = int(match[0]), int(match[1]), int(match[2])
                            else:  # DD.MM.YYYY Format
                                day, month, year = int(match[0]), int(match[1]), int(match[2])
                        else:  # DD.MM.YY Format
                            day, month, year = int(match[0]), int(match[1]), int(match[2])
                            year = 2000 + year if year < 100 else year
                        
                        if 1 <= month <= 12 and 1 <= day <= 31:
                            return datetime(year, month, day).date()
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_invoice_number(self, text):
        """Rechnungsnummer extrahieren"""
        patterns = [
            # Belegnummer Format: "Belegnummer Datum Seite" gefolgt von Zahl
            r'Belegnummer\s+Datum\s+Seite\s*\n\s*(\d+)',
            # Belegnummer direkt gefolgt von Zahl
            r'Belegnummer\s+(\d+)',
            # Rechnungsnummer Format: "Rechnungsnummer" gefolgt von Nummer (nicht das Wort selbst!)
            r'Rechnungsnummer\s*[:]?\s*([A-Z0-9\-/]+)',
            r'Rechnungsnummer\s+([A-Z0-9\-/]+)',
            # Spezielles Format: INVOICE-4937130
            r'INVOICE[-/](\d+)',
            # Standard-Muster (nur wenn nicht "Rechnungsnummer" selbst)
            r'(?:Invoice|Nr\.?|No\.?)[\s:]*([A-Z0-9\-/]+)',
            r'#\s*([A-Z0-9\-/]+)',
            r'INV[-/]?([A-Z0-9\-/]+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                result = matches[0].strip()
                # Prüfen ob es nicht nur "Belegnummer", "Rechnungsnummer" oder ähnliches ist
                invalid = ['belegnummer', 'rechnung', 'rechnungsnummer', 'invoice', 'nr', 'no', 'template', 'debitoren', 'xml', 'nummer']
                if result.lower() not in invalid and len(result) > 2:
                    return result
        
        return None
    
    def _extract_title(self, text, pdf_path):
        """Titel/Bezeichnung extrahieren"""
        # Erste Zeile oder Rechnungstitel
        lines = text.split('\n')
        for line in lines[:10]:  # Erste 10 Zeilen prüfen
            line = line.strip()
            if line and len(line) > 5 and not line.isdigit():
                # Wenn "Rechnung" oder ähnliches enthalten
                if any(word in line.lower() for word in ['rechnung', 'invoice', 'bill']):
                    return line
        
        # Fallback: Dateiname
        import os
        return os.path.basename(pdf_path)

