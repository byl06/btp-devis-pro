import requests
import json
import re
from datetime import datetime, timedelta
import bcrypt

class Database:
    def __init__(self):
        self.supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        self.supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        self.headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.create_tables()
        print("✅ Connecté à Supabase (API REST)")

    def create_tables(self):
        sql_script = """
        CREATE TABLE IF NOT EXISTS utilisateur (
            id_user SERIAL PRIMARY KEY,
            nom TEXT,
            email TEXT UNIQUE,
            mot_de_passe TEXT,
            mot_de_passe_hash TEXT,
            entreprise TEXT,
            telephone TEXT
        );
        
        CREATE TABLE IF NOT EXISTS client (
            id_client SERIAL PRIMARY KEY,
            nom TEXT,
            telephone TEXT,
            email TEXT,
            adresse TEXT,
            id_user INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS projet (
            id_projet SERIAL PRIMARY KEY,
            nom_projet TEXT,
            description TEXT,
            localisation TEXT,
            id_user INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS devis (
            id_devis SERIAL PRIMARY KEY,
            date_creation TIMESTAMP,
            total REAL,
            statut TEXT DEFAULT 'brouillon',
            id_client INTEGER,
            id_user INTEGER,
            id_projet INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS ligne_devis (
            id_ligne SERIAL PRIMARY KEY,
            designation TEXT,
            quantite INTEGER,
            prix_unitaire REAL,
            total_ligne REAL,
            id_devis INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS facture (
            id_facture SERIAL PRIMARY KEY,
            date_facture TIMESTAMP,
            montant REAL,
            statut TEXT DEFAULT 'non payée',
            id_devis INTEGER UNIQUE
        );
        
        CREATE TABLE IF NOT EXISTS abonnements (
            id_abonnement SERIAL PRIMARY KEY,
            id_user INTEGER NOT NULL,
            statut TEXT DEFAULT 'actif',
            date_debut TIMESTAMP,
            date_fin TIMESTAMP,
            type_abonnement TEXT DEFAULT 'mensuel'
        );
        
        CREATE TABLE IF NOT EXISTS settings (
            id_setting SERIAL PRIMARY KEY,
            id_user INTEGER NOT NULL,
            company_name TEXT,
            company_logo TEXT,
            company_email TEXT,
            company_phone TEXT,
            company_address TEXT,
            primary_color TEXT DEFAULT '#1E3A8A',
            secondary_color TEXT DEFAULT '#7C3AED',
            accent_color TEXT DEFAULT '#06B6D4',
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS notifications (
            id_notification SERIAL PRIMARY KEY,
            id_user INTEGER NOT NULL,
            message TEXT,
            type TEXT DEFAULT 'info',
            est_lue INTEGER DEFAULT 0,
            date_creation TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS paiements (
            id_paiement SERIAL PRIMARY KEY,
            id_user INTEGER NOT NULL,
            montant REAL,
            date_paiement TIMESTAMP,
            reference_paiement TEXT,
            methode TEXT,
            statut TEXT DEFAULT 'valide'
        );
        """

        headers = {
            "Authorization": f"Bearer {self.supabase_key}",
            "apikey": self.supabase_key,
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{self.supabase_url}/rest/v1/rpc/exec_sql",
            headers=headers,
            json={"query": sql_script}
        )

        if response.status_code == 200:
            print("✅ Tables créées/vérifiées")
        else:
            print(f"⚠️ Erreur création tables: {response.text}")

        self._create_admin_if_empty()

    def _create_admin_if_empty(self):
        response = requests.get(
            f"{self.supabase_url}/rest/v1/utilisateur?email=eq.bylgaitb@gmail.com&select=id_user",
            headers=self.headers
        )

        if response.status_code == 200 and not response.json():
            password = "000000"
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            admin_data = {
                "id_user": 1,
                "nom": "Admin BTP",
                "email": "bylgaitb@gmail.com",
                "mot_de_passe": password,
                "mot_de_passe_hash": hashed.decode(),
                "entreprise": "BTP Pro",
                "telephone": "+229 90000000"
            }

            response = requests.post(
                f"{self.supabase_url}/rest/v1/utilisateur",
                headers=self.headers,
                json=admin_data
            )

            if response.status_code in [200, 201]:
                print("✅ Admin créé (bylgaitb@gmail.com / 000000)")

                date_fin = datetime.now() + timedelta(days=365*100)
                abo_data = {
                    "id_user": 1,
                    "statut": "actif",
                    "date_debut": datetime.now().isoformat(),
                    "date_fin": date_fin.isoformat(),
                    "type_abonnement": "illimite"
                }
                requests.post(
                    f"{self.supabase_url}/rest/v1/abonnements",
                    headers=self.headers,
                    json=abo_data
                )

                settings_data = {
                    "id_user": 1,
                    "company_name": "BTP Devis Pro",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                requests.post(
                    f"{self.supabase_url}/rest/v1/settings",
                    headers=self.headers,
                    json=settings_data
                )

    def execute_query(self, query, params=None):
        return None

    def fetch_all(self, query, params=None):
        table = self._extract_table(query)
        if not table:
            return []
        
        url = f"{self.supabase_url}/rest/v1/{table}"
        filters = []
        
        # Extraire les filtres WHERE (ex: id_user = 1)
        import re
        where_match = re.search(r"WHERE\s+(\w+)\s*=\s*(\d+)", query, re.IGNORECASE)
        if where_match:
            column = where_match.group(1)
            value = where_match.group(2)
            filters.append(f"{column}=eq.{value}")
        
        # ORDER BY - Supabase attend un format spécifique
        order_match = re.search(r"ORDER\s+BY\s+(\w+)\s*(DESC|ASC)?", query, re.IGNORECASE)
        if order_match:
            order_col = order_match.group(1)
            order_dir = order_match.group(2) if order_match.group(2) else "asc"
            if order_dir.lower() == "desc":
                filters.append(f"order={order_col}.desc")
            else:
                filters.append(f"order={order_col}")
        
        if filters:
            url += "?" + "&".join(filters)
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Erreur fetch_all {table}: {response.text}")
                return []
        except Exception as e:
            print(f"❌ Erreur fetch_all: {e}")
            return []

    def fetch_one(self, query, params=None):
        results = self.fetch_all(query, params)
        return results[0] if results else None

    def find(self, table, column, value):
        # Convertir en int si c'est un ID
        if column == "id_user" or column == "id":
            try:
                value = int(value)
            except:
                pass
        
        url = f"{self.supabase_url}/rest/v1/{table}?{column}=eq.{value}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"❌ Erreur find: {e}")
            return []

    def insert(self, table, data):
        try:
            print(f"🔍 Insert dans {table}: {data}")
            
            response = requests.post(
                f"{self.supabase_url}/rest/v1/{table}",
                headers=self.headers,
                json=data
            )
            
            print(f"🔍 Status: {response.status_code}")
            print(f"🔍 Réponse brute: {response.text}")
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"❌ Erreur insert {table}: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur insert: {e}")
            return None

    def update(self, table, id_value, data, id_column="id"):
        try:
            response = requests.patch(
                f"{self.supabase_url}/rest/v1/{table}?{id_column}=eq.{id_value}",
                headers=self.headers,
                json=data
            )
            if response.status_code in [200, 204]:
                return True
            else:
                print(f"❌ Erreur update {table}: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Erreur update: {e}")
            return False

    def delete(self, table, id_value, id_column="id"):
        try:
            response = requests.delete(
                f"{self.supabase_url}/rest/v1/{table}?{id_column}=eq.{id_value}",
                headers=self.headers
            )
            if response.status_code in [200, 204]:
                return True
            else:
                print(f"❌ Erreur delete {table}: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Erreur delete: {e}")
            return False

    def _extract_table(self, query):
        query_lower = query.lower()
        if "from" in query_lower:
            parts = query_lower.split("from")
            if len(parts) > 1:
                table_part = parts[1].strip().split()[0]
                table_part = table_part.strip('"').strip("'").strip('`')
                return table_part
        return None

    def rollback(self):
        pass