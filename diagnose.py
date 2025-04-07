import socket
import os
import sys
import traceback
import subprocess

def check_port(port):
    """Zjistí, zda je port 5000 volný."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0  # True pokud je port volný

def check_flask_app():
    """Kontrola Flask aplikace."""
    try:
        from flask import Flask
        print("✅ Flask je nainstalován.")
        
        import flask_sqlalchemy
        print("✅ Flask-SQLAlchemy je nainstalován.")
        
        # Kontrola session settings
        if os.path.exists('hejbni_kostrou.py'):
            with open('hejbni_kostrou.py', 'r', encoding='utf-8') as f:
                content = f.read()
                if "app.config['SESSION_TYPE']" not in content:
                    print("❌ Chybí nastavení SESSION_TYPE v konfiguraci.")
                    print("Přidejte: app.config['SESSION_TYPE'] = 'filesystem'")
                else:
                    print("✅ SESSION_TYPE je nakonfigurován.")
                
                if "flask.session" in content or "from flask import session" in content:
                    print("✅ Session je používán v aplikaci.")
        
        return True
    except ImportError as e:
        print(f"❌ Chybí modul: {str(e)}")
        return False

def check_uploads_folder():
    """Kontrola složky pro uploads."""
    uploads_path = os.path.join('static', 'uploads')
    if not os.path.exists(uploads_path):
        print(f"❌ Složka {uploads_path} neexistuje. Vytvářím...")
        os.makedirs(uploads_path)
        print(f"✅ Složka {uploads_path} vytvořena.")
    else:
        print(f"✅ Složka {uploads_path} existuje.")
    
    return True

def check_templates():
    """Kontrola šablon, zejména odkazy_a_informace.html."""
    templates_path = 'templates'
    if not os.path.exists(templates_path):
        print(f"❌ Složka {templates_path} neexistuje!")
        return False
    
    odkazy_file = os.path.join(templates_path, 'odkazy_a_informace.html')
    if not os.path.exists(odkazy_file):
        print(f"❌ Soubor {odkazy_file} neexistuje!")
        return False
    
    print(f"✅ Šablona odkazy_a_informace.html existuje.")
    
    # Kontrola modálních oken v šabloně
    with open(odkazy_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'class="modal"' in content:
            print("✅ Modální okna nalezena v šabloně.")
            
            # Kontrola správných ID a funkcí
            modal_ids = ["odkazModal", "infoModal", "souborModal"]
            for modal_id in modal_ids:
                if modal_id in content:
                    print(f"✅ Modální okno {modal_id} nalezeno.")
                else:
                    print(f"❌ Modální okno {modal_id} chybí.")
            
            # Kontrola JavaScript funkcí pro modální okna
            if 'addEventListener("click"' in content or "addEventListener('click'" in content:
                print("✅ Event listenery pro tlačítka nalezeny.")
            else:
                print("❌ Event listenery pro tlačítka chybí.")
        else:
            print("❌ Modální okna nebyla nalezena v šabloně.")
    
    return True

def main():
    """Hlavní diagnostická funkce."""
    print("\n🔍 DIAGNOSTIKA APLIKACE HEJBNI KOSTROU")
    print("======================================\n")
    
    # 1. Kontrola portů
    print("1️⃣ Kontrola dostupnosti portu 5000...")
    if check_port(5000):
        print("✅ Port 5000 je volný.")
    else:
        print("❌ Port 5000 je obsazen jinou aplikací.")
    print()
    
    # 2. Kontrola Flask aplikace
    print("2️⃣ Kontrola Flask konfigurace...")
    check_flask_app()
    print()
    
    # 3. Kontrola složky uploads
    print("3️⃣ Kontrola složky uploads...")
    check_uploads_folder()
    print()
    
    # 4. Kontrola šablon
    print("4️⃣ Kontrola šablon...")
    check_templates()
    print()
    
    print("\n🛠️ DOPORUČENÉ OPRAVY:")
    print("""
1. Přidejte do hejbni_kostrou.py na začátek funkce main:
   print("🚀 Spouštím aplikaci Hejbni kostrou na http://127.0.0.1:5000")
   
2. Opravte modální okna v templates/odkazy_a_informace.html

3. Přidejte nastavení SESSION_TYPE, pokud chybí:
   app.config['SESSION_TYPE'] = 'filesystem'
   
4. Přidejte do if __name__ == "__main__": bloku:
   app.run(debug=True, host='127.0.0.1', port=5000)
""")

if __name__ == "__main__":
    main()