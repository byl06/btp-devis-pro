import psycopg2

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Vérifier l'utilisateur
cursor.execute("SELECT id_user, email, mot_de_passe, mot_de_passe_hash FROM utilisateur WHERE email = 'bylgaitb@gmail.com'")
user = cursor.fetchone()
if user:
    print(f"✅ Utilisateur trouvé: ID={user[0]}, Email={user[1]}")
    print(f"Hash stocké: {user[3]}")
else:
    print("❌ Utilisateur NON trouvé")

cursor.close()
conn.close()
