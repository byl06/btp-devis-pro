import psycopg2

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

cursor.execute("SELECT id_user, email, nom FROM utilisateur WHERE email = 'bylgaitb@gmail.com'")
user = cursor.fetchone()
print(f"Admin trouvé: ID={user[0]}, Email={user[1]}, Nom={user[2]}")

cursor.close()
conn.close()