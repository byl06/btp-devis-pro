from flask_mail import Mail, Message
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
from datetime import datetime, timedelta
import io
from models import Utilisateur, Client, Projet, Devis, Facture, Abonnement, Settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from flask import send_from_directory
import os

app = Flask(__name__)
# Configuration SendGrid
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = ''  # ← Ta clé API SendGrid
app.config['MAIL_DEFAULT_SENDER'] = 'bylgaitb@gmail.com'  # Ton email

mail = Mail(app)

# Configuration CORS - Autorise toutes les origines (pour Render)
CORS(app, origins=["http://localhost:8000", "https://btp-devis-pro-1.onrender.com"], supports_credentials=True)
# Configuration JWT
app.config['JWT_SECRET_KEY'] = 'btp-devis-pro-super-secret-key-2024-32chars'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

jwt = JWTManager(app)

# Initialisation des modèles
utilisateur_model = Utilisateur()
client_model = Client()
projet_model = Projet()
devis_model = Devis()
facture_model = Facture()
abonnement_model = Abonnement()
settings_model = Settings()
# Servir les fichiers du frontend
@app.route('/')
def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, path)
# ==================== AUTHENTIFICATION ====================
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        existing = utilisateur_model.get_by_email(data['email'])
        if existing:
            return jsonify({'success': False, 'message': 'Email déjà utilisé'}), 400
        
        result = utilisateur_model.create(
            data['nom'], data['email'], data['mot_de_passe'],
            data['entreprise'], data['telephone']
        )
        
        # Vérifier si result est une liste ou un dict
        if result:
            # Récupérer l'ID du nouvel utilisateur
            if isinstance(result, list) and len(result) > 0:
                user_id = result[0].get('id_user')
            elif isinstance(result, dict):
                user_id = result.get('id_user')
            else:
                # Si on n'a pas d'ID, récupérer le dernier utilisateur créé
                user = utilisateur_model.get_by_email(data['email'])
                if user:
                    user_id = user.get('id_user')
                else:
                    return jsonify({'success': False, 'message': 'Erreur lors de la récupération'}), 500
            
            if user_id:
                # Créer un abonnement essai de 14 jours
                from datetime import datetime, timedelta
                date_fin_essai = datetime.now() + timedelta(days=14)
                
                query = """
                INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
                VALUES (%s, 'actif', %s, %s, 'essai')
                """
                utilisateur_model.db.execute_query(query, (user_id, datetime.now(), date_fin_essai))
                
                return jsonify({'success': True, 'message': 'Inscription réussie ! Période d\'essai de 14 jours.'})
        
        return jsonify({'success': False, 'message': 'Erreur lors de l\'inscription'}), 500
        
    except Exception as e:
        print(f"❌ Erreur register: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        mot_de_passe = data.get('mot_de_passe')
        
        print(f"🔐 Login reçu: {email}")
        print(f"🔐 Mot de passe: {mot_de_passe}")
        
        user = utilisateur_model.authenticate(email, mot_de_passe)
        
        if user:
            user_id = str(user['id_user'])
            token = create_access_token(identity=user_id)
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': user['id_user'],
                    'nom': user['nom'],
                    'email': user['email'],
                    'entreprise': user['entreprise']
                }
            })
        return jsonify({'success': False, 'message': 'Identifiants incorrects'}), 401
    except Exception as e:
        print(f"❌ Erreur login: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin/abonnement/<int:id_user>/trial', methods=['POST'])
@jwt_required()
def admin_add_trial(id_user):
    try:
        admin_id = get_jwt_identity()
        admin_id = int(admin_id)
        
        # Vérifier que c'est l'admin (ID = 1)
        if admin_id != 1:
            return jsonify({'error': 'Non autorisé'}), 403
        
        from datetime import datetime, timedelta
        date_fin = datetime.now() + timedelta(days=14)
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier si l'utilisateur a déjà un abonnement
        check_response = requests.get(
            f"{supabase_url}/rest/v1/abonnements?id_user=eq.{id_user}",
            headers=headers
        )
        
        if check_response.status_code == 200 and check_response.json():
            # Mettre à jour
            update_data = {
                "statut": "actif",
                "date_fin": date_fin.isoformat(),
                "type_abonnement": "essai"
            }
            requests.patch(
                f"{supabase_url}/rest/v1/abonnements?id_user=eq.{id_user}",
                headers=headers,
                json=update_data
            )
        else:
            # Créer
            abo_data = {
                "id_user": id_user,
                "statut": "actif",
                "date_debut": datetime.now().isoformat(),
                "date_fin": date_fin.isoformat(),
                "type_abonnement": "essai"
            }
            requests.post(
                f"{supabase_url}/rest/v1/abonnements",
                headers=headers,
                json=abo_data
            )
        
        return jsonify({'success': True, 'message': '14 jours d\'essai ajoutés'})
        
    except Exception as e:
        print(f"❌ Erreur trial: {e}")
        return jsonify({'error': str(e)}), 500
# ==================== CLIENTS ====================
@app.route('/api/clients', methods=['GET'])
@jwt_required()
def get_clients():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{supabase_url}/rest/v1/client?select=*",
            headers=headers
        )
        
        if response.status_code == 200:
            all_clients = response.json()
            clients = [c for c in all_clients if c.get('id_user') == user_id]
            return jsonify(clients)
        else:
            return jsonify([]), 500
        
    except Exception as e:
        print(f"❌ Erreur get_clients: {e}")
        return jsonify([]), 500

@app.route('/api/clients', methods=['POST'])
@jwt_required()
def create_client():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        print(f"🔍 Création client pour user_id: {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        client_data = {
            "nom": data.get('nom'),
            "telephone": data.get('telephone'),
            "email": data.get('email'),
            "adresse": data.get('adresse'),
            "id_user": user_id
        }
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/client",
            headers=headers,
            json=client_data
        )
        
        print(f"🔍 Status Supabase: {response.status_code}")
        print(f"🔍 Réponse brute: {response.text}")
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Client créé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_client: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clients/<int:id_client>', methods=['PUT'])
@jwt_required()
def update_client(id_client):
    try:
        data = request.json
        query = """
        UPDATE CLIENT 
        SET nom = %s, telephone = %s, email = %s, adresse = %s
        WHERE id_client = %s
        """
        result = client_model.db.execute_query(query, (
            data['nom'], data['telephone'], data['email'], data['adresse'], id_client
        ))
        if result:
            return jsonify({'success': True, 'message': 'Client modifié'})
        return jsonify({'success': False, 'message': 'Erreur'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clients/<int:id_client>', methods=['DELETE'])
@jwt_required()
def delete_client(id_client):
    try:
        client_model.delete(id_client)
        return jsonify({'success': True, 'message': 'Client supprimé'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== PROJETS ====================
@app.route('/api/projets', methods=['GET'])
@jwt_required()
def get_projets():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{supabase_url}/rest/v1/projet?select=*",
            headers=headers
        )
        
        if response.status_code == 200:
            all_projets = response.json()
            projets = [p for p in all_projets if p.get('id_user') == user_id]
            return jsonify(projets)
        else:
            return jsonify([]), 500
        
    except Exception as e:
        print(f"❌ Erreur get_projets: {e}")
        return jsonify([]), 500

@app.route('/api/projets', methods=['POST'])
@jwt_required()
def create_projet():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        print(f"🔍 Création projet pour user_id: {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        projet_data = {
            "nom_projet": data.get('nom_projet'),
            "description": data.get('description'),
            "localisation": data.get('localisation'),
            "id_user": user_id
        }
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/projet",
            headers=headers,
            json=projet_data
        )
        
        print(f"🔍 Status Supabase: {response.status_code}")
        print(f"🔍 Réponse brute: {response.text}")
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Projet créé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_projet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/projets/<int:id_projet>', methods=['PUT'])
@jwt_required()
def update_projet(id_projet):
    try:
        data = request.json
        query = """
        UPDATE PROJET 
        SET nom_projet = %s, description = %s, localisation = %s
        WHERE id_projet = %s
        """
        result = projet_model.db.execute_query(query, (
            data['nom_projet'], data['description'], data['localisation'], id_projet
        ))
        if result:
            return jsonify({'success': True, 'message': 'Projet modifié'})
        return jsonify({'success': False, 'message': 'Erreur'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/projets/<int:id_projet>', methods=['DELETE'])
@jwt_required()
def delete_projet(id_projet):
    try:
        projet_model.delete(id_projet)
        return jsonify({'success': True, 'message': 'Projet supprimé'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== DEVIS ====================
@app.route('/api/devis', methods=['GET'])
@jwt_required()
def get_devis():
    try:
        user_id = get_jwt_identity()
        devis = devis_model.get_by_user(user_id)
        return jsonify(devis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/devis', methods=['POST'])
@jwt_required()
def create_devis():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        print(f"🔍 Création devis pour user_id: {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        import requests
        from datetime import datetime
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        # Calculer le total
        lignes = data.get('lignes', [])
        total_materiaux = sum(float(ligne['quantite']) * float(ligne['prix_unitaire']) for ligne in lignes)
        total = total_materiaux * 1.2
        
        # Insérer le devis
        devis_data = {
            "date_creation": datetime.now().isoformat(),
            "total": total,
            "statut": "brouillon",
            "id_client": data.get('id_client'),
            "id_user": user_id,
            "id_projet": data.get('id_projet')
        }
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/devis",
            headers=headers,
            json=devis_data
        )
        
        print(f"🔍 Status Supabase devis: {response.status_code}")
        print(f"🔍 Réponse brute devis: {response.text}")
        
        if response.status_code in [200, 201]:
            # Récupérer l'ID du devis créé
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                id_devis = result[0].get('id_devis')
            elif isinstance(result, dict):
                id_devis = result.get('id_devis')
            else:
                # Récupérer le dernier ID
                get_response = requests.get(
                    f"{supabase_url}/rest/v1/devis?select=id_devis&order=id_devis.desc&limit=1",
                    headers=headers
                )
                if get_response.status_code == 200 and get_response.json():
                    id_devis = get_response.json()[0].get('id_devis')
                else:
                    id_devis = None
            
            # Insérer les lignes du devis
            if id_devis:
                for ligne in lignes:
                    total_ligne = float(ligne['quantite']) * float(ligne['prix_unitaire'])
                    ligne_data = {
                        "designation": ligne.get('designation'),
                        "quantite": ligne.get('quantite'),
                        "prix_unitaire": ligne.get('prix_unitaire'),
                        "total_ligne": total_ligne,
                        "id_devis": id_devis
                    }
                    requests.post(
                        f"{supabase_url}/rest/v1/ligne_devis",
                        headers=headers,
                        json=ligne_data
                    )
                
                return jsonify({'success': True, 'id_devis': id_devis})
            else:
                return jsonify({'success': False, 'message': 'Devis créé mais ID non récupéré'}), 500
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_devis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/devis/<int:id_devis>', methods=['GET'])
@jwt_required()
def get_devis_detail(id_devis):
    try:
        devis = devis_model.get_details(id_devis)
        return jsonify(devis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== BACKUP & RESTORE ====================
@app.route('/api/backup', methods=['GET'])
@jwt_required()
def backup_database():
    try:
        user_id = get_jwt_identity()
        from datetime import datetime
        
        # Récupérer TOUS les clients (sans condition)
        clients = client_model.db.fetch_all("SELECT * FROM CLIENT")
        
        # Récupérer TOUS les projets
        projets = projet_model.db.fetch_all("SELECT * FROM PROJET")
        
        # Récupérer les devis de l'utilisateur avec leurs lignes
        devis = devis_model.get_by_user(user_id)
        for devis_item in devis:
            lignes = devis_model.db.fetch_all("SELECT * FROM LIGNE_DEVIS WHERE id_devis = %s", (devis_item['id_devis'],))
            devis_item['lignes'] = lignes
        
        # Récupérer les settings
        settings = utilisateur_model.db.fetch_one("SELECT * FROM SETTINGS WHERE id_user = %s", (user_id,))
        
        data = {
            'user_id': user_id,
            'export_date': datetime.now().isoformat(),
            'clients': clients,
            'projets': projets,
            'devis': devis,
            'settings': settings
        }
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restore', methods=['POST', 'OPTIONS'])
@jwt_required()
def restore_database():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        user_id = get_jwt_identity()
        backup_data = request.json
        
        print("=" * 60)
        print("🔵 RESTAURATION EN COURS...")
        
        # Vider les tables (pas besoin de FOREIGN_KEY_CHECKS en SQLite)
        devis_model.db.execute_query("DELETE FROM LIGNE_DEVIS")
        devis_model.db.execute_query("DELETE FROM FACTURE")
        devis_model.db.execute_query("DELETE FROM DEVIS")
        devis_model.db.execute_query("DELETE FROM CLIENT")
        devis_model.db.execute_query("DELETE FROM PROJET")
        
        # Insérer les clients
        for client in backup_data.get('clients', []):
            sql = "INSERT INTO CLIENT (nom, telephone, email, adresse, id_user) VALUES (%s, %s, %s, %s, %s)"
            devis_model.db.execute_query(sql, (
                client['nom'], 
                client['telephone'], 
                client['email'], 
                client['adresse'],
                user_id
            ))
            print(f"   ✅ Client inséré: {client['nom']}")

        # Insérer les projets
        for projet in backup_data.get('projets', []):
            sql = "INSERT INTO PROJET (nom_projet, description, localisation, id_user) VALUES (%s, %s, %s, %s)"
            devis_model.db.execute_query(sql, (
                projet['nom_projet'], 
                projet['description'], 
                projet['localisation'],
                user_id
            ))
            print(f"   ✅ Projet inséré: {projet['nom_projet']}")

        # Insérer les devis
        for devis_item in backup_data.get('devis', []):
            sql = """
            INSERT INTO DEVIS (date_creation, total, statut, id_client, id_user, id_projet) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            devis_model.db.execute_query(sql, (
                devis_item['date_creation'],
                devis_item['total'],
                devis_item['statut'],
                devis_item['id_client'],
                user_id,
                devis_item['id_projet']
            ))
            
            # Récupérer l'ID du nouveau devis
            cursor = devis_model.db.execute_query("SELECT last_insert_rowid()")
            id_devis = cursor.lastrowid
            
            # Insérer les lignes
            for ligne in devis_item.get('lignes', []):
                sql_ligne = """
                INSERT INTO LIGNE_DEVIS (designation, quantite, prix_unitaire, total_ligne, id_devis) 
                VALUES (%s, %s, %s, %s, %s)
                """
                devis_model.db.execute_query(sql_ligne, (
                    ligne['designation'],
                    ligne['quantite'],
                    ligne['prix_unitaire'],
                    ligne['total_ligne'],
                    id_devis
                ))
        
        # Réinsérer les settings si nécessaire
        settings = backup_data.get('settings')
        if settings:
            devis_model.db.execute_query("DELETE FROM SETTINGS WHERE id_user = %s", (user_id,))
            sql_settings = """
            INSERT INTO SETTINGS (id_user, company_name, company_logo, company_email, company_phone, 
                                 company_address, primary_color, secondary_color, accent_color, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            devis_model.db.execute_query(sql_settings, (
                user_id,
                settings.get('company_name', ''),
                settings.get('company_logo', ''),
                settings.get('company_email', ''),
                settings.get('company_phone', ''),
                settings.get('company_address', ''),
                settings.get('primary_color', '#1E3A8A'),
                settings.get('secondary_color', '#7C3AED'),
                settings.get('accent_color', '#06B6D4'),
                settings.get('created_at', datetime.now()),
                datetime.now()
            ))
        
        # Vérifier
        result = devis_model.db.fetch_one("SELECT COUNT(*) as total FROM CLIENT")
        print(f"📊 Clients après restauration: {result['total']}")
        
        print("🎉 RESTAURATION TERMINÉE !")
        print("=" * 60)
        
        return jsonify({'success': True, 'message': 'Restauration réussie'})
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== FACTURES ====================






# ==================== PDF ====================
@app.route('/api/devis/<int:id_devis>/pdf', methods=['GET'])
@jwt_required()
def generate_pdf(id_devis):
    try:
        user_id = get_jwt_identity()
        devis = devis_model.get_details(id_devis)
        if not devis:
            return jsonify({'error': 'Devis non trouvé'}), 404
        
        # Récupérer les paramètres de l'entreprise
        settings_query = "SELECT * FROM SETTINGS WHERE id_user = %s"
        settings = utilisateur_model.db.fetch_one(settings_query, (user_id,))
        
        if not settings:
            settings = {
                'company_name': 'BTP Devis Pro',
                'company_email': 'contact@btpdevispro.com',
                'company_phone': '+229 90000000',
                'company_address': '',
                'company_logo': None,
                'primary_color': '#1E3A8A',
                'secondary_color': '#7C3AED',
                'accent_color': '#06B6D4'
            }
        
        # Conversion des types Decimal en float
        for ligne in devis['lignes']:
            ligne['prix_unitaire'] = float(ligne['prix_unitaire']) if ligne['prix_unitaire'] else 0
            ligne['quantite'] = int(ligne['quantite']) if ligne['quantite'] else 0
            ligne['total_ligne'] = float(ligne['total_ligne']) if ligne['total_ligne'] else 0
        
        # Création du PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=2*cm, leftMargin=2*cm, 
                                topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        
        # Utiliser les couleurs personnalisées
        primary_color = settings.get('primary_color', '#1E3A8A')
        
        title_style = ParagraphStyle(
            'CustomTitle', 
            parent=styles['Heading1'], 
            fontSize=24, 
            textColor=colors.HexColor(primary_color),
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6B7280'),
            alignment=1
        )
        
        section_style = ParagraphStyle(
            'Section',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor(primary_color),
            spaceAfter=12
        )
        
        story = []
        
        # ========== EN-TÊTE AVEC LOGO ==========
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Image
        import os
        
        # Ajouter le logo s'il existe
        if settings.get('company_logo'):
            logo_path = os.path.join(os.path.dirname(__file__), 'uploads', settings['company_logo'])
            if os.path.exists(logo_path):
                try:
                    logo_img = Image(logo_path, width=60, height=60)
                    story.append(logo_img)
                except:
                    pass
        
        # Ajouter le nom de l'entreprise
        company_name = settings.get('company_name', 'BTP Devis Pro')
        story.append(Paragraph(company_name, styles['Normal']))
        story.append(Spacer(1, 0.2*cm))
        
        # Titre DEVIS
        story.append(Paragraph("DEVIS PROFESSIONNEL", title_style))
        story.append(Spacer(1, 0.3*cm))
        
        # Coordonnées de l'entreprise
        company_info = f"{settings.get('company_email', '')} | {settings.get('company_phone', '')}"
        story.append(Paragraph(company_info, subtitle_style))
        if settings.get('company_address'):
            story.append(Paragraph(settings.get('company_address'), subtitle_style))
        
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("<hr/>", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
        
        # ========== INFORMATIONS DEVIS ==========
        info_data = [
            ['Référence', f"DEVIS-{devis['id_devis']:06d}"],
            ['Date d\'émission', devis['date_creation'].strftime('%d/%m/%Y')],
            ['Validité', '30 jours'],
            ['Statut', devis['statut'].upper()]
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 8*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor(primary_color)),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))
        
        # ========== INFORMATIONS CLIENT ==========
        story.append(Paragraph("Informations Client", section_style))
        client_data = [
            ['Nom', devis['client_nom']],
            ['Email', devis.get('client_email', '-') or '-'],
            ['Téléphone', devis.get('client_telephone', '-') or '-'],
            ['Adresse', devis.get('client_adresse', '-') or '-']
        ]
        
        client_table = Table(client_data, colWidths=[3*cm, 9*cm])
        client_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4B5563')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(client_table)
        story.append(Spacer(1, 0.5*cm))
        
        # ========== INFORMATIONS PROJET ==========
        story.append(Paragraph("Informations Projet", section_style))
        projet_data = [
            ['Nom du projet', devis['nom_projet']],
            ['Description', devis.get('projet_description', '-') or '-'],
            ['Localisation', devis.get('localisation', '-') or '-']
        ]
        
        projet_table = Table(projet_data, colWidths=[3*cm, 9*cm])
        projet_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4B5563')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(projet_table)
        story.append(Spacer(1, 0.5*cm))
        
        # ========== TABLEAU DES MATÉRIAUX ==========
        story.append(Paragraph("Détail des Travaux et Matériaux", section_style))
        
        data = [['Désignation', 'Quantité', 'Prix unitaire (FCFA)', 'Total (FCFA)']]
        total_materiaux = 0
        
        for ligne in devis['lignes']:
            total_ligne = ligne['quantite'] * ligne['prix_unitaire']
            total_materiaux += total_ligne
            data.append([
                ligne['designation'],
                str(ligne['quantite']),
                f"{ligne['prix_unitaire']:,.0f}",
                f"{total_ligne:,.0f}"
            ])
        
        main_oeuvre = total_materiaux * 0.2
        total_ttc = total_materiaux + main_oeuvre
        
        data.append(['', '', 'Sous-total matériaux', f"{total_materiaux:,.0f}"])
        data.append(['', '', 'Main d\'œuvre (20%)', f"{main_oeuvre:,.0f}"])
        data.append(['', '', 'TOTAL TTC', f"{total_ttc:,.0f}"])
        
        table = Table(data, colWidths=[7*cm, 2.5*cm, 3.5*cm, 3.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -3), 9),
            ('ALIGN', (1, 1), (-1, -3), 'CENTER'),
            ('ALIGN', (0, 1), (0, -3), 'LEFT'),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, -3), (-1, -1), colors.HexColor(primary_color)),
            ('FONTSIZE', (0, -3), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.HexColor('#E5E7EB')),
            ('BOX', (0, -3), (-1, -1), 1, colors.HexColor(primary_color)),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.8*cm))
        
        # ========== CONDITIONS ET NOTES ==========
        story.append(Paragraph("Conditions et Modalités", section_style))
        
        conditions = [
            "• Le présent devis est valable pour une durée de 30 jours à compter de sa date d'émission.",
            "• Tout commencement des travaux vaut acceptation du devis.",
            "• Les matériaux fournis restent la propriété de l'entreprise jusqu'au paiement intégral.",
            "• Délai de livraison : à convenir selon planning du projet.",
        ]
        
        for condition in conditions:
            story.append(Paragraph(condition, styles['Normal']))
            story.append(Spacer(1, 0.2*cm))
        
        story.append(Spacer(1, 0.5*cm))
        
                # ========== SIGNATURES ==========
        entreprise_name = settings.get("company_name", "l'entreprise")
        signature_data = [
            [f'Pour {entreprise_name}', 'Pour le client'],
            ['_________________________', '_________________________'],
            ['Date et signature', 'Date et signature']
        ]
        
        signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, 2), 9),
            ('TEXTCOLOR', (0, 1), (-1, 2), colors.HexColor('#6B7280')),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
        ]))
        story.append(signature_table)
        story.append(Spacer(1, 0.5*cm))
        
        # ========== PIED DE PAGE ==========
        story.append(Paragraph("<hr/>", styles['Normal']))
        footer_text = f"Devis généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - {settings.get('company_name', 'BTP Devis Pro')}"
        story.append(Paragraph(footer_text, subtitle_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer, 
            mimetype='application/pdf', 
            as_attachment=True, 
            download_name=f'devis_{id_devis}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== ABONNEMENT ====================
@app.route('/api/abonnement/statut', methods=['GET'])
@jwt_required()
def get_abonnement_statut():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        from datetime import datetime
        
        # Admin illimité
        if user_id == 1:
            return jsonify({
                'success': True,
                'statut': 'actif',
                'type': 'illimite',
                'date_fin': (datetime.now() + timedelta(days=365*100)).isoformat(),
                'jours_restants': 365*100
            })
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{supabase_url}/rest/v1/abonnements?id_user=eq.{user_id}",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            abo = response.json()[0]
            statut = abo.get('statut', 'inactif')
            date_fin_str = abo.get('date_fin')
            
            # 🔥 VÉRIFIER SI LA DATE EST DÉPASSÉE
            if date_fin_str and statut == 'actif':
                date_fin = datetime.fromisoformat(date_fin_str.replace('Z', '+00:00'))
                jours_restants = (date_fin - datetime.now()).days
                
                if jours_restants <= 0:
                    # 🔥 L'abonnement est EXPIRÉ → on met à jour le statut
                    statut = 'expiré'
                    # Mettre à jour dans Supabase
                    update_data = {"statut": "expiré"}
                    requests.patch(
                        f"{supabase_url}/rest/v1/abonnements?id_abonnement=eq.{abo.get('id_abonnement')}",
                        headers=headers,
                        json=update_data
                    )
                    return jsonify({
                        'success': False,
                        'statut': 'expiré',
                        'message': 'Votre abonnement a expiré'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'statut': 'actif',
                        'type': abo.get('type_abonnement', 'starter'),
                        'date_fin': date_fin_str,
                        'jours_restants': max(0, jours_restants)
                    })
            elif statut == 'suspendu':
                return jsonify({
                    'success': False,
                    'statut': 'suspendu',
                    'message': 'Votre abonnement est suspendu'
                })
            else:
                return jsonify({
                    'success': False,
                    'statut': statut or 'inactif'
                })
        
        return jsonify({'success': False, 'statut': 'inactif'})
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/abonnement/start-trial', methods=['POST'])
@jwt_required()
def start_trial():
    try:
        user_id = get_jwt_identity()
        abonnement_model.create_trial(user_id)
        return jsonify({'success': True, 'message': 'Essai gratuit activé pour 14 jours'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== SETTINGS ====================
# ==================== SETTINGS (PERSONNALISATION) ====================
@app.route('/api/settings', methods=['GET'])
@jwt_required()
def get_settings():
    try:
        user_id = get_jwt_identity()
        query = "SELECT * FROM SETTINGS WHERE id_user = %s"
        settings = utilisateur_model.db.fetch_one(query, (user_id,))
        
        if not settings:
            from datetime import datetime
            query_insert = """
            INSERT INTO SETTINGS (id_user, company_name, created_at, updated_at)
            VALUES (%s, %s, %s, %s)
            """
            utilisateur_model.db.execute_query(query_insert, (user_id, 'Mon Entreprise', datetime.now(), datetime.now()))
            settings = utilisateur_model.db.fetch_one(query, (user_id,))
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
@app.route('/api/devis/<int:id_devis>', methods=['DELETE'])
@jwt_required()
def delete_devis(id_devis):
    try:
        # Vérifier si le devis est supprimable (pas validé)
        check_query = "SELECT statut FROM DEVIS WHERE id_devis = %s"
        devis_check = devis_model.db.fetch_one(check_query, (id_devis,))
        
        if not devis_check:
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        if devis_check['statut'] == 'validé':
            return jsonify({'success': False, 'message': 'Un devis validé ne peut pas être supprimé'}), 400
        
        # Supprimer les lignes d'abord (clé étrangère)
        devis_model.db.execute_query("DELETE FROM LIGNE_DEVIS WHERE id_devis = %s", (id_devis,))
        
        # Supprimer le devis
        devis_model.db.execute_query("DELETE FROM DEVIS WHERE id_devis = %s", (id_devis,))
        
        return jsonify({'success': True, 'message': 'Devis supprimé'})
    except Exception as e:
        print(f"❌ Erreur suppression devis: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== ROUTES FACTURES ====================
@app.route('/api/facture/<int:id_devis>', methods=['POST'])
@jwt_required()
def create_facture(id_devis):
    try:
        user_id = get_jwt_identity()
        
        # Vérifier si le devis existe et est validé
        devis = devis_model.get_details(id_devis)
        if not devis:
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        if devis['statut'] != 'validé':
            return jsonify({'success': False, 'message': 'Le devis doit être validé avant de créer une facture'}), 400
        
        # Vérifier si une facture existe déjà
        existing = facture_model.get_by_devis(id_devis)
        if existing:
            return jsonify({'success': False, 'message': 'Une facture existe déjà pour ce devis'}), 400
        
        # Créer la facture
        facture_model.create(id_devis, devis['total'])
        
        return jsonify({'success': True, 'message': 'Facture créée avec succès'})
    except Exception as e:
        print(f"❌ Erreur création facture: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/api/facture/<int:id_facture>/pay', methods=['PUT'])
@jwt_required()
def pay_facture(id_facture):
    try:
        query = "UPDATE FACTURE SET statut = 'payée' WHERE id_facture = %s"
        facture_model.db.execute_query(query, (id_facture,))
        return jsonify({'success': True, 'message': 'Facture payée'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    try:
        user_id = get_jwt_identity()
        data = request.json
        from datetime import datetime
        
        query = """
        UPDATE SETTINGS 
        SET company_name = %s, company_email = %s, company_phone = %s, 
            company_address = %s, primary_color = %s, secondary_color = %s, 
            accent_color = %s, updated_at = %s
        WHERE id_user = %s
        """
        utilisateur_model.db.execute_query(query, (
            data.get('company_name', ''),
            data.get('company_email', ''),
            data.get('company_phone', ''),
            data.get('company_address', ''),
            data.get('primary_color', '#1E3A8A'),
            data.get('secondary_color', '#7C3AED'),
            data.get('accent_color', '#06B6D4'),
            datetime.now(),
            user_id
        ))
        
        return jsonify({'success': True, 'message': 'Paramètres mis à jour'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/settings/logo', methods=['POST'])
@jwt_required()
def upload_logo():
    try:
        user_id = get_jwt_identity()
        
        if 'logo' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier'}), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Fichier vide'}), 400
        
        import os
        from datetime import datetime
        ext = file.filename.rsplit('.', 1)[-1].lower()
        filename = f"logo_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        query = "UPDATE SETTINGS SET company_logo = %s, updated_at = %s WHERE id_user = %s"
        utilisateur_model.db.execute_query(query, (filename, datetime.now(), user_id))
        
        return jsonify({'success': True, 'logo': filename})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Route pour servir les logos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    import os
    from flask import send_from_directory
    upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
    return send_from_directory(upload_folder, filename)
    

# Validation devis
@app.route('/api/devis/<int:id_devis>/validate', methods=['POST'])
@jwt_required()
def validate_devis(id_devis):
    try:
        devis_model.update_status(id_devis, 'validé')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Création facture
@app.route('/api/factures/<int:id_user>', methods=['GET'])
@jwt_required()
def get_factures(id_user):
    try:
        current_user = get_jwt_identity()
        print(f"🔍 Factures demandées pour user {id_user} (connecté: {current_user})")
        
        query = """
        SELECT f.*, d.id_devis, c.nom as client_nom, d.total as montant_devis
        FROM FACTURE f
        JOIN DEVIS d ON f.id_devis = d.id_devis
        JOIN CLIENT c ON d.id_client = c.id_client
        WHERE d.id_user = %s
        ORDER BY f.date_facture DESC
        """
        factures = devis_model.db.fetch_all(query, (id_user,))
        print(f"📋 {len(factures)} factures trouvées")
        return jsonify(factures)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/devis/<int:id_devis>', methods=['PUT'])
@jwt_required()
def update_devis(id_devis):
    try:
        data = request.json
        
        # Vérifier si le devis est modifiable
        check_query = "SELECT statut FROM DEVIS WHERE id_devis = %s"
        devis_check = devis_model.db.fetch_one(check_query, (id_devis,))
        if devis_check and devis_check['statut'] == 'validé':
            return jsonify({'success': False, 'message': 'Un devis validé ne peut pas être modifié'}), 400
        
        # Supprimer les anciennes lignes
        devis_model.db.execute_query("DELETE FROM LIGNE_DEVIS WHERE id_devis = %s", (id_devis,))
        
        # Recalculer le total
        total_materiaux = sum(ligne['quantite'] * ligne['prix_unitaire'] for ligne in data['lignes'])
        total = total_materiaux * 1.2
        
        # Mettre à jour le devis
        query = """
        UPDATE DEVIS 
        SET id_client = %s, id_projet = %s, total = %s, date_creation = %s
        WHERE id_devis = %s
        """
        devis_model.db.execute_query(query, (data['id_client'], data['id_projet'], total, datetime.now(), id_devis))
        
        # Réinsérer les nouvelles lignes
        for ligne in data['lignes']:
            total_ligne = ligne['quantite'] * ligne['prix_unitaire']
            query_ligne = """
            INSERT INTO LIGNE_DEVIS (designation, quantite, prix_unitaire, total_ligne, id_devis)
            VALUES (%s, %s, %s, %s, %s)
            """
            devis_model.db.execute_query(query_ligne, (
                ligne['designation'], ligne['quantite'], ligne['prix_unitaire'], total_ligne, id_devis
            ))
        
        return jsonify({'success': True, 'message': 'Devis modifié avec succès'})
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    

# ==================== ENVOI EMAIL ====================
import requests

@app.route('/api/devis/<int:id_devis>/send-email', methods=['POST'])
@jwt_required()
def send_devis_email(id_devis):
    try:
        data = request.json
        client_email = data.get('email')
        
        if not client_email:
            return jsonify({'success': False, 'message': 'Email client requis'}), 400
        
        # Récupérer le devis
        devis = devis_model.get_details(id_devis)
        if not devis:
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        # Générer le PDF (comme avant)
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        story = []
        story.append(Paragraph(f"DEVIS N° {devis['id_devis']:06d}", styles['Title']))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Client: {devis['client_nom']}", styles['Normal']))
        story.append(Paragraph(f"Date: {devis['date_creation'].strftime('%d/%m/%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.5*cm))
        
        data = [['Désignation', 'Qté', 'Prix U.', 'Total']]
        total = 0
        for ligne in devis['lignes']:
            total_ligne = ligne['quantite'] * ligne['prix_unitaire']
            total += total_ligne
            data.append([ligne['designation'], str(ligne['quantite']), f"{ligne['prix_unitaire']:,.0f}", f"{total_ligne:,.0f}"])
        
        data.append(['', '', 'TOTAL', f"{total:,.0f} FCFA"])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        
        # === ENVOI AVEC SENDGRID ===
        SENDGRID_API_KEY = "SG.ta_clé_api_ici"  # ← Remplace par TA VRAIE clé
        
        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Lire le PDF en base64
        import base64
        pdf_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        payload = {
            "personalizations": [
                {
                    "to": [{"email": client_email}],
                    "subject": f"Votre devis BTP Pro - N° {devis['id_devis']:06d}"
                }
            ],
            "from": {"email": "bylgaitb@gmail.com"},
            "content": [
                {
                    "type": "text/plain",
                    "value": f"""Bonjour {devis['client_nom']},

Veuillez trouver ci-joint votre devis pour le projet : {devis['nom_projet']}

Montant total: {total:,.0f} FCFA

Ce devis est valable 30 jours.

Cordialement,
L'équipe BTP Pro"""
                }
            ],
            "attachments": [
                {
                    "content": pdf_base64,
                    "type": "application/pdf",
                    "filename": f"devis_{devis['id_devis']}.pdf",
                    "disposition": "attachment"
                }
            ]
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 202:
            print(f"✅ Email envoyé à {client_email}")
            return jsonify({'success': True, 'message': 'Devis envoyé par email'})
        else:
            print(f"❌ Erreur SendGrid: {response.status_code} - {response.text}")
            return jsonify({'success': False, 'message': f'Erreur SendGrid: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ABONNEMENTS (ADMIN) ====================

@app.route('/api/admin/abonnements', methods=['GET'])
@jwt_required()
def admin_get_abonnements():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        # Vérifier que c'est l'admin (ID = 1)
        if user_id != 1:
            return jsonify({'error': 'Non autorisé'}), 403
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Récupérer tous les utilisateurs
        response = requests.get(f"{supabase_url}/rest/v1/utilisateur?select=*", headers=headers)
        result = []
        
        if response.status_code == 200:
            all_users = response.json()
            for u in all_users:
                if u.get('id_user') != 1:  # Exclure l'admin
                    # Récupérer l'abonnement
                    abo_response = requests.get(
                        f"{supabase_url}/rest/v1/abonnements?id_user=eq.{u.get('id_user')}",
                        headers=headers
                    )
                    abo = abo_response.json()[0] if abo_response.status_code == 200 and abo_response.json() else None
                    
                    result.append({
                        'id_user': u.get('id_user'),
                        'nom': u.get('nom', '-'),
                        'email': u.get('email', ''),
                        'entreprise': u.get('entreprise', '-'),
                        'telephone': u.get('telephone', '-'),
                        'statut': abo.get('statut') if abo else 'inactif',
                        'date_fin': abo.get('date_fin') if abo else None,
                        'type_abonnement': abo.get('type_abonnement') if abo else 'aucun',
                        'jours_restants': 0
                    })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur admin: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/abonnement/<int:id_user>/prolonger', methods=['POST'])
@jwt_required()
def admin_prolonger_abonnement(id_user):
    try:
        admin_id = get_jwt_identity()
        admin_id = int(admin_id)
        
        # Vérifier que c'est l'admin (ID = 1)
        if admin_id != 1:
            return jsonify({'error': 'Non autorisé'}), 403
        
        data = request.json
        jours = data.get('jours', 30)
        montant = data.get('montant', 0)
        methode = data.get('methode', 'virement')
        offreType = data.get('offreType', 'starter')
        
        from datetime import datetime, timedelta
        date_fin = datetime.now() + timedelta(days=jours)
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier si l'utilisateur a déjà un abonnement
        check_response = requests.get(
            f"{supabase_url}/rest/v1/abonnements?id_user=eq.{id_user}",
            headers=headers
        )
        
        if check_response.status_code == 200 and check_response.json():
            # Mettre à jour
            update_data = {
                "statut": "actif",
                "date_fin": date_fin.isoformat(),
                "type_abonnement": offreType
            }
            requests.patch(
                f"{supabase_url}/rest/v1/abonnements?id_user=eq.{id_user}",
                headers=headers,
                json=update_data
            )
        else:
            # Créer
            abo_data = {
                "id_user": id_user,
                "statut": "actif",
                "date_debut": datetime.now().isoformat(),
                "date_fin": date_fin.isoformat(),
                "type_abonnement": offreType
            }
            requests.post(
                f"{supabase_url}/rest/v1/abonnements",
                headers=headers,
                json=abo_data
            )
        
        # Enregistrer le paiement
        import uuid
        reference = f"PAY_{id_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        paiement_data = {
            "id_user": id_user,
            "montant": montant,
            "date_paiement": datetime.now().isoformat(),
            "reference_paiement": reference,
            "methode": methode,
            "statut": "valide"
        }
        requests.post(
            f"{supabase_url}/rest/v1/paiements",
            headers=headers,
            json=paiement_data
        )
        
        return jsonify({'success': True, 'message': f'Abonnement {offreType} prolongé de {jours} jours'})
        
    except Exception as e:
        print(f"❌ Erreur prolonger: {e}")
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        user_id = get_jwt_identity()
        query = """
        SELECT * FROM notifications 
        WHERE id_user = %s AND est_lue = 0
        ORDER BY date_creation DESC
        """
        notifications = utilisateur_model.db.fetch_all(query, (user_id,))
        return jsonify(notifications)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/<int:id_notification>/lire', methods=['PUT'])
@jwt_required()
def marquer_notification_lue(id_notification):
    try:
        query = "UPDATE notifications SET est_lue = 1 WHERE id_notification = %s"
        utilisateur_model.db.execute_query(query, (id_notification,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/api/db-reset', methods=['POST'])
@jwt_required()
def db_reset():
    try:
        user_id = get_jwt_identity()
        user = utilisateur_model.get_by_id(user_id)
        if user['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        # Forcer un rollback pour débloquer
        utilisateur_model.db.connection.rollback()
        
        # Reset des séquences si nécessaire
        cursor = utilisateur_model.db.connection.cursor()
        cursor.execute("SELECT setval('utilisateur_id_user_seq', (SELECT MAX(id_user) FROM utilisateur))")
        utilisateur_model.db.connection.commit()
        
        return jsonify({'success': True, 'message': 'Base de données réinitialisée'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/abonnement/<int:id_user>/changer-offre', methods=['POST'])
@jwt_required()
def admin_changer_offre(id_user):
    try:
        admin_id = get_jwt_identity()
        admin = utilisateur_model.get_by_id(admin_id)
        
        if admin['email'] != 'admin@btp.com' and admin['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        data = request.json
        type_offre = data.get('type_offre', 'pro')
        
        query = "UPDATE ABONNEMENTS SET type_abonnement = %s WHERE id_user = %s"
        utilisateur_model.db.execute_query(query, (type_offre, id_user))
        
        return jsonify({'success': True, 'message': f'Offre changée en {type_offre}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/abonnement/<int:id_user>/suspendre', methods=['POST'])
@jwt_required()
def admin_suspendre_abonnement(id_user):
    try:
        admin_id = get_jwt_identity()
        admin_id = int(admin_id)
        
        if admin_id != 1:
            return jsonify({'error': 'Non autorisé'}), 403
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier si l'utilisateur a un abonnement
        check_response = requests.get(
            f"{supabase_url}/rest/v1/abonnements?id_user=eq.{id_user}",
            headers=headers
        )
        
        if check_response.status_code == 200 and check_response.json():
            existing = check_response.json()[0]
            abo_id = existing.get('id_abonnement')
            
            # Mettre à jour le statut à "suspendu"
            update_data = {
                "statut": "suspendu"
            }
            
            patch_response = requests.patch(
                f"{supabase_url}/rest/v1/abonnements?id_abonnement=eq.{abo_id}",
                headers=headers,
                json=update_data
            )
            
            if patch_response.status_code in [200, 204]:
                # Ajouter une notification pour l'utilisateur
                notification_data = {
                    "id_user": id_user,
                    "message": "⛔ Votre abonnement a été suspendu par l'administrateur. Contactez-nous pour plus d'informations.",
                    "type": "suspension",
                    "date_creation": datetime.now().isoformat()
                }
                requests.post(
                    f"{supabase_url}/rest/v1/notifications",
                    headers=headers,
                    json=notification_data
                )
                
                return jsonify({'success': True, 'message': 'Abonnement suspendu'})
            else:
                return jsonify({'error': f'Erreur mise à jour: {patch_response.text}'}), 500
        else:
            return jsonify({'error': 'Aucun abonnement trouvé'}), 404
        
    except Exception as e:
        print(f"❌ Erreur suspendre: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/admin/abonnement/<int:id_user>/reactiver', methods=['POST'])
@jwt_required()
def admin_reactiver_abonnement(id_user):
    try:
        admin_id = get_jwt_identity()
        admin_id = int(admin_id)
        
        if admin_id != 1:
            return jsonify({'error': 'Non autorisé'}), 403
        
        from datetime import datetime, timedelta
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        check_response = requests.get(
            f"{supabase_url}/rest/v1/abonnements?id_user=eq.{id_user}",
            headers=headers
        )
        
        if check_response.status_code == 200 and check_response.json():
            existing = check_response.json()[0]
            abo_id = existing.get('id_abonnement')
            
            # Réactiver avec la date actuelle + 30 jours par défaut
            date_fin = datetime.now() + timedelta(days=30)
            
            update_data = {
                "statut": "actif",
                "date_fin": date_fin.isoformat()
            }
            
            patch_response = requests.patch(
                f"{supabase_url}/rest/v1/abonnements?id_abonnement=eq.{abo_id}",
                headers=headers,
                json=update_data
            )
            
            if patch_response.status_code in [200, 204]:
                notification_data = {
                    "id_user": id_user,
                    "message": "✅ Votre abonnement a été réactivé par l'administrateur.",
                    "type": "reactivation",
                    "date_creation": datetime.now().isoformat()
                }
                requests.post(
                    f"{supabase_url}/rest/v1/notifications",
                    headers=headers,
                    json=notification_data
                )
                
                return jsonify({'success': True, 'message': 'Abonnement réactivé'})
            else:
                return jsonify({'error': f'Erreur mise à jour: {patch_response.text}'}), 500
        else:
            return jsonify({'error': 'Aucun abonnement trouvé'}), 404
        
    except Exception as e:
        print(f"❌ Erreur réactiver: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export-abonnements', methods=['GET'])
@jwt_required()
def admin_export_abonnements():
    try:
        admin_id = get_jwt_identity()
        admin = utilisateur_model.get_by_id(admin_id)
        
        if admin['email'] != 'admin@btp.com' and admin['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        query = """
        SELECT u.nom, u.email, u.entreprise, u.telephone,
               a.type_abonnement, a.statut, a.date_debut, a.date_fin,
               DATEDIFF(a.date_fin, NOW()) as jours_restants
        FROM UTILISATEUR u
        LEFT JOIN ABONNEMENTS a ON u.id_user = a.id_user
        WHERE u.id_user != 1
        ORDER BY u.nom
        """
        abonnements = utilisateur_model.db.fetch_all(query)
        return jsonify(abonnements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/paiements/<int:id_user>', methods=['GET'])
@jwt_required()
def admin_get_paiements(id_user):
    try:
        admin_id = get_jwt_identity()
        admin = utilisateur_model.get_by_id(admin_id)
        
        if admin['email'] != 'admin@btp.com' and admin['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        query = "SELECT * FROM paiements WHERE id_user = %s ORDER BY date_paiement DESC"
        paiements = utilisateur_model.db.fetch_all(query, (id_user,))
        return jsonify(paiements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== TEST ====================
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({'status': 'success', 'message': 'API OK'})

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Démarrage du serveur BTP Devis Pro")
    print("=" * 50)
    app.run(debug=True, port=5000)