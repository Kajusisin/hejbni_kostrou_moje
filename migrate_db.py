from hejbni_kostrou import app, db
from models import StudentScore
import datetime

def add_skolni_rok_column():
    """Přidá sloupec skolni_rok do tabulky student_scores, pokud neexistuje."""
    with app.app_context():
        # Kontrola, zda sloupec už existuje
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('student_scores')]
        
        if 'skolni_rok' not in columns:
            print("💡 Přidávám sloupec 'skolni_rok' do tabulky student_scores...")
            
            # Získání aktuálního školního roku
            current_year = datetime.datetime.now().year
            current_month = datetime.datetime.now().month
            skolni_rok = current_year if current_month >= 9 else current_year - 1
            
            # Přidání sloupce
            db.engine.execute('ALTER TABLE student_scores ADD COLUMN skolni_rok INTEGER')
            
            # Aktualizace existujících záznamů
            db.engine.execute(f'UPDATE student_scores SET skolni_rok = {skolni_rok}')
            
            print(f"✅ Sloupec 'skolni_rok' přidán a nastaven na {skolni_rok}")
        else:
            print("✅ Sloupec 'skolni_rok' již existuje v tabulce student_scores")

if __name__ == "__main__":
    add_skolni_rok_column()