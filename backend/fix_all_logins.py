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

# Liste des comptes à créer/mettre à jour
comptes = [
    {'email': 'admin@btp.com', 'password': 'admin123', 'nom': 'Admin BTP', 'entreprise': 'BTP Pro'},
    {'email': 'bylgaitb@gmail.com', 'password': '000000', 'nom': 'BACHIROU by', 'entreprise': 'Bts metal'}
]

for compte in comptes:
    # Générer le bon hash
    hashed = bcrypt.hashpw(compte['password'].encode('utf-8'), bcrypt.gensalt())
    
    # Vérifier si l'utilisateur existe
    cursor.execute("SELECT id_user FROM utilisateur WHERE email = %s", (compte['email'],))
    existing = cursor.fetchone()
    
    if existing:
        # Mettre à jour
        cursor.execute("""
            UPDATE utilisateur 
            SET mot_de_passe = %s, mot_de_passe_hash = %s, nom = %s, entreprise = %s
            WHERE email = %s
        """, (compte['password'], hashed.decode(), compte['nom'], compte['entreprise'], compte['email']))
        print(f"✅ Mis à jour: {compte['email']} / {compte['password']}")
    else:
        # Créer
        cursor.execute("""
            INSERT INTO utilisateur (nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
            VALUES (%s, %s, %s, %s, %s, '+229 90000000')
        """, (compte['nom'], compte['email'], compte['password'], hashed.decode(), compte['entreprise']))
        
        # Récupérer l'ID
        cursor.execute("SELECT id_user FROM utilisateur WHERE email = %s", (compte['email'],))
        user_id = cursor.fetchone()[0]
        
        # Ajouter abonnement
        cursor.execute("""
            INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
            VALUES (%s, 'actif', NOW(), NOW() + INTERVAL '3650 days', 'illimite')
        """, (user_id,))
        
        # Ajouter settings
        cursor.execute("""
            INSERT INTO settings (id_user, company_name, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
        """, (user_id, compte['entreprise']))
        
        print(f"✅ Créé: {compte['email']} / {compte['password']}")

conn.commit()
print("\n🎉 Tous les comptes sont prêts !")

cursor.close()
conn.close()