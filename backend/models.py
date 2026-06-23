from datetime import datetime, timedelta
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
        return self.db.insert("utilisateur", data)
    
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
        user = self.get_by_email(email)
        if user:
            stored_hash = user.get('mot_de_passe_hash')
            if stored_hash:
                if isinstance(stored_hash, str):
                    stored_hash = stored_hash.encode('utf-8')
                if isinstance(mot_de_passe, str):
                    mot_de_passe = mot_de_passe.encode('utf-8')
                if bcrypt.checkpw(mot_de_passe, stored_hash):
                    return user
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
        return self.db.find("client", "id_user", id_user)
    
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
        return self.db.find("projet", "id_user", id_user)
    
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
        return self.db.find("devis", "id_user", id_user)
    
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
        # Requête directe avec fetch_all pour être sûr
        query = f"SELECT * FROM abonnements WHERE id_user = {id_user}"
        result = self.db.fetch_all(query)
        print(f"🔍 Abonnement get_by_user({id_user}): {result}")
        return result[0] if result else None
    
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