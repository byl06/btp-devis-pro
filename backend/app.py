from flask_mail import Mail, Message
from emcf import EMCFClient
import qrcode
from io import BytesIO
from datetime import datetime, timedelta
import json
from emcf import EMCFClient, build_invoice_data
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
        
        if result:
            if isinstance(result, list) and len(result) > 0:
                user_id = result[0].get('id_user')
            elif isinstance(result, dict):
                user_id = result.get('id_user')
            else:
                user = utilisateur_model.get_by_email(data['email'])
                user_id = user.get('id_user') if user else None
            
            if user_id:
                from datetime import datetime, timedelta
                date_fin_essai = datetime.now() + timedelta(days=14)
                
                import requests
                supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
                supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
                
                headers = {
                    "Authorization": f"Bearer {supabase_key}",
                    "apikey": supabase_key,
                    "Content-Type": "application/json"
                }
                
                abo_data = {
                    "id_user": user_id,
                    "statut": "actif",
                    "date_debut": datetime.now().isoformat(),
                    "date_fin": date_fin_essai.isoformat(),
                    "type_abonnement": "essai"
                }
                
                response = requests.post(
                    f"{supabase_url}/rest/v1/abonnements",
                    headers=headers,
                    json=abo_data
                )
                
                if response.status_code in [200, 201]:
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
        
        # Créer le projet avec les nouveaux champs
        projet_data = {
            "nom_projet": data.get('nom_projet'),
            "description": data.get('description'),
            "localisation": data.get('localisation'),
            "statut": data.get('statut', 'en_attente'),
            "date_debut": data.get('date_debut'),
            "date_fin": data.get('date_fin'),
            "progression": data.get('progression', 0),
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
        
        # Mettre à jour le projet avec tous les champs
        update_data = {
            "nom_projet": data.get('nom_projet'),
            "description": data.get('description'),
            "localisation": data.get('localisation'),
            "statut": data.get('statut', 'en_attente'),
            "date_debut": data.get('date_debut'),
            "date_fin": data.get('date_fin'),
            "progression": data.get('progression', 0)
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
        
        # 5. Construire le résultat avec TOUS les champs
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
            'lignes': lignes,
            # 🔥 CHAMPS ACOMPTE - AJOUTÉS
            'acompte_pourcentage': devis.get('acompte_pourcentage', 0),
            'acompte_montant': devis.get('acompte_montant', 0),
            'acompte_paye': devis.get('acompte_paye', False),
            'date_acompte': devis.get('date_acompte'),
            'nombre_situations': devis.get('nombre_situations', 0)
        }
        
        print(f"✅ Détail devis {id_devis} - Acompte: {result['acompte_pourcentage']}%")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur get_devis_detail: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/devis/<int:id_devis>/situation', methods=['POST'])
@jwt_required()
def creer_situation(id_devis):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Données JSON invalides'}), 400
        
        print(f"🔍 Création situation pour devis {id_devis}, user {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        import requests
        from datetime import datetime
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"  # 🔥 Demander à Supabase de retourner les données
        }
        
        # Vérifier que le devis existe
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,total,acompte_montant",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Calculer le montant restant
        total = float(devis.get('total', 0))
        acompte = float(devis.get('acompte_montant', 0))
        montant_restant = total - acompte
        
        # Récupérer les situations existantes
        situations_response = requests.get(
            f"{supabase_url}/rest/v1/situation_devis?id_devis=eq.{id_devis}&order=numero.desc&limit=1",
            headers=headers
        )
        
        situations = situations_response.json() if situations_response.status_code == 200 else []
        dernier_numero = situations[0].get('numero', 0) if situations else 0
        nouveau_numero = dernier_numero + 1
        
        # Récupérer les données
        pourcentage = data.get('pourcentage', 0)
        travaux_realises = data.get('travaux_realises', '')
        
        if pourcentage < 0 or pourcentage > 100:
            return jsonify({'success': False, 'message': 'Pourcentage invalide (0-100)'}), 400
        
        montant = montant_restant * (pourcentage / 100)
        
        print(f"🔍 Nouvelle situation: numero={nouveau_numero}, pourcentage={pourcentage}%, montant={montant}")
        
        # Créer la situation
        situation_data = {
            "id_devis": id_devis,
            "numero": nouveau_numero,
            "pourcentage": pourcentage,
            "montant": round(montant, 2),
            "statut": "en_attente",
            "date_creation": datetime.now().isoformat(),
            "travaux_realises": travaux_realises
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/situation_devis",
            headers=headers,
            json=situation_data
        )
        
        print(f"🔍 Status création situation: {response.status_code}")
        print(f"🔍 Réponse brute: '{response.text}'")
        
        # 🔥 Gérer la réponse - même si vide, la création a réussi
        if response.status_code in [200, 201, 204]:
            # La création a réussi, maintenant on récupère la situation créée
            # Récupérer la dernière situation créée
            get_response = requests.get(
                f"{supabase_url}/rest/v1/situation_devis?id_devis=eq.{id_devis}&order=id_situation.desc&limit=1",
                headers=headers
            )
            
            if get_response.status_code == 200 and get_response.json():
                nouvelle_situation = get_response.json()[0]
                id_situation = nouvelle_situation.get('id_situation')
                montant_created = nouvelle_situation.get('montant', montant)
                numero_created = nouvelle_situation.get('numero', nouveau_numero)
            else:
                id_situation = None
                montant_created = round(montant, 2)
                numero_created = nouveau_numero
            
            # Mettre à jour le nombre de situations
            requests.patch(
                f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
                headers=headers,
                json={"nombre_situations": nouveau_numero}
            )
            
            return jsonify({
                'success': True,
                'message': 'Situation créée avec succès',
                'id_situation': id_situation,
                'numero': numero_created,
                'montant': montant_created
            })
        else:
            return jsonify({'success': False, 'message': f'Erreur Supabase: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur creer_situation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/devis/<int:id_devis>/payer-acompte', methods=['PUT'])
@jwt_required()
def payer_acompte(id_devis):
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
        
        # Vérifier que le devis appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Marquer l'acompte comme payé
        update_data = {
            "acompte_paye": True,
            "date_acompte": datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Acompte marqué comme payé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur payer_acompte: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


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
        from reportlab.graphics.shapes import Drawing, String, Rect
        from reportlab.graphics import renderPDF
        from reportlab.lib.colors import Color, red
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
                'accent_color': '#06B6D4',
                'slogan': '',
                'website': '',
                'footer_text': ''
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
        
        # ============================================================
        # CRÉATION DU TAMPON "PAYÉ" (pour les devis payés)
        # ============================================================
        def create_stamp_paye():
            d = Drawing(280, 180)
            
            # Rectangle rouge
            rect = Rect(0, 20, 280, 140, 
                        fillColor=Color(1, 0, 0, 0.12),
                        strokeColor=Color(1, 0, 0, 0.7),
                        strokeWidth=3)
            d.add(rect)
            
            # Texte PAYÉ
            text = String(140, 90, "PAYÉ", 
                          fontSize=46, 
                          fillColor=Color(1, 0, 0, 0.75),
                          fontName='Helvetica-Bold')
            text.rotateAngle = -25
            text.textAnchor = 'middle'
            d.add(text)
            
            # Date
            date_text = String(140, 110, datetime.now().strftime('%d/%m/%Y'),
                               fontSize=11,
                               fillColor=Color(1, 0, 0, 0.5),
                               fontName='Helvetica')
            date_text.rotateAngle = -25
            date_text.textAnchor = 'middle'
            d.add(date_text)
            
            return d
        
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
        
        slogan = settings.get('slogan', '')
        if slogan:
            story.append(Paragraph(slogan, subtitle_style))
        
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph("DEVIS PROFESSIONNEL", title_style))
        story.append(Spacer(1, 0.3*cm))
        
        company_info = f"{settings.get('company_email', '')} | {settings.get('company_phone', '')}"
        story.append(Paragraph(company_info, subtitle_style))
        
        website = settings.get('website', '')
        if website:
            story.append(Paragraph(f"🌐 {website}", subtitle_style))
        
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
            [f'Pour {entreprise_name}', 'Pour el client'],
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
        
        footer_text = settings.get('footer_text', '')
        if footer_text:
            story.append(Paragraph(footer_text, subtitle_style))
        
        footer_info = f"Devis généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - {settings.get('company_name', 'BTP Devis Pro')}"
        story.append(Paragraph(footer_info, subtitle_style))
        
        # ============================================================
        # AJOUT DU TAMPON "PAYÉ" SI LE DEVIS EST PAYÉ
        # ============================================================
        # Pour un devis, le statut "payé" n'existe pas normalement,
        # mais on peut l'ajouter si jamais
        if devis.get('statut') == 'payé' or devis.get('statut') == 'paye':
            stamp = create_stamp_paye()
            story.append(Spacer(1, 0.5*cm))
            story.append(stamp)
        
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
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            settings = response.json()[0]
        else:
            # Créer des settings par défaut
            from datetime import datetime
            settings_data = {
                "id_user": user_id,
                "company_name": "Mon Entreprise",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            post_response = requests.post(
                f"{supabase_url}/rest/v1/settings",
                headers=headers,
                json=settings_data
            )
            settings = settings_data if post_response.status_code in [200, 201] else None
        
        return jsonify({'success': True, 'settings': settings})
    except Exception as e:
        print(f"❌ Erreur get_settings: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/settings/import-header', methods=['POST'])
@jwt_required()
def import_header():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        if 'header_file' not in request.files:
            return jsonify({'success': False, 'message': 'Aucun fichier'}), 400
        
        file = request.files['header_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Fichier vide'}), 400
        
        # 🔥 Vérifier l'extension (images uniquement)
        ext = file.filename.rsplit('.', 1)[-1].lower()
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        
        if ext not in allowed_extensions:
            return jsonify({'success': False, 'message': f'Format non supporté. Utilisez: {", ".join(allowed_extensions)}'}), 400
        
        # Sauvegarder le fichier
        import os
        from datetime import datetime
        filename = f"header_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        
        upload_folder = os.path.join(os.path.dirname(__file__), 'uploads', 'headers')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        print(f"✅ En-tête image sauvegardé: {filepath}")
        
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
                "custom_header": filename,
                "updated_at": datetime.now().isoformat()
            }
            response = requests.patch(
                f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
                headers=headers,
                json=update_data
            )
        else:
            # Créer les settings
            settings_data = {
                "id_user": user_id,
                "custom_header": filename,
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
            return jsonify({'success': True, 'message': 'En-tête image importé avec succès'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur import_header: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500
    

@app.route('/api/preview-imported-header', methods=['GET'])
@jwt_required()
def preview_imported_header():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        import os
        from flask import send_file
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        import io
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Récupérer les settings
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        settings = settings_response.json()[0] if settings_response.status_code == 200 and settings_response.json() else {}
        
        # Vérifier si un en-tête personnalisé a été importé
        custom_header = settings.get('custom_header')
        if custom_header:
            header_path = os.path.join(os.path.dirname(__file__), 'uploads', 'headers', custom_header)
            if os.path.exists(header_path):
                # Si c'est un PDF, l'envoyer directement
                if custom_header.endswith('.pdf'):
                    return send_file(header_path, mimetype='application/pdf', as_attachment=True, download_name='en-tete_importe.pdf')
                # Si c'est un HTML, le convertir en PDF
                elif custom_header.endswith('.html'):
                    # Lire le HTML
                    with open(header_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Générer un PDF à partir du HTML
                    from weasyprint import HTML
                    pdf_buffer = io.BytesIO()
                    HTML(string=html_content).write_pdf(pdf_buffer)
                    pdf_buffer.seek(0)
                    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name='en-tete_importe.pdf')
        
        # Si pas d'en-tête importé, afficher un message
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("AUCUN EN-TÊTE IMPORTÉ", styles['Title']))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("Vous n'avez pas encore importé d'en-tête personnalisé.", styles['Normal']))
        story.append(Paragraph("Allez dans Paramètres → Entreprise → Importer votre en-tête.", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='aucun_en-tete.pdf')
        
    except Exception as e:
        print(f"❌ Erreur preview_imported_header: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
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





@app.route('/api/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        from datetime import datetime
        
        import requests
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Vérifier si settings existe
        check_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        
        update_data = {
            "company_name": data.get('company_name', ''),
            "company_email": data.get('company_email', ''),
            "company_phone": data.get('company_phone', ''),
            "company_address": data.get('company_address', ''),
            "primary_color": data.get('primary_color', '#1E3A8A'),
            "secondary_color": data.get('secondary_color', '#7C3AED'),
            "accent_color": data.get('accent_color', '#06B6D4'),
            "updated_at": datetime.now().isoformat(),
            "slogan": data.get('slogan', ''),
            "website": data.get('website', ''),
            "footer_text": data.get('footer_text', '')
        }
        
        # Si settings existe, mettre à jour
        if check_response.status_code == 200 and check_response.json():
            response = requests.patch(
                f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
                headers=headers,
                json=update_data
            )
        else:
            # Créer si n'existe pas
            update_data["id_user"] = user_id
            update_data["created_at"] = datetime.now().isoformat()
            response = requests.post(
                f"{supabase_url}/rest/v1/settings",
                headers=headers,
                json=update_data
            )
        
        if response.status_code in [200, 201, 204]:
            return jsonify({'success': True, 'message': 'Paramètres mis à jour'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur update_settings: {e}")
        import traceback
        traceback.print_exc()
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

@app.route('/api/preview-header', methods=['GET'])
@jwt_required()
def preview_header():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.utils import ImageReader
        import io
        import os
        from flask import send_file
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Récupérer les settings
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        settings = settings_response.json()[0] if settings_response.status_code == 200 and settings_response.json() else {}
        
        # Couleurs
        primary_color = settings.get('primary_color', '#1E3A8A')
        secondary_color = settings.get('secondary_color', '#7C3AED')
        accent_color = settings.get('accent_color', '#06B6D4')
        
        # Créer le PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        
        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor(primary_color),
            alignment=1,
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#6B7280'),
            alignment=1,
            spaceAfter=20
        )
        
        section_title = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor(primary_color),
            spaceAfter=10
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            leading=14
        )
        
        story = []
        
        # ===== EN-TÊTE AVEC LOGO ET BANDEAU =====
        # Bandeau coloré en haut
        story.append(Spacer(1, 0.5*cm))
        
        # Logo
        logo_path = None
        if settings.get('company_logo'):
            logo_path = os.path.join(os.path.dirname(__file__), 'uploads', settings['company_logo'])
        
        # Conteneur logo + titre
        if logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image(logo_path, width=80, height=80)
                story.append(logo_img)
                story.append(Spacer(1, 0.3*cm))
            except:
                pass
        
        # Nom de l'entreprise
        company_name = settings.get('company_name', 'Mon Entreprise')
        story.append(Paragraph(company_name, title_style))
        
        # Slogan
        slogan = settings.get('slogan', '')
        if slogan:
            story.append(Paragraph(slogan, subtitle_style))
        
        story.append(Spacer(1, 0.3*cm))
        
        # Ligne de séparation colorée
        story.append(Paragraph(f"<hr color='{primary_color}' size='2'/>", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
        
        # Coordonnées
        coords = []
        if settings.get('company_phone'):
            coords.append(f"📞 {settings.get('company_phone')}")
        if settings.get('company_email'):
            coords.append(f"✉ {settings.get('company_email')}")
        if settings.get('company_address'):
            coords.append(f"📍 {settings.get('company_address')}")
        if settings.get('website'):
            coords.append(f"🌐 {settings.get('website')}")
        
        if coords:
            coord_text = " | ".join(coords)
            story.append(Paragraph(coord_text, body_style))
        
        story.append(Spacer(1, 0.5*cm))
        
        # ===== APERÇU DU DEVIS =====
        story.append(Paragraph("📄 APERÇU DE L'EN-TÊTE SUR VOS DEVIS", section_title))
        story.append(Spacer(1, 0.3*cm))
        
        # Cadre d'aperçu
        story.append(Paragraph(
            "Voici comment votre en-tête apparaîtra sur vos devis et factures.",
            body_style
        ))
        story.append(Spacer(1, 0.5*cm))
        
        # Exemple de devis
        devis_data = [
            ['Référence', 'DEVIS-2025-0001'],
            ['Date', '07/07/2025'],
            ['Client', 'Exemple Client'],
            ['Montant', '1 000 000 FCFA'],
            ['Statut', 'Brouillon']
        ]
        
        table_data = [['Information', 'Valeur']]
        table_data.extend(devis_data)
        
        table = Table(table_data, colWidths=[4*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#374151')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*cm))
        
        # ===== PIED DE PAGE =====
        footer_text = settings.get('footer_text', '')
        if footer_text:
            story.append(Spacer(1, 1*cm))
            story.append(Paragraph(
                f"<font color='#6B7280' size='8'><i>{footer_text}</i></font>",
                styles['Normal']
            ))
        
        # Pied de page standard
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            f"<font color='{primary_color}' size='8'>© {datetime.now().year} {settings.get('company_name', 'Mon Entreprise')} - Tous droits réservés</font>",
            styles['Normal']
        ))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='apercu_en-tete.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erreur preview: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

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
        
        # Récupérer TOUTES les factures
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
            
            # Récupérer le devis pour vérifier l'utilisateur
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
            
            # Récupérer le nom du client
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
            
            # 🔥 AJOUT DES CHAMPS D'ARCHIVAGE ET PAIEMENT
            result.append({
                'id_facture': facture.get('id_facture'),
                'id_devis': id_devis,
                'date_facture': facture.get('date_facture'),
                'montant': facture.get('montant', 0),
                'statut': facture.get('statut', 'non payée'),
                'client_nom': client_nom,
                'type_facture': facture.get('type_facture', 'simple'),
                'statut_fiscal': facture.get('statut_fiscal', 'non_normalisee'),
                'num_facture_fiscale': facture.get('num_facture_fiscale', ''),
                'code_securite': facture.get('code_securite', ''),
                'qr_code': facture.get('qr_code', ''),
                'ifu_client': facture.get('ifu_client', ''),
                'uid_facture': facture.get('uid_facture', ''),
                # 🔥 NOUVEAUX CHAMPS
                'archivee': facture.get('archivee', False),
                'date_archivage': facture.get('date_archivage'),
                'date_paiement': facture.get('date_paiement')
            })
        
        print(f"📋 {len(result)} factures trouvées pour l'utilisateur {current_user}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur get_factures: {e}")
        import traceback
        traceback.print_exc()
        return jsonify([]), 500


# ==================== FACTURE NORMALISÉE ====================

@app.route('/api/facture/<int:id_facture>/normaliser', methods=['POST'])
@jwt_required()
def normaliser_facture(id_facture):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        ifu_client = data.get('ifu_client', '').strip()
        payment_method = data.get('payment_method', 'ESPECES')
        regime_tva = data.get('regime_tva', 'non assujetti')
        
        print("=" * 60)
        print(f"🔍 Normalisation facture {id_facture} pour user {user_id}")
        print(f"🔍 IFU client: {ifu_client}")
        print(f"🔍 Méthode paiement: {payment_method}")
        print("=" * 60)
        
        if not ifu_client or len(ifu_client) != 13:
            return jsonify({'success': False, 'message': 'IFU client invalide (13 caractères requis)'}), 400
        
        import requests
        from datetime import datetime
        import json
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # 1. Récupérer la facture
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers
        )
        
        if facture_response.status_code != 200 or not facture_response.json():
            return jsonify({'success': False, 'message': 'Facture non trouvée'}), 404
        
        facture = facture_response.json()[0]
        print(f"✅ Facture récupérée: ID {facture.get('id_facture')}")
        
        # 2. Récupérer le devis
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{facture.get('id_devis')}",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        print(f"✅ Devis récupéré: ID {devis.get('id_devis')}")
        
        # Vérifier que le devis appartient à l'utilisateur
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # 3. Récupérer le client
        client_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
            headers=headers
        )
        client = client_response.json()[0] if client_response.status_code == 200 and client_response.json() else {}
        print(f"✅ Client récupéré: {client.get('nom')}")
        
        # 4. Récupérer les lignes du devis
        lignes_response = requests.get(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{devis.get('id_devis')}",
            headers=headers
        )
        lignes = lignes_response.json() if lignes_response.status_code == 200 else []
        print(f"✅ {len(lignes)} lignes récupérées")
        
        # 5. Récupérer les settings (pour le NIF du vendeur)
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        
        if settings_response.status_code != 200 or not settings_response.json():
            return jsonify({'success': False, 'message': 'Paramètres non trouvés. Configurez votre NIF dans les paramètres.'}), 404
        
        settings = settings_response.json()[0]
        nif_vendeur = settings.get('nif', '').strip()
        
        print(f"✅ NIF vendeur: {nif_vendeur}")
        
        if not nif_vendeur or len(nif_vendeur) != 13:
            return jsonify({'success': False, 'message': f'NIF vendeur invalide ({len(nif_vendeur)} caractères). Configurez un NIF de 13 caractères.'}), 400
        
        # 6. Construire les items
        items = []
        for ligne in lignes:
            prix = float(ligne.get('prix_unitaire', 0))
            qte = float(ligne.get('quantite', 1))
            items.append({
                "name": ligne.get('designation', 'Article'),
                "price": prix,
                "quantity": qte,
                "taxGroup": "B"
            })
        
        # Montant total
        montant_total = float(facture.get('montant', 0))
        
        # 7. Préparer le payload avec le champ operator obligatoire
        invoice_payload = {
            "ifu": nif_vendeur,
            "type": "FV",
            "items": items,
            "client": {
                "ifu": ifu_client,
                "name": client.get('nom', 'Client'),
                "contact": client.get('telephone', ''),
                "address": client.get('adresse', '')
            },
            "operator": {
                "id": "",
                "name": settings.get('company_name', 'BTP Devis Pro')
            },
            "payment": [
                {
                    "name": payment_method,
                    "amount": montant_total
                }
            ]
        }
        
        print(f"📤 Payload: {json.dumps(invoice_payload, indent=2)}")
        
        # 8. Appeler l'API e-MCF
        from emcf import EMCFClient
        emcf = EMCFClient()
        
        create_result = emcf.create_invoice(invoice_payload)
        print(f"📥 Création: {json.dumps(create_result, indent=2)}")
        
        if not create_result or 'error' in create_result:
            error_msg = create_result.get('error', 'Erreur inconnue')
            return jsonify({'success': False, 'message': f'Erreur API: {error_msg}'}), 500
        
        uid = create_result.get('uid')
        if not uid:
            return jsonify({'success': False, 'message': 'UID non reçu'}), 500
        
        print(f"✅ UID reçu: {uid}")
        
        # 9. Confirmer la facture
        confirm_result = emcf.confirm_invoice(uid)
        print(f"📥 Confirmation: {json.dumps(confirm_result, indent=2)}")
        
        if not confirm_result or 'error' in confirm_result:
            error_msg = confirm_result.get('error', 'Erreur inconnue')
            return jsonify({'success': False, 'message': f'Erreur confirmation: {error_msg}'}), 500
        
        # 10. Enregistrer dans Supabase
        update_data = {
            "type_facture": "normalisee",
            "statut_fiscal": "normalisee",
            "num_facture_fiscale": confirm_result.get('nim', ''),
            "code_securite": confirm_result.get('codeMECeFDGI', ''),
            "qr_code": confirm_result.get('qrCode', ''),
            "date_validation_fiscale": datetime.now().isoformat(),
            "ifu_client": ifu_client,
            "regime_tva": regime_tva,
            "uid_facture": uid
        }
        
        print(f"📝 Mise à jour Supabase: {update_data}")
        
        patch_response = requests.patch(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers,
            json=update_data
        )
        
        print(f"📥 Update status: {patch_response.status_code}")
        print(f"📥 Update response: {patch_response.text}")
        
        if patch_response.status_code not in [200, 204]:
            return jsonify({'success': False, 'message': f'Erreur mise à jour: {patch_response.text}'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Facture normalisée avec succès',
            'num_fiscal': confirm_result.get('nim', ''),
            'qr_code': confirm_result.get('qrCode', '')[:50] + '...' if confirm_result.get('qrCode') else '',
            'code_mecf': confirm_result.get('codeMECeFDGI', '')
        })
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/facture/<int:id_facture>/pdf-normalise', methods=['GET'])
@jwt_required()
def generate_pdf_normalise(id_facture):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        from datetime import datetime
        import io
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        from reportlab.lib.utils import ImageReader
        import os
        import sys
        
        # ============================================================
        # IMPORT QR CODE AVEC GESTION D'ERREUR
        # ============================================================
        try:
            import qrcode
            from io import BytesIO
            QRCODE_AVAILABLE = True
            print("✅ QRCode library loaded successfully")
        except ImportError as e:
            print(f"⚠️ QRCode library not available: {e}")
            QRCODE_AVAILABLE = False
            qrcode = None
            BytesIO = None
        
        print("=" * 60)
        print(f"🔍 Génération PDF normalisé pour facture {id_facture}")
        print(f"🔍 QRCode disponible: {QRCODE_AVAILABLE}")
        print("=" * 60)
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Récupérer la facture
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers
        )
        
        if facture_response.status_code != 200 or not facture_response.json():
            return jsonify({'error': 'Facture non trouvée'}), 404
        
        facture = facture_response.json()[0]
        print(f"✅ Facture récupérée: ID {facture.get('id_facture')}")
        
        # Récupérer le devis
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{facture.get('id_devis')}",
            headers=headers
        )
        devis = devis_response.json()[0] if devis_response.status_code == 200 and devis_response.json() else {}
        
        # Récupérer le client
        client_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
            headers=headers
        )
        client = client_response.json()[0] if client_response.status_code == 200 and client_response.json() else {}
        
        # Récupérer les lignes
        lignes_response = requests.get(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{devis.get('id_devis')}",
            headers=headers
        )
        lignes = lignes_response.json() if lignes_response.status_code == 200 else []
        
        # Récupérer les settings
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        settings = settings_response.json()[0] if settings_response.status_code == 200 and settings_response.json() else {
            'company_name': 'BTP Devis Pro',
            'company_email': 'contact@btpdevispro.com',
            'company_phone': '+229 90000000',
            'company_address': '',
            'company_logo': None,
            'primary_color': '#1E3A8A',
            'secondary_color': '#7C3AED',
            'accent_color': '#06B6D4',
            'slogan': '',
            'website': '',
            'footer_text': '',
            'nif': 'N/A'
        }
        
        # Créer le PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        
        styles = getSampleStyleSheet()
        primary_color = settings.get('primary_color', '#1E3A8A')
        
        # ===== STYLES =====
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(primary_color),
            alignment=1,
            spaceAfter=3
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6B7280'),
            alignment=1,
            spaceAfter=5,
            leading=10
        )
        
        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#374151'),
            leading=11
        )
        
        section_title = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor(primary_color),
            spaceAfter=5,
            spaceBefore=5
        )
        
        # ===== STORY =====
        story = []
        
        # ============================================================
        # 1. EN-TÊTE
        # ============================================================
        
        # Logo
        logo_img = None
        if settings.get('company_logo'):
            logo_path = os.path.join(os.path.dirname(__file__), 'uploads', settings['company_logo'])
            if os.path.exists(logo_path):
                try:
                    logo_img = Image(logo_path, width=40, height=40)
                except:
                    pass
        
        # Titre avec logo
        if logo_img:
            header_data = [[logo_img, Paragraph("FACTURE NORMALISÉE", title_style)]]
            header_table = Table(header_data, colWidths=[2*cm, 14*cm])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(header_table)
        else:
            story.append(Paragraph("FACTURE NORMALISÉE", title_style))
        
        # Nom de l'entreprise
        company_name = settings.get('company_name', 'BTP Devis Pro')
        story.append(Paragraph(company_name, subtitle_style))
        
        # Slogan
        slogan = settings.get('slogan', '')
        if slogan:
            story.append(Paragraph(slogan, subtitle_style))
        
        # Coordonnées
        coords = []
        if settings.get('company_address'):
            coords.append(settings.get('company_address'))
        if settings.get('company_phone'):
            coords.append(f"📞 {settings.get('company_phone')}")
        if settings.get('company_email'):
            coords.append(f"✉ {settings.get('company_email')}")
        if settings.get('website'):
            coords.append(f"🌐 {settings.get('website')}")
        
        if coords:
            story.append(Paragraph(" | ".join(coords), subtitle_style))
        
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(f"<hr color='{primary_color}' size='1'/>", styles['Normal']))
        story.append(Spacer(1, 0.2*cm))
        
        # ============================================================
        # 2. INFORMATIONS (3 colonnes)
        # ============================================================
        
        # Vendeur
        vendeur_text = f"""
        <b>Vendeur</b><br/>
        {settings.get('company_name', 'BTP Devis Pro')}<br/>
        IFU: {settings.get('nif', 'N/A')}
        """
        
        # Client
        client_text = f"""
        <b>Client</b><br/>
        {client.get('nom', 'Non renseigné')}<br/>
        IFU: {facture.get('ifu_client', 'N/A')}
        """
        
        # Facture
        facture_text = f"""
        <b>Facture</b><br/>
        NIM: {facture.get('num_facture_fiscale', 'N/A')}<br/>
        Date: {datetime.fromisoformat(facture['date_facture'].replace('Z', '+00:00')).strftime('%d/%m/%Y')}
        """
        
        info_data = [[
            Paragraph(vendeur_text, body_style),
            Paragraph(client_text, body_style),
            Paragraph(facture_text, body_style)
        ]]
        
        info_table = Table(info_data, colWidths=[4.5*cm, 4.5*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*cm))
        
        # ============================================================
        # 3. TABLEAU DES ARTICLES
        # ============================================================
        
        story.append(Paragraph("Détail des prestations", section_title))
        
        table_data = [['Désignation', 'Qté', 'Prix U.', 'Total']]
        total_ht = 0
        
        for ligne in lignes:
            total_ligne = ligne.get('quantite', 0) * ligne.get('prix_unitaire', 0)
            total_ht += total_ligne
            table_data.append([
                Paragraph(ligne.get('designation', ''), body_style),
                str(ligne.get('quantite', 0)),
                f"{ligne.get('prix_unitaire', 0):,.0f}",
                f"{total_ligne:,.0f}"
            ])
        
        tva = total_ht * 0.18
        total_ttc = total_ht + tva
        
        # Lignes de total
        table_data.append(['', '', '', ''])
        table_data.append(['', '', 'Sous-total HT', f"{total_ht:,.0f}"])
        table_data.append(['', '', 'TVA (18%)', f"{tva:,.0f}"])
        table_data.append(['', '', 'TOTAL TTC', f"{total_ttc:,.0f}"])
        
        main_table = Table(table_data, colWidths=[6.5*cm, 2*cm, 3*cm, 3.5*cm])
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(primary_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -4), 8),
            ('ALIGN', (1, 1), (-1, -4), 'CENTER'),
            ('ALIGN', (0, 1), (0, -4), 'LEFT'),
            ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 8),
            ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor('#F1F5F9')),
            ('TEXTCOLOR', (0, -3), (-1, -1), colors.HexColor(primary_color)),
            ('ALIGN', (2, -3), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(primary_color)),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.HexColor('#E2E8F0')),
            ('BOX', (0, -3), (-1, -1), 0.5, colors.HexColor(primary_color)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 0.3*cm))
        
        # ============================================================
        # 4. INFORMATIONS FISCALES + QR CODE
        # ============================================================
        
        # Récupérer le QR Code
        qr_code_data = facture.get('qr_code', '')
        print(f"🔍 QR Code data: {qr_code_data[:50] if qr_code_data else 'VIDE'}")
        print(f"🔍 Longueur: {len(qr_code_data) if qr_code_data else 0}")
        
        # Infos fiscales à gauche
        fiscal_left = f"""
        <b>Informations fiscales</b><br/>
        NIM: {facture.get('num_facture_fiscale', 'N/A')}<br/>
        Code MECeF: {facture.get('code_securite', 'N/A')}<br/>
        Date/Heure: {datetime.fromisoformat(facture['date_facture'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M:%S')}<br/>
        Type: Facture de vente (FV)
        """
        
        fiscal_left_paragraph = Paragraph(fiscal_left, body_style)
        
        # ===== GÉNÉRATION DU QR CODE =====
        qr_element = None
        
        if qr_code_data and len(qr_code_data) > 10 and QRCODE_AVAILABLE:
            try:
                print("🔍 Tentative de génération du QR Code...")
                
                # Créer le QR Code
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=5,
                    border=2,
                )
                qr.add_data(str(qr_code_data))
                qr.make(fit=True)
                
                # Générer l'image
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                
                # 🔥 CORRECTION : Utiliser directement le buffer avec Image
                # Ne pas utiliser ImageReader, passer le buffer directement
                qr_element = Image(qr_buffer, width=2.5*cm, height=2.5*cm)
                print("✅ QR Code généré avec succès !")
                
            except Exception as e:
                print(f"❌ Erreur génération QR Code: {e}")
                import traceback
                traceback.print_exc()
                qr_element = Paragraph("⚠️ Erreur QR Code", body_style)
        elif qr_code_data and len(qr_code_data) > 10 and not QRCODE_AVAILABLE:
            print("❌ QRCode library non disponible")
            qr_element = Paragraph("⚠️ QR Code (librairie manquante)", body_style)
        else:
            print("❌ Pas de données QR Code")
            qr_element = Paragraph("⚠️ Aucun QR Code", body_style)
        
        # Tableau 2 colonnes
        fiscal_qr_data = [[fiscal_left_paragraph, qr_element]]
        fiscal_qr_table = Table(fiscal_qr_data, colWidths=[9*cm, 5*cm])
        fiscal_qr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEFCE8')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#F59E0B')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        ]))
        story.append(fiscal_qr_table)
        story.append(Spacer(1, 0.3*cm))
        
        # ============================================================
        # 5. MENTION
        # ============================================================
        
        mention_text = """
        <b>✔️ Facture normalisée conforme à la réglementation fiscale en vigueur</b><br/>
        <font color='#6B7280' size='7'>Émise via le système e-MCF de la DGI</font>
        """
        mention_style = ParagraphStyle(
            'Mention',
            parent=styles['Normal'],
            alignment=1,
            fontSize=8,
            textColor=colors.HexColor('#1F2937'),
            spaceAfter=3
        )
        story.append(Paragraph(mention_text, mention_style))
        
        # ============================================================
        # 6. PIED DE PAGE
        # ============================================================
        
        story.append(Paragraph(f"<hr color='{primary_color}' size='0.5'/>", styles['Normal']))
        
        footer_info = f"""
        <font color='#6B7280' size='6'>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - {settings.get('company_name', 'BTP Devis Pro')}</font>
        """
        story.append(Paragraph(footer_info, subtitle_style))
        
        # ============================================================
        # CONSTRUCTION
        # ============================================================
        
        doc.build(story)
        buffer.seek(0)
        
        print("✅ PDF généré avec succès")
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'facture_normalisee_{id_facture}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erreur PDF normalisé: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/devis/<int:id_devis>/acompte', methods=['POST'])
@jwt_required()
def configurer_acompte(id_devis):
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
        
        # Vérifier que le devis existe
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user,total",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        pourcentage = data.get('pourcentage', 0)
        montant = float(devis.get('total', 0)) * (pourcentage / 100)
        
        update_data = {
            "acompte_pourcentage": pourcentage,
            "acompte_montant": round(montant, 2),
            "acompte_paye": False
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({
                'success': True,
                'message': 'Acompte configuré avec succès',
                'acompte_montant': round(montant, 2)
            })
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur configurer_acompte: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
    

@app.route('/api/devis/<int:id_devis>/situations', methods=['GET'])
@jwt_required()
def get_situations(id_devis):
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
        
        # Vérifier que le devis appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'error': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'error': 'Non autorisé'}), 403
        
        # Récupérer les situations
        response = requests.get(
            f"{supabase_url}/rest/v1/situation_devis?id_devis=eq.{id_devis}&order=numero.asc",
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([]), 500
        
    except Exception as e:
        print(f"❌ Erreur get_situations: {e}")
        return jsonify([]), 500

@app.route('/api/situation/<int:id_situation>/payer', methods=['PUT'])
@jwt_required()
def payer_situation(id_situation):
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
        
        # Vérifier que la situation existe
        situation_response = requests.get(
            f"{supabase_url}/rest/v1/situation_devis?id_situation=eq.{id_situation}&select=id_devis",
            headers=headers
        )
        
        if situation_response.status_code != 200 or not situation_response.json():
            return jsonify({'success': False, 'message': 'Situation non trouvée'}), 404
        
        situation = situation_response.json()[0]
        id_devis = situation.get('id_devis')
        
        # Vérifier que le devis appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Marquer comme payée
        update_data = {
            "statut": "payee",
            "date_paiement": datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/situation_devis?id_situation=eq.{id_situation}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Situation marquée comme payée'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur payer_situation: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ARCHIVAGE FACTURES ====================

@app.route('/api/facture/<int:id_facture>/archiver', methods=['POST'])
@jwt_required()
def archiver_facture(id_facture):
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
        
        # Vérifier que la facture existe
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}&select=id_facture,id_devis",
            headers=headers
        )
        
        if facture_response.status_code != 200 or not facture_response.json():
            return jsonify({'success': False, 'message': 'Facture non trouvée'}), 404
        
        facture = facture_response.json()[0]
        
        # Vérifier que le devis appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{facture.get('id_devis')}&select=id_user",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Archiver la facture
        update_data = {
            "archivee": True,
            "date_archivage": datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Facture archivée avec succès'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur archiver: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/facture/<int:id_facture>/desarchiver', methods=['POST'])
@jwt_required()
def desarchiver_facture(id_facture):
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
        
        update_data = {
            "archivee": False,
            "date_archivage": None
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Facture désarchivée avec succès'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur désarchiver: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== PAIEMENT FACTURES ====================

@app.route('/api/facture/<int:id_facture>/pay', methods=['PUT'])
@jwt_required()
def pay_facture(id_facture):
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
        
        # Vérifier que la facture existe
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}&select=id_facture,id_devis,statut",
            headers=headers
        )
        
        if facture_response.status_code != 200 or not facture_response.json():
            return jsonify({'success': False, 'message': 'Facture non trouvée'}), 404
        
        facture = facture_response.json()[0]
        
        # Vérifier que le devis appartient à l'utilisateur
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{facture.get('id_devis')}&select=id_user",
            headers=headers
        )
        
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'success': False, 'message': 'Devis non trouvé'}), 404
        
        devis = devis_response.json()[0]
        if devis.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # Si déjà payée
        if facture.get('statut') == 'payée':
            return jsonify({'success': False, 'message': 'Cette facture est déjà payée'}), 400
        
        # Marquer comme payée
        update_data = {
            "statut": "payée",
            "date_paiement": datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({
                'success': True,
                'message': 'Facture marquée comme payée',
                'date_paiement': update_data['date_paiement']
            })
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur pay_facture: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/facture/<int:id_facture>/pdf', methods=['GET'])
@jwt_required()
def generate_facture_pdf(id_facture):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        from datetime import datetime
        import io
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm
        import os
        
        supabase_url = "https://aoqiveekzucqjhqdwiql.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFvcWl2ZWVrenVjcWpocWR3aXFsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjIzMjI4NSwiZXhwIjoyMDk3ODA4Mjg1fQ.NqbuEcuQDAKOIqD26UkCbUNNJz0kRXWiAZpGLxYvtbA"
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Récupérer les données
        facture_response = requests.get(
            f"{supabase_url}/rest/v1/facture?id_facture=eq.{id_facture}",
            headers=headers
        )
        
        if facture_response.status_code != 200 or not facture_response.json():
            return jsonify({'error': 'Facture non trouvée'}), 404
        
        facture = facture_response.json()[0]
        
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{facture.get('id_devis')}",
            headers=headers
        )
        devis = devis_response.json()[0] if devis_response.status_code == 200 and devis_response.json() else {}
        
        client_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
            headers=headers
        )
        client = client_response.json()[0] if client_response.status_code == 200 and client_response.json() else {}
        
        lignes_response = requests.get(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{devis.get('id_devis')}",
            headers=headers
        )
        lignes = lignes_response.json() if lignes_response.status_code == 200 else []
        
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        settings = settings_response.json()[0] if settings_response.status_code == 200 and settings_response.json() else {}
        
        # ============================================================
        # CRÉATION DU PDF - 1 PAGE
        # ============================================================
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        
        styles = getSampleStyleSheet()
        
        # Styles réduits pour tenir sur 1 page
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Normal'],
            fontSize=16,
            fontName='Times-Bold',
            textColor=colors.HexColor('#333333'),
            alignment=1,
            spaceAfter=3
        )
        
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=8,
            fontName='Times-Roman',
            textColor=colors.HexColor('#333333'),
            leading=10
        )
        
        bold_style = ParagraphStyle(
            'BoldStyle',
            parent=normal_style,
            fontName='Times-Bold'
        )
        
        small_style = ParagraphStyle(
            'SmallStyle',
            parent=normal_style,
            fontSize=7,
            leading=9
        )
        
        beige = colors.HexColor('#F3C8AA')
        light_grey = colors.HexColor('#EEEEEE')
        black = colors.HexColor('#000000')
        
        story = []
        
        # ============================================================
        # 1. EN-TÊTE IMPORTÉ (IMAGE)
        # ============================================================
        custom_header = settings.get('custom_header')
        header_imported = False
        
        if custom_header:
            header_path = os.path.join(os.path.dirname(__file__), 'uploads', 'headers', custom_header)
            if os.path.exists(header_path):
                try:
                    header_img = Image(header_path, width=17*cm, height=2.5*cm)
                    story.append(header_img)
                    story.append(Spacer(1, 0.2*cm))
                    header_imported = True
                except:
                    pass
        
        if not header_imported:
            # FACTURE | Logo
            left_cell = Paragraph("FACTURE", title_style)
            logo_cell = ""
            if settings.get('company_logo'):
                logo_path = os.path.join(os.path.dirname(__file__), 'uploads', settings['company_logo'])
                if os.path.exists(logo_path):
                    try:
                        logo_img = Image(logo_path, width=40, height=40)
                        logo_cell = logo_img
                    except:
                        logo_cell = ""
            
            header_table = Table([[left_cell, logo_cell]], colWidths=[12*cm, 5*cm])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('BACKGROUND', (0, 0), (0, 0), beige),
                ('BOX', (0, 0), (0, 0), 1, black),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 0.2*cm))
        
        # ============================================================
        # 2. INFOS SOCIÉTÉ / CLIENT (réduit)
        # ============================================================
        
        company_info = f"""
        <b>{settings.get('company_name', 'Mon Entreprise')}</b><br/>
        {settings.get('company_address', '')}<br/>
        {settings.get('company_phone', '')}<br/>
        {settings.get('company_email', '')}
        """
        
        facture_info = f"""
        <b>Client</b><br/>
        {client.get('nom', 'Non renseigné')}<br/>
        {client.get('adresse', '')}<br/>
        N° Facture: {facture.get('id_facture')}<br/>
        Date: {datetime.fromisoformat(facture['date_facture'].replace('Z', '+00:00')).strftime('%d/%m/%Y')}
        """
        
        info_table = Table([
            [Paragraph(company_info, normal_style), Paragraph(facture_info, normal_style)]
        ], colWidths=[8*cm, 8*cm])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.2*cm))
        
        # ============================================================
        # 3. OBJET DE LA FACTURE (réduit)
        # ============================================================
        
        objet_data = [[Paragraph("<b>Objet de la facture</b>", normal_style)]]
        objet_table = Table(objet_data, colWidths=[17*cm])
        objet_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(objet_table)
        story.append(Spacer(1, 0.2*cm))
        
        # ============================================================
        # 4. TABLEAU PRINCIPAL (réduit)
        # ============================================================
        
        table_data = [
            ['Réf', 'Désignation', 'Qté', 'Prix U.', 'Montant HT']
        ]
        
        total_ht = 0
        for i, ligne in enumerate(lignes[:8]):  # Max 8 lignes pour tenir
            ref = f"ART-{i+1:03d}"
            designation = ligne.get('designation', '')[:30]  # Tronquer
            qte = str(ligne.get('quantite', 0))
            prix = f"{ligne.get('prix_unitaire', 0):,.0f}"
            total_ligne = ligne.get('quantite', 0) * ligne.get('prix_unitaire', 0)
            total_ht += total_ligne
            table_data.append([ref, designation, qte, prix, f"{total_ligne:,.0f}"])
        
        # Ajouter des lignes vides si moins de 8
        while len(table_data) < 9:
            table_data.append(['', '', '', '', ''])
        
        # Totaux
        remise = 0
        tva = total_ht * 0.18
        total_ttc = total_ht + tva
        
        table_data.append(['', '', '', '', ''])
        table_data.append(['', '', '', 'TOTAL HT', f"{total_ht:,.0f}"])
        table_data.append(['', '', '', 'TVA (18%)', f"{tva:,.0f}"])
        table_data.append(['', '', '', 'TOTAL TTC', f"{total_ttc:,.0f}"])
        
        main_table = Table(table_data, colWidths=[2*cm, 5.5*cm, 2*cm, 2.5*cm, 4*cm])
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), beige),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('FONTNAME', (0, 1), (-1, -4), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -4), 7),
            ('ALIGN', (2, 1), (4, -5), 'CENTER'),
            ('FONTNAME', (0, -3), (-1, -1), 'Times-Bold'),
            ('FONTSIZE', (0, -3), (-1, -1), 8),
            ('ALIGN', (3, -3), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (3, -3), (3, -1), beige),
            ('BACKGROUND', (0, -1), (2, -1), beige),
            ('BACKGROUND', (3, -1), (4, -1), beige),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(main_table)
        story.append(Spacer(1, 0.2*cm))
        
        # ============================================================
        # 5. MODE DE PAIEMENT (réduit)
        # ============================================================
        
        paiement_data = [
            [Paragraph("<b>Mode de paiement</b>", normal_style)],
            [Paragraph("Virement / Espèces", normal_style)],
            [Paragraph(f"Échéance: {datetime.now().strftime('%d/%m/%Y')}", small_style)]
        ]
        
        paiement_table = Table(paiement_data, colWidths=[5*cm])
        paiement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), beige),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(paiement_table)
        story.append(Spacer(1, 0.2*cm))
        
        # ============================================================
        # 6. CONDITIONS + REMERCIEMENT (réduit)
        # ============================================================
        
        conditions_text = """
        <b>Conditions :</b> Règlement avant échéance. Frais de retard applicables.
        """
        story.append(Paragraph(conditions_text, small_style))
        story.append(Spacer(1, 0.1*cm))
        
        thanks_text = """
        Nous vous remercions d'avoir choisi nos services.
        """
        thanks_style = ParagraphStyle(
            'ThanksStyle',
            parent=normal_style,
            alignment=1,
            fontSize=8
        )
        story.append(Paragraph(thanks_text, thanks_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'facture_{id_facture}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erreur génération facture PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
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
            f"{supabase_url}/rest/v1/notifications?id_user=eq.{user_id}&est_lue=eq.0&order=date_creation.desc",
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([])
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/<int:id_notification>/lire', methods=['PUT'])
@jwt_required()
def marquer_notification_lue(id_notification):
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
        
        update_data = {"est_lue": 1}
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/notifications?id_notification=eq.{id_notification}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True})
        else:
            return jsonify({'error': response.text}), 500
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
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
        
        # Récupérer tous les utilisateurs
        users_response = requests.get(
            f"{supabase_url}/rest/v1/utilisateur?select=*",
            headers=headers
        )
        
        if users_response.status_code != 200:
            return jsonify([]), 500
        
        all_users = users_response.json()
        result = []
        
        for u in all_users:
            if u.get('id_user') == 1:
                continue
            
            # Récupérer l'abonnement
            abo_response = requests.get(
                f"{supabase_url}/rest/v1/abonnements?id_user=eq.{u.get('id_user')}",
                headers=headers
            )
            abo = abo_response.json()[0] if abo_response.status_code == 200 and abo_response.json() else None
            
            from datetime import datetime
            jours_restants = 0
            if abo and abo.get('date_fin'):
                date_fin = datetime.fromisoformat(abo['date_fin'].replace('Z', '+00:00'))
                jours_restants = (date_fin - datetime.now()).days
            
            result.append({
                'nom': u.get('nom', ''),
                'email': u.get('email', ''),
                'entreprise': u.get('entreprise', ''),
                'telephone': u.get('telephone', ''),
                'type_abonnement': abo.get('type_abonnement') if abo else '-',
                'statut': abo.get('statut') if abo else '-',
                'date_debut': abo.get('date_debut') if abo else None,
                'date_fin': abo.get('date_fin') if abo else None,
                'jours_restants': max(0, jours_restants)
            })
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur export: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/paiements/<int:id_user>', methods=['GET'])
@jwt_required()
def admin_get_paiements(id_user):
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
        
        response = requests.get(
            f"{supabase_url}/rest/v1/paiements?id_user=eq.{id_user}&order=date_paiement.desc",
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([])
        
    except Exception as e:
        print(f"❌ Erreur paiements: {e}")
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

@app.route('/api/test-emcf', methods=['GET'])
@jwt_required()
def test_emcf():
    try:
        from emcf import EMCFClient
        import json
        
        print("=" * 60)
        print("🧪 TEST DE L'API e-MCF")
        print("=" * 60)
        
        client = EMCFClient()
        
        # 1. Tester le statut
        print("\n1️⃣ Test du statut...")
        status = client.get_status()
        print(f"Status: {status}")
        
        if not status:
            return jsonify({'error': 'JWT invalide ou API inaccessible'}), 500
        
        # 2. Créer une facture de test
        print("\n2️⃣ Création d'une facture de test...")
        test_data = {
            "ifu": "0202347221089",
            "type": "FV",
            "items": [
                {"name": "Article test", "price": 1000, "quantity": 1, "taxGroup": "B"}
            ],
            "client": {
                "ifu": "0202347221090",
                "name": "Client Test",
                "contact": "90000000",
                "address": "Test"
            },
            "payment": [
                {"name": "ESPECES", "amount": 1180}
            ]
        }
        
        print(f"📤 Payload: {json.dumps(test_data, indent=2)}")
        
        create_result = client.create_invoice(test_data)
        print(f"📥 Résultat création: {json.dumps(create_result, indent=2)}")
        
        result = {
            'status': status,
            'create': create_result
        }
        
        # 3. Si création OK, confirmer
        if create_result and 'uid' in create_result:
            uid = create_result['uid']
            print(f"\n3️⃣ Confirmation de la facture {uid}...")
            confirm_result = client.confirm_invoice(uid)
            print(f"📥 Résultat confirmation: {json.dumps(confirm_result, indent=2)}")
            result['confirm'] = confirm_result
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ==================== ROUTES DE TEST e-MCF ====================

@app.route('/api/test-emcf-status', methods=['GET'])
@jwt_required()
def test_emcf_status():
    """Test simple du statut e-MCF"""
    try:
        from emcf import EMCFClient
        client = EMCFClient()
        status = client.get_status()
        return jsonify({
            'success': True,
            'jwt_present': bool(client.jwt_token),
            'jwt_length': len(client.jwt_token) if client.jwt_token else 0,
            'status': status
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-emcf-create', methods=['GET'])
@jwt_required()
def test_emcf_create():
    """Test de création d'une facture e-MCF"""
    try:
        from emcf import EMCFClient
        import json
        
        client = EMCFClient()
        
        # Facture de test très simple
        test_data = {
            "ifu": "0202347221089",
            "type": "FV",
            "items": [
                {"name": "Article Test", "price": 1000, "quantity": 1, "taxGroup": "B"}
            ],
            "client": {
                "ifu": "0202347221090",
                "name": "Client Test",
                "contact": "90000000",
                "address": "Test"
            },
            "payment": [
                {"name": "ESPECES", "amount": 1180}
            ]
        }
        
        create_result = client.create_invoice(test_data)
        
        return jsonify({
            'success': True,
            'create_result': create_result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-emcf-confirm/<uid>', methods=['GET'])
@jwt_required()
def test_emcf_confirm(uid):
    """Test de confirmation d'une facture e-MCF"""
    try:
        from emcf import EMCFClient
        client = EMCFClient()
        
        confirm_result = client.confirm_invoice(uid)
        
        return jsonify({
            'success': True,
            'uid': uid,
            'confirm_result': confirm_result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-emcf-pending', methods=['GET'])
@jwt_required()
def test_emcf_pending():
    """Voir les factures en attente"""
    try:
        from emcf import EMCFClient
        client = EMCFClient()
        
        pending = client.get_pending_invoices()
        
        return jsonify({
            'success': True,
            'pending_count': len(pending) if pending else 0,
            'pending': pending
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-emcf-cancel/<uid>', methods=['POST'])
@jwt_required()
def test_emcf_cancel(uid):
    """Annuler une facture en attente"""
    try:
        from emcf import EMCFClient
        client = EMCFClient()
        
        result = client.cancel_invoice(uid)
        
        return jsonify({
            'success': True,
            'uid': uid,
            'cancelled': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-emcf-clear-all', methods=['POST'])
@jwt_required()
def test_emcf_clear_all():
    """Annuler toutes les factures en attente"""
    try:
        from emcf import EMCFClient
        client = EMCFClient()
        
        pending = client.get_pending_invoices()
        if not pending:
            return jsonify({'message': 'Aucune facture en attente'})
        
        results = []
        for invoice in pending:
            uid = invoice.get('uid')
            if uid:
                result = client.cancel_invoice(uid)
                results.append({'uid': uid, 'cancelled': result})
        
        return jsonify({
            'message': f'{len(results)} factures annulées',
            'results': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500