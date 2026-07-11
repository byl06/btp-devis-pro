import psycopg2

try:
    conn = psycopg2.connect(
        host='aws-0-eu-west-1.pooler.supabase.com',
        port=6543,
        database='postgres',
        user='postgres',
        password='Btbdevispro@2006',
        options='-c project=aoqiveekzucqjhqdwiql'
    )
    print("✅ Connexion réussie !")
    conn.close()
except Exception as e:
    print(f"❌ Erreur: {e}")