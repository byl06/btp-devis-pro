import psycopg2

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Le nouveau hash généré
nouveau_hash = "$2b$12$k6wJhiYBiH6s7ONsDX9a7O/nwsbG6L36FUg56b5Y7a8QxSGgUONgu"

cursor.execute("""
    UPDATE utilisateur 
    SET mot_de_passe_hash = %s, mot_de_passe = '000000'
    WHERE email = 'bylgaitb@gmail.com'
""", (nouveau_hash,))

conn.commit()
print(f"✅ Mis à jour: {cursor.rowcount} utilisateur(s) modifié(s)")

cursor.close()
conn.close()