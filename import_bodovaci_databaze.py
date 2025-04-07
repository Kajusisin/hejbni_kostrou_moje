import pandas as pd
import os
from flask import current_app as app  # ✅ Použití správného kontextu aplikace
from sqlalchemy import text  # ✅ Nutné pro správné spouštění SQL příkazů
from db_config import db
from models import Discipline, Score

# 🔹 Formátovací pravidla pro disciplíny
FORMATY_DISCIPLIN = {
    "Shyby na šikmé lavici za 2 min.": "int",
    "Kliky za 2 min.": "int",
    "Švihadlo za 2 min.": "int",
    "Jacík za 2 min.": "int",
    "Člunkový běh": "float",
    "Šplh": "float",
    "Skok z místa": "int",
    "Trojskok z místa": "int",
    "Hod medicinbalem": "float",
    "Hod kriketovým míčkem": "float",
    "Hod oštěpem": "float",
    "Vrh koulí": "float",
    "Skok daleký": "int",
    "Skok vysoký": "int",
    "Běh 60 m": "float",
    "Běh 100 m": "float",
    "Běh 150 m": "float",
    "Běh 300 m": "str",
    "Běh 600 m": "str",
    "Běh 800 m": "str",
    "Běh 1000 m": "str",
    "Běh 1500 m": "str",
    "Referát": "int",
    "Reprezentace školy": "int",
    "Cvičební úbor": "int",
    "Vedení rozcvičky": "int",
    "Aktivita mimo školu např. 'screen' běhu": "int",
    "Aktivní přístup, snaha": "int",
    "Zlepšení výkonu od posledního měření": "int",
    "Pomoc s organizací": "int",
    "Ostatní plusové body": "int",
    "Ostatní mínusové body": "int",
    "Bezpečnostní riziko (gumička, boty, …)": "int",
    "Nekázeň (rušení, neperespektování pokynů, …)": "int"
}

def convert_value(value, format_type):
    """Převede hodnotu výkonu na správný formát podle disciplíny."""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None  

    value = str(value).strip().replace(",", ".")

    if format_type == "float":
        return str(round(float(value), 2))  # ✅ Vrací string pro správné vyhledávání

    if format_type == "int":
        try:
            return str(int(float(value)))  # Převede na int a pak na string pro konzistenci
        except ValueError:
            print(f"⚠️ Chyba při konverzi hodnoty '{value}' na int")
            return "0"

    if format_type == "str":  # ✅ Opraveno z "text" na "str"
        parts = value.split(":")
        if len(parts) == 2:  # MM:SS
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"  
        elif len(parts) == 3:  # H:MM:SS → M:SS
            minutes = int(parts[0]) * 60 + int(parts[1])  
            return f"{minutes}:{int(parts[2]):02d}"
        else:
            raise ValueError(f"Neplatný časový formát: {value}")

    return value

def import_excel(file_path):
    """Načte bodovací databázi z Excelu a uloží do SQL databáze včetně jednotky a nápovědy."""
    try:
        with app.app_context():
            # Použití no_autoflush
            with db.session.no_autoflush:
                print(f"🚀 Spouštím import bodovací databáze...")

                if not os.path.exists(file_path):
                    print(f"❌ Chyba: Soubor {file_path} neexistuje!")
                    return

                df = pd.read_excel(file_path, dtype=str)  
                print(f"✅ Načteno {len(df)} řádků z Excelu.")

                db.session.execute(text("DELETE FROM score"))  # ✅ Opraveno pro SQLAlchemy 2.x
                db.session.commit()

                for index, row in df.iterrows():
                    try:
                        nazev_disciplíny = row.iloc[0].strip()  
                        vykon_hodnota = row.iloc[1].strip() if len(row) > 1 and pd.notna(row.iloc[1]) else None
                        body = int(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else None
                        jednotka = row.iloc[3].strip() if len(row) > 3 and pd.notna(row.iloc[3]) else "NEZADÁNO"
                        napoveda = row.iloc[4].strip() if len(row) > 4 and pd.notna(row.iloc[4]) else "NEZADÁNO"

                        if not nazev_disciplíny or vykon_hodnota is None or body is None:
                            print(f"⚠️ Přeskakuji řádek {index}: Chybějící data")
                            continue  

                        discipline = Discipline.query.filter_by(nazev=nazev_disciplíny).first()
                        if not discipline:
                            discipline = Discipline(nazev=nazev_disciplíny, jednotka=jednotka, napoveda=napoveda)
                            db.session.add(discipline)
                            db.session.commit()

                        format_type = FORMATY_DISCIPLIN.get(nazev_disciplíny, "float")
                        vykon_hodnota = convert_value(vykon_hodnota, format_type)

                        # ✅ Rozpoznání, zda se jedná o plusové nebo mínusové body
                        is_bonus = body > 0  # Bonusové body
                        is_penalty = body < 0  # Penalizační body

                        new_score = Score(discipline_id=discipline.id, vykon=str(vykon_hodnota).strip(), body=body)
                        db.session.add(new_score)

                    except Exception as e:
                        print(f"❌ Chyba při zpracování řádku {index}: {e}")

                db.session.commit()
                print("✅ Import bodovací databáze dokončen!")
                return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při importu bodovací databáze: {e}")
        return False

if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    
    # 🔹 Připojení k databázi
    from db_config import db, DATABASE_URI
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():  # ✅ Správný Flask kontext pro databázi
        import_excel("bodovaci_databaze.xlsx")
