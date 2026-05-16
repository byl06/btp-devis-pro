import psycopg2

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Supprimer les anciennes données
cursor.execute("DELETE FROM abonnements WHERE id_user = 1")
cursor.execute("DELETE FROM settings WHERE id_user = 1")
cursor.execute("DELETE FROM utilisateur WHERE id_user = 1")

# Créer l'admin avec le NOUVEAU HASH
cursor.execute("""
    INSERT INTO utilisateur (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
    VALUES (1, 'Admin BTP', 'bylgaitb@gmail.com', '000000', '$2b$12$IXKaOV1lYOdDgvvgOIW2s.tZoNi40p9AJ/tWjxZJwCh3diCuz4Q92', 'BTP Pro', '+229 90000000')
""")

cursor.execute("""
    INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (1, 'actif', NOW(), NOW() + INTERVAL '3650 days', 'illimite')
""")

cursor.execute("""
    INSERT INTO settings (id_user, company_name, created_at, updated_at)
    VALUES (1, 'BTP Devis Pro', NOW(), NOW())
""")

conn.commit()
cursor.close()
conn.close()

print("✅ Admin créé avec le bon hash !")