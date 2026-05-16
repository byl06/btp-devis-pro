from datetime import datetime
from database import Database
import bcrypt

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
        # Convertir en string pour PostgreSQL
        hash_str = mot_de_passe_hash.decode('utf-8')
        
        query = """
        INSERT INTO utilisateur (nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_query(query, (nom, email, mot_de_passe, hash_str, entreprise, telephone))
    
    def get_by_email(self, email):
        query = "SELECT * FROM utilisateur WHERE email = %s"
        return self.db.fetch_one(query, (email,))
    
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
        query = "SELECT id_user, nom, email, entreprise, telephone FROM utilisateur WHERE id_user = %s"
        return self.db.fetch_one(query, (id_user,))

class Client:
    def __init__(self):
        self.db = Database()
    
    def create(self, nom, telephone, email, adresse, id_user):
        query = "INSERT INTO client (nom, telephone, email, adresse, id_user) VALUES (%s, %s, %s, %s, %s)"
        return self.db.execute_query(query, (nom, telephone, email, adresse, id_user))
    
    def get_all(self, id_user):
        query = "SELECT * FROM client WHERE id_user = %s ORDER BY nom"
        return self.db.fetch_all(query, (id_user,))
    
    def get_by_id(self, id_client):
        query = "SELECT * FROM client WHERE id_client = %s"
        return self.db.fetch_one(query, (id_client,))
    
    def update(self, id_client, nom, telephone, email, adresse):
        query = "UPDATE client SET nom=%s, telephone=%s, email=%s, adresse=%s WHERE id_client=%s"
        return self.db.execute_query(query, (nom, telephone, email, adresse, id_client))
    
    def delete(self, id_client):
        query = "DELETE FROM client WHERE id_client = %s"
        return self.db.execute_query(query, (id_client,))

class Projet:
    def __init__(self):
        self.db = Database()
    
    def create(self, nom_projet, description, localisation, id_user):
        query = "INSERT INTO projet (nom_projet, description, localisation, id_user) VALUES (%s, %s, %s, %s)"
        return self.db.execute_query(query, (nom_projet, description, localisation, id_user))
    
    def get_all(self, id_user):
        query = "SELECT * FROM projet WHERE id_user = %s ORDER BY nom_projet"
        return self.db.fetch_all(query, (id_user,))
    
    def get_by_id(self, id_projet):
        query = "SELECT * FROM projet WHERE id_projet = %s"
        return self.db.fetch_one(query, (id_projet,))
    
    def update(self, id_projet, nom_projet, description, localisation):
        query = "UPDATE projet SET nom_projet=%s, description=%s, localisation=%s WHERE id_projet=%s"
        return self.db.execute_query(query, (nom_projet, description, localisation, id_projet))
    
    def delete(self, id_projet):
        query = "DELETE FROM projet WHERE id_projet = %s"
        return self.db.execute_query(query, (id_projet,))

class Devis:
    def __init__(self):
        self.db = Database()
    
    def create(self, id_client, id_user, id_projet, lignes):
        total_materiaux = sum(float(ligne['quantite']) * float(ligne['prix_unitaire']) for ligne in lignes)
        total = total_materiaux * 1.2
        query = """
        INSERT INTO devis (date_creation, total, statut, id_client, id_user, id_projet)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor = self.db.execute_query(query, (datetime.now(), total, 'brouillon', id_client, id_user, id_projet))
        if cursor:
            id_devis = cursor.lastrowid
            for ligne in lignes:
                total_ligne = float(ligne['quantite']) * float(ligne['prix_unitaire'])
                query_ligne = """
                INSERT INTO ligne_devis (designation, quantite, prix_unitaire, total_ligne, id_devis)
                VALUES (%s, %s, %s, %s, %s)
                """
                self.db.execute_query(query_ligne, (ligne['designation'], ligne['quantite'], ligne['prix_unitaire'], total_ligne, id_devis))
            return id_devis
        return None
    
    def get_by_user(self, id_user):
        query = """
        SELECT d.*, c.nom as client_nom, p.nom_projet
        FROM devis d
        JOIN client c ON d.id_client = c.id_client
        JOIN projet p ON d.id_projet = p.id_projet
        WHERE d.id_user = %s
        ORDER BY d.date_creation DESC
        """
        return self.db.fetch_all(query, (id_user,))
    
    def get_details(self, id_devis):
        query_devis = """
        SELECT d.*, c.nom as client_nom, c.email as client_email, c.telephone as client_telephone, c.adresse as client_adresse,
               p.nom_projet, p.description as projet_description, p.localisation
        FROM devis d
        JOIN client c ON d.id_client = c.id_client
        JOIN projet p ON d.id_projet = p.id_projet
        WHERE d.id_devis = %s
        """
        devis = self.db.fetch_one(query_devis, (id_devis,))
        if devis:
            query_lignes = "SELECT * FROM ligne_devis WHERE id_devis = %s"
            devis['lignes'] = self.db.fetch_all(query_lignes, (id_devis,))
        return devis
    
    def update_status(self, id_devis, statut):
        query = "UPDATE devis SET statut = %s WHERE id_devis = %s"
        return self.db.execute_query(query, (statut, id_devis))
    
    def delete(self, id_devis):
        self.db.execute_query("DELETE FROM ligne_devis WHERE id_devis = %s", (id_devis,))
        return self.db.execute_query("DELETE FROM devis WHERE id_devis = %s", (id_devis,))

class Facture:
    def __init__(self):
        self.db = Database()
    
    def create(self, id_devis, montant):
        query = "INSERT INTO facture (date_facture, montant, statut, id_devis) VALUES (%s, %s, %s, %s)"
        return self.db.execute_query(query, (datetime.now(), float(montant), 'non payée', id_devis))
    
    def get_by_devis(self, id_devis):
        query = "SELECT * FROM facture WHERE id_devis = %s"
        return self.db.fetch_one(query, (id_devis,))
    
    def update_status(self, id_facture, statut):
        query = "UPDATE facture SET statut = %s WHERE id_facture = %s"
        return self.db.execute_query(query, (statut, id_facture))

class Abonnement:
    def __init__(self):
        self.db = Database()
    
    def get_by_user(self, id_user):
        query = "SELECT * FROM abonnements WHERE id_user = %s"
        return self.db.fetch_one(query, (id_user,))
    
    def create_trial(self, id_user):
        from datetime import datetime, timedelta
        date_fin = datetime.now() + timedelta(days=14)
        query = """
        INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
        VALUES (%s, 'actif', %s, %s, 'essai')
        """
        return self.db.execute_query(query, (id_user, datetime.now(), date_fin))

class Settings:
    def __init__(self):
        self.db = Database()
    
    def get_by_user(self, id_user):
        query = "SELECT * FROM settings WHERE id_user = %s"
        return self.db.fetch_one(query, (id_user,))
    
    def create_default(self, id_user):
        from datetime import datetime
        query = "INSERT INTO settings (id_user, company_name, created_at, updated_at) VALUES (%s, %s, %s, %s)"
        return self.db.execute_query(query, (id_user, 'Mon Entreprise', datetime.now(), datetime.now()))