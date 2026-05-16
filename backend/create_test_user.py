import psycopg2
import bcrypt
from datetime import datetime, timedelta

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Vérifier si l'utilisateur existe déjà
cursor.execute("SELECT id_user FROM utilisateur WHERE email = 'client@test.com'")
existing = cursor.fetchone()

if not existing:
    password = "123456"
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Créer l'utilisateur (sans spécifier id_user, PostgreSQL l'attribue automatiquement)
    cursor.execute("""
        INSERT INTO utilisateur (nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, ('Client Test', 'client@test.com', password, hashed.decode(), 'Entreprise Test', '+229 90000001'))
    
    # Récupérer l'ID généré
    cursor.execute("SELECT lastval()")
    user_id = cursor.fetchone()[0]
    
    # Abonnement essai 14 jours
    date_fin = datetime.now() + timedelta(days=14)
    cursor.execute("""
        INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
        VALUES (%s, 'actif', %s, %s, 'essai')
    """, (user_id, datetime.now(), date_fin))
    
    # Settings
    cursor.execute("""
        INSERT INTO settings (id_user, company_name, created_at, updated_at)
        VALUES (%s, %s, %s, %s)
    """, (user_id, 'Entreprise Test', datetime.now(), datetime.now()))
    
    conn.commit()
    print(f"✅ Utilisateur test créé avec ID={user_id}")
    print("📧 Email: client@test.com")
    print("🔑 Mot de passe: 123456")
else:
    print(f"ℹ️ L'utilisateur client@test.com existe déjà avec ID={existing[0]}")

cursor.close()
conn.close()