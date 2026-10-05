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
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
import os
import re
import hmac
import hashlib
from dotenv import load_dotenv
import os

# 🔥 Charger les variables d'environnement
load_dotenv()

app = Flask(__name__)

CORS(app, origins=[
    "http://localhost:8000",
    "https://btp-devis-pro-1.onrender.com",
    "https://btpdevispro-info.netlify.app"
], supports_credentials=True)



# OU pour plusieurs origines


# ============================================================
# 5. CONFIGURATION RATE LIMITING
# ============================================================

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
limiter.init_app(app)  # 🔥 IMPORTANT : init_app après la création

def sanitize_input(text):
    """Nettoie les entrées utilisateur contre les XSS"""
    if not text:
        return text
    
    # Supprimer les balises HTML/JavaScript
    text = re.sub(r'<[^>]*>', '', text)
    
    # Supprimer les caractères dangereux
    dangerous = ['&', '<', '>', '"', "'", '/', ';']
    for char in dangerous:
        text = text.replace(char, '')
    
    return text.strip()
# ==================== UTILITAIRE VÉRIFICATION ABONNEMENT ====================
def verifier_abonnement(user_id):
    """Vérifie si l'utilisateur a un abonnement actif. Retourne (bool, message, headers, supabase_url)"""
    from datetime import datetime
    import requests
    
    supabase_url = os.environ.get('SUPABASE_URL', '')
    supabase_key = os.environ.get('SUPABASE_KEY', '')
    
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
def log_action(user_id, action, details=None):
    """Enregistre une action dans les logs"""
    try:
        import requests
        from datetime import datetime
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        log_data = {
            "id_user": user_id,
            "action": action,
            "details": details,
            "ip": request.remote_addr,
            "user_agent": request.headers.get('User-Agent')
        }
        
        requests.post(
            f"{supabase_url}/rest/v1/logs",
            headers=headers,
            json=log_data
        )
    except Exception as e:
        print(f"⚠️ Erreur log: {e}")

def valider_nif(ifu):
    """
    Valide un NIF/IFU béninois (13 caractères)
    Format: 02 + 9 chiffres + 2 chiffres de contrôle
    """
    if not ifu or len(ifu) != 13:
        return False
    
    if not ifu.isdigit():
        return False
    
    # Vérification simple : tous les IFU commencent par 02
    if not ifu.startswith('02'):
        return False
    
    return True


# Configuration SendGrid
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = ''  # ← Ta clé API SendGrid
app.config['MAIL_DEFAULT_SENDER'] = 'bylgaitb@gmail.com'  # Ton email

mail = Mail(app)

# Configuration CORS - Autorise toutes les origines (pour Render)

# Configuration JWT
app.config['JWT_SECRET_KEY'] = 'btp-devis-pro-super-secret-key-2024-32chars'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

 #AJOUTER CES LIGNES
app.config['JWT_TOKEN_LOCATION'] = ['cookies']  # Forcer les cookies
app.config['JWT_COOKIE_SECURE'] = False  # True en production avec HTTPS
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Désactiver CSRF pour test
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token_cookie'
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
@limiter.limit("10 per minute")
@limiter.limit("10 per minute")  # 🔥 Anti-brute force
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        existing = utilisateur_model.get_by_email(data['email'])
        if existing:
            return jsonify({'success': False, 'message': 'Email déjà utilisé'}), 400
        
        # 🔥 SANITIZE - Nettoyer les entrées
        nom = sanitize_input(data.get('nom'))
        email = sanitize_input(data.get('email'))
        entreprise = sanitize_input(data.get('entreprise'))
        telephone = sanitize_input(data.get('telephone'))
        mot_de_passe = data.get('mot_de_passe')
        
        result = utilisateur_model.create(
            nom, email, mot_de_passe,
            entreprise, telephone
        )
        
        if result:
            if isinstance(result, list) and len(result) > 0:
                user_id = result[0].get('id_user')
            elif isinstance(result, dict):
                user_id = result.get('id_user')
            else:
                user = utilisateur_model.get_by_email(email)
                user_id = user.get('id_user') if user else None
            
            if user_id:
                from datetime import datetime, timedelta
                date_fin_essai = datetime.now() + timedelta(days=14)
                
                import requests
                supabase_url = os.environ.get('SUPABASE_URL', '')
                supabase_key = os.environ.get('SUPABASE_KEY', '')
                
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
                    log_action(user_id, 'register', "Nouvel utilisateur inscrit")
                    return jsonify({'success': True, 'message': 'Inscription réussie ! Période d\'essai de 14 jours.'})
        
        return jsonify({'success': False, 'message': 'Erreur lors de l\'inscription'}), 500
        
    except Exception as e:
        print(f"❌ Erreur register: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

    
@limiter.limit("5 per minute")
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        mot_de_passe = data.get('mot_de_passe')
        
        user = utilisateur_model.authenticate(email, mot_de_passe)
        
        if user:
            user_id = str(user['id_user'])
            token = create_access_token(identity=user_id)
            
            response = jsonify({
                'success': True,
                'user': {
                    'id': user['id_user'],
                    'nom': user['nom'],
                    'email': user['email'],
                    'entreprise': user['entreprise']
                }
            })
            
            # 🔥 LA LIGNE MAGIQUE
            set_access_cookies(response, token)
            
            return response
        return jsonify({'success': False, 'message': 'Identifiants incorrects'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({'success': True, 'message': 'Déconnexion réussie'})
    unset_jwt_cookies(response)
    return response
    
    


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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
    
@limiter.limit("100 per hour")
@app.route('/api/clients', methods=['POST'])
@jwt_required()
def create_client():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        ok, message, headers, supabase_url = verifier_abonnement(user_id)
        if not ok:
            return jsonify({'success': False, 'message': message}), 403
        
        # 🔥 SANITIZE - Nettoyer les entrées
        client_data = {
            "nom": sanitize_input(data.get('nom')),
            "telephone": sanitize_input(data.get('telephone')),
            "email": sanitize_input(data.get('email')),
            "adresse": sanitize_input(data.get('adresse')),
            "ifu": sanitize_input(data.get('ifu', '')),
            "id_user": user_id
        }
        
        response = requests.post(
            f"{supabase_url}/rest/v1/client",
            headers=headers,
            json=client_data
        )
        
        if response.status_code in [200, 201]:
            log_action(user_id, 'create_client', f"Client {client_data['nom']} créé")
            return jsonify({'success': True, 'message': 'Client créé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_client: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
@limiter.limit("100 per hour")
@app.route('/api/clients/<int:id_client>', methods=['PUT'])
@jwt_required()
def update_client(id_client):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        check_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}&select=id_user",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        
        client = check_response.json()[0]
        if client.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # 🔥 SANITIZE - Nettoyer les entrées
        update_data = {
            "nom": sanitize_input(data.get('nom')),
            "telephone": sanitize_input(data.get('telephone')),
            "email": sanitize_input(data.get('email')),
            "adresse": sanitize_input(data.get('adresse')),
            "ifu": sanitize_input(data.get('ifu', ''))
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            log_action(user_id, 'update_client', f"Client {update_data['nom']} modifié")
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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

@limiter.limit("100 per hour")
@app.route('/api/projets', methods=['POST'])
@jwt_required()
def create_projet():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        ok, message, headers, supabase_url = verifier_abonnement(user_id)
        if not ok:
            return jsonify({'success': False, 'message': message}), 403
        
        # 🔥 SANITIZE - Nettoyer les entrées
        projet_data = {
            "nom_projet": sanitize_input(data.get('nom_projet')),
            "description": sanitize_input(data.get('description')),
            "localisation": sanitize_input(data.get('localisation')),
            "statut": sanitize_input(data.get('statut', 'en_attente')),
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
            log_action(user_id, 'create_projet', f"Projet {projet_data['nom_projet']} créé")
            return jsonify({'success': True, 'message': 'Projet créé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_projet: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@limiter.limit("100 per hour")
@app.route('/api/projets/<int:id_projet>', methods=['PUT'])
@jwt_required()
def update_projet(id_projet):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')

        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        check_response = requests.get(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{id_projet}&select=id_user",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Projet non trouvé'}), 404
        
        projet = check_response.json()[0]
        if projet.get('id_user') != user_id:
            return jsonify({'success': False, 'message': 'Non autorisé'}), 403
        
        # 🔥 SANITIZE - Nettoyer les entrées
        update_data = {
            "nom_projet": sanitize_input(data.get('nom_projet')),
            "description": sanitize_input(data.get('description')),
            "localisation": sanitize_input(data.get('localisation')),
            "statut": sanitize_input(data.get('statut', 'en_attente')),
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
            log_action(user_id, 'update_projet', f"Projet {update_data['nom_projet']} modifié")
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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

@limiter.limit("100 per hour")
@app.route('/api/devis', methods=['POST'])
@jwt_required()
def create_devis():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        print(f"🔍 Création devis pour user_id: {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        ok, message, headers, supabase_url = verifier_abonnement(user_id)
        if not ok:
            return jsonify({'success': False, 'message': message}), 403
        
        from datetime import datetime
        
        lignes = data.get('lignes', [])
        total_materiaux = sum(float(ligne['quantite']) * float(ligne['prix_unitaire']) for ligne in lignes)
        total = total_materiaux * 1.2
        
        # 🔥 SANITIZE - Nettoyer les entrées
        devis_data = {
            "date_creation": datetime.now().isoformat(),
            "total": total,
            "statut": "brouillon",
            "id_client": data.get('id_client'),
            "id_user": user_id,
            "id_projet": data.get('id_projet'),
            "show_signature": show_signature 
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
            try:
                result = response.json()
                print(f"🔍 Résultat JSON: {result}")
            except Exception as e:
                print(f"❌ Erreur parsing JSON: {e}")
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
                for ligne in lignes:
                    total_ligne = float(ligne['quantite']) * float(ligne['prix_unitaire'])
                    # 🔥 SANITIZE - Nettoyer la désignation
                    ligne_data = {
                        "designation": sanitize_input(ligne.get('designation')),
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
                
                log_action(user_id, 'create_devis', f"Devis #{id_devis} créé")
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        import os
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        
        # ============================================================
        # CONFIGURATION
        # ============================================================
        
        VERT_PROFOND = colors.HexColor('#438A5C')
        VERT_CLAIR = colors.HexColor('#7FAF91')
        BLANC = colors.HexColor('#FFFFFF')
        GRIS_FONCE = colors.HexColor('#303030')
        GRIS_MOYEN = colors.HexColor('#5F665F')
        GRIS_BORDURE = colors.HexColor('#D4E0D7')
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # ============================================================
        # RÉCUPÉRATION DES DONNÉES
        # ============================================================
        
        devis_response = requests.get(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        if devis_response.status_code != 200 or not devis_response.json():
            return jsonify({'error': 'Devis non trouvé'}), 404
        devis = devis_response.json()[0]
        
        client_response = requests.get(
            f"{supabase_url}/rest/v1/client?id_client=eq.{devis.get('id_client')}",
            headers=headers
        )
        client = client_response.json()[0] if client_response.status_code == 200 and client_response.json() else {}
        
        projet_response = requests.get(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{devis.get('id_projet')}",
            headers=headers
        )
        projet = projet_response.json()[0] if projet_response.status_code == 200 and projet_response.json() else {}
        
        lignes_response = requests.get(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        lignes = lignes_response.json() if lignes_response.status_code == 200 else []
        
        settings_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        settings = settings_response.json()[0] if settings_response.status_code == 200 and settings_response.json() else {}
        
        # ============================================================
        # PRÉPARATION DES DONNÉES
        # ============================================================
        
        client_nom = client.get('nom', 'Non renseigné')
        client_telephone = client.get('telephone', '')
        client_email = client.get('email', '')
        client_adresse = client.get('adresse', '')
        client_id = devis.get('id_client', '')
        
        company_name = settings.get('company_name', 'Mon Entreprise')
        company_email = settings.get('company_email', '')
        company_phone = settings.get('company_phone', '')
        company_address = settings.get('company_address', '')
        company_website = settings.get('website', '')
        company_logo = settings.get('company_logo')
        
        # Projet
        nom_projet = projet.get('nom_projet', '')
        description_projet = projet.get('description', '')
        localisation_projet = projet.get('localisation', '')
        statut_devis = devis.get('statut', 'brouillon')
        
        # Date
        date_creation = devis.get('date_creation', '')
        if date_creation:
            try:
                date_obj = datetime.fromisoformat(date_creation.replace('Z', '+00:00'))
                date_formatee = date_obj.strftime('%d/%m/%Y')
            except:
                date_formatee = date_creation
        else:
            date_formatee = datetime.now().strftime('%d/%m/%Y')
        
        num_devis = f"{devis.get('id_devis', 0):06d}"
        validite = "30 jours"
        
        # Lignes
        for ligne in lignes:
            ligne['prix_unitaire'] = float(ligne['prix_unitaire']) if ligne.get('prix_unitaire') else 0
            ligne['quantite'] = int(ligne['quantite']) if ligne.get('quantite') else 0
            ligne['total_ligne'] = float(ligne['total_ligne']) if ligne.get('total_ligne') else 0
        
        total_ht = sum(l['total_ligne'] for l in lignes)
        
        # Signature : valeur du devis > valeur des settings (par défaut True)
                # Signature : valeur du devis > valeur des settings (par défaut True)
        # 🔥 show_signature dans le devis peut être :
        #    - True  → afficher
        #    - False → ne pas afficher
        #    - None  → utiliser la valeur des settings
        devis_show_signature = devis.get('show_signature')
        
        if devis_show_signature is None:
            # Pas de valeur dans le devis → utiliser les settings
            show_signature = settings.get('show_signature', True)
        else:
            # Valeur définie dans le devis → l'utiliser
            show_signature = devis_show_signature
        
        print(f"🔍 show_signature - devis: {devis_show_signature}, settings: {settings.get('show_signature')}, final: {show_signature}")
        
        # ============================================================
        # CRÉATION DU PDF
        # ============================================================
        
        buffer = io.BytesIO()
        page_width, page_height = A4
        header_height = 35 * mm
        footer_height = 45 * mm
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=header_height + 3*mm,
            bottomMargin=footer_height + 3*mm
        )
        
        largeur_utile = page_width - 40*mm
        
        # ============================================================
        # STYLES
        # ============================================================
        
        styles = getSampleStyleSheet()
        
        style_pour = ParagraphStyle(
            'Pour', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=11,
            textColor=VERT_PROFOND, leading=14, spaceAfter=4
        )
        
        style_client_info = ParagraphStyle(
            'ClientInfo', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            textColor=GRIS_MOYEN, leading=13
        )
        
        style_info_projet = ParagraphStyle(
            'InfoProjet', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_MOYEN, leading=12
        )
        
        style_id_client = ParagraphStyle(
            'IdClient', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            textColor=GRIS_MOYEN, alignment=2, leading=13
        )
        
        style_statut = ParagraphStyle(
            'Statut', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_MOYEN, alignment=2, leading=12
        )
        
        style_th = ParagraphStyle(
            'TH', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9,
            textColor=BLANC, leading=12
        )
        
        style_td = ParagraphStyle(
            'TD', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_FONCE, leading=11
        )
        
        style_td_center = ParagraphStyle('TDCenter', parent=style_td, alignment=1)
        style_td_right = ParagraphStyle('TDRight', parent=style_td, alignment=2)
        
        style_section_titre = ParagraphStyle(
            'SectionTitre', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9,
            textColor=VERT_PROFOND, leading=12, spaceAfter=4
        )
        
        style_section_texte = ParagraphStyle(
            'SectionTexte', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_MOYEN, leading=11
        )
        
        style_bon_pour_accord = ParagraphStyle(
            'BonPourAccord', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=10,
            textColor=VERT_PROFOND, alignment=1, leading=13
        )
        
        style_merci = ParagraphStyle(
            'Merci', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=11,
            textColor=VERT_PROFOND, alignment=1
        )
        
        # ============================================================
        # FONCTION HEADER + FOOTER
        # ============================================================
        
        def draw_header_footer(canvas, doc):
            canvas.saveState()
            
            # ---------- HEADER ----------
            canvas.setFillColor(VERT_PROFOND)
            canvas.rect(0, page_height - header_height, page_width, header_height, fill=1, stroke=0)
            
            # Titre "Devis"
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica', 32)
            canvas.drawString(20*mm, page_height - 22*mm, "Devis")
            
            # Numéro
            canvas.setFillColor(colors.HexColor('#D4E8DC'))
            canvas.setFont('Helvetica', 10)
            canvas.drawString(20*mm, page_height - 29*mm, f"N° {num_devis}")
            
            # Date / Validité (droite)
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica-Bold', 9)
            canvas.drawRightString(page_width - 20*mm, page_height - 16*mm, f"Date : {date_formatee}")
            canvas.drawRightString(page_width - 20*mm, page_height - 22*mm, f"Validité : {validite}")
            
            # ---------- FOOTER ----------
            canvas.setFillColor(VERT_PROFOND)
            canvas.rect(0, 0, page_width, footer_height, fill=1, stroke=0)
            
            # Logo
            logo_width = 0
            if company_logo:
                logo_path = os.path.join(os.path.dirname(__file__), 'uploads', company_logo)
                if os.path.exists(logo_path):
                    try:
                        img = ImageReader(logo_path)
                        img_w, img_h = img.getSize()
                        max_logo_size = 15*mm
                        ratio = min(max_logo_size / img_w, max_logo_size / img_h)
                        new_w = img_w * ratio
                        new_h = img_h * ratio
                        canvas.drawImage(
                            logo_path,
                            20*mm,
                            footer_height - 20*mm,
                            width=new_w, height=new_h,
                            preserveAspectRatio=True, mask='auto'
                        )
                        logo_width = new_w + 4*mm
                    except Exception as e:
                        print(f"⚠️ Erreur logo: {e}")
            
            # Nom entreprise
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica-Bold', 13)
            canvas.drawString(20*mm + logo_width, footer_height - 12*mm, company_name)
            
            # Séparateur
            separator_x = 20*mm + logo_width + 50*mm
            canvas.setStrokeColor(colors.HexColor('#7FAF91'))
            canvas.setLineWidth(0.5)
            canvas.line(separator_x, 8*mm, separator_x, footer_height - 8*mm)
            
            # Coordonnées
            canvas.setFont('Helvetica', 8.5)
            canvas.setFillColor(colors.HexColor('#D4E8DC'))
            y_pos = footer_height - 12*mm
            if company_phone:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Tél : {company_phone}")
                y_pos -= 4.5*mm
            if company_email:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Email : {company_email}")
                y_pos -= 4.5*mm
            if company_address:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Adresse : {company_address}")
                y_pos -= 4.5*mm
            if company_website:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Site : {company_website}")
            
            # Infos admin
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#B8D4C3'))
            infos_admin = []
            nif = settings.get('nif', '')
            rccm = settings.get('rccm', '')
            if nif:
                infos_admin.append(f"NIF : {nif}")
            if rccm:
                infos_admin.append(f"RCCM : {rccm}")
            if infos_admin:
                canvas.drawString(20*mm, 4*mm, "  ·  ".join(infos_admin))
            
            canvas.restoreState()
        
        # ============================================================
        # CONSTRUCTION DU CONTENU
        # ============================================================
        
        story = []
        
        # ------------------------------------------------------------
        # 1. INFOS CLIENT + PROJET
        # ------------------------------------------------------------
        
        # Colonne gauche : Client + Projet
        client_lines = [f"<b>{client_nom}</b>"]
        if client_telephone:
            client_lines.append(client_telephone)
        if client_email:
            client_lines.append(client_email)
        if client_adresse:
            client_lines.append(client_adresse)
        
        client_text = "<br/>".join(client_lines)
        
        gauche_content = [
            Paragraph("Pour :", style_pour),
            Paragraph(client_text, style_client_info),
        ]
        
        # Ajouter les infos projet si présentes
        if nom_projet or description_projet or localisation_projet:
            gauche_content.append(Spacer(1, 4*mm))
            if nom_projet:
                gauche_content.append(Paragraph(f"<b>Projet :</b> {nom_projet}", style_info_projet))
            if description_projet:
                gauche_content.append(Paragraph(f"<b>Description :</b> {description_projet}", style_info_projet))
            if localisation_projet:
                gauche_content.append(Paragraph(f"<b>Localisation :</b> {localisation_projet}", style_info_projet))
        
        # Colonne droite : ID + Statut
        droite_content = [
            Paragraph(f"ID client : {client_id}", style_id_client),
        ]
        
        if statut_devis:
            droite_content.append(Spacer(1, 4*mm))
            droite_content.append(Paragraph(f"<b>Statut :</b> {statut_devis.upper()}", style_statut))
        
        client_table = Table(
            [[gauche_content, droite_content]],
            colWidths=[largeur_utile * 0.65, largeur_utile * 0.35]
        )
        client_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(client_table)
        
        # ------------------------------------------------------------
        # 2. TABLEAU DES PRESTATIONS
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 10*mm))
        
        table_header = [
            Paragraph("<b>Détail</b>", style_th),
            Paragraph("<b>Quantité</b>", style_th),
            Paragraph("<b>Prix HT</b>", style_th),
            Paragraph("<b>Total HT</b>", style_th)
        ]
        
        table_data = [table_header]
        
        for ligne in lignes:
            table_data.append([
                Paragraph(ligne.get('designation', ''), style_td),
                Paragraph(str(ligne.get('quantite', 0)), style_td_center),
                Paragraph(f"{ligne.get('prix_unitaire', 0):,.0f}".replace(',', ' '), style_td_center),
                Paragraph(f"{ligne.get('total_ligne', 0):,.0f}".replace(',', ' '), style_td_right)
            ])
        
        col_widths = [
            largeur_utile * 0.52,
            largeur_utile * 0.16,
            largeur_utile * 0.16,
            largeur_utile * 0.16
        ]
        
        tableau = Table(table_data, colWidths=col_widths, repeatRows=1)
        tableau.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERT_CLAIR),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLANC),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), BLANC),
            ('TEXTCOLOR', (0, 1), (-1, -1), GRIS_FONCE),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORDURE),
            ('LINEBELOW', (0, 0), (-1, 0), 1, VERT_PROFOND),
        ]))
        
        story.append(tableau)
        
        # ------------------------------------------------------------
        # 3. ZONE DES TOTAUX
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 6*mm))
        
        total_devis = float(devis.get('total', 0)) if devis.get('total') else total_ht
        tva_montant = 0
        total_final = total_devis
        
        totaux_data = [
            ["Total HT", f"{total_ht:,.0f} FCFA".replace(',', ' ')],
        ]
        
        if tva_montant > 0:
            totaux_data.append(["TVA", f"{tva_montant:,.0f} FCFA".replace(',', ' ')])
        
        totaux_data.append(["Total", f"{total_final:,.0f} FCFA".replace(',', ' ')])
        
        totaux_table = Table(
            totaux_data,
            colWidths=[largeur_utile * 0.25, largeur_utile * 0.20]
        )
        
        totaux_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -2), GRIS_MOYEN),
            ('TEXTCOLOR', (0, -1), (-1, -1), VERT_PROFOND),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRIS_BORDURE),
            ('LINEABOVE', (0, -1), (-1, -1), 1, VERT_PROFOND),
        ]))
        
        totaux_container = Table(
            [["", totaux_table]],
            colWidths=[largeur_utile * 0.55, largeur_utile * 0.45]
        )
        totaux_container.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(totaux_container)
        
        # ------------------------------------------------------------
        # 4. ZONE SIGNATURE (CONDITIONNELLE)
        # ------------------------------------------------------------
        
        if show_signature:
            story.append(Spacer(1, 8*mm))
            story.append(Paragraph("Bon pour accord", style_bon_pour_accord))
            story.append(Spacer(1, 3*mm))
            
            signature_zone = Table(
                [[""]],
                colWidths=[80*mm],
                rowHeights=[20*mm]
            )
            signature_zone.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, VERT_CLAIR),
                ('BACKGROUND', (0, 0), (-1, -1), BLANC),
            ]))
            
            signature_container = Table(
                [[signature_zone]],
                colWidths=[largeur_utile]
            )
            signature_container.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            
            story.append(signature_container)
            
            style_sous_signature = ParagraphStyle(
                'SousSignature', parent=styles['Normal'],
                fontName='Helvetica-Oblique', fontSize=7.5,
                textColor=GRIS_MOYEN, alignment=1, leading=9
            )
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph("à retourner daté et signé", style_sous_signature))
        
        # ------------------------------------------------------------
        # 5. CONDITIONS
        # ------------------------------------------------------------
        
        conditions = devis.get('conditions', '')
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("<b>Conditions</b>", style_section_titre))
        if conditions:
            story.append(Paragraph(conditions, style_section_texte))
        else:
            story.append(Paragraph(
                "Devis valable 30 jours. Le commencement des travaux vaut acceptation. "
                "Matériaux restant propriété de l'entreprise jusqu'au paiement intégral.",
                style_section_texte
            ))
        
        # ------------------------------------------------------------
        # 6. MESSAGE FINAL
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("Merci pour votre confiance !", style_merci))
        
        # ============================================================
        # CONSTRUCTION
        # ============================================================
        
        doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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





@limiter.limit("50 per hour")
@app.route('/api/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        from datetime import datetime
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        check_response = requests.get(
            f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
            headers=headers
        )
        
        # 🔥 SANITIZE - Nettoyer toutes les entrées
        update_data = {
            "company_name": sanitize_input(data.get('company_name', '')),
            "company_email": sanitize_input(data.get('company_email', '')),
            "company_phone": sanitize_input(data.get('company_phone', '')),
            "company_address": sanitize_input(data.get('company_address', '')),
            "primary_color": sanitize_input(data.get('primary_color', '#1E3A8A')),
            "secondary_color": sanitize_input(data.get('secondary_color', '#7C3AED')),
            "accent_color": sanitize_input(data.get('accent_color', '#06B6D4')),
            "updated_at": datetime.now().isoformat(),
            "slogan": sanitize_input(data.get('slogan', '')),
            "website": sanitize_input(data.get('website', '')),
            "footer_text": sanitize_input(data.get('footer_text', '')),
            "nif": sanitize_input(data.get('nif', '')),
            "regime_tva": sanitize_input(data.get('regime_tva', 'non assujetti')),
            "numero_contribuable": sanitize_input(data.get('numero_contribuable', '')),
            "adresse_fiscale": sanitize_input(data.get('adresse_fiscale', '')),
            "show_signature": data.get('show_signature', True)
        }
        
        print(f"🔍 Mise à jour settings: {update_data}")
        
        if check_response.status_code == 200 and check_response.json():
            response = requests.patch(
                f"{supabase_url}/rest/v1/settings?id_user=eq.{user_id}",
                headers=headers,
                json=update_data
            )
        else:
            update_data["id_user"] = user_id
            update_data["created_at"] = datetime.now().isoformat()
            response = requests.post(
                f"{supabase_url}/rest/v1/settings",
                headers=headers,
                json=update_data
            )
        
        if response.status_code in [200, 201, 204]:
            log_action(user_id, 'update_settings', "Paramètres mis à jour")
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')

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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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


@app.route('/api/devis/rapide', methods=['POST'])
@jwt_required()
def create_devis_rapide():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.get_json()
        
        print(f"🔍 Devis rapide pour user {user_id}")
        print(f"🔍 Données reçues: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'Données JSON invalides'}), 400
        
        import requests
        from datetime import datetime
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')

        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # ============================================================
        # 1. GESTION DU CLIENT
        # ============================================================
        id_client = data.get('id_client')
        client_nom = data.get('client_nom', '').strip()
        
        print(f"🔍 id_client: {id_client}, client_nom: '{client_nom}'")
        
        if not id_client and not client_nom:
            return jsonify({'success': False, 'message': 'Client requis'}), 400
        
        if id_client:
            # Client existant
            check_response = requests.get(
                f"{supabase_url}/rest/v1/client?id_client=eq.{id_client}&id_user=eq.{user_id}&select=id_client",
                headers=headers
            )
            if check_response.status_code != 200 or not check_response.json():
                return jsonify({'success': False, 'message': 'Client non trouvé'}), 404
        else:
            # Créer un nouveau client
            client_data = {
                "nom": client_nom,
                "telephone": data.get('client_telephone', ''),
                "email": data.get('client_email', ''),
                "adresse": data.get('client_adresse', ''),
                "id_user": user_id
            }
            
            print(f"🔍 Création client: {client_data}")
            
            client_response = requests.post(
                f"{supabase_url}/rest/v1/client",
                headers=headers,
                json=client_data
            )
            
            print(f"🔍 Status création client: {client_response.status_code}")
            print(f"🔍 Réponse: {client_response.text}")
            
            if client_response.status_code in [200, 201]:
                try:
                    result = client_response.json()
                    if isinstance(result, list) and len(result) > 0:
                        id_client = result[0].get('id_client')
                    elif isinstance(result, dict):
                        id_client = result.get('id_client')
                except:
                    # Récupérer le client créé
                    get_response = requests.get(
                        f"{supabase_url}/rest/v1/client?nom=eq.{client_nom}&id_user=eq.{user_id}&order=id_client.desc&limit=1",
                        headers=headers
                    )
                    if get_response.status_code == 200 and get_response.json():
                        id_client = get_response.json()[0].get('id_client')
            else:
                return jsonify({'success': False, 'message': f'Erreur création client: {client_response.text}'}), 500
        
        if not id_client:
            return jsonify({'success': False, 'message': 'ID client non récupéré'}), 500
        
        # ============================================================
        # 2. GESTION DU PROJET
        # ============================================================
        id_projet = data.get('id_projet')
        projet_nom = data.get('projet_nom', '').strip()
        
        print(f"🔍 id_projet: {id_projet}, projet_nom: '{projet_nom}'")
        
        if not id_projet and not projet_nom:
            return jsonify({'success': False, 'message': 'Projet requis'}), 400
        
        if id_projet:
            # Projet existant
            check_response = requests.get(
                f"{supabase_url}/rest/v1/projet?id_projet=eq.{id_projet}&id_user=eq.{user_id}&select=id_projet",
                headers=headers
            )
            if check_response.status_code != 200 or not check_response.json():
                return jsonify({'success': False, 'message': 'Projet non trouvé'}), 404
        else:
            # Créer un nouveau projet
            projet_data = {
                "nom_projet": projet_nom,
                "description": data.get('projet_description', ''),
                "localisation": data.get('projet_localisation', ''),
                "id_user": user_id
            }
            
            print(f"🔍 Création projet: {projet_data}")
            
            projet_response = requests.post(
                f"{supabase_url}/rest/v1/projet",
                headers=headers,
                json=projet_data
            )
            
            print(f"🔍 Status création projet: {projet_response.status_code}")
            print(f"🔍 Réponse: {projet_response.text}")
            
            if projet_response.status_code in [200, 201]:
                try:
                    result = projet_response.json()
                    if isinstance(result, list) and len(result) > 0:
                        id_projet = result[0].get('id_projet')
                    elif isinstance(result, dict):
                        id_projet = result.get('id_projet')
                except:
                    get_response = requests.get(
                        f"{supabase_url}/rest/v1/projet?nom_projet=eq.{projet_nom}&id_user=eq.{user_id}&order=id_projet.desc&limit=1",
                        headers=headers
                    )
                    if get_response.status_code == 200 and get_response.json():
                        id_projet = get_response.json()[0].get('id_projet')
            else:
                return jsonify({'success': False, 'message': f'Erreur création projet: {projet_response.text}'}), 500
        
        if not id_projet:
            return jsonify({'success': False, 'message': 'ID projet non récupéré'}), 500
        
        # ============================================================
        # 3. CRÉATION DU DEVIS
        # ============================================================
        lignes = data.get('lignes', [])
        if not lignes or len(lignes) == 0:
            return jsonify({'success': False, 'message': 'Ajoutez au moins un article'}), 400
        
        total_materiaux = sum(float(ligne.get('quantite', 0)) * float(ligne.get('prix_unitaire', 0)) for ligne in lignes)
        total = total_materiaux * 1.2
        
        devis_data = {
            "date_creation": datetime.now().isoformat(),
            "total": round(total, 2),
            "statut": "brouillon",
            "id_client": id_client,
            "id_user": user_id,
            "id_projet": id_projet
        }
        
        print(f"🔍 Création devis: {devis_data}")
        
        devis_response = requests.post(
            f"{supabase_url}/rest/v1/devis",
            headers=headers,
            json=devis_data
        )
        
        print(f"🔍 Status création devis: {devis_response.status_code}")
        print(f"🔍 Réponse: {devis_response.text}")
        
        if devis_response.status_code not in [200, 201]:
            return jsonify({'success': False, 'message': f'Erreur création devis: {devis_response.text}'}), 500
        
        # Récupérer l'ID du devis
        try:
            result = devis_response.json()
            if isinstance(result, list) and len(result) > 0:
                id_devis = result[0].get('id_devis')
            elif isinstance(result, dict):
                id_devis = result.get('id_devis')
            else:
                id_devis = None
        except:
            id_devis = None
        
        if not id_devis:
            # Récupérer le dernier devis créé
            get_response = requests.get(
                f"{supabase_url}/rest/v1/devis?id_user=eq.{user_id}&order=id_devis.desc&limit=1",
                headers=headers
            )
            if get_response.status_code == 200 and get_response.json():
                id_devis = get_response.json()[0].get('id_devis')
        
        if not id_devis:
            return jsonify({'success': False, 'message': 'Devis créé mais ID non récupéré'}), 500
        
        # ============================================================
        # 4. AJOUT DES LIGNES
        # ============================================================
        for ligne in lignes:
            total_ligne = float(ligne.get('quantite', 0)) * float(ligne.get('prix_unitaire', 0))
            ligne_data = {
                "designation": ligne.get('designation', 'Article'),
                "quantite": ligne.get('quantite', 1),
                "prix_unitaire": ligne.get('prix_unitaire', 0),
                "total_ligne": round(total_ligne, 2),
                "id_devis": id_devis
            }
            requests.post(
                f"{supabase_url}/rest/v1/ligne_devis",
                headers=headers,
                json=ligne_data
            )
        
        return jsonify({
            'success': True,
            'id_devis': id_devis,
            'message': 'Devis créé avec succès',
            'total': round(total, 2)
        })
        
    except Exception as e:
        print(f"❌ Erreur create_devis_rapide: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/recherche', methods=['GET'])
@jwt_required()
def recherche_globale():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        query = request.args.get('q', '').strip().lower()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
        
        print(f"🔍 Recherche globale: '{query}' pour user {user_id}")
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        results = []
        
        # ============================================================
        # 1. RECHERCHE DANS LES CLIENTS
        # ============================================================
        try:
            clients_response = requests.get(
                f"{supabase_url}/rest/v1/client?id_user=eq.{user_id}&select=*",
                headers=headers
            )
            
            if clients_response.status_code == 200:
                clients = clients_response.json()
                for client in clients:
                    nom = (client.get('nom') or '').lower()
                    email = (client.get('email') or '').lower()
                    tel = (client.get('telephone') or '').lower()
                    
                    if query in nom or query in email or query in tel:
                        results.append({
                            'type': 'client',
                            'id': client.get('id_client'),
                            'titre': client.get('nom', 'Client'),
                            'sous_titre': client.get('telephone', '') or client.get('email', ''),
                            'icone': 'fa-user',
                            'couleur': '#06B6D4',
                            'page': 'clients'
                        })
        except Exception as e:
            print(f"⚠️ Erreur recherche clients: {e}")
        
        # ============================================================
        # 2. RECHERCHE DANS LES PROJETS
        # ============================================================
        try:
            projets_response = requests.get(
                f"{supabase_url}/rest/v1/projet?id_user=eq.{user_id}&select=*",
                headers=headers
            )
            
            if projets_response.status_code == 200:
                projets = projets_response.json()
                for projet in projets:
                    nom = (projet.get('nom_projet') or '').lower()
                    desc = (projet.get('description') or '').lower()
                    loc = (projet.get('localisation') or '').lower()
                    
                    if query in nom or query in desc or query in loc:
                        results.append({
                            'type': 'projet',
                            'id': projet.get('id_projet'),
                            'titre': projet.get('nom_projet', 'Projet'),
                            'sous_titre': projet.get('localisation', '') or projet.get('description', ''),
                            'icone': 'fa-hard-hat',
                            'couleur': '#8B5CF6',
                            'page': 'projets'
                        })
        except Exception as e:
            print(f"⚠️ Erreur recherche projets: {e}")
        
        # ============================================================
        # 3. RECHERCHE DANS LES DEVIS
        # ============================================================
        try:
            devis_response = requests.get(
                f"{supabase_url}/rest/v1/devis?id_user=eq.{user_id}&select=*&order=id_devis.desc&limit=50",
                headers=headers
            )
            
            if devis_response.status_code == 200:
                devis_list = devis_response.json()
                for devis in devis_list:
                    ref = f"devis-{devis.get('id_devis', 0):06d}".lower()
                    ref2 = str(devis.get('id_devis', '')).lower()
                    statut = (devis.get('statut') or '').lower()
                    total = str(devis.get('total', '')).lower()
                    
                    if query in ref or query in ref2 or query in statut or query in total:
                        results.append({
                            'type': 'devis',
                            'id': devis.get('id_devis'),
                            'titre': f"Devis #{devis.get('id_devis')}",
                            'sous_titre': f"{(devis.get('total') or 0):,.0f} FCFA · {devis.get('statut', 'brouillon')}",
                            'icone': 'fa-file-invoice',
                            'couleur': '#F59E0B',
                            'page': 'devis'
                        })
        except Exception as e:
            print(f"⚠️ Erreur recherche devis: {e}")
        
        # ============================================================
        # 4. RECHERCHE DANS LES FACTURES
        # ============================================================
        try:
            factures_response = requests.get(
                f"{supabase_url}/rest/v1/facture?select=*&order=id_facture.desc&limit=50",
                headers=headers
            )
            
            if factures_response.status_code == 200:
                factures = factures_response.json()
                for facture in factures:
                    # Vérifier que la facture appartient à l'utilisateur via le devis
                    id_devis = facture.get('id_devis')
                    if id_devis:
                        devis_check = requests.get(
                            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}&select=id_user",
                            headers=headers
                        )
                        if devis_check.status_code == 200 and devis_check.json():
                            if devis_check.json()[0].get('id_user') != user_id:
                                continue
                    
                    ref = f"facture-{facture.get('id_facture', 0):06d}".lower()
                    ref2 = str(facture.get('id_facture', '')).lower()
                    statut = (facture.get('statut') or '').lower()
                    montant = str(facture.get('montant', '')).lower()
                    
                    if query in ref or query in ref2 or query in statut or query in montant:
                        results.append({
                            'type': 'facture',
                            'id': facture.get('id_facture'),
                            'titre': f"Facture #{facture.get('id_facture')}",
                            'sous_titre': f"{(facture.get('montant') or 0):,.0f} FCFA · {facture.get('statut', 'non payée')}",
                            'icone': 'fa-receipt',
                            'couleur': '#10B981',
                            'page': 'factures'
                        })
        except Exception as e:
            print(f"⚠️ Erreur recherche factures: {e}")
        
        # Limiter à 10 résultats
        results = results[:10]
        
        print(f"✅ {len(results)} résultats trouvés")
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"❌ Erreur recherche_globale: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'results': [], 'message': str(e)}), 500



# ============================================================
# CATALOGUE DE PRODUITS
# ============================================================

@app.route('/api/catalogue', methods=['GET'])
@jwt_required()
def get_catalogue():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{supabase_url}/rest/v1/catalogue?id_user=eq.{user_id}&order=designation.asc",
            headers=headers
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify([]), 500
        
    except Exception as e:
        print(f"❌ Erreur get_catalogue: {e}")
        return jsonify([]), 500


@app.route('/api/catalogue', methods=['POST'])
@jwt_required()
def create_produit():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        from datetime import datetime
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        produit_data = {
            "designation": data.get('designation', '').strip(),
            "prix_unitaire": float(data.get('prix_unitaire', 0)),
            "unite": data.get('unite', 'unité'),
            "categorie": data.get('categorie', 'Général'),
            "id_user": user_id,
            "date_creation": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if not produit_data['designation']:
            return jsonify({'success': False, 'message': 'Désignation requise'}), 400
        
        response = requests.post(
            f"{supabase_url}/rest/v1/catalogue",
            headers=headers,
            json=produit_data
        )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Produit ajouté'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur create_produit: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/catalogue/<int:id_produit>', methods=['PUT'])
@jwt_required()
def update_produit(id_produit):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        from datetime import datetime
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier que le produit appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/catalogue?id_produit=eq.{id_produit}&id_user=eq.{user_id}&select=id_produit",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Produit non trouvé'}), 404
        
        update_data = {
            "designation": data.get('designation', '').strip(),
            "prix_unitaire": float(data.get('prix_unitaire', 0)),
            "unite": data.get('unite', 'unité'),
            "categorie": data.get('categorie', 'Général'),
            "updated_at": datetime.now().isoformat()
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/catalogue?id_produit=eq.{id_produit}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Produit modifié'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur update_produit: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/catalogue/<int:id_produit>', methods=['DELETE'])
@jwt_required()
def delete_produit(id_produit):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # Vérifier que le produit appartient à l'utilisateur
        check_response = requests.get(
            f"{supabase_url}/rest/v1/catalogue?id_produit=eq.{id_produit}&id_user=eq.{user_id}&select=id_produit",
            headers=headers
        )
        
        if check_response.status_code != 200 or not check_response.json():
            return jsonify({'success': False, 'message': 'Produit non trouvé'}), 404
        
        response = requests.delete(
            f"{supabase_url}/rest/v1/catalogue?id_produit=eq.{id_produit}",
            headers=headers
        )
        
        if response.status_code in [200, 204]:
            return jsonify({'success': True, 'message': 'Produit supprimé'})
        else:
            return jsonify({'success': False, 'message': f'Erreur: {response.text}'}), 500
        
    except Exception as e:
        print(f"❌ Erreur delete_produit: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
# ==================== FACTURE NORMALISÉE ====================

@app.route('/api/facture/<int:id_facture>/pdf-normalise', methods=['GET'])
@jwt_required()
def generate_pdf_normalise(id_facture):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        import requests
        from datetime import datetime
        import io
        import os
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        
        # ============================================================
        # CONFIGURATION
        # ============================================================
        
        VERT_PROFOND = colors.HexColor('#438A5C')
        VERT_CLAIR = colors.HexColor('#7FAF91')
        BLANC = colors.HexColor('#FFFFFF')
        GRIS_FONCE = colors.HexColor('#303030')
        GRIS_MOYEN = colors.HexColor('#5F665F')
        GRIS_BORDURE = colors.HexColor('#D4E0D7')
        ROUGE = colors.HexColor('#DC2626')
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # ============================================================
        # RÉCUPÉRATION DES DONNÉES
        # ============================================================
        
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
        # PRÉPARATION DES DONNÉES
        # ============================================================
        
        # Client
        client_nom = client.get('nom', 'Non renseigné')
        client_telephone = client.get('telephone', '')
        client_email = client.get('email', '')
        client_adresse = client.get('adresse', '')
        client_id = devis.get('id_client', '')
        ifu_client = facture.get('ifu_client', '')
        
        # Entreprise
        company_name = settings.get('company_name', 'Mon Entreprise')
        company_email = settings.get('company_email', '')
        company_phone = settings.get('company_phone', '')
        company_address = settings.get('company_address', '')
        company_website = settings.get('website', '')
        company_logo = settings.get('company_logo')
        company_nif = settings.get('nif', '')
        
        # Facture
        num_facture = f"{facture.get('id_facture', 0):06d}"
        nim = facture.get('num_facture_fiscale', '')
        code_mecf = facture.get('code_securite', '')
        qr_code_data = facture.get('qr_code', '')
        
        date_facture = facture.get('date_facture', '')
        if date_facture:
            try:
                date_obj = datetime.fromisoformat(date_facture.replace('Z', '+00:00'))
                date_formatee = date_obj.strftime('%d/%m/%Y')
                heure_formatee = date_obj.strftime('%H:%M')
                date_heure_complete = date_obj.strftime('%d/%m/%Y %H:%M:%S')
            except:
                date_formatee = date_facture
                heure_formatee = ''
                date_heure_complete = date_facture
        else:
            date_formatee = datetime.now().strftime('%d/%m/%Y')
            heure_formatee = datetime.now().strftime('%H:%M')
            date_heure_complete = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # Lignes
        for ligne in lignes:
            ligne['prix_unitaire'] = float(ligne['prix_unitaire']) if ligne.get('prix_unitaire') else 0
            ligne['quantite'] = int(ligne['quantite']) if ligne.get('quantite') else 0
            ligne['total_ligne'] = float(ligne['total_ligne']) if ligne.get('total_ligne') else 0
        
        total_ht = sum(l['total_ligne'] for l in lignes)
        tva_montant = total_ht * 0.18
        total_ttc = total_ht + tva_montant
        
        # Environnement
        ENV = os.environ.get('EMCF_ENV', 'test')
        is_test = (ENV == 'test')
        
        # ============================================================
        # CRÉATION DU PDF
        # ============================================================
        
        buffer = io.BytesIO()
        page_width, page_height = A4
        
        bande_rouge_height = 10 * mm   # Bande rouge
        header_height = 35 * mm         # Header vert
        total_top_height = bande_rouge_height + header_height  # 45mm
        footer_height = 45 * mm
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=total_top_height + 3*mm,  # Header total + espace
            bottomMargin=footer_height + 3*mm
        )
        
        largeur_utile = page_width - 40*mm
        
        # ============================================================
        # STYLES
        # ============================================================
        
        styles = getSampleStyleSheet()
        
        style_pour = ParagraphStyle(
            'Pour', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=11,
            textColor=VERT_PROFOND, leading=14, spaceAfter=4
        )
        
        style_client_info = ParagraphStyle(
            'ClientInfo', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            textColor=GRIS_MOYEN, leading=13
        )
        
        style_id_client = ParagraphStyle(
            'IdClient', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            textColor=GRIS_MOYEN, alignment=2, leading=13
        )
        
        style_th = ParagraphStyle(
            'TH', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9,
            textColor=BLANC, leading=12
        )
        
        style_td = ParagraphStyle(
            'TD', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_FONCE, leading=11
        )
        
        style_td_center = ParagraphStyle('TDCenter', parent=style_td, alignment=1)
        style_td_right = ParagraphStyle('TDRight', parent=style_td, alignment=2)
        
        # ============================================================
        # FONCTION HEADER + FOOTER
        # ============================================================
        
        def draw_header_footer(canvas, doc):
            canvas.saveState()
            
            # ============================================================
            # 🔴 BANDE ROUGE (si test) — tout en haut
            # ============================================================
            if is_test:
                canvas.setFillColor(ROUGE)
                canvas.rect(
                    0,
                    page_height - bande_rouge_height,
                    page_width,
                    bande_rouge_height,
                    fill=1, stroke=0
                )
                
                canvas.setFillColor(BLANC)
                canvas.setFont('Helvetica-Bold', 11)
                canvas.drawCentredString(
                    page_width / 2,
                    page_height - 6.5*mm,
                    "⚠️ FACTURE D'ESSAI – NON VALABLE FISCALEMENT"
                )
            
            # ============================================================
            # 🟩 HEADER VERT (en dessous de la bande rouge)
            # ============================================================
            header_top_y = page_height - bande_rouge_height
            header_bottom_y = header_top_y - header_height
            
            canvas.setFillColor(VERT_PROFOND)
            canvas.rect(0, header_bottom_y, page_width, header_height, fill=1, stroke=0)
            
            # Titre "Facture Normalisée"
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica', 26)
            canvas.drawString(20*mm, header_bottom_y + 22*mm, "Facture Normalisée")
            
            # Numéro
            canvas.setFillColor(colors.HexColor('#D4E8DC'))
            canvas.setFont('Helvetica', 10)
            canvas.drawString(20*mm, header_bottom_y + 15*mm, f"N° {num_facture}")
            
            # Date et Heure (droite)
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica-Bold', 9)
            canvas.drawRightString(page_width - 20*mm, header_bottom_y + 24*mm, f"Date : {date_formatee}")
            canvas.drawRightString(page_width - 20*mm, header_bottom_y + 18*mm, f"Heure : {heure_formatee}")
            
            # ============================================================
            # 🟩 FOOTER VERT
            # ============================================================
            canvas.setFillColor(VERT_PROFOND)
            canvas.rect(0, 0, page_width, footer_height, fill=1, stroke=0)
            
            # Logo
            logo_width = 0
            if company_logo:
                logo_path = os.path.join(os.path.dirname(__file__), 'uploads', company_logo)
                if os.path.exists(logo_path):
                    try:
                        img = ImageReader(logo_path)
                        img_w, img_h = img.getSize()
                        max_logo_size = 15*mm
                        ratio = min(max_logo_size / img_w, max_logo_size / img_h)
                        new_w = img_w * ratio
                        new_h = img_h * ratio
                        canvas.drawImage(
                            logo_path,
                            20*mm,
                            footer_height - 20*mm,
                            width=new_w, height=new_h,
                            preserveAspectRatio=True, mask='auto'
                        )
                        logo_width = new_w + 4*mm
                    except Exception as e:
                        print(f"⚠️ Erreur logo: {e}")
            
            # Nom entreprise
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica-Bold', 13)
            canvas.drawString(20*mm + logo_width, footer_height - 12*mm, company_name)
            
            # Séparateur
            separator_x = 20*mm + logo_width + 50*mm
            canvas.setStrokeColor(colors.HexColor('#7FAF91'))
            canvas.setLineWidth(0.5)
            canvas.line(separator_x, 8*mm, separator_x, footer_height - 8*mm)
            
            # Coordonnées
            canvas.setFont('Helvetica', 8.5)
            canvas.setFillColor(colors.HexColor('#D4E8DC'))
            y_pos = footer_height - 12*mm
            if company_phone:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Tél : {company_phone}")
                y_pos -= 4.5*mm
            if company_email:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Email : {company_email}")
                y_pos -= 4.5*mm
            if company_address:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Adresse : {company_address}")
                y_pos -= 4.5*mm
            if company_website:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Site : {company_website}")
            
            # Infos admin (NIF vendeur + RCCM)
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#B8D4C3'))
            infos_admin = []
            if company_nif:
                infos_admin.append(f"NIF : {company_nif}")
            rccm = settings.get('rccm', '')
            if rccm:
                infos_admin.append(f"RCCM : {rccm}")
            if infos_admin:
                canvas.drawString(20*mm, 4*mm, "  ·  ".join(infos_admin))
            
            canvas.restoreState()
        
        # ============================================================
        # CONSTRUCTION DU CONTENU
        # ============================================================
        
        story = []
        
        # ------------------------------------------------------------
        # 1. INFOS CLIENT + IFU
        # ------------------------------------------------------------
        
        client_lines = [f"<b>{client_nom}</b>"]
        if client_telephone:
            client_lines.append(client_telephone)
        if client_email:
            client_lines.append(client_email)
        if client_adresse:
            client_lines.append(client_adresse)
        
        client_text = "<br/>".join(client_lines)
        
        gauche_client = [
            Paragraph("Pour :", style_pour),
            Paragraph(client_text, style_client_info)
        ]
        
        droite_client = [
            Paragraph(f"ID client : {client_id}", style_id_client),
            Paragraph(f"IFU client : {ifu_client if ifu_client else 'N/A'}", style_id_client)
        ]
        
        client_table = Table(
            [[gauche_client, droite_client]],
            colWidths=[largeur_utile * 0.6, largeur_utile * 0.4]
        )
        client_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(client_table)
        
        # ------------------------------------------------------------
        # 2. TABLEAU DES PRESTATIONS
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 10*mm))
        
        table_header = [
            Paragraph("<b>Détail</b>", style_th),
            Paragraph("<b>Quantité</b>", style_th),
            Paragraph("<b>Prix HT</b>", style_th),
            Paragraph("<b>Total HT</b>", style_th)
        ]
        
        table_data = [table_header]
        
        for ligne in lignes:
            table_data.append([
                Paragraph(ligne.get('designation', ''), style_td),
                Paragraph(str(ligne.get('quantite', 0)), style_td_center),
                Paragraph(f"{ligne.get('prix_unitaire', 0):,.0f}".replace(',', ' '), style_td_center),
                Paragraph(f"{ligne.get('total_ligne', 0):,.0f}".replace(',', ' '), style_td_right)
            ])
        
        col_widths = [
            largeur_utile * 0.52,
            largeur_utile * 0.16,
            largeur_utile * 0.16,
            largeur_utile * 0.16
        ]
        
        tableau = Table(table_data, colWidths=col_widths, repeatRows=1)
        tableau.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERT_CLAIR),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLANC),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), BLANC),
            ('TEXTCOLOR', (0, 1), (-1, -1), GRIS_FONCE),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORDURE),
            ('LINEBELOW', (0, 0), (-1, 0), 1, VERT_PROFOND),
        ]))
        
        story.append(tableau)
        
        # ------------------------------------------------------------
        # 3. ZONE DES TOTAUX (HT + TVA + TTC)
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 6*mm))
        
        totaux_data = [
            ["Total HT", f"{total_ht:,.0f} FCFA".replace(',', ' ')],
            ["TVA (18%)", f"{tva_montant:,.0f} FCFA".replace(',', ' ')],
            ["Total TTC", f"{total_ttc:,.0f} FCFA".replace(',', ' ')],
        ]
        
        totaux_table = Table(
            totaux_data,
            colWidths=[largeur_utile * 0.25, largeur_utile * 0.20]
        )
        
        totaux_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -2), GRIS_MOYEN),
            ('TEXTCOLOR', (0, -1), (-1, -1), VERT_PROFOND),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, GRIS_BORDURE),
            ('LINEABOVE', (0, -1), (-1, -1), 1, VERT_PROFOND),
        ]))
        
        totaux_container = Table(
            [["", totaux_table]],
            colWidths=[largeur_utile * 0.55, largeur_utile * 0.45]
        )
        totaux_container.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(totaux_container)
        
        # ------------------------------------------------------------
        # PLACEHOLDER POUR ÉTAPES 2+ (Zone fiscale, QR Code, etc.)
        # ------------------------------------------------------------
        
                # ------------------------------------------------------------
        # 4. ZONE FISCALE + QR CODE
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 8*mm))
        
        # Style pour les infos fiscales
        style_fiscal_titre = ParagraphStyle(
            'FiscalTitre', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=10,
            textColor=VERT_PROFOND, leading=13, spaceAfter=6
        )
        
        style_fiscal_info = ParagraphStyle(
            'FiscalInfo', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_FONCE, leading=13
        )
        
        style_fiscal_mention = ParagraphStyle(
            'FiscalMention', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=8.5,
            textColor=VERT_PROFOND, leading=12, alignment=1
        )
        
        style_fiscal_sous_mention = ParagraphStyle(
            'FiscalSousMention', parent=styles['Normal'],
            fontName='Helvetica', fontSize=7.5,
            textColor=GRIS_MOYEN, leading=10, alignment=1
        )
        
        # Titre de la zone fiscale
        story.append(Paragraph("<b>Informations fiscales</b>", style_fiscal_titre))
        
        # Construction des infos fiscales (texte à droite du QR Code)
        fiscal_info_lines = []
        if nim:
            fiscal_info_lines.append(f"<b>NIM :</b> {nim}")
        if code_mecf:
            fiscal_info_lines.append(f"<b>Code MECeF :</b> {code_mecf}")
        if date_heure_complete:
            fiscal_info_lines.append(f"<b>Date/Heure :</b> {date_heure_complete}")
        fiscal_info_lines.append("<b>Type :</b> Facture de vente (FV)")
        
        fiscal_info_text = "<br/>".join(fiscal_info_lines)
        fiscal_info_paragraph = Paragraph(fiscal_info_text, style_fiscal_info)
        
        # ============================================================
        # GÉNÉRATION DU QR CODE
        # ============================================================
        
        qr_element = None
        
        try:
            import qrcode
            from io import BytesIO
            
            if qr_code_data and len(qr_code_data) > 10:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=4,
                    border=1,
                )
                qr.add_data(str(qr_code_data))
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                
                from reportlab.platypus import Image as RLImage
                qr_element = RLImage(qr_buffer, width=30*mm, height=30*mm)
                print("✅ QR Code généré")
            else:
                qr_element = Paragraph("⚠️ QR Code non disponible", style_fiscal_info)
        except Exception as e:
            print(f"⚠️ Erreur QR Code: {e}")
            qr_element = Paragraph("⚠️ Erreur QR Code", style_fiscal_info)
        
        # ============================================================
        # TABLEAU ZONE FISCALE (QR Code | Infos)
        # ============================================================
        
        fiscal_data = [[qr_element, fiscal_info_paragraph]]
        
        fiscal_table = Table(
            fiscal_data,
            colWidths=[35*mm, largeur_utile - 35*mm]
        )
        
        fiscal_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 5*mm),
            ('LEFTPADDING', (1, 0), (1, 0), 5*mm),
            ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(fiscal_table)
        
        # ============================================================
        # MENTION DGI (conformité)
        # ============================================================
        
        story.append(Spacer(1, 4*mm))
        
        mention_conformite = Paragraph(
            "✔ Facture normalisée conforme à la réglementation fiscale en vigueur",
            style_fiscal_mention
        )
        story.append(mention_conformite)
        
        mention_dgi = Paragraph(
            "Émise via le système e-MCF de la DGI",
            style_fiscal_sous_mention
        )
        story.append(mention_dgi)
        
        # ============================================================
        # CONSTRUCTION
        # ============================================================
        
        doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'facture_normalisee_{id_facture}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erreur génération PDF facture normalisée: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/facture/<int:id_facture>/normaliser', methods=['POST'])
@jwt_required()
def normaliser_facture(id_facture):
    ifu_client = data.get('ifu_client', '').strip()
    
    if not valider_nif(ifu_client):
        return jsonify({
            'success': False, 
            'message': 'IFU client invalide (13 chiffres, commence par 02)'
        }), 400

@app.route('/api/devis/<int:id_devis>/acompte', methods=['POST'])
@jwt_required()
def configurer_acompte(id_devis):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')  
        
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
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        import os
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        
        # ============================================================
        # CONFIGURATION
        # ============================================================
        
        VERT_PROFOND = colors.HexColor('#438A5C')
        VERT_CLAIR = colors.HexColor('#7FAF91')
        BLANC = colors.HexColor('#FFFFFF')
        GRIS_FONCE = colors.HexColor('#303030')
        GRIS_MOYEN = colors.HexColor('#5F665F')
        GRIS_BORDURE = colors.HexColor('#D4E0D7')
        
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
        # ============================================================
        # RÉCUPÉRATION DES DONNÉES
        # ============================================================
        
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
        
        projet_response = requests.get(
            f"{supabase_url}/rest/v1/projet?id_projet=eq.{devis.get('id_projet')}",
            headers=headers
        )
        projet = projet_response.json()[0] if projet_response.status_code == 200 and projet_response.json() else {}
        
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
        # PRÉPARATION DES DONNÉES
        # ============================================================
        
        # Client
        client_nom = client.get('nom', 'Non renseigné')
        client_telephone = client.get('telephone', '')
        client_email = client.get('email', '')
        client_adresse = client.get('adresse', '')
        client_id = devis.get('id_client', '')
        client_ifu = client.get('ifu', '')
        
        # Entreprise
        company_name = settings.get('company_name', 'Mon Entreprise')
        company_email = settings.get('company_email', '')
        company_phone = settings.get('company_phone', '')
        company_address = settings.get('company_address', '')
        company_website = settings.get('website', '')
        company_logo = settings.get('company_logo')
        company_nif = settings.get('nif', '')
        
        # Projet
        nom_projet = projet.get('nom_projet', '')
        description_projet = projet.get('description', '')
        
        # Facture
        num_facture = f"{facture.get('id_facture', 0):06d}"
        
        date_facture = facture.get('date_facture', '')
        if date_facture:
            try:
                date_obj = datetime.fromisoformat(date_facture.replace('Z', '+00:00'))
                date_formatee = date_obj.strftime('%d/%m/%Y')
                heure_formatee = date_obj.strftime('%H:%M')
            except:
                date_formatee = date_facture
                heure_formatee = ''
        else:
            date_formatee = datetime.now().strftime('%d/%m/%Y')
            heure_formatee = datetime.now().strftime('%H:%M')
        
        # Lignes
        for ligne in lignes:
            ligne['prix_unitaire'] = float(ligne['prix_unitaire']) if ligne.get('prix_unitaire') else 0
            ligne['quantite'] = int(ligne['quantite']) if ligne.get('quantite') else 0
            ligne['total_ligne'] = float(ligne['total_ligne']) if ligne.get('total_ligne') else 0
        
        total_ht = sum(l['total_ligne'] for l in lignes)
        
        # ============================================================
        # CRÉATION DU PDF
        # ============================================================
        
        buffer = io.BytesIO()
        page_width, page_height = A4
        
        header_height = 35 * mm
        footer_height = 45 * mm
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=header_height + 3*mm,
            bottomMargin=footer_height + 3*mm
        )
        
        largeur_utile = page_width - 40*mm
        
        # ============================================================
        # STYLES
        # ============================================================
        
        styles = getSampleStyleSheet()
        
        style_pour = ParagraphStyle(
            'Pour', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=11,
            textColor=VERT_PROFOND, leading=14, spaceAfter=4
        )
        
        style_client_info = ParagraphStyle(
            'ClientInfo', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            textColor=GRIS_MOYEN, leading=13
        )
        
        style_info_projet = ParagraphStyle(
            'InfoProjet', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_MOYEN, leading=12
        )
        
        style_id_client = ParagraphStyle(
            'IdClient', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9,
            textColor=GRIS_MOYEN, alignment=2, leading=13
        )
        
        style_th = ParagraphStyle(
            'TH', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9,
            textColor=BLANC, leading=12
        )
        
        style_td = ParagraphStyle(
            'TD', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_FONCE, leading=11
        )
        
        style_td_center = ParagraphStyle('TDCenter', parent=style_td, alignment=1)
        style_td_right = ParagraphStyle('TDRight', parent=style_td, alignment=2)
        
        style_section_titre = ParagraphStyle(
            'SectionTitre', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=9,
            textColor=VERT_PROFOND, leading=12, spaceAfter=4
        )
        
        style_section_texte = ParagraphStyle(
            'SectionTexte', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8.5,
            textColor=GRIS_MOYEN, leading=11
        )
        
        style_merci = ParagraphStyle(
            'Merci', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=11,
            textColor=VERT_PROFOND, alignment=1
        )
        
        # ============================================================
        # FONCTION HEADER + FOOTER
        # ============================================================
        
        def draw_header_footer(canvas, doc):
            canvas.saveState()
            
            # ============================================================
            # 🟩 HEADER VERT
            # ============================================================
            canvas.setFillColor(VERT_PROFOND)
            canvas.rect(0, page_height - header_height, page_width, header_height, fill=1, stroke=0)
            
            # Titre "Facture"
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica', 32)
            canvas.drawString(20*mm, page_height - 22*mm, "Facture")
            
            # Numéro
            canvas.setFillColor(colors.HexColor('#D4E8DC'))
            canvas.setFont('Helvetica', 10)
            canvas.drawString(20*mm, page_height - 29*mm, f"N° {num_facture}")
            
            # Date et Heure (droite)
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica-Bold', 9)
            canvas.drawRightString(page_width - 20*mm, page_height - 16*mm, f"Date : {date_formatee}")
            canvas.drawRightString(page_width - 20*mm, page_height - 22*mm, f"Heure : {heure_formatee}")
            
            # ============================================================
            # 🟩 FOOTER VERT
            # ============================================================
            canvas.setFillColor(VERT_PROFOND)
            canvas.rect(0, 0, page_width, footer_height, fill=1, stroke=0)
            
            # Logo
            logo_width = 0
            if company_logo:
                logo_path = os.path.join(os.path.dirname(__file__), 'uploads', company_logo)
                if os.path.exists(logo_path):
                    try:
                        img = ImageReader(logo_path)
                        img_w, img_h = img.getSize()
                        max_logo_size = 15*mm
                        ratio = min(max_logo_size / img_w, max_logo_size / img_h)
                        new_w = img_w * ratio
                        new_h = img_h * ratio
                        canvas.drawImage(
                            logo_path,
                            20*mm,
                            footer_height - 20*mm,
                            width=new_w, height=new_h,
                            preserveAspectRatio=True, mask='auto'
                        )
                        logo_width = new_w + 4*mm
                    except Exception as e:
                        print(f"⚠️ Erreur logo: {e}")
            
            # Nom entreprise
            canvas.setFillColor(BLANC)
            canvas.setFont('Helvetica-Bold', 13)
            canvas.drawString(20*mm + logo_width, footer_height - 12*mm, company_name)
            
            # Séparateur
            separator_x = 20*mm + logo_width + 50*mm
            canvas.setStrokeColor(colors.HexColor('#7FAF91'))
            canvas.setLineWidth(0.5)
            canvas.line(separator_x, 8*mm, separator_x, footer_height - 8*mm)
            
            # Coordonnées
            canvas.setFont('Helvetica', 8.5)
            canvas.setFillColor(colors.HexColor('#D4E8DC'))
            y_pos = footer_height - 12*mm
            if company_phone:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Tél : {company_phone}")
                y_pos -= 4.5*mm
            if company_email:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Email : {company_email}")
                y_pos -= 4.5*mm
            if company_address:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Adresse : {company_address}")
                y_pos -= 4.5*mm
            if company_website:
                canvas.drawString(separator_x + 6*mm, y_pos, f"Site : {company_website}")
            
            # Infos admin
            canvas.setFont('Helvetica', 7)
            canvas.setFillColor(colors.HexColor('#B8D4C3'))
            infos_admin = []
            if company_nif:
                infos_admin.append(f"NIF : {company_nif}")
            rccm = settings.get('rccm', '')
            if rccm:
                infos_admin.append(f"RCCM : {rccm}")
            if infos_admin:
                canvas.drawString(20*mm, 4*mm, "  ·  ".join(infos_admin))
            
            canvas.restoreState()
        
        # ============================================================
        # CONSTRUCTION DU CONTENU
        # ============================================================
        
        story = []
        
        # ------------------------------------------------------------
        # 1. INFOS CLIENT + PROJET
        # ------------------------------------------------------------
        
        client_lines = [f"<b>{client_nom}</b>"]
        if client_telephone:
            client_lines.append(client_telephone)
        if client_email:
            client_lines.append(client_email)
        if client_adresse:
            client_lines.append(client_adresse)
        
        client_text = "<br/>".join(client_lines)
        
        gauche_content = [
            Paragraph("Pour :", style_pour),
            Paragraph(client_text, style_client_info),
        ]
        
        # Ajouter les infos projet si présentes
        if nom_projet or description_projet:
            gauche_content.append(Spacer(1, 4*mm))
            if nom_projet:
                gauche_content.append(Paragraph(f"<b>Projet :</b> {nom_projet}", style_info_projet))
            if description_projet:
                gauche_content.append(Paragraph(f"<b>Description :</b> {description_projet}", style_info_projet))
        
        # Colonne droite : ID client + IFU (si présent)
        droite_content = [
            Paragraph(f"ID client : {client_id}", style_id_client),
        ]
        
        if client_ifu:
            droite_content.append(Paragraph(f"IFU client : {client_ifu}", style_id_client))
        
        client_table = Table(
            [[gauche_content, droite_content]],
            colWidths=[largeur_utile * 0.65, largeur_utile * 0.35]
        )
        client_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(client_table)
        
        # ------------------------------------------------------------
        # 2. TABLEAU DES PRESTATIONS
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 10*mm))
        
        table_header = [
            Paragraph("<b>Détail</b>", style_th),
            Paragraph("<b>Quantité</b>", style_th),
            Paragraph("<b>Prix HT</b>", style_th),
            Paragraph("<b>Total HT</b>", style_th)
        ]
        
        table_data = [table_header]
        
        for ligne in lignes:
            table_data.append([
                Paragraph(ligne.get('designation', ''), style_td),
                Paragraph(str(ligne.get('quantite', 0)), style_td_center),
                Paragraph(f"{ligne.get('prix_unitaire', 0):,.0f}".replace(',', ' '), style_td_center),
                Paragraph(f"{ligne.get('total_ligne', 0):,.0f}".replace(',', ' '), style_td_right)
            ])
        
        col_widths = [
            largeur_utile * 0.52,
            largeur_utile * 0.16,
            largeur_utile * 0.16,
            largeur_utile * 0.16
        ]
        
        tableau = Table(table_data, colWidths=col_widths, repeatRows=1)
        tableau.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERT_CLAIR),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLANC),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), BLANC),
            ('TEXTCOLOR', (0, 1), (-1, -1), GRIS_FONCE),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, GRIS_BORDURE),
            ('LINEBELOW', (0, 0), (-1, 0), 1, VERT_PROFOND),
        ]))
        
        story.append(tableau)
        
        # ------------------------------------------------------------
        # 3. ZONE DES TOTAUX (juste Total HT)
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 6*mm))
        
        totaux_data = [
            ["Total", f"{total_ht:,.0f} FCFA".replace(',', ' ')],
        ]
        
        totaux_table = Table(
            totaux_data,
            colWidths=[largeur_utile * 0.25, largeur_utile * 0.20]
        )
        
        totaux_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), VERT_PROFOND),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEABOVE', (0, 0), (-1, 0), 1, VERT_PROFOND),
        ]))
        
        totaux_container = Table(
            [["", totaux_table]],
            colWidths=[largeur_utile * 0.55, largeur_utile * 0.45]
        )
        totaux_container.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(totaux_container)
        
        # ------------------------------------------------------------
        # 4. CONDITIONS
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("<b>Conditions</b>", style_section_titre))
        story.append(Paragraph(
            "Règlement avant échéance. Frais de retard applicables.",
            style_section_texte
        ))
        
        # ------------------------------------------------------------
        # 5. MESSAGE FINAL
        # ------------------------------------------------------------
        
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("Merci pour votre confiance !", style_merci))
        
        # ============================================================
        # CONSTRUCTION
        # ============================================================
        
        doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'facture_{id_facture}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ Erreur génération PDF facture simple: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
@limiter.limit("100 per hour")
@app.route('/api/devis/<int:id_devis>', methods=['PUT'])
@jwt_required()
def update_devis(id_devis):
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        import requests
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "apikey": supabase_key,
            "Content-Type": "application/json"
        }
        
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
        
        requests.delete(
            f"{supabase_url}/rest/v1/ligne_devis?id_devis=eq.{id_devis}",
            headers=headers
        )
        
        lignes = data.get('lignes', [])
        total_materiaux = sum(float(ligne['quantite']) * float(ligne['prix_unitaire']) for ligne in lignes)
        total = total_materiaux * 1.2
        
        from datetime import datetime
        update_data = {
            "id_client": data.get('id_client'),
            "id_projet": data.get('id_projet'),
            "total": total,
            "date_creation": datetime.now().isoformat(),
            "show_signature": data.get('show_signature')
        }
        
        response = requests.patch(
            f"{supabase_url}/rest/v1/devis?id_devis=eq.{id_devis}",
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 204]:
            for ligne in lignes:
                total_ligne = float(ligne['quantite']) * float(ligne['prix_unitaire'])
                # 🔥 SANITIZE - Nettoyer la désignation
                ligne_data = {
                    "designation": sanitize_input(ligne.get('designation')),
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
            
            log_action(user_id, 'update_devis', f"Devis #{id_devis} modifié")
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
    

@app.route('/api/paiement/initier', methods=['POST'])
@jwt_required()
def initier_paiement():
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        data = request.json
        
        # 1. Récupérer l'offre choisie
        offre = data.get('offre')
        montant = data.get('montant')
        description = data.get('description', f'Abonnement {offre}')
        
        if not offre or not montant:
            return jsonify({'success': False, 'message': 'Offre et montant requis'}), 400
        
        # 2. Récupérer les infos utilisateur
        user_response = requests.get(
            f"{os.environ.get('SUPABASE_URL')}/rest/v1/utilisateur?id_user=eq.{user_id}",
            headers={
                "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
                "apikey": os.environ.get('SUPABASE_KEY'),
                "Content-Type": "application/json"
            }
        )
        
        if user_response.status_code != 200 or not user_response.json():
            return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404
        
        user = user_response.json()[0]
        
        # 3. Créer la transaction sur FedaPay
        fedapay_url = "https://sandbox-api.fedapay.com/v1/transactions"
        fedapay_key = os.environ.get('FEDAPAY_SECRET_KEY')
        
        transaction_data = {
            "description": description,
            "amount": int(montant),
            "currency": {"iso": "XOF"},
            "callback_url": "https://btp-devis-pro-1.onrender.com/paiement/callback",
            "customer": {
                "firstname": user.get('nom', 'Client'),
                "lastname": "",
                "email": user.get('email', ''),
                "phone_number": {
                    "number": user.get('telephone', ''),
                    "country": "bj"
                }
            }
        }
        
        print(f"🔍 Création transaction FedaPay: {transaction_data}")
        
        transaction_response = requests.post(
            fedapay_url,
            headers={
                "Authorization": f"Bearer {fedapay_key}",
                "Content-Type": "application/json"
            },
            json=transaction_data
        )
        
        print(f"🔍 Réponse FedaPay: {transaction_response.status_code}")
        print(f"🔍 {transaction_response.text}")
        
        if transaction_response.status_code not in [200, 201]:
            return jsonify({
                'success': False, 
                'message': f'Erreur FedaPay: {transaction_response.text}'
            }), 500
        
        transaction = transaction_response.json()
        
        # 🔥 FedaPay enveloppe la réponse dans 'v1/transaction'
        transaction_info = transaction.get('v1/transaction', transaction)
        
        transaction_id = transaction_info.get('id')
        payment_token = transaction_info.get('payment_token')
        payment_url = transaction_info.get('payment_url')
        reference = transaction_info.get('reference')
        
        print(f"🔍 Transaction ID: {transaction_id}")
        print(f"🔍 Payment URL: {payment_url}")
        
        if not payment_url:
            return jsonify({
                'success': False, 
                'message': 'URL de paiement non reçue de FedaPay'
            }), 500
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'reference': reference,
            'token': payment_token,
            'url': payment_url,
            'message': 'Transaction créée avec succès'
        })
        
    except Exception as e:
        print(f"❌ Erreur initier_paiement: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/paiement/webhook', methods=['POST'])
def webhook_fedapay():
    try:
        # 1. Récupérer les données du webhook
        event = request.json
        event_type = event.get('name')
        event_data = event.get('data', {})
        
        print(f"🔔 Webhook reçu: {event_type}")
        print(f"🔔 Data: {event_data}")
        
        # 2. Extraire l'ID de la transaction
        transaction_id = event_data.get('id')
        
        if not transaction_id:
            print("❌ Pas d'ID de transaction")
            return jsonify({'error': 'ID manquant'}), 400
        
        # 3. Vérifier le statut directement auprès de FedaPay
        # 🔥 C'est la méthode la plus fiable
        fedapay_key = os.environ.get('FEDAPAY_SECRET_KEY')
        
        fedapay_response = requests.get(
            f"https://sandbox-api.fedapay.com/v1/transactions/{transaction_id}",
            headers={
                "Authorization": f"Bearer {fedapay_key}",
                "Content-Type": "application/json"
            }
        )
        
        if fedapay_response.status_code != 200:
            print(f"❌ Erreur vérification FedaPay: {fedapay_response.text}")
            return jsonify({'error': 'Transaction non trouvée'}), 404
        
        fedapay_data = fedapay_response.json()
        transaction = fedapay_data.get('v1/transaction', fedapay_data)
        
        statut_fedapay = transaction.get('status')
        reference = transaction.get('reference')
        montant = transaction.get('amount')
        description = transaction.get('description', '')
        customer_email = ''
        
        # Récupérer l'email du customer
        customer_id = transaction.get('customer_id')
        if customer_id:
            customer_response = requests.get(
                f"https://sandbox-api.fedapay.com/v1/customers/{customer_id}",
                headers={"Authorization": f"Bearer {fedapay_key}"}
            )
            if customer_response.status_code == 200:
                customer_data = customer_response.json()
                customer = customer_data.get('v1/customer', customer_data)
                customer_email = customer.get('email', '')
        
        print(f"🔍 Statut FedaPay confirmé: {statut_fedapay}")
        print(f"🔍 Reference: {reference}")
        print(f"🔍 Email: {customer_email}")
        
        # 4. Si le paiement est approuvé, activer l'abonnement
        if statut_fedapay == 'approved':
            # Trouver l'utilisateur par email
            if customer_email:
                user_response = requests.get(
                    f"{os.environ.get('SUPABASE_URL')}/rest/v1/utilisateur?email=eq.{customer_email}",
                    headers={
                        "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
                        "apikey": os.environ.get('SUPABASE_KEY'),
                        "Content-Type": "application/json"
                    }
                )
                
                if user_response.status_code == 200 and user_response.json():
                    user = user_response.json()[0]
                    user_id = user.get('id_user')
                    
                    # Extraire l'offre depuis la description
                    offre = 'starter'  # Par défaut
                    if 'artisan' in description.lower():
                        offre = 'artisan'
                    elif 'pro' in description.lower():
                        offre = 'pro'
                    elif 'annuel' in description.lower() or 'annuelle' in description.lower():
                        offre = 'annuel'
                    
                    # Calculer la durée
                    durees = {
                        'artisan': 30,
                        'starter': 30,
                        'pro': 30,
                        'annuel': 365
                    }
                    jours = durees.get(offre, 30)
                    
                    from datetime import datetime, timedelta
                    date_fin = datetime.now() + timedelta(days=jours)
                    
                    # Vérifier si l'utilisateur a déjà un abonnement
                    abo_response = requests.get(
                        f"{os.environ.get('SUPABASE_URL')}/rest/v1/abonnements?id_user=eq.{user_id}",
                        headers={
                            "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
                            "apikey": os.environ.get('SUPABASE_KEY'),
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if abo_response.status_code == 200 and abo_response.json():
                        # Mettre à jour
                        abo_id = abo_response.json()[0].get('id_abonnement')
                        requests.patch(
                            f"{os.environ.get('SUPABASE_URL')}/rest/v1/abonnements?id_abonnement=eq.{abo_id}",
                            headers={
                                "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
                                "apikey": os.environ.get('SUPABASE_KEY'),
                                "Content-Type": "application/json"
                            },
                            json={
                                "statut": "actif",
                                "date_fin": date_fin.isoformat(),
                                "type_abonnement": offre
                            }
                        )
                    else:
                        # Créer
                        requests.post(
                            f"{os.environ.get('SUPABASE_URL')}/rest/v1/abonnements",
                            headers={
                                "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
                                "apikey": os.environ.get('SUPABASE_KEY'),
                                "Content-Type": "application/json"
                            },
                            json={
                                "id_user": user_id,
                                "statut": "actif",
                                "date_debut": datetime.now().isoformat(),
                                "date_fin": date_fin.isoformat(),
                                "type_abonnement": offre
                            }
                        )
                    
                    # Enregistrer la transaction
                    requests.post(
                        f"{os.environ.get('SUPABASE_URL')}/rest/v1/transactions_fedapay",
                        headers={
                            "Authorization": f"Bearer {os.environ.get('SUPABASE_KEY')}",
                            "apikey": os.environ.get('SUPABASE_KEY'),
                            "Content-Type": "application/json"
                        },
                        json={
                            "id_user": user_id,
                            "transaction_id": str(transaction_id),
                            "offre": offre,
                            "montant": montant,
                            "statut": "approved",
                            "reference": reference
                        }
                    )
                    
                    print(f"✅ Abonnement {offre} activé pour user {user_id}")
                else:
                    print(f"⚠️ Utilisateur non trouvé: {customer_email}")
        
        return jsonify({'received': True}), 200
        
    except Exception as e:
        print(f"❌ Erreur webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
# ============================================================
# PAGE CALLBACK FEDAPAY
# ============================================================

@app.route('/paiement/callback')
def paiement_callback():
    """Page de retour après paiement FedaPay"""
    from flask import send_from_directory
    frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
    return send_from_directory(frontend_path, 'paiement-callback.html')


@app.route('/api/paiement/verifier/<int:transaction_id>', methods=['GET'])
@jwt_required()
def verifier_paiement(transaction_id):
    """Vérifie le statut d'une transaction FedaPay"""
    try:
        user_id = get_jwt_identity()
        user_id = int(user_id)
        
        fedapay_key = os.environ.get('FEDAPAY_SECRET_KEY')
        
        # Appeler FedaPay pour vérifier le statut
        response = requests.get(
            f"https://sandbox-api.fedapay.com/v1/transactions/{transaction_id}",
            headers={
                "Authorization": f"Bearer {fedapay_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'message': 'Transaction non trouvée'
            }), 404
        
        data = response.json()
        transaction = data.get('v1/transaction', data)
        
        return jsonify({
            'success': True,
            'statut': transaction.get('status'),
            'reference': transaction.get('reference'),
            'montant': transaction.get('amount'),
            'offre': transaction.get('description', '')
        })
        
    except Exception as e:
        print(f"❌ Erreur verifier_paiement: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


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

@app.route('/api/test-version', methods=['GET'])
def test_version():
    return jsonify({
        'version': 'v2-paiement',
        'timestamp': '2026-10-05',
        'routes_paiement': [
            str(rule) for rule in app.url_map.iter_rules() 
            if 'paiement' in str(rule)
        ]
    })

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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_KEY', '')
        
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