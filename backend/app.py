from flask_mail import Mail, Message
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
from datetime import datetime, timedelta
import io
import sys


# Forcer l'encodage UTF-8 pour la console Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from models import Utilisateur, Client, Projet, Devis, Facture, Abonnement, Settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

app = Flask(__name__)
# Configuration SendGrid
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = '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'  # ← Ta clé API SendGrid
app.config['MAIL_DEFAULT_SENDER'] = 'bylgaitb@gmail.com'  # Ton email

mail = Mail(app)



# Configuration CORS complète
CORS(app, origins=["http://localhost:8000"], supports_credentials=True, allow_headers=["Content-Type", "Authorization"])
CORS(app)

# Configuration JWT
app.config['JWT_SECRET_KEY'] = 'super-secret-key-btp-2024'
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
            return jsonify({'success': True, 'message': 'Inscription réussie'})
        return jsonify({'success': False, 'message': 'Erreur'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        user = utilisateur_model.authenticate(data['email'], data['mot_de_passe'])
        if user:
            token = create_access_token(identity=str(user['id_user']))
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
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== CLIENTS ====================
@app.route('/api/clients', methods=['GET'])
@jwt_required()
def get_clients():
    try:
        user_id = get_jwt_identity()
        # Ne récupérer que les clients de l'utilisateur connecté
        query = """
        SELECT DISTINCT c.* FROM CLIENT c
        LEFT JOIN DEVIS d ON c.id_client = d.id_client
        WHERE d.id_user = %s OR d.id_user IS NULL
        ORDER BY c.nom
        """
        clients = client_model.db.fetch_all(query, (user_id,))
        return jsonify(clients)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients', methods=['POST'])
@jwt_required()
def create_client():
    try:
        data = request.json
        client_model.create(data['nom'], data['telephone'], data['email'], data['adresse'])
        return jsonify({'success': True, 'message': 'Client créé'})
    except Exception as e:
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
        query = """
        SELECT DISTINCT p.* FROM PROJET p
        LEFT JOIN DEVIS d ON p.id_projet = d.id_projet
        WHERE d.id_user = %s OR d.id_user IS NULL
        ORDER BY p.nom_projet
        """
        projets = projet_model.db.fetch_all(query, (user_id,))
        return jsonify(projets)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projets', methods=['POST'])
@jwt_required()
def create_projet():
    try:
        data = request.json
        projet_model.create(data['nom_projet'], data['description'], data['localisation'])
        return jsonify({'success': True, 'message': 'Projet créé'})
    except Exception as e:
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
        data = request.json
        id_devis = devis_model.create(
            data['id_client'], data['id_user'], data['id_projet'], data['lignes']
        )
        if id_devis:
            return jsonify({'success': True, 'id_devis': id_devis})
        return jsonify({'success': False, 'message': 'Erreur'}), 500
    except Exception as e:
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
        
        # Désactiver les contraintes
        devis_model.db.execute_query("SET FOREIGN_KEY_CHECKS = 0")
        
        # Vider les tables
        devis_model.db.execute_query("DELETE FROM LIGNE_DEVIS")
        devis_model.db.execute_query("DELETE FROM FACTURE")
        devis_model.db.execute_query("DELETE FROM DEVIS")
        devis_model.db.execute_query("DELETE FROM CLIENT")
        devis_model.db.execute_query("DELETE FROM PROJET")
        
        # Insérer les clients
        for client in backup_data.get('clients', []):
            sql = "INSERT INTO CLIENT (nom, telephone, email, adresse) VALUES (%s, %s, %s, %s)"
            devis_model.db.execute_query(sql, (
                client['nom'], 
                client['telephone'], 
                client['email'], 
                client['adresse']
            ))
            print(f"   ✅ Client inséré: {client['nom']}")
        
        # FORCER LE COMMIT
        devis_model.db.connection.commit()
        print("✅ COMMIT forcé")
        
        # Insérer les projets
        for projet in backup_data.get('projets', []):
            sql = "INSERT INTO PROJET (nom_projet, description, localisation) VALUES (%s, %s, %s)"
            devis_model.db.execute_query(sql, (
                projet['nom_projet'], 
                projet['description'], 
                projet['localisation']
            ))
            print(f"   ✅ Projet inséré: {projet['nom_projet']}")
        
        # FORCER LE COMMIT
        devis_model.db.connection.commit()
        
        # Réactiver les contraintes
        devis_model.db.execute_query("SET FOREIGN_KEY_CHECKS = 1")
        
        # Vérifier
        result = devis_model.db.fetch_one("SELECT COUNT(*) as total FROM CLIENT")
        print(f"📊 Clients après restauration: {result['total']}")
        
        print("🎉 RESTAURATION TERMINÉE !")
        print("=" * 60)
        
        return jsonify({'success': True, 'message': 'Restauration réussie'})
        
    except Exception as e:
        devis_model.db.execute_query("SET FOREIGN_KEY_CHECKS = 1")
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
        signature_data = [
            [f'Pour {settings.get("company_name", "l\'entreprise")}', 'Pour le client'],
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
        abonnement = abonnement_model.get_by_user(user_id)
        if abonnement:
            jours_restants = (abonnement['date_fin'] - datetime.now()).days
            return jsonify({
                'success': True,
                'statut': abonnement['statut'],
                'type': abonnement['type_abonnement'],
                'date_fin': abonnement['date_fin'],
                'jours_restants': max(0, jours_restants)
            })
        return jsonify({'success': False, 'statut': 'inactif'})
    except Exception as e:
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
        user = utilisateur_model.get_by_id(user_id)
        
        # Vérifier que c'est l'admin (email admin@btp.com)
        if user['email'] != 'admin@btp.com' and user['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        query = """
        SELECT u.id_user, u.nom, u.email, u.entreprise, u.telephone,
               a.id_abonnement, a.statut, a.date_debut, a.date_fin, a.type_abonnement,
               DATEDIFF(a.date_fin, NOW()) as jours_restants
        FROM UTILISATEUR u
        LEFT JOIN ABONNEMENTS a ON u.id_user = a.id_user
        WHERE u.id_user != 1 AND u.id_user != 2
        ORDER BY a.date_fin ASC
        """
        abonnements = utilisateur_model.db.fetch_all(query)
        return jsonify(abonnements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/abonnement/<int:id_user>/prolonger', methods=['POST'])
@jwt_required()
def admin_prolonger_abonnement(id_user):
    try:
        admin_id = get_jwt_identity()
        admin = utilisateur_model.get_by_id(admin_id)
        
        if admin['email'] != 'admin@btp.com' and admin['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        data = request.json
        jours = data.get('jours', 30)
        montant = data.get('montant', 0)
        methode = data.get('methode', 'virement')
        offreType = data.get('offreType', 'pro')
        
        from datetime import datetime, timedelta
        
        check_query = "SELECT * FROM ABONNEMENTS WHERE id_user = %s"
        abonnement = utilisateur_model.db.fetch_one(check_query, (id_user,))
        
        if abonnement:
            nouvelle_date = abonnement['date_fin'] + timedelta(days=jours)
            query = """
            UPDATE ABONNEMENTS 
            SET date_fin = %s, statut = 'actif', type_abonnement = %s
            WHERE id_user = %s
            """
            utilisateur_model.db.execute_query(query, (nouvelle_date, offreType, id_user))
        else:
            nouvelle_date = datetime.now() + timedelta(days=jours)
            query = """
            INSERT INTO ABONNEMENTS (id_user, statut, date_debut, date_fin, type_abonnement)
            VALUES (%s, 'actif', %s, %s, %s)
            """
            utilisateur_model.db.execute_query(query, (id_user, datetime.now(), nouvelle_date, offreType))
        
        # Notification
        notification_message = f"✅ Abonnement {offreType} renouvelé pour {jours} jours. Échéance: {nouvelle_date.strftime('%d/%m/%Y')}"
        notification_query = """
        INSERT INTO notifications (id_user, message, type, date_creation)
        VALUES (%s, %s, 'renouvellement', %s)
        """
        utilisateur_model.db.execute_query(notification_query, (id_user, notification_message, datetime.now()))
        
        # Paiement
        import uuid
        reference = f"PAY_{id_user}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        paiement_query = """
        INSERT INTO paiements (id_user, montant, date_paiement, reference_paiement, methode, statut)
        VALUES (%s, %s, %s, %s, %s, 'valide')
        """
        utilisateur_model.db.execute_query(paiement_query, (id_user, montant, datetime.now(), reference, methode))
        
        return jsonify({'success': True, 'message': f'Abonnement {offreType} prolongé'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        user_id = get_jwt_identity()
        query = """
        SELECT * FROM notifications 
        WHERE id_user = %s AND est_lue = FALSE
        ORDER BY date_creation DESC
        """
        notifications = utilisateur_model.db.fetch_all(query, (user_id,))
        return jsonify(notifications)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/<int:id_notification>/lire', methods=['PUT'])
@jwt_required()
def marquer_notification_lue(id_notification):
    try:
        query = "UPDATE notifications SET est_lue = TRUE WHERE id_notification = %s"
        utilisateur_model.db.execute_query(query, (id_notification,))
        return jsonify({'success': True})
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
        admin = utilisateur_model.get_by_id(admin_id)
        
        if admin['email'] != 'admin@btp.com' and admin['email'] != 'bylgaitb@gmail.com':
            return jsonify({'error': 'Non autorisé'}), 403
        
        query = "UPDATE ABONNEMENTS SET statut = 'suspendu' WHERE id_user = %s"
        utilisateur_model.db.execute_query(query, (id_user,))
        
        return jsonify({'success': True, 'message': 'Abonnement suspendu'})
    except Exception as e:
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