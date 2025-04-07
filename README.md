# 🏗️ Projekt: Hejbni kostrou

Tento projekt je webová aplikace pro správu školní databáze žáků, tříd, disciplín a statistik. Umožňuje snadné nahrávání dat z Excelu, zobrazování informací ve webovém rozhraní a zpracování statistik.

---

## 🚀 Spuštění projektu

1. **Vytvoř a aktivuj virtuální prostředí:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Nainstaluj závislosti:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Spusť hlavní aplikaci:**
   ```bash
   python hejbni_kostrou.py
   ```

---

## 📁 Struktura projektu

```txt
hejbni_kostrou/
│
├── alembic/                   # Alembic konfigurace pro migrace
│   └── env.py
├── migrations/               # Další migrace (alternativa k alembic)
│   └── env.py
├── static/                   # Statické soubory (CSS, JS, obrázky)
│   └── styles.css
├── templates/                # HTML šablony pro Flask (Jinja2)
│   ├── base.html             # Základní layout
│   ├── home.html             # Domovská stránka
│   ├── 404.html              # Chybová stránka
│   ├── error.html            # Obecné chyby
│   ├── discipliny.html       # Přehled disciplín
│   ├── zaci.html             # Výpis žáků
│   ├── trida.html            # Detail třídy
│   ├── detail_tridy.html     # Detailní pohled na třídu
│   ├── detail_zaka.html      # Detailní pohled na žáka
│   ├── odkazy_a_informace.html
│   ├── vyhledani.html
│   └── zebricky_a_statistiky.html
│
├── db_config.py              # Konfigurace databáze
├── diagnose.py               # Diagnostika obsahu databáze
├── fix_db.py                 # Opravy dat v databázi
├── hejbni_kostrou.py         # Hlavní Flask aplikace
├── import_bodovaci_databaze.py  # Import dat z bodovacího Excelu
├── import_skolni_roky.py     # Import školních roků
├── import_zaci.py            # Import dat žáků z Excelu
├── migrate_db.py             # Spouštění migrací
├── models.py                 # SQLAlchemy modely
│
├── bodovaci_databaze.xlsx    # Zdroj dat pro bodování
├── skolni_roky.xlsx          # Seznam školních roků
├── zaci.xlsx                 # Excel se seznamem žáků
├── zaci_zkouska.xlsx         # Testovací verze Excelu
│
├── requirements.txt          # Seznam závislostí
├── struktura.txt             # Pomocný popis struktury
└── readme.txt                # Starší README (pro porovnání)
```

---

## 📦 Použité technologie

- **Python 3.12**
- **Flask** – webový framework
- **SQLAlchemy** – ORM vrstva
- **Alembic / Flask-Migrate** – databázové migrace
- **Jinja2** – HTML šablonovací systém
- **Pandas** – zpracování Excel souborů
- **Openpyxl** – čtení `.xlsx`

---

## 📋 Requirements

Seznam závislostí z `requirements.txt`:

```
alembic==1.14.1
blinker==1.9.0
click==8.1.8
colorama==0.4.6
et_xmlfile==2.0.0
Flask==3.1.0
Flask-Migrate==4.1.0
Flask-SQLAlchemy==3.1.1
greenlet==3.1.1
itsdangerous==2.2.0
Jinja2==3.1.5
Mako==1.3.9
MarkupSafe==3.0.2
numpy==2.2.3
openpyxl==3.1.5
pandas==2.2.3
python-dateutil==2.9.0.post0
python-dotenv==1.0.1
pytz==2025.1
six==1.17.0
SQLAlchemy==2.0.38
typing_extensions==4.12.2
tzdata==2025.1
Werkzeug==3.1.3
```

📥 Instalace:
```bash
pip install -r requirements.txt
```

---

✅ Projekt je připraven ke spuštění lokálně. Pro další pomoc nebo rozšíření napiš Codymu 😎💻