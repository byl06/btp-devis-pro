import requests

SUPABASE_URL = "https://aoqiveekzucqjhqdwiql.supabase.co"
SUPABASE_KEY = "TeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"  # ← Ta clé service_role

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Créer l'admin via l'API REST
admin_data = {
    "id_user": 1,
    "nom": "Admin BTP",
    "email": "bylgaitb@gmail.com",
    "mot_de_passe": "000000",
    "mot_de_passe_hash": "hash_ici",
    "entreprise": "BTP Pro",
    "telephone": "+229 90000000"
}

response = requests.post(
    f"{SUPABASE_URL}/rest/v1/utilisateur",
    headers=headers,
    json=admin_data
)

print(f"Status: {response.status_code}")
print(f"Réponse: {response.json() if response.text else 'OK'}")