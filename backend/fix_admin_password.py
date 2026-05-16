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

# Vérifier l'utilisateur
cursor.execute("SELECT id_user, email FROM utilisateur WHERE email = 'bylgaitb@gmail.com'")
user = cursor.fetchone()
print(f"Utilisateur trouvé: {user}")

# Générer le bon hash pour "000000"
password = "000000"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
print(f"Nouveau hash: {hashed.decode()}")

# Mettre à jour le mot de passe (sans INSERT)
cursor.execute("""
    UPDATE utilisateur 
    SET mot_de_passe = %s, mot_de_passe_hash = %s
    WHERE email = 'bylgaitb@gmail.com'
""", (password, hashed.decode()))

# Abonnement
cursor.execute("DELETE FROM abonnements WHERE id_user = 1")
cursor.execute("""
    INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (1, 'actif', NOW(), NOW() + INTERVAL '3650 days', 'illimite')
""")

# Settings
cursor.execute("DELETE FROM settings WHERE id_user = 1")
cursor.execute("""
    INSERT INTO settings (id_user, company_name, created_at, updated_at)
    VALUES (1, 'BTP Devis Pro', NOW(), NOW())
""")

conn.commit()
print("\n✅ Admin mis à jour avec succès !")
print("Email: bylgaitb@gmail.com")
print("Mot de passe: 000000")

cursor.close()
conn.close()