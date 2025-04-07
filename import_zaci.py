from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import re
from db_config import db, DATABASE_URI
from models import Zak

# Inicializace Flask aplikace
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def import_zaci(soubor):
    try:
        with app.app_context():
            # Použití no_autoflush
            with db.session.no_autoflush:
                print(f"🚀 Spouštím import žáků z {soubor}...")
                # Načtení dat z Excelu
                df = pd.read_excel(soubor)
                
                # Zpracování každého žáka
                for index, row in df.iterrows():
                    jmeno = row['Jméno'].strip()
                    prijmeni = row['Příjmení'].strip()
                    
                    # Ošetření nepovinných hodnot s defaulty
                    cislo_tridy = int(row['Číslo třídy']) if pd.notna(row.get('Číslo třídy')) else None
                    # Zpracování písmena třídy bez tečky
                    pismeno_tridy = row['Písmeno třídy'].strip() if pd.notna(row.get('Písmeno třídy', '')) else None
                    # Zajištění, že písmeno třídy nezačíná tečkou
                    if pismeno_tridy and pismeno_tridy.startswith('.'):
                        pismeno_tridy = pismeno_tridy[1:]
                    pohlavi = row.get('Pohlaví', 'neuvedeno').strip().lower()
                    
                    # ✅ Ošetření chybějících sloupců
                    rok_nastupu_2_stupen = int(row['Rok nástupu na 2. stupeň']) if 'Rok nástupu na 2. stupeň' in row and pd.notna(row['Rok nástupu na 2. stupeň']) else None
                    
                    # ✅ Kontrola odchodu pro absolventy
                    skolni_rok_odchodu_od = int(row['Školní rok odchodu z 2. stupně od']) if 'Školní rok odchodu z 2. stupně od' in row and pd.notna(row.get('Školní rok odchodu z 2. stupně od')) else None
                    skolni_rok_odchodu_do = int(row['Školní rok odchodu z 2. stupně do']) if 'Školní rok odchodu z 2. stupně do' in row and pd.notna(row.get('Školní rok odchodu z 2. stupně do')) else None

                    # Pokud chybí rok nástupu, nelze zpracovat žáka
                    if rok_nastupu_2_stupen is None:
                        print(f"⚠️ Pro žáka {jmeno} {prijmeni} chybí rok nástupu - přeskakuji")
                        continue

                    # ✅ Ověření, zda žák už existuje
                    existing_zak = Zak.query.filter_by(jmeno=jmeno, prijmeni=prijmeni).first()
                    if existing_zak:
                        existing_zak.cislo_tridy = cislo_tridy
                        existing_zak.pismeno_tridy = pismeno_tridy
                        existing_zak.pohlavi = pohlavi
                        
                        # Aktualizujeme pouze hodnoty, které existují
                        if rok_nastupu_2_stupen is not None:
                            existing_zak.rok_nastupu_2_stupen = rok_nastupu_2_stupen
                        if skolni_rok_odchodu_od is not None:
                            existing_zak.skolni_rok_odchodu_od = skolni_rok_odchodu_od
                        if skolni_rok_odchodu_do is not None:
                            existing_zak.skolni_rok_odchodu_do = skolni_rok_odchodu_do
                    else:
                        new_zak = Zak(
                            jmeno=jmeno,
                            prijmeni=prijmeni,
                            cislo_tridy=cislo_tridy,
                            pismeno_tridy=pismeno_tridy,
                            pohlavi=pohlavi,
                            rok_nastupu_2_stupen=rok_nastupu_2_stupen,
                            skolni_rok_odchodu_od=skolni_rok_odchodu_od,
                            skolni_rok_odchodu_do=skolni_rok_odchodu_do
                        )
                        db.session.add(new_zak)

                # Commit na konec
                db.session.commit()
                print("✅ Import žáků dokončen!")
                return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při importu žáků: {e}")
        return False

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print(f"📊 Test databáze: Zak.query.first() = {Zak.query.first()}")
        import_zaci("zaci.xlsx")
