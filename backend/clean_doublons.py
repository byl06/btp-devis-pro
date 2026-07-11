import psycopg2

conn = psycopg2.connect(
    host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
    port=5432,
    database='btp_devis',
    user='btp_user',
    password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
)

cursor = conn.cursor()

# Supprimer toutes les lignes de devis
cursor.execute("DELETE FROM ligne_devis")
# Supprimer tous les devis
cursor.execute("DELETE FROM devis")
# Réinitialiser la séquence des IDs
cursor.execute("SELECT setval('devis_id_devis_seq', 1, false)")

conn.commit()
print("✅ Tous les devis ont été supprimés (plus de doublons)")

cursor.close()
conn.close()