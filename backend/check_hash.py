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

cursor.execute("SELECT mot_de_passe_hash FROM utilisateur WHERE email = 'bylgaitb@gmail.com'")
row = cursor.fetchone()
stored_hash = row[0]

print(f"Hash stocké: {stored_hash}")

# Tester le mot de passe 000000
password = "000000"
is_valid = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
print(f"Test du mot de passe '000000': {is_valid}")

# Tester d'autres mots de passe possibles
test_passwords = ["admin123", "Admin123", "password", "123456", "admin"]
for pwd in test_passwords:
    test = bcrypt.checkpw(pwd.encode('utf-8'), stored_hash.encode('utf-8'))
    if test:
        print(f"✅ Mot de passe trouvé: {pwd}")

cursor.close()
conn.close()