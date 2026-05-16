import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Vérifier les utilisateurs
cursor.execute("SELECT id_user, email, nom FROM utilisateur")
users = cursor.fetchall()
print("=== UTILISATEURS ===")
for u in users:
    print(f"ID={u[0]}, Email={u[1]}, Nom={u[2]}")

# Vérifier les abonnements
cursor.execute("SELECT id_user, statut, date_fin, type_abonnement FROM abonnements")
abos = cursor.fetchall()
print("\n=== ABONNEMENTS ===")
for a in abos:
    print(f"User ID={a[0]}, Statut={a[1]}, Date fin={a[2]}, Type={a[3]}")

cursor.close()
conn.close()