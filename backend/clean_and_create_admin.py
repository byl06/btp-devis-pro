import psycopg2
import bcrypt

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Nettoyer toutes les tables
cursor.execute("DELETE FROM paiements")
cursor.execute("DELETE FROM notifications")
cursor.execute("DELETE FROM settings")
cursor.execute("DELETE FROM abonnements")
cursor.execute("DELETE FROM ligne_devis")
cursor.execute("DELETE FROM facture")
cursor.execute("DELETE FROM devis")
cursor.execute("DELETE FROM client")
cursor.execute("DELETE FROM projet")
cursor.execute("DELETE FROM utilisateur")

# Réinitialiser les séquences
cursor.execute("SELECT setval('utilisateur_id_user_seq', 1, false)")

# Créer l'admin UNIQUE
password = "000000"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

cursor.execute("""
    INSERT INTO utilisateur (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
    VALUES (1, 'Admin BTP', 'bylgaitb@gmail.com', %s, %s, 'BTP Pro', '+229 90000000')
""", (password, hashed.decode()))

from datetime import datetime, timedelta
date_fin = datetime.now() + timedelta(days=365*100)

cursor.execute("""
    INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (1, 'actif', %s, %s, 'illimite')
""", (datetime.now(), date_fin))

cursor.execute("""
    INSERT INTO settings (id_user, company_name, created_at, updated_at)
    VALUES (1, 'BTP Devis Pro', %s, %s)
""", (datetime.now(), datetime.now()))

conn.commit()

print("✅ Base nettoyée et admin unique créé !")
print("📧 Email: bylgaitb@gmail.com")
print("🔑 Mot de passe: 000000")

cursor.close()
conn.close()