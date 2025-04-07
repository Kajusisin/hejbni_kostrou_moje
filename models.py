from db_config import db
import re  # Pro správné zpracování třídy
from datetime import datetime  # Import pro nové modely

class SkolniRok(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rok_od = db.Column(db.Integer, nullable=False, unique=True)
    rok_do = db.Column(db.Integer, nullable=False, unique=True)
    aktualni = db.Column(db.Boolean, default=False)

    @staticmethod
    def nastav_aktualni_rok(rok_od):
        """Nastaví daný rok jako aktuální a ostatní deaktivuje."""
        try:
            db.session.query(SkolniRok).update({SkolniRok.aktualni: False})
            rok = SkolniRok.query.filter_by(rok_od=rok_od).first()
            if rok:
                rok.aktualni = True
                db.session.commit()
            else:
                print(f"❌ Chyba: Školní rok {rok_od} nebyl nalezen!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Chyba při aktualizaci školního roku: {e}")

    def __repr__(self):
        return f"<Školní rok {self.rok_od}/{self.rok_do} {'(aktuální)' if self.aktualni else ''}>"

class Zak(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jmeno = db.Column(db.String(50), nullable=False)
    prijmeni = db.Column(db.String(50), nullable=False)
    cislo_tridy = db.Column(db.Integer, nullable=True)  # ✅ Povolit NULL pro absolventy
    pismeno_tridy = db.Column(db.String(1), nullable=True)  # ✅ Povolit NULL pro absolventy
    pohlavi = db.Column(db.String(10), nullable=False)
    rok_nastupu_2_stupen = db.Column(db.Integer, nullable=False)
    skolni_rok_odchodu_od = db.Column(db.Integer, nullable=True)
    skolni_rok_odchodu_do = db.Column(db.Integer, nullable=True)
    aktualni_skolni_rok_od = db.Column(db.Integer, nullable=True, default=None)
    aktualni_skolni_rok_do = db.Column(db.Integer, nullable=True, default=None)

    def get_trida(self, skolni_rok):
        """Vrátí správnou třídu žáka podle školního roku."""
        # Zajištění konzistentního typu
        if isinstance(skolni_rok, str) and "/" in skolni_rok:
            skolni_rok = int(skolni_rok.split("/")[0])
        elif isinstance(skolni_rok, str):
            skolni_rok = int(skolni_rok)
            
        # Pokud chybí rok nástupu, nelze určit třídu
        if self.rok_nastupu_2_stupen is None:
            return "Neznámý"
            
        rocnik = skolni_rok - self.rok_nastupu_2_stupen + 6

        # Odstranění duplicitní tečky z pismeno_tridy
        pismeno = self.pismeno_tridy
        if pismeno and pismeno.startswith('.'):
            pismeno = pismeno[1:]  # Odstraní úvodní tečku

        if 6 <= rocnik <= 9:
            return f"{rocnik}.{pismeno}" if pismeno else f"{rocnik}"
        
        elif rocnik > 9:
            if self.skolni_rok_odchodu_od:
                return f"Absolvent 9.{pismeno} {self.skolni_rok_odchodu_od}"  # Upraveno - pouze rok odchodu
            else:
                return f"Absolvent 9.{pismeno}"

        elif rocnik < 6:
            return "Před nástupem"
        
        return "Neznámý"

    def get_skolni_rok_odchodu(self):
        """Vrátí školní rok odchodu ve formátu YYYY, pokud existuje."""
        if self.skolni_rok_odchodu_od:
            return f"{self.skolni_rok_odchodu_od}"  # Vrátí pouze první rok
        else:
            return "Neznámý"

    def __repr__(self):
        """Vrátí reprezentaci žáka s třídou pro debugging."""
        aktualni_rok = SkolniRok.query.filter_by(aktualni=True).first()
        trida = self.get_trida(aktualni_rok.rok_od) if aktualni_rok else "Neznámý"
        return f"<Zak {self.prijmeni} {self.jmeno} - {trida}>"

class Discipline(db.Model):
    __tablename__ = 'discipline'  # Explicitně nastavuji název tabulky
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(100), nullable=False)
    jednotka = db.Column(db.String(50))  
    napoveda = db.Column(db.String(255))  

    def __repr__(self):
        return f"<Disciplína {self.nazev}>"

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discipline_id = db.Column(db.Integer, db.ForeignKey('discipline.id'), nullable=False)
    vykon = db.Column(db.String(50), nullable=False)
    body = db.Column(db.Integer, nullable=False)

    discipline = db.relationship("Discipline", backref="scores")

    def __repr__(self):
        return f"<Výkon {self.vykon} ({self.body} bodů) - {self.discipline.nazev}>"

class StudentScore(db.Model):
    """Výkon studenta v dané disciplíně."""
    __tablename__ = 'student_scores'
    id = db.Column(db.Integer, primary_key=True)
    zak_id = db.Column(db.Integer, db.ForeignKey('zak.id'), nullable=False)
    discipline_id = db.Column(db.Integer, db.ForeignKey('discipline.id'), nullable=False)
    vykon = db.Column(db.String, nullable=False)
    body = db.Column(db.Integer, nullable=False)
    rocnik = db.Column(db.Integer, nullable=False)  # Ročník žáka (6-9)
    skolni_rok = db.Column(db.Integer, nullable=True)  # Školní rok (např. 2024 pro 2024/2025)
    
    # Vztahy k ostatním tabulkám - opraveno pro odstranění konfliktu
    zak = db.relationship('Zak', backref=db.backref('student_scores', lazy=True))
    
    # Upraveno - nepoužíváme backref, ale explicitní vztah
    discipline = db.relationship('Discipline')
    
    def __repr__(self):
        return f"<StudentScore {self.zak_id} - {self.discipline_id} - {self.rocnik}>"

# Nové modely pro odkazy a informace
class Odkaz(db.Model):
    __tablename__ = 'odkazy'
    
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    kategorie = db.Column(db.String(100), nullable=False)
    datum_vytvoreni = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Odkaz {self.nazev} ({self.kategorie})>"

class Informace(db.Model):
    __tablename__ = 'informace'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    datum = db.Column(db.String(20), nullable=False)  # Ve formátu DD.MM.YYYY
    datum_vytvoreni = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Informace {self.text[:20]}... ({self.datum})>"

class Soubor(db.Model):
    __tablename__ = 'soubory'
    
    id = db.Column(db.Integer, primary_key=True)
    nazev = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    velikost = db.Column(db.Integer)  # Velikost v bajtech
    typ_souboru = db.Column(db.String(50))  # Např. pdf, docx
    datum_nahrani = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f"<Soubor {self.nazev}>"

