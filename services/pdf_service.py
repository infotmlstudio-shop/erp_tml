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
                
                if not full_text or len(full_text.strip()) < 10:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"PDF enthält keinen oder zu wenig Text: {pdf_path}")
                    return None
                
                # Daten extrahieren
                betrag = self._extract_amount(full_text)
                datum = self._extract_date(full_text)
                rechnungsnummer = self._extract_invoice_number(full_text)
                titel = self._extract_title(full_text, pdf_path)
                
                data = {
                    'betrag': betrag,
                    'datum': datum,
                    'rechnungsnummer': rechnungsnummer,
                    'titel': titel
                }
                
                # Logging für Debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"PDF-Analyse: Betrag={betrag}, Datum={datum}, Rechnungsnummer={rechnungsnummer}, Titel={titel}")
                
                # Wenn kein Betrag gefunden, zeige ersten 500 Zeichen des Textes für Debugging
                if not betrag:
                    logger.warning(f"PDF-Analyse: Kein Betrag gefunden. Erste 500 Zeichen: {full_text[:500]}")
                    # Suche auch nach "Gesamt", "Total" etc. im Text
                    import re
                    gesamt_matches = re.findall(r'(?:Gesamt|Total|Summe|Totaal|Endbetrag)[\s:]*([\d.,]+)', full_text, re.IGNORECASE)
                    if gesamt_matches:
                        logger.warning(f"PDF-Analyse: Gefundene 'Gesamt/Total' Matches: {gesamt_matches}")
                
                return data if data['betrag'] else None
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Fehler bei PDF-Verarbeitung: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_amount(self, text):
        """Betrag aus Text extrahieren"""
        # Verschiedene Muster für Beträge
        patterns = [
            # Spezielles Format: ##BETRAGBRUTTO=1744,36##
            r'##BETRAGBRUTTO=([\d.,]+)##',
            r'##BETRAGNETTO=([\d.,]+)##',
            # Standard-Muster mit € Symbol
            r'(?:Summe|Gesamt|Total|Betrag|Endbetrag|Zu zahlen|Brutto|Netto|Totaal|Totaalbedrag)[\s:]*([\d.,]+)\s*€',
            r'([\d.,]+)\s*€\s*(?:inkl|MwSt|inkl\.|MwSt\.|BTW)',
            r'([\d.,]+)\s*EUR',
            r'([\d.,]+)\s*€',
            r'€\s*([\d.,]+)',
            # Weitere Muster für verschiedene Formate
            r'(?:Amount|Total|Sum|Price|Totaal)[\s:]*([\d.,]+)',
            r'([\d.,]+)\s*(?:EUR|€|Euro)',
            # Muster ohne Währungssymbol (nur wenn nach "Gesamt", "Total" etc.)
            r'(?:Gesamt|Total|Summe|Totaal|Endbetrag|Zu zahlen)[\s:]*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            # Zahlen mit Tausender-Trennzeichen am Ende (wahrscheinlich Gesamtbetrag)
            r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*(?:€|EUR|Euro|BTW|inkl\.|MwSt)',
        ]
        
        # Suche nach größtem Betrag (wahrscheinlich Gesamtbetrag)
        amounts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
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
                    # Nur Beträge > 0 und < 1 Million akzeptieren (realistische Rechnungsbeträge)
                    if 0 < amount < 1000000:
                        amounts.append(amount)
                except (ValueError, InvalidOperation):
                    continue
        
        if amounts:
            # Größten Betrag zurückgeben (wahrscheinlich Gesamtbetrag)
            return max(amounts)
        
        # Fallback: Suche nach großen Zahlen am Ende des Textes (oft Gesamtbetrag)
        # Suche nach Zahlen mit 2 Dezimalstellen am Ende
        fallback_patterns = [
            r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*$',  # Am Ende der Zeile
            r'([\d]{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*\n',  # Vor Zeilenumbruch
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                try:
                    if ',' in match and '.' in match:
                        amount_str = match.replace('.', '').replace(',', '.')
                    elif ',' in match:
                        amount_str = match.replace(',', '.')
                    else:
                        amount_str = match
                    
                    amount = float(amount_str)
                    if 1 <= amount < 1000000:  # Mindestens 1 EUR
                        amounts.append(amount)
                except (ValueError, InvalidOperation):
                    continue
        
        if amounts:
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
            # Wichtig: Muss mit Zahl oder Buchstabe-Zahl-Kombination beginnen, nicht mit "Rechnungsdatum"
            # Pattern: "Rechnungsnummer" gefolgt von Leerzeichen/Doppelpunkt, dann Nummer (nicht "Rechnungsdatum"!)
            # Format für Ralateam: "Rechnungsnummer Rechnungsdatum Zahlungsziel" - Rechnungsnummer steht in der nächsten Zeile
            r'Rechnungsnummer\s+Rechnungsdatum\s+Zahlungsziel\s*\n\s*(\d+)',  # Format: Rechnungsnummer Rechnungsdatum Zahlungsziel\n999901690
            r'Rechnungsnummer\s*[:]?\s+([A-Z0-9][A-Z0-9\-/]*)',  # Mindestens ein Leerzeichen nach "Rechnungsnummer"
            r'Rechnungsnummer\s*:\s*([A-Z0-9][A-Z0-9\-/]*)',  # Mit Doppelpunkt
            # Format für Ralateam: "Rechnungsnummer OP/I051733" oder "999901690"
            r'Rechnungsnummer\s+([A-Z0-9][A-Z0-9\-/]+)',  # Mindestens 2 Zeichen
            # Spezielles Format: INVOICE-4937130 oder OP/I051733
            r'INVOICE[-/](\d+)',
            r'OP[/]?([A-Z0-9\-/]+)',  # Format: OP/I051733
            # Standard-Muster (nur wenn nicht "Rechnungsnummer" selbst)
            r'(?:Invoice|Nr\.?|No\.?)[\s:]*([A-Z0-9][A-Z0-9\-/]*)',
            r'#\s*([A-Z0-9][A-Z0-9\-/]*)',
            r'INV[-/]?([A-Z0-9][A-Z0-9\-/]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                result = matches[0].strip()
                # Prüfen ob es nicht nur "Belegnummer", "Rechnungsnummer", "Rechnungsdatum" oder ähnliches ist
                invalid = ['belegnummer', 'rechnung', 'rechnungsnummer', 'rechnungsdatum', 'zahlungsziel', 'datum', 'invoice', 'nr', 'no', 'template', 'debitoren', 'xml', 'nummer', 'seite']
                if result.lower() not in invalid and len(result) > 2:
                    # Prüfe auch, ob es nicht mit "rechnungs" beginnt
                    if not result.lower().startswith('rechnungs'):
                        # Prüfe ob es eine Zahl enthält (Rechnungsnummern enthalten meist Zahlen)
                        if any(char.isdigit() for char in result):
                            return result
                        # Oder wenn es ein Format wie "OP/I051733" ist
                        if '/' in result and any(char.isdigit() for char in result):
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

