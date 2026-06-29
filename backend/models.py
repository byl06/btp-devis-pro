from datetime import datetime, timedelta
from unittest import result
from database import Database
import bcrypt
import requests

class Utilisateur:
    def __init__(self):
        self.db = Database()
    
    def create(self, nom, email, mot_de_passe, entreprise, telephone):
        if isinstance(mot_de_passe, str):
         mot_de_passe_bytes = mot_de_passe.encode('utf-8')
        else:
         mot_de_passe_bytes = mot_de_passe
        salt = bcrypt.gensalt()
        mot_de_passe_hash = bcrypt.hashpw(mot_de_passe_bytes, salt)
        hash_str = mot_de_passe_hash.decode('utf-8')
    
        data = {
        "nom": nom,
        "email": email,
        "mot_de_passe": mot_de_passe,
        "mot_de_passe_hash": hash_str,
        "entreprise": entreprise,
        "telephone": telephone
 }
        result = self.db.insert("utilisateur", data)
        print(f"🔍 Résultat création utilisateur: {result}")
        return result
    
    def get_by_email(self, email):
        result = self.db.find("utilisateur", "email", email)
        return result[0] if result else None
    
    def verify_password(self, plain_password, hashed_password):
        if isinstance(plain_password, str):
            plain_password = plain_password.encode('utf-8')
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(plain_password, hashed_password)
    
    def authenticate(self, email, mot_de_passe):
        print(f"🔐 Tentative login pour: {email}")
        
        user = self.get_by_email(email)
        if not user:
            print("❌ Utilisateur non trouvé")
            return None
        
        stored_hash = user.get('mot_de_passe_hash')
        print(f"🔑 Hash stocké: {stored_hash}")
        print(f"🔑 Type du hash: {type(stored_hash)}")
        
        if not stored_hash:
            print("❌ Pas de hash stocké")
            return None
        
        # Convertir en bytes
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        if isinstance(mot_de_passe, str):
            mot_de_passe = mot_de_passe.encode('utf-8')
        
        print(f"🔑 Mot de passe testé: {mot_de_passe}")
        
        try:
            result = bcrypt.checkpw(mot_de_passe, stored_hash)
            print(f"✅ Résultat bcrypt: {result}")
            if result:
                return user
            else:
                print("❌ Mot de passe incorrect")
                return None
        except Exception as e:
            print(f"❌ Erreur bcrypt: {e}")
            return None
    
    def get_by_id(self, id_user):
        result = self.db.find("utilisateur", "id_user", id_user)
        return result[0] if result else None

class Client:
    def __init__(self):
        self.db = Database()
    
    def create(self, nom, telephone, email, adresse, id_user):
        data = {
            "nom": nom,
            "telephone": telephone,
            "email": email,
            "adresse": adresse,
            "id_user": id_user
        }
        return self.db.insert("client", data)
    
    def get_all(self, id_user):
        # Requête directe vers Supabase via l'API REST
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        response = requests.get(
            f"{supabase_url}/rest/v1/client?select=*",
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            all_clients = response.json()
            # Filtrer par id_user
            return [c for c in all_clients if c.get('id_user') == id_user]
        return []
    
    def get_by_id(self, id_client):
        result = self.db.find("client", "id_client", id_client)
        return result[0] if result else None
    
    def update(self, id_client, nom, telephone, email, adresse):
        data = {
            "nom": nom,
            "telephone": telephone,
            "email": email,
            "adresse": adresse
        }
        return self.db.update("client", id_client, data)
    
    def delete(self, id_client):
        return self.db.delete("client", id_client)

class Projet:
    def __init__(self):
        self.db = Database()
    
    def create(self, nom_projet, description, localisation, id_user):
        data = {
            "nom_projet": nom_projet,
            "description": description,
            "localisation": localisation,
            "id_user": id_user
        }
        return self.db.insert("projet", data)
    
    def get_all(self, id_user):
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        response = requests.get(
            f"{supabase_url}/rest/v1/projet?select=*",
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            all_projets = response.json()
            return [p for p in all_projets if p.get('id_user') == id_user]
        return []
    
    def get_by_id(self, id_projet):
        result = self.db.find("projet", "id_projet", id_projet)
        return result[0] if result else None
    
    def update(self, id_projet, nom_projet, description, localisation):
        data = {
            "nom_projet": nom_projet,
            "description": description,
            "localisation": localisation
        }
        return self.db.update("projet", id_projet, data)
    
    def delete(self, id_projet):
        return self.db.delete("projet", id_projet)

class Devis:
    def __init__(self):
        self.db = Database()

    def create(self, id_client, id_user, id_projet, lignes):
        try:
            total_materiaux = sum(float(ligne['quantite']) * float(ligne['prix_unitaire']) for ligne in lignes)
            total = total_materiaux * 1.2
            
            devis_data = {
                "date_creation": datetime.now().isoformat(),
                "total": total,
                "statut": "brouillon",
                "id_client": id_client,
                "id_user": id_user,
                "id_projet": id_projet
            }
            
            result = self.db.insert("devis", devis_data)
            
            if result and isinstance(result, list) and len(result) > 0:
                id_devis = result[0].get('id_devis')
            elif result and isinstance(result, dict):
                id_devis = result.get('id_devis')
            else:
                devis_list = self.db.fetch_all("SELECT id_devis FROM devis ORDER BY id_devis DESC LIMIT 1")
                id_devis = devis_list[0]['id_devis'] if devis_list else None
            
            if id_devis:
                for ligne in lignes:
                    total_ligne = float(ligne['quantite']) * float(ligne['prix_unitaire'])
                    ligne_data = {
                        "designation": ligne['designation'],
                        "quantite": ligne['quantite'],
                        "prix_unitaire": ligne['prix_unitaire'],
                        "total_ligne": total_ligne,
                        "id_devis": id_devis
                    }
                    self.db.insert("ligne_devis", ligne_data)
                
                return id_devis
            return None
            
        except Exception as e:
            print(f"❌ Erreur create_devis: {e}")
            return None
    
def get_by_user(self, id_user):
    import requests
    supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json"
    }
    
    print(f"🔍 get_by_user appelé avec id_user: {id_user}")
    
    # 1. Récupérer les devis de l'utilisateur
    response = requests.get(
        f"{supabase_url}/rest/v1/devis?id_user=eq.{id_user}&order=id_devis.desc",
        headers=headers
    )
    
    print(f"🔍 Status devis: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Erreur devis: {response.text}")
        return []
    
    devis_list = response.json()
    print(f"🔍 Devis trouvés: {len(devis_list)}")
    
    result = []
    for devis in devis_list:
        # 2. Récupérer le client séparément
        client_nom = "Client inconnu"
        if devis.get('id_client'):
            client_response = requests.get(
                f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
                headers=headers
            )
            if client_response.status_code == 200 and client_response.json():
                client = client_response.json()[0]
                client_nom = client.get('nom', 'Client inconnu')
        
        # 3. Récupérer le projet séparément
        projet_nom = "Projet inconnu"
        if devis.get('id_projet'):
            projet_response = requests.get(
                f"{supabase_url}/rest/v1/projet?id_projet=eq.{devis.get('id_projet')}",
                headers=headers
            )
            if projet_response.status_code == 200 and projet_response.json():
                projet = projet_response.json()[0]
                projet_nom = projet.get('nom_projet', 'Projet inconnu')
        
        devis['client_nom'] = client_nom
        devis['nom_projet'] = projet_nom
        result.append(devis)
    
    print(f"✅ {len(result)} devis retournés")
    return result
    
    def get_details(self, id_devis):
        result = self.db.find("devis", "id_devis", id_devis)
        if result and len(result) > 0:
            devis = result[0]
            lignes = self.db.find("ligne_devis", "id_devis", id_devis)
            devis['lignes'] = lignes
            return devis
        return None
    
    def update_status(self, id_devis, statut):
        return self.db.update("devis", id_devis, {"statut": statut})
    
    def delete(self, id_devis):
        self.db.delete("ligne_devis", id_devis, "id_devis")
        return self.db.delete("devis", id_devis)

class Facture:
    def __init__(self):
        self.db = Database()
    
    def create(self, id_devis, montant):
        data = {
            "date_facture": datetime.now().isoformat(),
            "montant": float(montant),
            "statut": "non payée",
            "id_devis": id_devis
        }
        return self.db.insert("facture", data)
    
    def get_by_devis(self, id_devis):
        result = self.db.find("facture", "id_devis", id_devis)
        return result[0] if result else None
    
    def update_status(self, id_facture, statut):
        return self.db.update("facture", id_facture, {"statut": statut})

class Abonnement:
    def __init__(self):
        self.db = Database()
    
    def get_by_user(self, id_user):
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        response = requests.get(
            f"{supabase_url}/rest/v1/abonnements?select=*",
            headers={
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            all_abos = response.json()
            for abo in all_abos:
                if abo.get('id_user') == id_user:
                    print(f"🔍 Abonnement get_by_user({id_user}): {abo}")
                    return abo
        print(f"🔍 Abonnement get_by_user({id_user}): None")
        return None
    
    def create_trial(self, id_user):
        date_fin = datetime.now() + timedelta(days=14)
        data = {
            "id_user": id_user,
            "statut": "actif",
            "date_debut": datetime.now().isoformat(),
            "date_fin": date_fin.isoformat(),
            "type_abonnement": "essai"
        }
        return self.db.insert("abonnements", data)

class Settings:
    def __init__(self):
        self.db = Database()
    
    def get_by_user(self, id_user):
        result = self.db.find("settings", "id_user", id_user)
        return result[0] if result else None
    
    def create_default(self, id_user):
        data = {
            "id_user": id_user,
            "company_name": "Mon Entreprise",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return self.db.insert("settings", data)