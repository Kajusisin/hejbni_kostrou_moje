import os
from flask_sqlalchemy import SQLAlchemy

# 🔹 Zajištění existence složky `instance/`
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# 🔹 Cesta k databázi
db_path = os.path.join(instance_path, "database.db")
DATABASE_URI = f"sqlite:///{db_path}"

# 🔹 Inicializace SQLAlchemy
db = SQLAlchemy()
