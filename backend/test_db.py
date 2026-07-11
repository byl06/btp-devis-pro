from database import Database

db = Database()

# Tester la récupération des utilisateurs
users = db.fetch_all("SELECT * FROM utilisateur")
print("👥 Utilisateurs:", users)

# Tester la récupération des settings
settings = db.fetch_all("SELECT * FROM settings")
print("⚙️ Settings:", settings)