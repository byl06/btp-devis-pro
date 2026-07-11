import requests

SUPABASE_URL = "https://aoqiveekzucqjhqdwiql.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODIyMzIyODUsImV4cCI6MjA5NzgwODI4NX0.XTxOqQLUGoNAfcWaLBXjBUxHoNTmgl3bRbcFYe9tdeI"  # ← Ta clé anon public

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Tester la connexion à la table utilisateur
try:
    response = requests.get(f"{SUPABASE_URL}/rest/v1/utilisateur?select=*", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Réponse: {response.json()}")
except Exception as e:
    print(f"❌ Erreur: {e}")