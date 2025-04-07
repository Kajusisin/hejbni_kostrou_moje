import sqlite3
import os

def fix_database():
    """Sladí databázovou strukturu s modely."""
    # Cesta k SQLite databázi
    db_path = "instance/hejbni_kostrou.db"  # Výchozí cesta pro Flask
    
    # Kontrola existence souboru
    if not os.path.exists(db_path):
        print(f"❌ Databáze nenalezena na cestě: {db_path}")
        # Hledání souboru .db v aktuálním adresáři
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        if db_files:
            db_path = db_files[0]
            print(f"✅ Nalezena alternativní databáze: {db_path}")
        else:
            if os.path.exists('./instance'):
                db_files = [f for f in os.listdir('./instance') if f.endswith('.db')]
                if db_files:
                    db_path = f"instance/{db_files[0]}"
                    print(f"✅ Nalezena alternativní databáze v instance/: {db_path}")
                else:
                    print("❌ Nebyla nalezena žádná SQLite databáze (.db soubor)")
                    return
            else:
                print("❌ Složka instance neexistuje a nebyla nalezena žádná databáze")
                return
    
    print(f"🔄 Připojuji se k databázi: {db_path}")
    
    try:
        # Připojení k databázi
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Kontrola sloupců v tabulce 'discipline'
        cursor.execute("PRAGMA table_info(discipline)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Sloupce, které by měly být v tabulce
        expected_columns = ['id', 'nazev', 'jednotka', 'napoveda']
        
        # Kontrola chybějících sloupců
        missing_columns = [col for col in expected_columns if col not in column_names]
        if missing_columns:
            for col in missing_columns:
                print(f"➕ Přidávám chybějící sloupec '{col}' do tabulky 'discipline'...")
                col_type = "TEXT" if col != 'id' else "INTEGER"
                cursor.execute(f"ALTER TABLE discipline ADD COLUMN {col} {col_type}")
            conn.commit()
            print(f"✅ Přidány chybějící sloupce: {', '.join(missing_columns)}")
        
        # Kontrola nadbytečných sloupců
        extra_columns = [col for col in column_names if col not in expected_columns and col != 'popis']
        if 'popis' in column_names:
            print("ℹ️ Sloupec 'popis' nalezen v databázi, ale není v modelu - ignoruji ho.")
        
        if extra_columns:
            print(f"⚠️ Nadbytečné sloupce v tabulce 'discipline': {', '.join(extra_columns)}")
            print("   SQLite neumožňuje odebrat sloupce - ignoruji tyto sloupce.")
        
        # 2. Kontrola sloupce 'skolni_rok' v tabulce 'student_scores'
        cursor.execute("PRAGMA table_info(student_scores)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'skolni_rok' not in column_names:
            print("➕ Přidávám sloupec 'skolni_rok' do tabulky 'student_scores'...")
            cursor.execute("ALTER TABLE student_scores ADD COLUMN skolni_rok INTEGER")
            
            # Výchozí hodnota pro stávající záznamy
            import datetime
            current_year = datetime.datetime.now().year
            skolni_rok = current_year if datetime.datetime.now().month >= 9 else current_year - 1
            
            cursor.execute(f"UPDATE student_scores SET skolni_rok = {skolni_rok}")
            conn.commit()
            print(f"✅ Sloupec 'skolni_rok' byl přidán a nastaven na {skolni_rok} pro všechny záznamy.")
        else:
            print("✅ Sloupec 'skolni_rok' již existuje v tabulce 'student_scores'.")
        
        # 3. Výpis struktury tabulky 'discipline' pro ověření
        cursor.execute("PRAGMA table_info(discipline)")
        columns = cursor.fetchall()
        print("\n📋 Aktuální struktura tabulky 'discipline':")
        for col in columns:
            print(f"  - {col[1]} ({col[2]}){' (PRIMARY KEY)' if col[5] > 0 else ''}")
        
        conn.close()
        print("\n✅ Oprava databáze dokončena!")
        
    except Exception as e:
        print(f"❌ Chyba při úpravě databáze: {e}")

if __name__ == "__main__":
    fix_database()