import sqlite3
import os

db_path = os.path.join(os.environ['APPDATA'], 'BTPDevisPro', 'btp_devis.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Voir les clients sans utilisateur
cursor.execute("SELECT id_client, nom, id_user FROM CLIENT WHERE id_user IS NULL")
orphans = cursor.fetchall()
print(f"🧹 Clients orphelins trouvés: {len(orphans)}")
for c in orphans:
    print(f"   - {c[1]} (ID: {c[0]})")

# Supprimer les clients orphelins
cursor.execute("DELETE FROM CLIENT WHERE id_user IS NULL")
print(f"✅ Clients orphelins supprimés")

# Voir les projets sans utilisateur
cursor.execute("SELECT id_projet, nom_projet, id_user FROM PROJET WHERE id_user IS NULL")
orphans_projets = cursor.fetchall()
print(f"🧹 Projets orphelins trouvés: {len(orphans_projets)}")
for p in orphans_projets:
    print(f"   - {p[1]} (ID: {p[0]})")

# Supprimer les projets orphelins
cursor.execute("DELETE FROM PROJET WHERE id_user IS NULL")
print(f"✅ Projets orphelins supprimés")

conn.commit()
conn.close()
print("\n🎉 Nettoyage terminé !")