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

# 1. Voir tous les utilisateurs
cursor.execute("SELECT id_user, email, mot_de_passe FROM utilisateur")
all_users = cursor.fetchall()
print("=== UTILISATEURS DANS LA BASE ===")
for u in all_users:
    print(f"ID={u[0]}, Email={u[1]}, Mot de passe stocké={u[2]}")

# 2. Chercher bylgaitb@gmail.com
cursor.execute("SELECT id_user, email, mot_de_passe FROM utilisateur WHERE email = 'bylgaitb@gmail.com'")
user = cursor.fetchone()

if user:
    print(f"\n✅ Utilisateur trouvé: ID={user[0]}, Email={user[1]}")
    
    # 3. Mettre à jour le mot de passe
    new_password = "000000"
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    cursor.execute("""
        UPDATE utilisateur 
        SET mot_de_passe = %s, mot_de_passe_hash = %s
        WHERE email = 'bylgaitb@gmail.com'
    """, (new_password, hashed.decode()))
    
    print(f"✅ Mot de passe mis à jour: {new_password}")
    print(f"Nouveau hash: {hashed.decode()}")
    
else:
    print("\n❌ Utilisateur NON trouvé, création...")
    new_password = "000000"
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    
    cursor.execute("""
        INSERT INTO utilisateur (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
        VALUES (1, 'Admin BTP', 'bylgaitb@gmail.com', %s, %s, 'BTP Pro', '+229 90000000')
    """, (new_password, hashed.decode()))
    print(f"✅ Utilisateur créé avec mot de passe {new_password}")

# 4. Abonnement
cursor.execute("DELETE FROM abonnements WHERE id_user = 1")
cursor.execute("""
    INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (1, 'actif', NOW(), NOW() + INTERVAL '3650 days', 'illimite')
""")

# 5. Settings
cursor.execute("DELETE FROM settings WHERE id_user = 1")
cursor.execute("""
    INSERT INTO settings (id_user, company_name, created_at, updated_at)
    VALUES (1, 'BTP Devis Pro', NOW(), NOW())
""")

conn.commit()

# 6. Vérification finale
cursor.execute("SELECT id_user, email, mot_de_passe FROM utilisateur WHERE email = 'bylgaitb@gmail.com'")
final_user = cursor.fetchone()
print(f"\n=== VÉRIFICATION FINALE ===")
print(f"Email: {final_user[1]}")
print(f"Mot de passe stocké: {final_user[2]}")

cursor.close()
conn.close()

print("\n🔑 Connecte-toi avec:")
print("   Email: bylgaitb@gmail.com")
print("   Mot de passe: 000000")