import sqlite3
import os
from datetime import datetime, timedelta

db_path = os.path.join(os.environ['APPDATA'], 'BTPDevisPro', 'btp_devis.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Vérifier l'admin
cursor.execute("SELECT * FROM UTILISATEUR WHERE email = 'bylgaitb@gmail.com'")
admin = cursor.fetchone()
print(f"Admin trouvé: {admin}")

# Ajouter un abonnement illimité
cursor.execute('''
    INSERT OR REPLACE INTO ABONNEMENTS (id_user, statut, date_debut, date_fin, type_abonnement)
    VALUES (1, 'actif', ?, ?, 'illimite')
''', (datetime.now(), datetime.now() + timedelta(days=365*100)))

conn.commit()

# Vérifier
cursor.execute("SELECT * FROM ABONNEMENTS WHERE id_user = 1")
abonnement = cursor.fetchone()
print(f"Abonnement: {abonnement}")

conn.close()
print("✅ Abonnement admin créé")