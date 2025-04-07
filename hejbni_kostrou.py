from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from db_config import db, DATABASE_URI
from models import Zak, Discipline, Score, StudentScore, SkolniRok, Odkaz, Informace, Soubor
from import_zaci import import_zaci
from import_skolni_roky import import_skolni_roky
from import_bodovaci_databaze import import_excel, FORMATY_DISCIPLIN, convert_value
import pandas as pd
import os
import re
from dotenv import load_dotenv
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy.sql import func
from sqlalchemy import desc, asc, and_, or_
import logging
import os
from logging.handlers import RotatingFileHandler

# ✅ Načtení bezpečných proměnných
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'  
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'png', 'jpg', 'jpeg', 'gif', 'xlsx', 'pptx', 'txt', 'csv', 'zip', 'rar', 'mp4', 'mp3'}
app.secret_key = os.getenv("SECRET_KEY", "tajnyklic")  # 🔑 Použití bezpečnějšího způsobu

# Přidejte toto po inicializaci aplikace (před app.config['UPLOAD_FOLDER'])
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.getenv("SECRET_KEY", "hejbni_kostrou_secret_key")

# Vytvoření adresáře pro uploady, pokud neexistuje
uploads_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
    print(f"✅ Vytvořena složka pro nahrávání souborů: {uploads_dir}")

# Inicializace databáze a migrací
db.init_app(app)
migrate = Migrate(app, db)

# ✅ Funkce pro povolené formáty souborů
def allowed_file(filename):
    """Ověří, zda má soubor povolenou příponu a neobsahuje neplatné znaky."""
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Nastavení loggeru
def setup_logger():
    log_dir = os.path.join(app.root_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'app.log')
    handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=5)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    app.logger.info('Aplikace spuštěna')

# Zavolat tuto funkci po vytvoření aplikace
setup_logger()

@app.route("/")
def home():
    skolni_roky = SkolniRok.query.order_by(SkolniRok.rok_od.asc()).all()
    if not skolni_roky:
        flash("❌ Žádné školní roky nejsou dostupné v databázi!", "warning")
    return render_template("home.html", skolni_roky=skolni_roky)

@app.route('/tridy')
def zobraz_tridy():
    """Zobrazení seznamu všech tříd."""
    try:
        # Načtení aktuálního školního roku
        vybrany_skolni_rok = session.get('vybrany_skolni_rok_od', datetime.now().year)
        
        # Převod na int, pokud je to rok ve formátu 2023/2024
        if isinstance(vybrany_skolni_rok, str) and "/" in vybrany_skolni_rok:
            vybrany_skolni_rok = int(vybrany_skolni_rok.split("/")[0])
        
        # Získání všech žáků
        vsichni_zaci = Zak.query.all()
        
        # Slovníky pro aktivní třídy a absolventy
        aktivni_tridy = {}  # {(cislo, pismeno): pocet_zaku}
        absolventi_tridy = {}  # {(cislo, pismeno, rok_odchodu): pocet_zaku}
        
        # Procházení všech žáků
        for zak in vsichni_zaci:
            rocnik = vybrany_skolni_rok - zak.rok_nastupu_2_stupen + 6
            
            # Aktivní žáci (6. - 9. třída)
            if 6 <= rocnik <= 9:
                pismeno = zak.pismeno_tridy
                if pismeno and pismeno.startswith('.'):
                    pismeno = pismeno[1:]
                    
                tridni_klic = (rocnik, pismeno)
                if tridni_klic not in aktivni_tridy:
                    aktivni_tridy[tridni_klic] = 0
                aktivni_tridy[tridni_klic] += 1
            
            # Absolventi (opustili už školu)
            elif rocnik > 9 and zak.skolni_rok_odchodu_od:
                pismeno = zak.pismeno_tridy
                if pismeno and pismeno.startswith('.'):
                    pismeno = pismeno[1:]
                    
                absolventi_klic = (9, pismeno, zak.skolni_rok_odchodu_od)
                if absolventi_klic not in absolventi_tridy:
                    absolventi_tridy[absolventi_klic] = 0
                absolventi_tridy[absolventi_klic] += 1
        
        # Seřazení tříd
        tridni_seznam = sorted(aktivni_tridy.items(), key=lambda x: (x[0][0], x[0][1]))
        absolventi_seznam = sorted(absolventi_tridy.items(), key=lambda x: (-x[0][2], x[0][1]))  # Sestupně podle roku
        
        return render_template(
            'trida.html', 
            tridni_seznam=[(t[0][0], t[0][1], t[1]) for t in tridni_seznam],
            absolventi_tridy=[(a[0][0], a[0][1], a[0][2], a[1]) for a in absolventi_seznam],
            vybrany_rok=vybrany_skolni_rok
        )
        
    except Exception as e:
        print(f"❌ Chyba při zobrazení tříd: {e}")
        return render_template('error.html', error=str(e))

# Přidejte tuto route pro zpětnou kompatibilitu
@app.route("/zobraz_tridy")
def zobraz_tridy_alt():
    """Alternativní cesta pro zobrazení tříd."""
    return redirect(url_for("zobraz_tridy"))

@app.route("/detail_tridy/<int:cislo>/<string:pismeno>")
@app.route("/detail_tridy/<int:cislo>/<string:pismeno>/<int:rok>")
@app.route("/detail_tridy/<int:cislo>/<string:pismeno>/<int:rok>/<int:absolvent_rok>")
def detail_tridy(cislo, pismeno, rok=None, absolvent_rok=None):
    """Zobrazí detail konkrétní třídy včetně seznamu žáků."""
    try:
        # Zpracování roku - pokud není zadán, použijeme aktuální školní rok
        if rok is None:
            rok = session.get('vybrany_skolni_rok_od', datetime.now().year)
            
        # Převod na int, pokud je to rok ve formátu 2023/2024
        if isinstance(rok, str) and "/" in rok:
            rok = int(rok.split("/")[0])
            
        rok = int(rok)  # Zajistíme, že rok je int
        
        # Zobrazované písmeno (pro případ, že by v URL mělo tečku)
        zobrazene_pismeno = pismeno
        if zobrazene_pismeno.startswith('.'):
            zobrazene_pismeno = zobrazene_pismeno[1:]
        
        # Standardně zobrazujeme žáky v dané třídě pro tento školní rok
        if not absolvent_rok:
            # Výpočet roku nástupu
            rok_nastupu = rok - cislo + 6
            
            # Načtení žáků, kteří jsou v této třídě
            zaci = Zak.query.filter(
                Zak.rok_nastupu_2_stupen == rok_nastupu
            ).all()
            
            # Dodatečné filtrování podle písmena třídy
            zaci_filtrovani = []
            for zak in zaci:
                zak_pismeno = zak.pismeno_tridy
                if zak_pismeno and zak_pismeno.startswith('.'):
                    zak_pismeno = zak_pismeno[1:]
                
                if zak_pismeno == zobrazene_pismeno:
                    zaci_filtrovani.append(zak)
            
            zaci = zaci_filtrovani
            
            # Název třídy
            trida_nazev = f"{cislo}.{zobrazene_pismeno}"
        
        # Pro absolventy zobrazíme žáky, kteří odešli v daném roce
        else:
            # Převod formátu absolventského roku
            if isinstance(absolvent_rok, str) and "/" in absolvent_rok:
                absolvent_rok = int(absolvent_rok.split("/")[0])
            else:
                absolvent_rok = int(absolvent_rok)
            
            # Načtení žáků, kteří absolvovali v daném roce
            zaci = Zak.query.filter(
                Zak.skolni_rok_odchodu_od == absolvent_rok
            ).all()
            
            # Dodatečné filtrování podle písmena třídy
            zaci_filtrovani = []
            for zak in zaci:
                zak_pismeno = zak.pismeno_tridy
                if zak_pismeno and zak_pismeno.startswith('.'):
                    zak_pismeno = zak_pismeno[1:]
                
                if zak_pismeno == zobrazene_pismeno:
                    zaci_filtrovani.append(zak)
            
            zaci = zaci_filtrovani
            
            trida_nazev = f"9.{zobrazene_pismeno} - Absolventi {absolvent_rok}"  # Upraveno - pouze rok
        
        # Řazení žáků podle příjmení a jména
        zaci.sort(key=lambda x: (x.prijmeni, x.jmeno))
        
        # Rozdělení žáků na chlapce a dívky pro lepší zobrazení
        # Vylepšená logika pro správné rozpoznání pohlaví
        chlapci = []
        divky = []
        
        for z in zaci:
            # Pokud pohlavi je None, použijeme bezpečnou hodnotu
            pohlaví = z.pohlavi.lower() if z.pohlavi else ""
            
            # Kontrola všech možných hodnot pro chlapce
            if pohlaví in ["chlapec", "hoch", "muž", "m", "male", "boy", "kluk"]:
                chlapci.append(z)
            # Kontrola všech možných hodnot pro dívky
            elif pohlaví in ["divka", "dívka", "f", "female", "dievča", "girl", "holka", "žena"]:
                divky.append(z)
            else:
                # Pro nejasné případy, použijeme defaultní zařazení (např. podle jména)
                # Alternativně můžeme přidat do logů a upozornit na problém
                print(f"❗ Nerozpoznáno pohlaví '{z.pohlavi}' u žáka {z.jmeno} {z.prijmeni}")
                
                # Jednoduchá heuristika - pokud jméno končí na 'a', pravděpodobně jde o dívku
                if z.jmeno.lower().endswith("a"):
                    divky.append(z)
                else:
                    chlapci.append(z)
        
        # Předáme vybrany_rok do šablony pro správné zobrazení
        vybrany_rok = rok
        
        # Debug log pro kontrolu počtů
        print(f"🔍 Třída {cislo}.{zobrazene_pismeno}: celkem {len(zaci)} žáků, {len(chlapci)} chlapců, {len(divky)} dívek")
        
        return render_template(
            'detail_tridy.html', 
            trida_nazev=trida_nazev,
            zaci=zaci,
            chlapci=chlapci,  # Přidáno pro přehledné zobrazení
            divky=divky,      # Přidáno pro přehledné zobrazení
            cislo=cislo,
            pismeno=zobrazene_pismeno,
            absolventi=(absolvent_rok is not None),
            rok_odchodu=absolvent_rok,
            vybrany_rok=vybrany_rok  # Toto je důležité - předáváme proměnnou do šablony
        )
    
    except Exception as e:
        print(f"❌ Chyba při zobrazení detailu třídy: {e}")
        return render_template('error.html', error=str(e))

@app.route('/detail_tridy_alt/<int:cislo>/<string:pismeno>/<int:rok>', methods=['GET'])
def detail_tridy_alt(cislo, pismeno, rok=None):
    try:
        # Pokud není rok specifikován v URL, použijeme aktuální rok ze session
        vybrany_rok = session.get('skolni_rok') if rok is None else f"{rok}/{rok+1}"
        
        # Použijeme existující detail_tridy funkci
        return detail_tridy(cislo, pismeno, rok)
    except Exception as e:
        app.logger.error(f"❌ Chyba při zobrazení detailu třídy: {str(e)}")
        return render_template('error.html', message=f"Chyba při zobrazení detailu třídy: {str(e)}")

@app.route("/zmen_skolni_rok", methods=["POST"])
def zmen_skolni_rok():
    """Změní aktuální školní rok a přesune žáky do správných tříd."""
    data = request.get_json()
    print(f"🟡 Přijatá data: {data}")  

    novy_rok = data.get("rok")
    if not novy_rok:
        return jsonify({"error": "❌ Nebyl zadán žádný rok!"}), 400

    try:
        rok_od = int(novy_rok.split("/")[0])
        rok_do = int(novy_rok.split("/")[1]) if "/" in novy_rok else rok_od + 1
    except ValueError:
        return jsonify({"error": "❌ Neplatný formát roku!"}), 400

    # ✅ Nastavení roku do session pro použití na dalších stránkách
    # Toto je klíčové pro správné fungování stránky trida.html
    session['vybrany_skolni_rok_od'] = rok_od
    session['vybrany_skolni_rok_do'] = rok_do

    skolni_rok = SkolniRok.query.filter_by(rok_od=rok_od).first()
    if not skolni_rok:
        return jsonify({"error": f"❌ Školní rok {novy_rok} nebyl nalezen!"}), 404

    # ✅ Aktualizace aktuálního školního roku
    SkolniRok.nastav_aktualni_rok(rok_od)

    # ✅ Posunutí žáků do správných tříd
    posunout_zaky_podle_skolniho_roku(rok_od)

    print(f"✅ Školní rok změněn na {novy_rok}!")
    return jsonify({
        "message": f"Školní rok změněn na {novy_rok}!",
        "reload": True  # Přidáme signál pro refresh stránky
    })

def posunout_zaky_podle_skolniho_roku(rok_od):
    """Posune žáky do správného ročníku podle vybraného školního roku."""
    try:
        for zak in Zak.query.all():
            # Výpočet ročníku: aktuální rok - rok nástupu + 6 (6. třída je první ročník 2. stupně)
            rocnik = rok_od - zak.rok_nastupu_2_stupen + 6  

            if 6 <= rocnik <= 9:
                # Žáci 6.-9. třídy
                zak.cislo_tridy = rocnik
                # Zachováme písmeno třídy nebo nastavíme výchozí "A"
                zak.pismeno_tridy = zak.pismeno_tridy or "A"

            elif rocnik > 9:
                # Absolventi (již odešli ze školy)
                # Ponecháme poslední třídu jako 9
                zak.cislo_tridy = 9
                # Nastavíme rok odchodu, pokud ještě není nastaven
                if not zak.skolni_rok_odchodu_od:
                    zak.skolni_rok_odchodu_od = rok_od - (rocnik - 9)
                    zak.skolni_rok_odchodu_do = zak.skolni_rok_odchodu_od + 1

            elif rocnik < 6:
                # Žáci, kteří ještě nenastoupili na 2. stupeň
                zak.cislo_tridy = None
                zak.pismeno_tridy = None
                
        db.session.commit()
        print(f"✅ Žáci posunuti pro školní rok {rok_od}/{rok_od+1}")
        return True
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při posouvání žáků: {e}")
        return False

@app.context_processor
def inject_skolni_rok():
    """Předává aktuální školní rok do všech šablon."""
    aktualni_rok = SkolniRok.query.filter_by(aktualni=True).first()
    return {"aktualni_rok": f"{aktualni_rok.rok_od}/{aktualni_rok.rok_do}" if aktualni_rok else "Neznámý"}

@app.route("/zaci")
def zobraz_zaky():
    """Zobrazí seznam všech žáků s možností filtrace."""
    try:
        # Získání všech žáků a aktuálního školního roku
        zaky = Zak.query.order_by(Zak.prijmeni, Zak.jmeno).all()
        print(f"🟢 DEBUG: Načteno {len(zaky)} žáků.")
        
        # Aktuální školní rok
        aktualni_rok_obj = SkolniRok.query.filter_by(aktualni=True).first()
        vybrany_skolni_rok = request.args.get("rok")
        
        # Pokud není vybrán rok v URL, použijeme aktuální
        if not vybrany_skolni_rok and aktualni_rok_obj:
            vybrany_skolni_rok = aktualni_rok_obj.rok_od
        elif not vybrany_skolni_rok:
            # Pokud nemáme ani aktuální rok, použijeme aktuální rok
            from datetime import datetime
            current_year = datetime.now().year
            vybrany_skolni_rok = current_year
        
        # Převést na int, pokud je ve formátu "2025/2026"
        if isinstance(vybrany_skolni_rok, str) and "/" in vybrany_skolni_rok:
            vybrany_skolni_rok = int(vybrany_skolni_rok.split("/")[0])
        else:
            vybrany_skolni_rok = int(vybrany_skolni_rok)
        
        # Předáme oba roky do šablony
        return render_template(
            "zaci.html", 
            zaky=zaky,
            aktualni_rok=aktualni_rok_obj,
            vybrany_skolni_rok=vybrany_skolni_rok
        )
    except Exception as e:
        print(f"❌ Chyba při zobrazení žáků: {e}")
        return render_template("error.html", error=str(e))

@app.route("/detail_tridy")
def seznam_trid():
    """Tento endpoint pouze přesměruje na správnou stránku tříd."""
    return redirect(url_for("zobraz_tridy"))

@app.route("/discipliny")
def discipliny():
    """Zobrazení seznamu všech disciplín s možností procházení tříd."""
    try:
        # Získání všech disciplín
        disciplines = Discipline.query.all()
        
        # Získání všech školních roků pro select
        skolni_roky = SkolniRok.query.order_by(SkolniRok.rok_od.asc()).all()
        
        return render_template(
            "discipliny.html",
            disciplines=disciplines,
            skolni_roky=skolni_roky
        )
    except Exception as e:
        flash(f"❌ Chyba při načítání disciplín: {str(e)}", "error")
        return redirect(url_for("home"))

@app.route("/get_classes_for_discipline")
def get_classes_for_discipline():
    """API koncový bod pro získání tříd s žáky, kteří mají záznamy v dané disciplíně."""
    discipline_id = request.args.get("discipline_id", type=int)
    skolni_rok = request.args.get("skolni_rok", "")
    
    if not discipline_id:
        return jsonify({"error": "Chybí ID disciplíny"}), 400
    
    try:
        # Převod roku na int - první část z "2024/2025"
        rok_od = int(skolni_rok.split("/")[0]) if "/" in skolni_rok else int(skolni_rok)
        
        # Získání všech žáků pro daný školní rok
        zaci = Zak.query.all()
        
        # Seznam tříd (například 6.A, 7.B, atd.)
        classes = set()
        
        for zak in zaci:
            rocnik = rok_od - zak.rok_nastupu_2_stupen + 6
            
            # Pokud je žák v 6.-9. třídě
            if 6 <= rocnik <= 9:
                pismeno = zak.pismeno_tridy
                if pismeno and pismeno.startswith('.'):
                    pismeno = pismeno[1:]
                
                if pismeno:
                    trida = f"{rocnik}.{pismeno}"
                    classes.add(trida)
        
        # Seřazení tříd
        sorted_classes = sorted(list(classes), key=lambda x: (int(x.split('.')[0]), x.split('.')[1]))
        
        return jsonify({"classes": sorted_classes})
    
    except Exception as e:
        app.logger.error(f"Chyba při získávání tříd: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_discipline_name")
def get_discipline_name():
    """API koncový bod pro získání názvu disciplíny podle ID."""
    discipline_id = request.args.get("discipline_id", type=int)
    
    if not discipline_id:
        return jsonify({"error": "Chybí ID disciplíny"}), 400
    
    try:
        discipline = Discipline.query.get(discipline_id)
        if not discipline:
            return jsonify({"error": "Disciplína nenalezena"}), 404
        
        return jsonify({"name": discipline.nazev})
    
    except Exception as e:
        app.logger.error(f"Chyba při získávání názvu disciplíny: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/get_students_performances")
def get_students_performances():
    """API koncový bod pro získání žáků a jejich výkonů pro danou třídu, pohlaví a disciplínu."""
    discipline_id = request.args.get("discipline_id", type=int)
    class_name = request.args.get("class", "")
    gender = request.args.get("gender", "")
    skolni_rok = request.args.get("skolni_rok", "")
    
    if not discipline_id or not class_name or not gender or not skolni_rok:
        return jsonify({"error": "Chybí povinné parametry"}), 400
    
    try:
        # Rozparsování třídy na číslo a písmeno
        cislo_tridy, pismeno_tridy = class_name.split(".")
        cislo_tridy = int(cislo_tridy)
        
        # Převod roku na int - první část z "2024/2025"
        rok_od = int(skolni_rok.split("/")[0]) if "/" in skolni_rok else int(skolni_rok)
        
        # Výpočet roku nástupu pro danou třídu
        rok_nastupu = rok_od - cislo_tridy + 6
        
        # Získání disciplíny
        discipline = Discipline.query.get(discipline_id)
        if not discipline:
            return jsonify({"error": "Disciplína nenalezena"}), 404
        
        # Získání žáků v dané třídě
        zaci = Zak.query.filter(
            Zak.rok_nastupu_2_stupen == rok_nastupu,
            Zak.pismeno_tridy.in_([pismeno_tridy, f".{pismeno_tridy}"]),
            Zak.pohlavi == gender
        ).order_by(Zak.prijmeni, Zak.jmeno).all()
        
        # Seznam žáků s jejich výkony
        students = []
        
        for zak in zaci:
            # Kontrola výkonu v databázi
            student_score = StudentScore.query.filter_by(
                zak_id=zak.id,
                discipline_id=discipline_id,
                rocnik=cislo_tridy,
                skolni_rok=rok_od
            ).first()
            
            students.append({
                "id": zak.id,
                "jmeno": zak.jmeno,
                "prijmeni": zak.prijmeni,
                "vykon": student_score.vykon if student_score else "",
                "body": student_score.body if student_score else "0"
            })
        
        return jsonify({
            "students": students,
            "jednotka": discipline.jednotka,
            "napoveda": discipline.napoveda
        })
    
    except Exception as e:
        app.logger.error(f"Chyba při získávání žáků a výkonů: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/ulozit_vykony_hromadne", methods=["POST"])
def ulozit_vykony_hromadne():
    """API koncový bod pro hromadné uložení výkonů žáků."""
    data = request.get_json()
    
    if not data or "performances" not in data:
        return jsonify({"success": False, "error": "Chybějící data"}), 400
    
    performances = data["performances"]
    
    try:
        # Počítadlo úspěšně uložených výkonů
        saved_count = 0
        error_count = 0
        error_messages = []
        
        for performance in performances:
            zak_id = performance.get("zak_id")
            discipline_id = performance.get("discipline_id")
            rocnik = performance.get("rocnik")
            vykon = performance.get("vykon", "").strip()
            skolni_rok = performance.get("skolni_rok")
            
            # Kontrola povinných polí
            if not zak_id or not discipline_id or not rocnik or not skolni_rok:
                error_count += 1
                error_messages.append(f"Chybí povinné parametry pro výkon {zak_id}/{discipline_id}")
                continue
            
            try:
                # Převod na správné datové typy
                zak_id = int(zak_id)
                discipline_id = int(discipline_id)
                rocnik = int(rocnik)
                skolni_rok = int(skolni_rok)
                
                # Pokud je výkon prázdný, smažeme záznam
                if not vykon:
                    student_score = StudentScore.query.filter_by(
                        zak_id=zak_id, 
                        discipline_id=discipline_id, 
                        rocnik=rocnik,
                        skolni_rok=skolni_rok
                    ).first()
                    
                    if student_score:
                        db.session.delete(student_score)
                        saved_count += 1
                    continue
                
                # Získání disciplíny
                discipline = Discipline.query.get(discipline_id)
                if not discipline:
                    error_count += 1
                    error_messages.append(f"Disciplína ID {discipline_id} nebyla nalezena")
                    continue
                
                # Získání bodů pro zadaný výkon
                format_type = FORMATY_DISCIPLIN.get(discipline.nazev, "float")
                
                try:
                    vykon_formatovany = convert_value(vykon, format_type)
                except ValueError as e:
                    error_count += 1
                    error_messages.append(f"Neplatný formát výkonu: {vykon}")
                    continue
                
                score = None
                
                # Použití bodů z výkonu, pokud existují
                if "body" in performance and performance["body"]:
                    body = int(performance["body"])
                else:
                    # Hledání bodů v bodovací tabulce
                    if format_type == "str":
                        score = Score.query.filter_by(discipline_id=discipline_id, vykon=str(vykon_formatovany)).first()
                    else:
                        score = Score.query.filter_by(discipline_id=discipline_id, vykon=str(vykon_formatovany)).first()
                    
                    if not score:
                        error_count += 1
                        error_messages.append(f"Pro výkon {vykon} nebyly nalezeny žádné body")
                        continue
                    
                    body = score.body
                
                # Kontrola, zda už existuje záznam
                student_score = StudentScore.query.filter_by(
                    zak_id=zak_id, 
                    discipline_id=discipline_id, 
                    rocnik=rocnik,
                    skolni_rok=skolni_rok
                ).first()
                
                if student_score:
                    # Aktualizace existujícího záznamu
                    student_score.vykon = vykon
                    student_score.body = body
                else:
                    # Vytvoření nového záznamu
                    student_score = StudentScore(
                        zak_id=zak_id,
                        discipline_id=discipline_id,
                        vykon=vykon,
                        body=body,
                        rocnik=rocnik,
                        skolni_rok=skolni_rok
                    )
                    db.session.add(student_score)
                
                saved_count += 1
            
            except Exception as e:
                error_count += 1
                error_messages.append(f"Chyba při ukládání výkonu {vykon}: {str(e)}")
                continue
        
        # Uložení všech změn
        db.session.commit()
        
        message = f"Úspěšně uloženo {saved_count} výkonů"
        if error_count > 0:
            message += f", {error_count} výkonů se nepodařilo uložit"
        
        app.logger.info(f"✅ {message}")
        
        return jsonify({
            "success": True,
            "message": message,
            "saved_count": saved_count,
            "error_count": error_count,
            "errors": error_messages[:5]  # Omezíme počet chybových zpráv
        })
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"❌ Chyba při ukládání výkonů: {str(e)}")
        return jsonify({
            "success": False, 
            "error": f"Chyba při ukládání výkonů: {str(e)}"
        }), 500

@app.route("/get_student_performance")
def get_student_performance():
    """API koncový bod pro získání výkonu žáka."""
    try:
        zak_id = request.args.get("zak_id", type=int)
        discipline_id = request.args.get("discipline_id", type=int)
        
        if not zak_id or not discipline_id:
            return jsonify({"error": "Chybí povinné parametry"}), 400
            
        # Získání výkonu žáka
        student_score = StudentScore.query.filter_by(
            zak_id=zak_id,
            discipline_id=discipline_id
        ).order_by(StudentScore.skolni_rok.desc()).first()
        
        if student_score:
            return jsonify({
                "success": True,
                "vykon": student_score.vykon,
                "body": student_score.body
            })
        else:
            return jsonify({"success": True, "vykon": None, "body": 0})
            
    except Exception as e:
        app.logger.error(f"Chyba při získávání výkonu žáka: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/ulozit_vykon", methods=["POST"])
def ulozit_vykon():
    """API koncový bod pro uložení výkonu jednoho žáka."""
    data = request.get_json()
    app.logger.info(f"🔍 DEBUG: Přijata data pro uložení výkonu: {data}")
    
    if not data:
        return jsonify({"success": False, "error": "Žádná data nebyla poskytnuta"}), 400
    
    zak_id = data.get("zak_id")
    discipline_id = data.get("discipline_id")
    rocnik = data.get("rocnik")
    vykon = data.get("vykon")
    
    if not zak_id or not discipline_id or not rocnik:
        return jsonify({"success": False, "error": "Chybí povinné parametry"}), 400
    
    try:
        # Převod na správné datové typy
        zak_id = int(zak_id)
        discipline_id = int(discipline_id)
        rocnik = int(rocnik)
        
        # Získání aktuálního školního roku z session
        skolni_rok = session.get('vybrany_skolni_rok_od')
        if not skolni_rok:
            # Získáme školní rok z databáze
            aktualni_rok = SkolniRok.query.filter_by(aktualni=True).first()
            if aktualni_rok:
                skolni_rok = aktualni_rok.rok_od
            else:
                # Pokud není nalezen žádný školní rok, použijeme aktuální rok
                skolni_rok = datetime.now().year
        
        # Převod na int, pokud je to rok ve formátu 2023/2024
        if isinstance(skolni_rok, str) and "/" in skolni_rok:
            skolni_rok = int(skolni_rok.split("/")[0])
        
        # Získání disciplíny
        discipline = Discipline.query.get(discipline_id)
        if not discipline:
            return jsonify({"success": False, "error": "Disciplína nebyla nalezena"}), 404
        
        # Prázdný výkon = smazání záznamu
        if vykon is None or not str(vykon).strip():
            # Najdeme existující záznam a smažeme ho
            student_score = StudentScore.query.filter_by(
                zak_id=zak_id, 
                discipline_id=discipline_id, 
                rocnik=rocnik,
                skolni_rok=skolni_rok
            ).first()
            
            if student_score:
                db.session.delete(student_score)
                db.session.commit()
                return jsonify({"success": True, "body": 0, "message": "Výkon byl smazán"})
            else:
                return jsonify({"success": True, "body": 0, "message": "Žádný výkon k smazání"})
        
        # Získání bodů pro zadaný výkon
        format_type = FORMATY_DISCIPLIN.get(discipline.nazev, "float")
        
        try:
            vykon_formatovany = convert_value(vykon, format_type)
        except ValueError as e:
            return jsonify({"success": False, "error": f"Neplatný formát výkonu: {str(e)}"}), 400
        
        score = None
        
        # Hledání bodů v bodovací tabulce
        if format_type == "str":
            score = Score.query.filter_by(discipline_id=discipline_id, vykon=str(vykon_formatovany)).first()
        else:
            score = Score.query.filter_by(discipline_id=discipline_id, vykon=str(vykon_formatovany)).first()
        
        if not score:
            return jsonify({"success": False, "error": "Pro tento výkon nebyly nalezeny žádné body"}), 404
        
        # Kontrola, zda již existuje záznam
        student_score = StudentScore.query.filter_by(
            zak_id=zak_id, 
            discipline_id=discipline_id, 
            rocnik=rocnik,
            skolni_rok=skolni_rok
        ).first()
        
        if student_score:
            # Aktualizace existujícího záznamu
            student_score.vykon = vykon
            student_score.body = score.body
        else:
            # Vytvoření nového záznamu
            student_score = StudentScore(
                zak_id=zak_id,
                discipline_id=discipline_id,
                vykon=vykon,
                body=score.body,
                rocnik=rocnik,
                skolni_rok=skolni_rok
            )
            db.session.add(student_score)
        
        db.session.commit()
        
        app.logger.info(f"✅ Výkon uložen - žák:{zak_id}, disciplína:{discipline_id}, ročník:{rocnik}, hodnota:{vykon}, body:{score.body}")
        
        return jsonify({
            "success": True,
            "body": score.body,
            "message": "Výkon byl úspěšně uložen"
        })
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"❌ Chyba při ukládání výkonu: {str(e)}")
        return jsonify({"success": False, "error": f"Chyba při ukládání výkonu: {str(e)}"}), 500

@app.route("/zebricky_a_statistiky")
def zebricky_a_statistiky():
    """Zobrazí stránku s žebříčky a statistikami s reálnými daty."""
    try:
        # Získání parametrů filtrů z URL
        selected_rocnik = request.args.get("rocnik", "all")
        selected_skolni_rok = request.args.get("skolni_rok", "")

        # Přidání logování pro lepší diagnostiku
        app.logger.info(f"🔍 Načítání žebříčků - ročník: {selected_rocnik}, školní rok: {selected_skolni_rok}")
        
        # Pokud není zadán školní rok, použijeme aktuální
        if not selected_skolni_rok:
            aktualni_rok_obj = SkolniRok.query.filter_by(aktualni=True).first()
            if aktualni_rok_obj:
                selected_skolni_rok = f"{aktualni_rok_obj.rok_od}/{aktualni_rok_obj.rok_do}"
        
        # Převedení školního roku na číslo pro filtrování
        try:
            rok_od = int(selected_skolni_rok.split("/")[0]) if "/" in selected_skolni_rok else int(selected_skolni_rok)
        except (ValueError, TypeError) as e:
            app.logger.error(f"❌ Chyba při zpracování školního roku '{selected_skolni_rok}': {e}")
            rok_od = datetime.now().year  # Fallback na aktuální rok

        # 1. Získání nejlepších žáků podle průměrného počtu bodů
        top_chlapci = db.session.query(
            Zak.id, Zak.jmeno, Zak.prijmeni, Zak.rok_nastupu_2_stupen, Zak.pismeno_tridy,
            func.avg(StudentScore.body).label('prumer_bodu')
        ).join(StudentScore, Zak.id == StudentScore.zak_id)\
         .filter(Zak.pohlavi.in_(["chlapec", "hoch", "muž", "m", "male", "boy", "kluk"]))
        
        # Filtrování podle školního roku
        top_chlapci = top_chlapci.filter(StudentScore.skolni_rok == rok_od)
        
        # Filtrování podle ročníku
        if selected_rocnik != "all":
            top_chlapci = top_chlapci.filter(StudentScore.rocnik == int(selected_rocnik))
        
        # Dokončení dotazu
        top_chlapci = top_chlapci.group_by(Zak.id)\
                                 .order_by(desc('prumer_bodu'))\
                                 .limit(10).all()
        
        # Formátování výsledků chlapců
        formatted_top_chlapci = []
        for zak_id, jmeno, prijmeni, rok_nastupu, pismeno_tridy, prumer_bodu in top_chlapci:
            # Výpočet třídy
            rocnik = rok_od - rok_nastupu + 6
            if 6 <= rocnik <= 9:
                trida = f"{rocnik}.{pismeno_tridy}" if pismeno_tridy else f"{rocnik}"
            else:
                trida = "Absolvent" if rocnik > 9 else "Před nástupem"
            
            formatted_top_chlapci.append({
                "jmeno": f"{jmeno} {prijmeni}",
                "trida": trida,
                "prumer_bodu": round(prumer_bodu, 1)
            })
        
        # Podobný dotaz pro dívky
        top_divky = db.session.query(
            Zak.id, Zak.jmeno, Zak.prijmeni, Zak.rok_nastupu_2_stupen, Zak.pismeno_tridy,
            func.avg(StudentScore.body).label('prumer_bodu')
        ).join(StudentScore, Zak.id == StudentScore.zak_id)\
         .filter(Zak.pohlavi.in_(["divka", "dívka", "f", "female", "dievča", "girl", "holka", "žena"]))
        
        # Filtrování podle školního roku
        top_divky = top_divky.filter(StudentScore.skolni_rok == rok_od)
        
        # Filtrování podle ročníku
        if selected_rocnik != "all":
            top_divky = top_divky.filter(StudentScore.rocnik == int(selected_rocnik))
        
        # Dokončení dotazu
        top_divky = top_divky.group_by(Zak.id)\
                              .order_by(desc('prumer_bodu'))\
                              .limit(10).all()
        
        # Formátování výsledků dívek
        formatted_top_divky = []
        for zak_id, jmeno, prijmeni, rok_nastupu, pismeno_tridy, prumer_bodu in top_divky:
            rocnik = rok_od - rok_nastupu + 6
            if 6 <= rocnik <= 9:
                trida = f"{rocnik}.{pismeno_tridy}" if pismeno_tridy else f"{rocnik}"
            else:
                trida = "Absolvent" if rocnik > 9 else "Před nástupem"
                
            formatted_top_divky.append({
                "jmeno": f"{jmeno} {prijmeni}",
                "trida": trida,
                "prumer_bodu": round(prumer_bodu, 1)
            })
        
        # 2. Získání disciplín pro záložky
        disciplines = Discipline.query.all()
        
        # 3. Získání nejlepších výkonů pro každou disciplínu
        discipline_performances = {}
        
        for discipline in disciplines:
            # Získání nejlepších výkonů pro chlapce
            chlapci_vysledky = db.session.query(
                Zak.id, Zak.jmeno, Zak.prijmeni, Zak.rok_nastupu_2_stupen, Zak.pismeno_tridy,
                StudentScore.vykon, StudentScore.rocnik, StudentScore.skolni_rok
            ).join(StudentScore, Zak.id == StudentScore.zak_id)\
             .filter(StudentScore.discipline_id == discipline.id)\
             .filter(Zak.pohlavi.in_(["chlapec", "hoch", "muž", "m", "male", "boy", "kluk"]))\
             .filter(StudentScore.skolni_rok == rok_od)
            
            if selected_rocnik != "all":
                chlapci_vysledky = chlapci_vysledky.filter(StudentScore.rocnik == int(selected_rocnik))
            
            # Seřazení podle výkonů závisí na disciplíně (některé disciplíny mají nižší hodnotu = lepší výsledek)
            # Zde bychom potřebovali logiku pro každou disciplínu
            chlapci_vysledky = chlapci_vysledky.order_by(asc(StudentScore.vykon) if discipline.nazev in ["Běh 60m", "Běh 1000m"] else desc(StudentScore.vykon))\
                                               .limit(5).all()
            
            # Formátování výsledků chlapců pro disciplínu
            formatted_chlapci = []
            for zak_id, jmeno, prijmeni, rok_nastupu, pismeno_tridy, vykon, rocnik, skolni_rok in chlapci_vysledky:
                if 6 <= rocnik <= 9:
                    trida = f"{rocnik}.{pismeno_tridy}" if pismeno_tridy else f"{rocnik}"
                else:
                    trida = "Absolvent" if rocnik > 9 else "Před nástupem"
                
                formatted_chlapci.append({
                    "jmeno": f"{jmeno} {prijmeni}",
                    "trida": trida,
                    "vykon": vykon,
                    "skolni_rok": f"{skolni_rok}/{skolni_rok + 1}"
                })
            
            # Podobný proces pro dívky
            divky_vysledky = db.session.query(
                Zak.id, Zak.jmeno, Zak.prijmeni, Zak.rok_nastupu_2_stupen, Zak.pismeno_tridy,
                StudentScore.vykon, StudentScore.rocnik, StudentScore.skolni_rok
            ).join(StudentScore, Zak.id == StudentScore.zak_id)\
             .filter(StudentScore.discipline_id == discipline.id)\
             .filter(Zak.pohlavi.in_(["divka", "dívka", "f", "female", "dievča", "girl", "holka", "žena"]))\
             .filter(StudentScore.skolni_rok == rok_od)
             
            if selected_rocnik != "all":
                divky_vysledky = divky_vysledky.filter(StudentScore.rocnik == int(selected_rocnik))
                
            divky_vysledky = divky_vysledky.order_by(asc(StudentScore.vykon) if discipline.nazev in ["Běh 60m", "Běh 600m"] else desc(StudentScore.vykon))\
                                           .limit(5).all()
            
            # Formátování výsledků dívek pro disciplínu
            formatted_divky = []
            for zak_id, jmeno, prijmeni, rok_nastupu, pismeno_tridy, vykon, rocnik, skolni_rok in divky_vysledky:
                if 6 <= rocnik <= 9:
                    trida = f"{rocnik}.{pismeno_tridy}" if pismeno_tridy else f"{rocnik}"
                else:
                    trida = "Absolvent" if rocnik > 9 else "Před nástupem"
                
                formatted_divky.append({
                    "jmeno": f"{jmeno} {prijmeni}",
                    "trida": trida,
                    "vykon": vykon,
                    "skolni_rok": f"{skolni_rok}/{skolni_rok + 1}"
                })
            
            # Uložení výsledků pro disciplínu
            discipline_performances[discipline.nazev] = {
                "chlapci": formatted_chlapci,
                "divky": formatted_divky,
                "jednotka": discipline.jednotka
            }
        
        # 4. Získání rekordů a statistik
        
        # 4.1 Aktuální rekordy
        aktualni_rekordy = {
            "chlapci": {},
            "divky": {}
        }
        
        for discipline in disciplines:
            # Rekordy chlapců
            rekord_chlapci = db.session.query(
                Zak.jmeno, Zak.prijmeni, Zak.rok_nastupu_2_stupen, Zak.pismeno_tridy,
                StudentScore.vykon, StudentScore.rocnik
            ).join(StudentScore, Zak.id == StudentScore.zak_id)\
             .filter(StudentScore.discipline_id == discipline.id)\
             .filter(Zak.pohlavi.in_(["chlapec", "hoch", "muž", "m", "male", "boy", "kluk"]))\
             .filter(StudentScore.skolni_rok == rok_od)
            
            if selected_rocnik != "all":
                rekord_chlapci = rekord_chlapci.filter(StudentScore.rocnik == int(selected_rocnik))
                
            rekord_chlapci = rekord_chlapci.order_by(asc(StudentScore.vykon) if discipline.nazev in ["Běh 60m", "Běh 1000m"] else desc(StudentScore.vykon))\
                                          .first()
            
            if rekord_chlapci:
                jmeno, prijmeni, rok_nastupu, pismeno_tridy, vykon, rocnik = rekord_chlapci
                trida = f"{rocnik}.{pismeno_tridy}" if pismeno_tridy else f"{rocnik}"
                
                aktualni_rekordy["chlapci"][discipline.nazev] = {
                    "jmeno": f"{jmeno} {prijmeni}",
                    "trida": trida,
                    "vykon": vykon
                }
            
            # Rekordy dívek - obdobný proces
            rekord_divky = db.session.query(
                Zak.jmeno, Zak.prijmeni, Zak.rok_nastupu_2_stupen, Zak.pismeno_tridy,
                StudentScore.vykon, StudentScore.rocnik
            ).join(StudentScore, Zak.id == StudentScore.zak_id)\
             .filter(StudentScore.discipline_id == discipline.id)\
             .filter(Zak.pohlavi.in_(["divka", "dívka", "f", "female", "dievča", "girl", "holka", "žena"]))\
             .filter(StudentScore.skolni_rok == rok_od)
            
            if selected_rocnik != "all":
                rekord_divky = rekord_divky.filter(StudentScore.rocnik == int(selected_rocnik))
                
            rekord_divky = rekord_divky.order_by(asc(StudentScore.vykon) if discipline.nazev in ["Běh 60m", "Běh 600m"] else desc(StudentScore.vykon))\
                                        .first()
            
            if rekord_divky:
                jmeno, prijmeni, rok_nastupu, pismeno_tridy, vykon, rocnik = rekord_divky
                trida = f"{rocnik}.{pismeno_tridy}" if pismeno_tridy else f"{rocnik}"
                
                aktualni_rekordy["divky"][discipline.nazev] = {
                    "jmeno": f"{jmeno} {prijmeni}",
                    "trida": trida,
                    "vykon": vykon
                }
        
        # 4.2 Historické rekordy - obdobně jako aktuální rekordy, ale bez filtru na školní rok
        
        # 5. Statistiky tříd - průměrné body
        tridy_statistiky = db.session.query(
            StudentScore.rocnik, 
            Zak.pismeno_tridy, 
            func.avg(StudentScore.body).label('prumer_bodu'),
            func.count(func.distinct(Zak.id)).label('pocet_zaku')
        ).join(Zak, StudentScore.zak_id == Zak.id)\
         .filter(StudentScore.skolni_rok == rok_od)
        
        if selected_rocnik != "all":
            tridy_statistiky = tridy_statistiky.filter(StudentScore.rocnik == int(selected_rocnik))
            
        tridy_statistiky = tridy_statistiky.group_by(StudentScore.rocnik, Zak.pismeno_tridy)\
                                          .order_by(desc('prumer_bodu'))\
                                          .all()
        
        formatted_tridy_statistiky = []
        for rocnik, pismeno_tridy, prumer_bodu, pocet_zaku in tridy_statistiky:
            if pismeno_tridy:
                trida = f"{rocnik}.{pismeno_tridy}"
                formatted_tridy_statistiky.append({
                    "trida": trida,
                    "prumer_bodu": round(prumer_bodu, 1),
                    "pocet_zaku": pocet_zaku
                })
        
        # 6. Osobní rekordy žáka
        zak_id = request.args.get("zak_id", None)
        osobni_rekordy = None
        vsichni_zaci = []

        # Získání všech žáků pro seznam bez ohledu na výběr konkrétního žáka
        try:
            vsichni_zaci = Zak.query.order_by(Zak.prijmeni, Zak.jmeno).all() 
        except Exception as e:
            app.logger.error(f"❌ Chyba při načítání seznamu žáků: {e}")
            vsichni_zaci = []  # Prázdný seznam v případě chyby
        
        # Zpracování osobních rekordů pouze pokud je zvolen žák
        if zak_id:
            try:
                zak_id_int = int(zak_id)  # Bezpečné převedení na int
                zak = Zak.query.get(zak_id_int)
                
                if zak:
                    osobni_rekordy = {
                        "jmeno": f"{zak.jmeno} {zak.prijmeni}",
                        "discipliny": {}
                    }
                    
                    for discipline in disciplines:
                        # Nejlepší výkon žáka v disciplíně
                        try:
                            nejlepsi_vykon = db.session.query(
                                StudentScore.vykon, 
                                StudentScore.rocnik, 
                                StudentScore.skolni_rok,
                                StudentScore.body
                            ).filter(
                                StudentScore.zak_id == zak_id_int,
                                StudentScore.discipline_id == discipline.id
                            ).order_by(
                                asc(StudentScore.vykon) if discipline.nazev in ["Běh 60m", "Běh 600m", "Běh 1000m"] else desc(StudentScore.vykon)
                            ).first()
                            
                            if nejlepsi_vykon:
                                vykon, rocnik, skolni_rok, body = nejlepsi_vykon
                                osobni_rekordy["discipliny"][discipline.nazev] = {
                                    "vykon": vykon,
                                    "rocnik": rocnik,
                                    "skolni_rok": f"{skolni_rok}/{skolni_rok+1}" if skolni_rok else "Neznámý",
                                    "body": body,
                                    "jednotka": discipline.jednotka
                                }
                        except Exception as e:
                            app.logger.error(f"❌ Chyba při získávání výkonu žáka {zak_id} pro disciplínu {discipline.nazev}: {e}")
                else:
                    app.logger.warning(f"⚠️ Žák s ID {zak_id} nebyl nalezen")
            except ValueError:
                app.logger.error(f"❌ Neplatné ID žáka: {zak_id}")
        
        # Předání dat do šablony - důležitá je kontrola, aby všechny očekávané parametry existovaly
        return render_template(
            "zebricky_a_statistiky.html",
            top_chlapci=formatted_top_chlapci or [],
            top_divky=formatted_top_divky or [],
            discipline_performances=discipline_performances or {},
            disciplines=disciplines or [],
            aktualni_rekordy=aktualni_rekordy or {"chlapci": {}, "divky": {}},
            tridy_statistiky=formatted_tridy_statistiky or [],
            osobni_rekordy=osobni_rekordy,  # Může být None
            selected_rocnik=selected_rocnik,
            selected_skolni_rok=selected_skolni_rok,
            skolni_roky=SkolniRok.query.order_by(SkolniRok.rok_od.desc()).all() or [],
            vsichni_zaci=vsichni_zaci,
            vybrany_rocnik=selected_rocnik,
            vybrany_skolni_rok=selected_skolni_rok,
            vybrany_zak_id=zak_id
        )
            
    except Exception as e:
        app.logger.error(f"❌ Chyba v zebricky_a_statistiky: {str(e)}", exc_info=True)
        return render_template("error.html", error=str(e))

@app.route("/vyhledat")
def vyhledat_zaka():
    """Vyhledá žáky podle zadaného dotazu."""
    query = request.args.get("query", "").strip()
    
    # Získání aktuálního školního roku
    from datetime import datetime
    aktualni_rok_obj = SkolniRok.query.filter_by(aktualni=True).first()
    vybrany_skolni_rok = session.get('vybrany_skolni_rok_od') or (
        aktualni_rok_obj.rok_od if aktualni_rok_obj else datetime.now().year
    )
    
    # Převést na int, pokud je ve formátu "2025/2026"
    if isinstance(vybrany_skolni_rok, str) and "/" in vybrany_skolni_rok:
        vybrany_skolni_rok = int(vybrany_skolni_rok.split("/")[0])
    
    # Vyhledání žáků podle dotazu
    if query:
        # Hledáme v jméně nebo příjmení (bez ohledu na velikost písmen)
        zaky = Zak.query.filter(
            db.or_(
                Zak.jmeno.ilike(f"%{query}%"),
                Zak.prijmeni.ilike(f"%{query}%")
            )
        ).order_by(Zak.prijmeni, Zak.jmeno).all()
    else:
        zaky = []
    
    return render_template(
        "vyhledani.html", 
        zaky=zaky, 
        query=query,
        vybrany_skolni_rok=vybrany_skolni_rok
    )

@app.route("/synchronizovat_rok", methods=["POST"])
def synchronizovat_rok():
    """Synchronizuje školní rok mezi localStorage a session."""
    data = request.get_json()
    rok = data.get("rok")
    if rok:
        if "/" in rok:
            rok_od = int(rok.split("/")[0])
            rok_do = int(rok.split("/")[1])
        else:
            rok_od = int(rok)
            rok_do = rok_od + 1
        
        session['vybrany_skolni_rok_od'] = rok_od
        session['vybrany_skolni_rok_do'] = rok_do
        
        return jsonify({"success": True})
    return jsonify({"error": "Neplatný rok"}), 400

@app.route("/zak/<int:zak_id>")
def detail_zaka(zak_id):
    """Zobrazí detailní informace o žákovi."""
    try:
        zak = Zak.query.get(int(zak_id))
        
        disciplines = Discipline.query.all()
        
        # Získání vybraného školního roku z session
        aktualni_rok_obj = SkolniRok.query.filter_by(aktualni=True).first()
        vybrany_skolni_rok = session.get('vybrany_skolni_rok_od') or (
            aktualni_rok_obj.rok_od if aktualni_rok_obj else datetime.now().year
        )
        
        if isinstance(vybrany_skolni_rok, str) and "/" in vybrany_skolni_rok:
            try:
                vybrany_skolni_rok = int(vybrany_skolni_rok.split("/")[0])
            except ValueError:
                flash("❌ Neplatný formát školního roku!", "error")
                return redirect(url_for("zobraz_zaky"))
        else:
            vybrany_skolni_rok = int(vybrany_skolni_rok)

        # Výpočet ročníku žáka
        rocnik = vybrany_skolni_rok - zak.rok_nastupu_2_stupen + 6

        # Pokud je žák absolvent, nastavíme ročník na 9
        if rocnik > 9:
            rocnik = 9

        # Výpočet bodových rozmezí pro známky
        bodove_rozmezi = vypocet_rozmezi_bodu(zak.pohlavi, rocnik)

        # Načtení výkonů žáka
        vykony = StudentScore.query.filter_by(zak_id=zak.id).all()
        
        # Načtení výsledků pro odpovídající ročník a školní rok
        scores_by_grade = {}
        if rocnik and 6 <= rocnik <= 9:
            scores_by_grade[rocnik] = StudentScore.query.filter_by(
                zak_id=zak_id, 
                rocnik=rocnik,
                skolni_rok=vybrany_skolni_rok
            ).all()
            
            # Pro zpětnou kompatibilitu - pokud nejsou data se školním rokem
            if not scores_by_grade[rocnik]:
                scores_by_grade[rocnik] = StudentScore.query.filter_by(
                    zak_id=zak_id, 
                    rocnik=rocnik,
                    skolni_rok=None
                ).all()
        
        return render_template(
            "detail_zaka.html",
            zak=zak,
            disciplines=disciplines,
            vykony=vykony,
            vybrany_skolni_rok=vybrany_skolni_rok,
            scores_by_grade=scores_by_grade,
            aktualni_rok=f"{vybrany_skolni_rok}/{vybrany_skolni_rok+1}",
            bodove_rozmezi=bodove_rozmezi,
            vypocet_znamky=vypocet_znamky
        )
    except Exception as e:
        app.logger.error(f"❌ Chyba při zobrazení detailu žáka: {str(e)}")
        flash(f"Chyba při načítání detailu žáka: {str(e)}", "error")
        return redirect(url_for("zobraz_zaky"))

def vypocet_rozmezi_bodu(pohlavi, rocnik):
    """
    Vypočítá rozmezí bodů pro známky na základě pohlaví a ročníku.
    """
    base_reference = 130 if pohlavi.lower() == "chlapec" else 110  # Výchozí hodnoty
    reference_value = base_reference * (0.9 ** (9 - rocnik))  # Přizpůsobení podle ročníku

    # Vytvoříme rozmezí bodů
    grade_ranges = {
        1: f"{round(reference_value * 1.0)} - 200",
        2: f"{round(reference_value * 0.9)} - {round(reference_value * 1.0) - 1}",
        3: f"{round(reference_value * 0.8)} - {round(reference_value * 0.9) - 1}",
        4: f"20 - {round(reference_value * 0.8) - 1}"
    }
    
    return grade_ranges

def vypocet_znamky(body, pohlavi, rocnik):
    """
    Vyhodnotí známku na základě počtu bodů, pohlaví a ročníku studenta.
    """
    if body is None:
        return None
    
    base_reference = 130 if pohlavi.lower() == "chlapec" else 110  # Výchozí hodnoty
    reference_value = base_reference * (0.9 ** (9 - rocnik))  # Přizpůsobení podle ročníku
    
    # Definování bodových hranic
    if body >= round(reference_value * 1.0):
        return 1
    elif body >= round(reference_value * 0.9):
        return 2
    elif body >= round(reference_value * 0.8):
        return 3
    elif body >= 20:  # Minimální hranice pro známku 4
        return 4
    else:
        return 5  # Pokud má méně než 20 bodů

def inicializovat_databazi():
    """Inicializuje databázi výchozími daty, pokud je prázdná."""
    try:
        # Kontrola, zda databáze obsahuje školní roky
        skolni_roky_count = SkolniRok.query.count()
        if skolni_roky_count == 0:
            print("🔄 Importuji výchozí školní roky...")
            try:
                import_skolni_roky("skolni_roky.xlsx")
                print("✅ Školní roky úspěšně importovány")
                
                # Nastavení aktuálního školního roku
                aktualni_rok = datetime.now().year
                if datetime.now().month < 9:  # Před zářím používáme předchozí školní rok
                    aktualni_rok -= 1
                SkolniRok.nastav_aktualni_rok(aktualni_rok)
                print(f"✅ Nastaven aktuální školní rok: {aktualni_rok}/{aktualni_rok+1}")
            except Exception as e:
                print(f"❌ Chyba při importu školních roků: {str(e)}")
        
        # Kontrola, zda databáze obsahuje žáky
        zaci_count = Zak.query.count()
        if zaci_count == 0:
            print("🔄 Importuji výchozí žáky...")
            try:
                import_zaci("zaci.xlsx")
                print(f"✅ Importováno {Zak.query.count()} žáků")
            except Exception as e:
                print(f"❌ Chyba při importu žáků: {str(e)}")
        
        # Kontrola, zda databáze obsahuje disciplíny a bodovací systém
        discipline_count = Discipline.query.count()
        if discipline_count == 0:
            print("🔄 Importuji výchozí bodovací databázi...")
            try:
                import_excel("bodovaci_databaze.xlsx")
                print(f"✅ Importováno {Discipline.query.count()} disciplín")
            except Exception as e:
                print(f"❌ Chyba při importu bodovací databáze: {str(e)}")
            
    except Exception as e:
        print(f"❌ Chyba při inicializaci databáze: {str(e)}")

# ========= ODKAZY A INFORMACE ==========

@app.route("/odkazy_a_informace/", methods=["GET", "POST"])
@app.route("/odkazy_a_informace", methods=["GET", "POST"])
@app.route("/odkazy", methods=["GET", "POST"])  # Pro zpětnou kompatibilitu
def odkazy_a_informace():
    """Zobrazí stránku s odkazy, informacemi a soubory."""
    
    # Načtení odkazů z databáze
    try:
        odkazy = Odkaz.query.all()
    except Exception as e:
        print(f"Chyba při načítání odkazů z DB: {e}")
        odkazy = []
    
    # Seskupení odkazů podle kategorií
    odkazy_podle_kategorii = {}
    for odkaz in odkazy:
        if odkaz.kategorie not in odkazy_podle_kategorii:
            odkazy_podle_kategorii[odkaz.kategorie] = []
        odkazy_podle_kategorii[odkaz.kategorie].append({
            "id": odkaz.id,
            "nazev": odkaz.nazev,
            "url": odkaz.url
        })
    
    # Pokud nemáme žádné odkazy, vytvoříme ukázkové
    if not odkazy_podle_kategorii:
        odkazy_podle_kategorii = {
            "Videa": [{"id": None, "nazev": "Základy gymnastiky", "url": "https://example.com/video1"}],
            "Články": [{"id": None, "nazev": "Jak se správně protahovat", "url": "https://example.com/article1"}]
        }
    
    # Načtení informací z databáze
    try:
        informace_db = Informace.query.order_by(Informace.datum_vytvoreni.desc()).all()
        informace = [{"text": info.text, "date": info.datum, "id": info.id} for info in informace_db]
    except Exception as e:
        print(f"Chyba při načítání informací z DB: {e}")
        informace = [{"text": "Nezapomeňte na školní závody!", "date": datetime.now().strftime("%d.%m.%Y"), "id": None}]
    
    # Kontrola a vytvoření složky pro soubory
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    os.makedirs(upload_folder, exist_ok=True)

    # Získání seznamu nahraných souborů
    try:
        soubory_db = Soubor.query.order_by(Soubor.datum_nahrani.desc()).all()
        uploaded_files = [(soubor.filename, soubor.id) for soubor in soubory_db]
    except Exception as e:
        print(f"Chyba při načítání souborů z DB: {e}")
        uploaded_files = []
        if os.path.exists(upload_folder):
            uploaded_files = [(f, None) for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))]

    # Aktuální datum pro formulář
    today_date = datetime.now().strftime("%Y-%m-%d")

    # Seznam kategorií pro select
    kategorie_list = list(odkazy_podle_kategorii.keys())

    return render_template(
        "odkazy_a_informace.html",
        odkazy_podle_kategorii=odkazy_podle_kategorii,
        informace=informace,
        uploaded_files=uploaded_files,
        today_date=today_date,
        kategorie_list=kategorie_list
    )

@app.route("/pridat_odkaz", methods=["POST"])
def pridat_odkaz():
    """Přidá nový odkaz do databáze."""
    try:
        nazev = request.form.get("nazev", "").strip()
        url = request.form.get("url", "").strip()
        kategorie = request.form.get("kategorie", "").strip()
        
        # Vytvoření nové kategorie, pokud je vybrána možnost "nová"
        if kategorie == "nová":
            kategorie = request.form.get("nova_kategorie", "").strip()
            if not kategorie:
                flash("❌ Zadejte název nové kategorie!", "error")
                return redirect(url_for("odkazy_a_informace"))
        
        # Validace vstupních dat
        if not nazev or not url:  # Oprava: nebo -> or
            flash("❌ Název a URL jsou povinné!", "error")
            return redirect(url_for("odkazy_a_informace"))
        
        # Vytvoření nového odkazu v databázi
        novy_odkaz = Odkaz(
            nazev=nazev,
            url=url,
            kategorie=kategorie
        )
        
        db.session.add(novy_odkaz)
        db.session.commit()
        
        flash("✅ Odkaz byl úspěšně přidán!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při přidání odkazu: {e}")
        flash(f"❌ Chyba při přidání odkazu: {str(e)}", "error")
    
    return redirect(url_for("odkazy_a_informace"))

@app.route("/pridat_informaci", methods=["POST"])
def pridat_informaci():
    """Přidá novou informaci do databáze."""
    try:
        text = request.form.get("text", "").strip()
        date = request.form.get("date", "")
        
        # Validace vstupních dat
        if not text:
            flash("❌ Text informace je povinný!", "error")
            return redirect(url_for("odkazy_a_informace"))
        
        # Formátování datumu
        date_obj = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
        formatted_date = date_obj.strftime("%d.%m.%Y")
        
        # Vytvoření nové informace v databázi
        nova_informace = Informace(
            text=text,
            datum=formatted_date
        )
        
        db.session.add(nova_informace)
        db.session.commit()
        
        flash("✅ Informace byla úspěšně přidána!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při přidání informace: {e}")
        flash(f"❌ Chyba při přidání informace: {str(e)}", "error")
    
    return redirect(url_for("odkazy_a_informace"))

@app.route("/nahrat_soubor", methods=["POST"])
def nahrat_soubor():
    """Nahraje nový soubor do složky uploads a zaznamená ho v databázi."""
    try:
        # Kontrola, zda byl nahrán soubor
        if "soubor" not in request.files:
            flash("❌ Nebyl vybrán žádný soubor!", "error")
            return redirect(url_for("odkazy_a_informace"))
        
        soubor = request.files["soubor"]
        
        # Kontrola, zda má soubor název
        if soubor.filename == "":
            flash("❌ Nebyl vybrán žádný soubor!", "error")
            return redirect(url_for("odkazy_a_informace"))
        
        # Kontrola, zda má soubor povolený formát
        if not allowed_file(soubor.filename):
            flash("❌ Nepodporovaný formát souboru!", "error")
            return redirect(url_for("odkazy_a_informace"))
        
        # Zajištění bezpečnosti názvu souboru
        filename = secure_filename(soubor.filename)
        
        # Kontrola duplicity názvu souboru
        uploads_path = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"])
        if os.path.exists(os.path.join(uploads_path, filename)):
            # Přidání časového razítka k názvu souboru
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
        
        # Uložení souboru
        soubor.save(os.path.join(uploads_path, filename))
        
        # Zjištění velikosti a typu souboru
        velikost = os.path.getsize(os.path.join(uploads_path, filename))
        typ_souboru = os.path.splitext(filename)[1][1:].lower()
        
        # Záznam souboru v databázi
        novy_soubor = Soubor(
            nazev=os.path.splitext(soubor.filename)[0],
            filename=filename,
            velikost=velikost,
            typ_souboru=typ_souboru
        )
        
        db.session.add(novy_soubor)
        db.session.commit()
        
        flash(f"✅ Soubor {filename} byl úspěšně nahrán!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při nahrávání souboru: {e}")
        flash(f"❌ Chyba při nahrávání souboru: {str(e)}", "error")
    
    return redirect(url_for("odkazy_a_informace"))

@app.route("/smazat_odkaz/<int:odkaz_id>", methods=["GET"])
def smazat_odkaz(odkaz_id):
    """Smaže odkaz z databáze."""
    try:
        odkaz = Odkaz.query.get_or_404(odkaz_id)
        
        db.session.delete(odkaz)
        db.session.commit()
        
        flash("✅ Odkaz byl úspěšně smazán!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při mazání odkazu: {e}")
        flash(f"❌ Chyba při mazání odkazu: {str(e)}", "error")
    
    return redirect(url_for("odkazy_a_informace"))

@app.route("/smazat_informaci/<int:informace_id>", methods=["GET"])
def smazat_informaci(informace_id):
    """Smaže informaci z databáze."""
    try:
        informace = Informace.query.get_or_404(informace_id)
        
        db.session.delete(informace)
        db.session.commit()
        
        flash("✅ Informace byla úspěšně smazána!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při mazání informace: {e}")
        flash(f"❌ Chyba při mazání informace: {str(e)}", "error")
    
    return redirect(url_for("odkazy_a_informace"))

@app.route("/smazat_soubor/<int:soubor_id>", methods=["GET"])
def smazat_soubor(soubor_id):
    """Smaže soubor z databáze a z disku."""
    try:
        soubor = Soubor.query.get_or_404(soubor_id)
        
        # Smazání souboru z disku
        file_path = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"], soubor.filename)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
        
        # Smazání záznamu z databáze
        db.session.delete(soubor)
        db.session.commit()
        
        flash(f"✅ Soubor {soubor.nazev} byl úspěšně smazán!", "success")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Chyba při mazání souboru: {e}")
        flash(f"❌ Chyba při mazání souboru: {str(e)}", "error")
    
    return redirect(url_for("odkazy_a_informace"))

@app.route("/stahnout_soubor/<path:filename>", methods=["GET"])
def stahnout_soubor(filename):
    """Stáhne soubor ze složky uploads."""
    try:
        # Kontrola, zda soubor existuje
        uploads_path = os.path.join(app.root_path, app.config["UPLOAD_FOLDER"])
        return send_from_directory(
            uploads_path, 
            filename, 
            as_attachment=True
        )
    except Exception as e:
        print(f"❌ Chyba při stahování souboru: {e}")
        flash(f"❌ Chyba při stahování souboru: {str(e)}", "error")
        return redirect(url_for("odkazy_a_informace"))

@app.route("/nacti_vykony")
def nacti_vykony():
    """Načte výkony žáka pro daný ročník."""
    zak_id = request.args.get("zak_id", type=int)
    rocnik = request.args.get("rocnik", type=int)
    
    if not zak_id or not rocnik:
        return jsonify({"success": False, "error": "Chybí povinné parametry"}), 400
    
    try:
        # Získání aktuálního školního roku z session
        skolni_rok = session.get('vybrany_skolni_rok_od')
        if not skolni_rok:
            # Získáme školní rok z databáze
            aktualni_rok = db.session.get(SkolniRok, {"aktualni": True})
            if aktualni_rok:
                skolni_rok = aktualni_rok.rok_od
            else:
                # Pokud není nalezen žádný školní rok, použijeme aktuální rok
                skolni_rok = datetime.now().year
        
        # Převod na int, pokud je to rok ve formátu 2023/2024
        if isinstance(skolni_rok, str) and "/" in skolni_rok:
            skolni_rok = int(skolni_rok.split("/")[0])
        
        # Načtení výkonů z databáze
        vykony = StudentScore.query.filter_by(
            zak_id=zak_id, 
            rocnik=rocnik,
            skolni_rok=skolni_rok
        ).all()
        
        # Příprava dat pro odpověď
        data = []
        for vykon in vykony:
            data.append({
                "discipline_id": vykon.discipline_id,
                "vykon": vykon.vykon,
                "body": vykon.body
            })
        
        app.logger.info(f"✅ Načteno {len(data)} výkonů pro žáka {zak_id}, ročník {rocnik}, školní rok {skolni_rok}")
        
        return jsonify({
            "success": True,
            "vykony": data
        })
    
    except Exception as e:
        app.logger.error(f"❌ Chyba při načítání výkonů: {str(e)}")
        return jsonify({"success": False, "error": f"Chyba při načítání výkonů: {str(e)}"}), 500
    
if __name__ == "__main__":
    print("🌐 Aplikace běží na adrese: http://127.0.0.1:5000/")
    app.run(debug=True, host='0.0.0.0', port=5000)    