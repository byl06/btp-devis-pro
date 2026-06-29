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

# ==================== UTILITAIRE VÉRIFICATION ABONNEMENT ====================
def verifier_abonnement(user_id):
    """Vérifie si l'utilisateur a un abonnement actif. Retourne (bool, message, headers, supabase_url)"""
    from datetime import datetime
    import requests
    
    supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json"
    }
    
    # Récupérer l'abonnement
    abo_response = requests.get(
        f"{supabase_url}/rest/v1/abonnements?id_user=eq.{user_id}",
        headers=headers
    )
    
    if abo_response.status_code == 200 and abo_response.json():
        abo = abo_response.json()[0]
        statut = abo.get('statut', 'inactif')
        date_fin_str = abo.get('date_fin')
        
        # Suspendu
        if statut == 'suspendu':
            return False, '❌ Abonnement suspendu. Action bloquée.', headers, supabase_url
        
        # Expiré
        if date_fin_str:
            try:
                date_fin = datetime.fromisoformat(date_fin_str.replace('Z', '+00:00'))
                if date_fin < datetime.now():
                    # Mettre à jour le statut à "expiré"
                    requests.patch(
                        f"{supabase_url}/rest/v1/abonnements?id_abonnement=eq.{abo.get('id_abonnement')}",
                        headers=headers,
                        json={"statut": "expiré"}
                    )
                    return False, '❌ Abonnement expiré. Action bloquée.', headers, supabase_url
            except:
                pass
        
        # Inactif
        if statut != 'actif':
            return False, '❌ Abonnement inactif. Action bloquée.', headers, supabase_url
        
        return True, 'OK', headers, supabase_url
    else:
        return False, '❌ Aucun abonnement trouvé. Action bloquée.', headers, supabase_url

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
        
        # 🔥 Vérifier l'abonnement
        ok, message, headers, supabase_url = verifier_abonnement(user_id)
        if not ok:
            return jsonify({'success': False, 'message': message}), 403
        
        # Créer le client
        client_data = {
            "nom": data.get('nom'),
            "telephone": data.get('telephone'),
            "email": data.get('email'),
            "adresse": data.get('adresse'),
            "id_user": user_id
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/client",
            headers=headers,
            json=client_data
        )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Client créé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_client: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/clients/<int:id_client>', methods=['PUT'])
@jwt_required()
def update_client(id_client):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier que le client appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}&select=id_user",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        
        client = check_response.json()[0]
        if client.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Mettre à jour le client
        update_data = {
            "nom": data.get('nom'),
            "telephone": data.get('telephone'),
            "email": data.get('email'),
            "adresse": data.get('adresse')
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Client modifié'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur update_client: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
@app.route('/api/clients/<int:id_client>', methods=['DELETE'])
@jwt_required()
def delete_client(id_client):
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
        
        # Vérifier que le client appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}&select=id_user",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        
        client = check_response.json()[0]
        if client.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Supprimer le client
        response = requests.delete(
            f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}",
            headers=headers
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Client supprimé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur delete_client: {e}")
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
        
        # 🔥 Vérifier l'abonnement
        ok, message, headers, supabase_url = verifier_abonnement(user_id)
        if not ok:
            return jsonify({'success': False, 'message': message}), 403
        
        # Créer le projet
        projet_data = {
            "nom_projet": data.get('nom_projet'),
            "description": data.get('description'),
            "localisation": data.get('localisation'),
            "id_user": user_id
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/projet",
            headers=headers,
            json=projet_data
        )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Projet créé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_projet: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_projet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/projets/<int:id_projet>', methods=['PUT'])
@jwt_required()
def update_projet(id_projet):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier que le projet appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{id_projet}&select=id_user",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Projet non trouvé'}), 404
        
        projet = check_response.json()[0]
        if projet.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Mettre à jour le projet
        update_data = {
            "nom_projet": data.get('nom_projet'),
            "description": data.get('description'),
            "localisation": data.get('localisation')
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{id_projet}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Projet modifié'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur update_projet: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/projets/<int:id_projet>', methods=['DELETE'])
@jwt_required()
def delete_projet(id_projet):
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
        
        # Vérifier que le projet appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{id_projet}&select=id_user",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Projet non trouvé'}), 404
        
        projet = check_response.json()[0]
        if projet.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Supprimer le projet
        response = requests.delete(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{id_projet}",
            headers=headers
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Projet supprimé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur delete_projet: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== DEVIS ====================
@app.route('/api/devis', methods=['GET'])
@jwt_required()
def get_devis():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        print(f"🔍 Récupération devis pour user_id: {user_id}")
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 🔥 Récupérer les devis SANS jointure (requête simple)
        response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_user=eq.{user_id}&order=id_devis.desc",
            headers=headers
        )
        
        print(f"🔍 Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Erreur: {response.text}")
            return jsonify([]), 500
        
        devis_list = response.json()
        print(f"🔍 Devis trouvés: {len(devis_list)}")
        
        result = []
        for devis in devis_list:
            # Récupérer le client séparément avec id_client
            client_nom = "Client inconnu"
            if devis.get('id_client'):
                client_response = requests.get(
                    f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
                    headers=headers
                )
                if client_response.status_code == 200 and client_response.json():
                    client = client_response.json()[0]
                    client_nom = client.get('nom', 'Client inconnu')
            
            # Récupérer le projet séparément
            projet_nom = "Projet inconnu"
            if devis.get('id_projet'):
                projet_response = requests.get(
                    f"{supabase_url}/rest/v1/projet?id_projet=eq.{devis.get('id_projet')}",
                    headers=headers
                )
                if projet_response.status_code == 200 and projet_response.json():
                    projet = projet_response.json()[0]
                    projet_nom = projet.get('nom_projet', 'Projet inconnu')
            
            result.append({
                'id_devis': devis.get('id_devis'),
                'date_creation': devis.get('date_creation'),
                'total': devis.get('total', 0),
                'statut': devis.get('statut', 'brouillon'),
                'id_client': devis.get('id_client'),
                'id_user': devis.get('id_user'),
                'id_projet': devis.get('id_projet'),
                'client_nom': client_nom,
                'nom_projet': projet_nom
            })
        
        print(f"✅ {len(result)} devis retournés")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur get_devis: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500

@app.route('/api/devis', methods=['POST'])
@jwt_required()
def create_devis():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        print(f"🔍 Création devis pour user_id: {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        # 🔥 Vérifier l'abonnement
        ok, message, headers, supabase_url = verifier_abonnement(user_id)
        if not ok:
            return jsonify({'success': False, 'message': message}), 403
        
        from datetime import datetime
        
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
        
        print(f"🔍 Données devis à insérer: {devis_data}")
        
        response = requests.post(
            f"{supabase_url}/rest/v1/devis",
            headers=headers,
            json=devis_data
        )
        
        print(f"🔍 Status Supabase devis: {response.status_code}")
        print(f"🔍 Réponse brute devis: {response.text}")
        
        if response.status_code in [200, 201]:
            # 🔥 Récupérer l'ID du devis créé
            try:
                result = response.json()
                print(f"🔍 Résultat JSON: {result}")
            except Exception as e:
                print(f"❌ Erreur parsing JSON: {e}")
                # Si la réponse est vide, récupérer le dernier ID
                get_response = requests.get(
                    f"{supabase_url}/rest/v1/devis?select=id_devis&order=id_devis.desc&limit=1",
                    headers=headers
                )
                if get_response.status_code == 200 and get_response.json():
                    id_devis = get_response.json()[0].get('id_devis')
                    print(f"🔍 ID récupéré via SELECT: {id_devis}")
                else:
                    id_devis = None
            
            if 'result' in locals() and result:
                if isinstance(result, list) and len(result) > 0:
                    id_devis = result[0].get('id_devis')
                elif isinstance(result, dict):
                    id_devis = result.get('id_devis')
                elif 'id_devis' not in locals() or not id_devis:
                    id_devis = None
            
            if id_devis:
                # Insérer les lignes
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
        user_id = get_jwt_identity()
        user_id = int(user_id)
        print(f"🔍 Récupération détail devis {id_devis} pour user {user_id}")
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 1. Récupérer le devis
        response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        if response.status_code != 200 or not response.json():
            return jsonify({'error': 'Devis non trouvé'}), 404
        
        devis = response.json()[0]
        
        # Vérifier que le devis appartient à l'utilisateur
        if devis.get('id_user') != user_id:
            return jsonify({'error': 'Non autorisé'}), 403
        
        # 2. Récupérer le client
        client_nom = "Client inconnu"
        client_email = ""
        client_telephone = ""
        client_adresse = ""
        if devis.get('id_client'):
            client_response = requests.get(
                f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
                headers=headers
            )
            if client_response.status_code == 200 and client_response.json():
                client = client_response.json()[0]
                client_nom = client.get('nom', 'Client inconnu')
                client_email = client.get('email', '')
                client_telephone = client.get('telephone', '')
                client_adresse = client.get('adresse', '')
        
        # 3. Récupérer le projet
        projet_nom = "Projet inconnu"
        projet_description = ""
        localisation = ""
        if devis.get('id_projet'):
            projet_response = requests.get(
                f"{supabase_url}/rest/v1/projet?id_projet=eq.{devis.get('id_projet')}",
                headers=headers
            )
            if projet_response.status_code == 200 and projet_response.json():
                projet = projet_response.json()[0]
                projet_nom = projet.get('nom_projet', 'Projet inconnu')
                projet_description = projet.get('description', '')
                localisation = projet.get('localisation', '')
        
        # 4. Récupérer les lignes
        lignes_response = requests.get(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        lignes = lignes_response.json() if lignes_response.status_code == 200 else []
        
        # 5. Construire le résultat
        result = {
            'id_devis': devis.get('id_devis'),
            'date_creation': devis.get('date_creation'),
            'total': devis.get('total', 0),
            'statut': devis.get('statut', 'brouillon'),
            'id_client': devis.get('id_client'),
            'id_user': devis.get('id_user'),
            'id_projet': devis.get('id_projet'),
            'client_nom': client_nom,
            'client_email': client_email,
            'client_telephone': client_telephone,
            'client_adresse': client_adresse,
            'nom_projet': projet_nom,
            'projet_description': projet_description,
            'localisation': localisation,
            'lignes': lignes
        }
        
        print(f"✅ Détail devis {id_devis} retourné")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur get_devis_detail: {e}")
        import traceback
        traceback.print_exc()
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
        user_id = int(user_id)
        backup_data = request.json
        
        print("=" * 60)
        print("🔵 RESTAURATION EN COURS...")
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 🔥 VIDER LES TABLES
        tables = ['ligne_devis', 'facture', 'devis', 'client', 'projet']
        for table in tables:
            response = requests.delete(
                f"{supabase_url}/rest/v1/{table}",
                headers=headers
            )
            print(f"   🗑️ Table {table} vidée (status: {response.status_code})")
        
        # 🔥 INSÉRER LES CLIENTS
        for client in backup_data.get('clients', []):
            client_data = {
                "nom": client.get('nom'),
                "telephone": client.get('telephone'),
                "email": client.get('email'),
                "adresse": client.get('adresse'),
                "id_user": user_id
            }
            response = requests.post(
                f"{supabase_url}/rest/v1/client",
                headers=headers,
                json=client_data
            )
            if response.status_code in [200, 201]:
                print(f"   ✅ Client inséré: {client.get('nom')}")
            else:
                print(f"   ❌ Erreur client: {response.text}")
        
        # 🔥 INSÉRER LES PROJETS
        for projet in backup_data.get('projets', []):
            projet_data = {
                "nom_projet": projet.get('nom_projet'),
                "description": projet.get('description'),
                "localisation": projet.get('localisation'),
                "id_user": user_id
            }
            response = requests.post(
                f"{supabase_url}/rest/v1/projet",
                headers=headers,
                json=projet_data
            )
            if response.status_code in [200, 201]:
                print(f"   ✅ Projet inséré: {projet.get('nom_projet')}")
            else:
                print(f"   ❌ Erreur projet: {response.text}")
        
        # 🔥 INSÉRER LES DEVIS (avec gestion du cas sans devis)
        print("📥 Insertion des devis...")
        devis_list = backup_data.get('devis', [])
        if devis_list:
            for devis_item in devis_list:
                try:
                    devis_data = {
                        "date_creation": devis_item.get('date_creation'),
                        "total": devis_item.get('total'),
                        "statut": devis_item.get('statut', 'brouillon'),
                        "id_client": devis_item.get('id_client'),
                        "id_user": user_id,
                        "id_projet": devis_item.get('id_projet')
                    }
                    
                    response = requests.post(
                        f"{supabase_url}/rest/v1/devis",
                        headers=headers,
                        json=devis_data
                    )
                    
                    if response.status_code in [200, 201]:
                        result = response.json()
                        if isinstance(result, list) and len(result) > 0:
                            id_devis = result[0].get('id_devis')
                        elif isinstance(result, dict):
                            id_devis = result.get('id_devis')
                        else:
                            id_devis = None
                        
                        print(f"   ✅ Devis inséré (ID: {id_devis})")
                        
                        # Insérer les lignes
                        for ligne in devis_item.get('lignes', []):
                            ligne_data = {
                                "designation": ligne.get('designation'),
                                "quantite": ligne.get('quantite'),
                                "prix_unitaire": ligne.get('prix_unitaire'),
                                "total_ligne": ligne.get('total_ligne'),
                                "id_devis": id_devis
                            }
                            requests.post(
                                f"{supabase_url}/rest/v1/ligne_devis",
                                headers=headers,
                                json=ligne_data
                            )
                    else:
                        print(f"   ❌ Erreur devis: {response.text}")
                except Exception as e:
                    print(f"   ❌ Exception devis: {e}")
        else:
            print("   ℹ️ Aucun devis à restaurer")
        
        # 🔥 RESTAURER LES SETTINGS
        settings = backup_data.get('settings')
        if settings:
            # Supprimer les anciens settings
            delete_response = requests.delete(
                f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
                headers=headers
            )
            print(f"   🗑️ Settings supprimés (status: {delete_response.status_code})")
            
            from datetime import datetime
            settings_data = {
                "id_user": user_id,
                "company_name": settings.get('company_name', ''),
                "company_logo": settings.get('company_logo', ''),
                "company_email": settings.get('company_email', ''),
                "company_phone": settings.get('company_phone', ''),
                "company_address": settings.get('company_address', ''),
                "primary_color": settings.get('primary_color', '#1E3A8A'),
                "secondary_color": settings.get('secondary_color', '#7C3AED'),
                "accent_color": settings.get('accent_color', '#06B6D4'),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            response = requests.post(
                f"{supabase_url}/rest/v1/settings",
                headers=headers,
                json=settings_data
            )
            
            if response.status_code in [200, 201]:
                print("   ✅ Settings restaurés")
            else:
                print(f"   ❌ Erreur settings: {response.text}")
        
        print("🎉 RESTAURATION TERMINÉE !")
        print("=" * 60)
        
        # 🔥 RETOURNER UNE RÉPONSE JSON VALIDE
        return jsonify({'success': True, 'message': 'Restauration réussie'})
        
    except Exception as e:
        print(f"❌ Erreur restauration: {e}")
        import traceback
        traceback.print_exc()
        # 🔥 TOUJOURS retourner du JSON valide
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== FACTURES ====================


# ==================== MOT DE PASSE OUBLIÉ ====================
@app.route('/api/check-email', methods=['POST'])
def check_email():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'exists': False, 'error': 'Email requis'}), 400
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{supabase_url}/rest/v1/utilisateur?email=eq.{email}&select=id_user",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            return jsonify({'exists': True})
        else:
            return jsonify({'exists': False})
        
    except Exception as e:
        print(f"❌ Erreur check_email: {e}")
        return jsonify({'exists': False, 'error': str(e)}), 500
    


@app.route('/api/change-password', methods=['POST'])
@jwt_required()
def change_password():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        ancien_mot_de_passe = data.get('ancien_mot_de_passe')
        nouveau_mot_de_passe = data.get('nouveau_mot_de_passe')
        
        if not ancien_mot_de_passe or not nouveau_mot_de_passe:
            return jsonify({'success': False, 'message': 'Tous les champs sont requis'}), 400
        
        if len(nouveau_mot_de_passe) < 4:
            return jsonify({'success': False, 'message': 'Le nouveau mot de passe doit contenir au moins 4 caractères'}), 400
        
        import requests
        import bcrypt
        from datetime import datetime
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Récupérer l'utilisateur pour vérifier l'ancien mot de passe
        response = requests.get(
            f"{supabase_url}/rest/v1/utilisateur?id_user=eq.{user_id}&select=mot_de_passe_hash",
            headers=headers
        )
        
        if response.status_code != 200 or not response.json():
            return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404
        
        user = response.json()[0]
        stored_hash = user.get('mot_de_passe_hash')
        
        # Vérifier l'ancien mot de passe
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        if isinstance(ancien_mot_de_passe, str):
            ancien_mot_de_passe = ancien_mot_de_passe.encode('utf-8')
        
        if not bcrypt.checkpw(ancien_mot_de_passe, stored_hash):
            return jsonify({'success': False, 'message': 'Ancien mot de passe incorrect'}), 401
        
        # Générer le hash du nouveau mot de passe
        nouveau_hash = bcrypt.hashpw(nouveau_mot_de_passe.encode('utf-8'), bcrypt.gensalt())
        
        # Mettre à jour le mot de passe
        update_data = {
            "mot_de_passe": nouveau_mot_de_passe,
            "mot_de_passe_hash": nouveau_hash.decode()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/utilisateur?id_user=eq.{user_id}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            # Ajouter une notification
            notification_data = {
                "id_user": user_id,
                "message": "🔑 Votre mot de passe a été changé avec succès.",
                "type": "info",
                "date_creation": datetime.now().isoformat()
            }
            requests.post(
                f"{supabase_url}/rest/v1/notifications",
                headers=headers,
                json=notification_data
            )
            
            return jsonify({'success': True, 'message': 'Mot de passe changé avec succès'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur change_password: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500



# ==================== PDF ====================
@app.route('/api/devis/<int:id_devis>/pdf', methods=['GET'])
@jwt_required()
def generate_pdf(id_devis):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        from datetime import datetime
        import io
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Image
        import os
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 1. Récupérer le devis
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'error': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        
        # 2. Récupérer le client
        client_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
            headers=headers
        )
        client = client_response.json()[0] if client_response.status_code == 200 and client_response.json() else {}
        
        # 3. Récupérer le projet
        projet_response = requests.get(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{devis.get('id_projet')}",
            headers=headers
        )
        projet = projet_response.json()[0] if projet_response.status_code == 200 and projet_response.json() else {}
        
        # 4. Récupérer les lignes
        lignes_response = requests.get(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        lignes = lignes_response.json() if lignes_response.status_code == 200 else []
        
        # 5. Récupérer les settings
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        
        if settings_response.status_code == 200 and settings_response.json():
            settings = settings_response.json()[0]
        else:
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
        
        # Ajouter les infos au devis
        devis['client_nom'] = client.get('nom', 'Non renseigné')
        devis['client_email'] = client.get('email', '-')
        devis['client_telephone'] = client.get('telephone', '-')
        devis['client_adresse'] = client.get('adresse', '-')
        devis['nom_projet'] = projet.get('nom_projet', 'Non renseigné')
        devis['projet_description'] = projet.get('description', '-')
        devis['localisation'] = projet.get('localisation', '-')
        devis['lignes'] = lignes
        
        # Conversion des types
        for ligne in devis['lignes']:
            ligne['prix_unitaire'] = float(ligne['prix_unitaire']) if ligne['prix_unitaire'] else 0
            ligne['quantite'] = int(ligne['quantite']) if ligne['quantite'] else 0
            ligne['total_ligne'] = float(ligne['total_ligne']) if ligne['total_ligne'] else 0
        
        # ========== CRÉATION DU PDF ==========
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=2*cm, leftMargin=2*cm, 
                                topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
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
        
        # Logo
        if settings.get('company_logo'):
            logo_path = os.path.join(os.path.dirname(__file__), 'uploads', settings['company_logo'])
            if os.path.exists(logo_path):
                try:
                    logo_img = Image(logo_path, width=60, height=60)
                    story.append(logo_img)
                except:
                    pass
        
        # En-tête
        company_name = settings.get('company_name', 'BTP Devis Pro')
        story.append(Paragraph(company_name, styles['Normal']))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("DEVIS PROFESSIONNEL", title_style))
        story.append(Spacer(1, 0.3*cm))
        
        company_info = f"{settings.get('company_email', '')} | {settings.get('company_phone', '')}"
        story.append(Paragraph(company_info, subtitle_style))
        if settings.get('company_address'):
            story.append(Paragraph(settings.get('company_address'), subtitle_style))
        
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("<hr/>", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
        
        # Infos devis
        info_data = [
            ['Référence', f"DEVIS-{devis['id_devis']:06d}"],
            ['Date d\'émission', datetime.fromisoformat(devis['date_creation'].replace('Z', '+00:00')).strftime('%d/%m/%Y')],
            ['Validité', '30 jours'],
            ['Statut', devis.get('statut', 'brouillon').upper()]
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
        
        # Infos client
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
        
        # Infos projet
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
        
        # Tableau des matériaux
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
        
        # Conditions
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
        
        # Signatures
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
        
        # Pied de page
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
        
        # Vérifier que le devis existe et appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,statut",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = check_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        if devis.get('statut') == 'validé':
            return jsonify({'success': False, 'message': 'Un devis validé ne peut pas être supprimé'}), 400
        
        # Supprimer les lignes du devis d'abord (clé étrangère)
        requests.delete(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        # Supprimer le devis
        response = requests.delete(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Devis supprimé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur delete_devis: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== ROUTES FACTURES ====================
@app.route('/api/facture/<int:id_devis>', methods=['POST'])
@jwt_required()
def create_facture(id_devis):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        from datetime import datetime
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 1. Vérifier que le devis existe, est validé et appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,statut,total",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        if devis.get('statut') != 'validé':
            return jsonify({'success': False, 'message': 'Le devis doit être validé avant de créer une facture'}), 400
        
        # 2. Vérifier si une facture existe déjà
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        if facture_response.status_code == 200 and facture_response.json():
            return jsonify({'success': False, 'message': 'Une facture existe déjà pour ce devis'}), 400
        
        # 3. Créer la facture
        facture_data = {
            "date_facture": datetime.now().isoformat(),
            "montant": devis.get('total', 0),
            "statut": "non payée",
            "id_devis": id_devis
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/facture",
            headers=headers,
            json=facture_data
        )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Facture créée avec succès'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur création facture: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500



@app.route('/api/facture/<int:id_facture>/pay', methods=['PUT'])
@jwt_required()
def pay_facture(id_facture):
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
        
        # 1. Vérifier que la facture existe
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}&select=id_devis",
            headers=headers
        )
        
        if facture_response.status_code != 200 or not facture_response.json():
            return jsonify({'success': False, 'message': 'Facture non trouvée'}), 404
        
        facture = facture_response.json()[0]
        id_devis = facture.get('id_devis')
        
        # 2. Vérifier que le devis appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # 3. Mettre à jour le statut de la facture
        update_data = {"statut": "payée"}
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Facture payée'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur pay_facture: {e}")
        import traceback
        traceback.print_exc()
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
        user_id = int(user_id)
        
        if 'logo' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier'}), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Fichier vide'}), 400
        
        import os
        from datetime import datetime
        ext = file.filename.rsplit('.', 1)[-1].lower()
        filename = f"logo_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        # 📁 Créer le dossier uploads s'il n'existe pas
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        # 💾 Sauvegarder le fichier
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        print(f"✅ Logo sauvegardé: {filepath}")
        
        # 🔥 Mettre à jour dans Supabase
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier si settings existe
        check_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        
        if check_response.status_code == 200 and check_response.json():
            # Mettre à jour
            update_data = {
                "company_logo": filename,
                "updated_at": datetime.now().isoformat()
            }
            response = requests.patch(
                f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
                headers=headers,
                json=update_data
            )
        else:
            # Créer
            settings_data = {
                "id_user": user_id,
                "company_logo": filename,
                "company_name": "Mon Entreprise",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            response = requests.post(
                f"{supabase_url}/rest/v1/settings",
                headers=headers,
                json=settings_data
            )
        
        if response.status_code in [200, 201, 204]:
            return jsonify({'success': True, 'logo': filename})
        else:
            return jsonify({'success': False, 'message': f'Erreur Supabase: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur upload logo: {e}")
        import traceback
        traceback.print_exc()
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
        
        # Vérifier que le devis existe et appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,statut",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = check_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Mettre à jour le statut
        update_data = {"statut": "validé"}
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Devis validé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur validate_devis: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Création facture
@app.route('/api/factures/<int:id_user>', methods=['GET'])
@jwt_required()
def get_factures(id_user):
    try:
        current_user = get_jwt_identity()
        current_user = int(current_user)
        
        print(f"🔍 Factures demandées pour user {id_user} (connecté: {current_user})")
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 1. Récupérer TOUTES les factures
        response = requests.get(
            f"{supabase_url}/rest/v1/facture?select=*",
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"❌ Erreur: {response.text}")
            return jsonify([]), 500
        
        all_factures = response.json()
        print(f"🔍 Total factures en base: {len(all_factures)}")
        
        result = []
        for facture in all_factures:
            id_devis = facture.get('id_devis')
            if not id_devis:
                continue
            
            # 2. Récupérer le devis pour vérifier l'utilisateur
            devis_response = requests.get(
                f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,id_client",
                headers=headers
            )
            
            if devis_response.status_code != 200 or not devis_response.json():
                print(f"⚠️ Devis {id_devis} non trouvé")
                continue
            
            devis = devis_response.json()[0]
            
            # Vérifier que le devis appartient à l'utilisateur
            if devis.get('id_user') != current_user:
                print(f"⏭️ Devis {id_devis} appartient à un autre utilisateur")
                continue
            
            # 3. Récupérer le nom du client
            client_nom = "Inconnu"
            id_client = devis.get('id_client')
            if id_client:
                client_response = requests.get(
                    f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}&select=nom",
                    headers=headers
                )
                if client_response.status_code == 200 and client_response.json():
                    client = client_response.json()[0]
                    client_nom = client.get('nom', 'Inconnu')
            
            result.append({
                'id_facture': facture.get('id_facture'),
                'id_devis': id_devis,
                'date_facture': facture.get('date_facture'),
                'montant': facture.get('montant', 0),
                'statut': facture.get('statut', 'non payée'),
                'client_nom': client_nom
            })
        
        print(f"📋 {len(result)} factures trouvées pour l'utilisateur {current_user}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur get_factures: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500
    
@app.route('/api/devis/<int:id_devis>', methods=['PUT'])
@jwt_required()
def update_devis(id_devis):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier que le devis existe et appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,statut",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = check_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        if devis.get('statut') == 'validé':
            return jsonify({'success': False, 'message': 'Un devis validé ne peut pas être modifié'}), 400
        
        # Supprimer les anciennes lignes
        requests.delete(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        # Recalculer le total
        lignes = data.get('lignes', [])
        total_materiaux = sum(float(ligne['quantite']) * float(ligne['prix_unitaire']) for ligne in lignes)
        total = total_materiaux * 1.2
        
        # Mettre à jour le devis
        from datetime import datetime
        update_data = {
            "id_client": data.get('id_client'),
            "id_projet": data.get('id_projet'),
            "total": total,
            "date_creation": datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            # Réinsérer les nouvelles lignes
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
            
            return jsonify({'success': True, 'message': 'Devis modifié avec succès'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur update_devis: {e}")
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
        
        from datetime import datetime
        
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
                # 🔥 Ajouter une notification UNIQUEMENT si l'utilisateur n'est PAS l'admin (id_user != 1)
                if id_user != 1:
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
                    print(f"📬 Notification de suspension envoyée à l'utilisateur {id_user}")
                else:
                    print(f"👑 Admin {id_user} suspendu - pas de notification")
                
                return jsonify({'success': True, 'message': 'Abonnement suspendu'})
            else:
                return jsonify({'error': f'Erreur mise à jour: {patch_response.text}'}), 500
        else:
            return jsonify({'error': 'Aucun abonnement trouvé'}), 404
        
    except Exception as e:
        print(f"❌ Erreur suspendre: {e}")
        import traceback
        traceback.print_exc()
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