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

# Vérifier l'ID maximum
cursor.execute("SELECT MAX(id_user) FROM utilisateur")
max_id = cursor.fetchone()[0]
new_id = (max_id or 0) + 1
print(f"Nouvel ID: {new_id}")

# Créer l'utilisateur bylgaitb@gmail.com
new_password = "000000"
hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

cursor.execute("""
    INSERT INTO utilisateur (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
    VALUES (%s, 'Admin BTP', 'bylgaitb@gmail.com', %s, %s, 'BTP Pro', '+229 90000000')
""", (new_id, new_password, hashed.decode()))

# Abonnement pour ce nouvel utilisateur
cursor.execute("""
    INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (%s, 'actif', NOW(), NOW() + INTERVAL '3650 days', 'illimite')
""", (new_id,))

# Settings pour ce nouvel utilisateur
cursor.execute("""
    INSERT INTO settings (id_user, company_name, created_at, updated_at)
    VALUES (%s, 'BTP Devis Pro', NOW(), NOW())
""", (new_id,))

conn.commit()

print(f"\n✅ Utilisateur créé avec ID={new_id}")
print("Email: bylgaitb@gmail.com")
print("Mot de passe: 000000")

cursor.close()
conn.close()