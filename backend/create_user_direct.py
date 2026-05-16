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

# 1. Supprimer l'ancien utilisateur avec ID=1 s'il existe
cursor.execute("DELETE FROM abonnements WHERE id_user = 1")
cursor.execute("DELETE FROM settings WHERE id_user = 1")
cursor.execute("DELETE FROM utilisateur WHERE id_user = 1")

# 2. Créer le nouvel admin avec ID=1
password = "000000"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

cursor.execute("""
    INSERT INTO utilisateur (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
    VALUES (1, 'Admin BTP', 'bylgaitb@gmail.com', %s, %s, 'BTP Pro', '+229 90000000')
""", (password, hashed.decode()))

# 3. Abonnement
cursor.execute("""
    INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (1, 'actif', NOW(), NOW() + INTERVAL '3650 days', 'illimite')
""")

# 4. Settings
cursor.execute("""
    INSERT INTO settings (id_user, company_name, created_at, updated_at)
    VALUES (1, 'BTP Devis Pro', NOW(), NOW())
""")

conn.commit()
print("✅ Admin créé avec succès !")
print("Email: bylgaitb@gmail.com")
print("Mot de passe: 000000")

cursor.close()
conn.close()