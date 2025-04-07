import pandas as pd
from flask import Flask
from db_config import db, DATABASE_URI
from models import SkolniRok

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def import_skolni_roky(file_path):
    """Importuje školní roky z Excelu do databáze."""
    with app.app_context():
        try:
            data = pd.read_excel(file_path, dtype=str)
            required_columns = ['Školní rok od', 'Školní rok do']

            if not all(col in data.columns for col in required_columns):
                print("❌ Chybí požadované sloupce v Excelu!")
                return
            
            for _, row in data.iterrows():
                rok_od = int(row['Školní rok od'])
                rok_do = int(row['Školní rok do'])

                existing_rok = SkolniRok.query.filter_by(rok_od=rok_od, rok_do=rok_do).first()
                if not existing_rok:
                    new_rok = SkolniRok(rok_od=rok_od, rok_do=rok_do)
                    db.session.add(new_rok)

            db.session.commit()
            print("✅ Import školních roků dokončen!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Chyba při importu školních roků: {e}")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        import_skolni_roky("skolni_roky.xlsx")
