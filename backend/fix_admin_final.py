import psycopg2

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Voir tous les utilisateurs
cursor.execute("SELECT id_user, email, nom FROM utilisateur")
print("=== AVANT CORRECTION ===")
for u in cursor.fetchall():
    print(f"ID={u[0]}, Email={u[1]}, Nom={u[2]}")

# Mettre à jour l'admin pour qu'il ait ID=1
cursor.execute("""
    UPDATE utilisateur SET id_user = 1 WHERE email = 'bylgaitb@gmail.com'
""")

# Supprimer l'ancien ID=1 s'il existe (autre utilisateur)
cursor.execute("""
    DELETE FROM utilisateur WHERE id_user = 1 AND email != 'bylgaitb@gmail.com'
""")

# Réinitialiser la séquence
cursor.execute("SELECT setval('utilisateur_id_user_seq', (SELECT MAX(id_user) FROM utilisateur))")

conn.commit()

# Voir après correction
cursor.execute("SELECT id_user, email, nom FROM utilisateur")
print("\n=== APRÈS CORRECTION ===")
for u in cursor.fetchall():
    print(f"ID={u[0]}, Email={u[1]}, Nom={u[2]}")

cursor.close()
conn.close()
print("\n✅ Admin forcé à ID=1")