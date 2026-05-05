import sqlite3
import os

db_path = os.path.join(os.environ['APPDATA'], 'BTPDevisPro', 'btp_devis.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Ajouter la colonne id_user à CLIENT si elle n'existe pas
try:
    cursor.execute("ALTER TABLE CLIENT ADD COLUMN id_user INTEGER")
    print("✅ Colonne id_user ajoutée à CLIENT")
except sqlite3.OperationalError as e:
    print(f"⚠️ Colonne existe déjà ou erreur: {e}")

# Ajouter la colonne id_user à PROJET si elle n'existe pas
try:
    cursor.execute("ALTER TABLE PROJET ADD COLUMN id_user INTEGER")
    print("✅ Colonne id_user ajoutée à PROJET")
except sqlite3.OperationalError as e:
    print(f"⚠️ Colonne existe déjà ou erreur: {e}")

# Mettre à jour les clients existants pour les associer à leurs devis
cursor.execute("""
    UPDATE CLIENT SET id_user = (
        SELECT id_user FROM DEVIS WHERE DEVIS.id_client = CLIENT.id_client LIMIT 1
    ) WHERE id_user IS NULL
""")
print("✅ Clients existants mis à jour")

# Mettre à jour les projets existants pour les associer à leurs devis
cursor.execute("""
    UPDATE PROJET SET id_user = (
        SELECT id_user FROM DEVIS WHERE DEVIS.id_projet = PROJET.id_projet LIMIT 1
    ) WHERE id_user IS NULL
""")
print("✅ Projets existants mis à jour")

conn.commit()
conn.close()
print("\n🎉 Mise à jour terminée !")