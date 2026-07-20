# 🏗️ BTP Devis Pro

**La solution de gestion de devis et facturation pour les professionnels du BTP au Bénin.**

[![Render](https://img.shields.io/badge/Render-Deployed-success)](https://btp-devis-pro-1.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.2-green)](https://flask.palletsprojects.com)

---

## 📋 À propos

BTP Devis Pro est une application SaaS conçue pour les professionnels du bâtiment au Bénin. Elle permet de :

- ✅ Créer des **devis professionnels** en quelques minutes
- ✅ Gérer vos **clients** et **projets**
- ✅ Suivre vos **chantiers** (statut, progression, dates)
- ✅ Générer des **factures normalisées** conformes à la DGI avec QR Code
- ✅ Gérer les **acomptes** et **situations de travaux**
- ✅ Archiver et restaurer vos documents
- ✅ Exporter vos données (Excel, PDF)

---

## 🚀 Démo en ligne

👉 [https://btp-devis-pro-1.onrender.com](https://btp-devis-pro-1.onrender.com)

**Identifiants de test :**
- Email : `bylgaitb@gmail.com`
- Mot de passe : `000000`

---

## 🛠️ Technologies

### Backend
| Technologie            | Version | Utilisation           |
|------------------------|---------|-----------------------|
| **Python**             | 3.12    | Langage principal     |
| **Flask**              | 2.3.2   | Framework web         |
| **Flask-JWT-Extended** | 4.5.2   | Authentification      |
| **Flask-CORS**         | 4.0.0   | Gestion CORS          |
| **ReportLab**          | 4.0.4   | Génération PDF        |
| **QRCode**             | 7.4.2   | Génération QR Code    |
| **bcrypt**             | 4.0.1   | Hashage mots de passe |
| **Requests**           | 2.31.0  | Requêtes HTTP         |

### Base de données
| Technologie | Utilisation |
|-------------|-------------|
| **Supabase** | Base de données PostgreSQL + API REST |

### Frontend
| Technologie | Utilisation |
|-------------|-------------|
| **HTML/CSS/JS** | Interface utilisateur |
| **FontAwesome** | Icônes |

### Hébergement
| Service | Utilisation |
|---------|-------------|
| **Render** | Hébergement backend + frontend |
| **Supabase** | Base de données |

---

## 📁 Structure du projet
btp-devis-pro/
├── backend/
│ ├── app.py # Application Flask principale
│ ├── models.py # Modèles de données
│ ├── database.py # Connexion Supabase
│ ├── emcf.py # Intégration API e-MCF (DGI)
│ ├── requirements.txt # Dépendances Python
│ └── runtime.txt # Version Python
│
├── frontend/
│ ├── index.html # Dashboard
│ ├── login.html # Page de connexion
│ ├── register.html # Page d'inscription
│ ├── css/style.css # Styles
│ └── js/app.js # Logique frontend
│
├── uploads/ # Logos et en-têtes importés
├── README.md # Documentation
└── LICENSE # Licence

text

---

## ⚙️ Installation locale

### 1. Cloner le projet

```bash
git clone https://github.com/byl06/btp-devis-pro.git
cd btp-devis-pro
2. Créer un environnement virtuel
bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
3. Installer les dépendances
bash
pip install -r requirements.txt
4. Configurer les variables d'environnement
Crée un fichier .env dans backend/ :

env
# Supabase
SUPABASE_URL=https://aoqiveekzucqjhqdwiql.supabase.co
SUPABASE_KEY=ta_clé_supabase

# JWT
JWT_SECRET_KEY=ta_clé_jwt

# e-MCF (DGI)
EMCEF_JWT_TOKEN=ton_token_dgi
5. Lancer l'application
bash
python app.py
L'application est accessible à : http://localhost:5000

🔐 Authentification
Endpoint	Méthode	Description
/api/register	POST	Inscription
/api/login	POST	Connexion (retourne JWT)
Exemple de requête login :

json
POST /api/login
{
    "email": "user@email.com",
    "mot_de_passe": "password"
}
Réponse :

json
{
    "success": true,
    "token": "jwt_token_here",
    "user": {
        "id": 1,
        "nom": "User",
        "email": "user@email.com"
    }
}
📡 API Principales
Endpoint	Méthode	Description
/api/clients	GET	Liste des clients
/api/clients	POST	Créer un client
/api/clients/<id>	PUT	Modifier un client
/api/clients/<id>	DELETE	Supprimer un client
/api/projets	GET	Liste des projets
/api/projets	POST	Créer un projet
/api/projets/<id>	PUT	Modifier un projet
/api/projets/<id>	DELETE	Supprimer un projet
/api/devis	GET	Liste des devis
/api/devis	POST	Créer un devis
/api/devis/<id>	GET	Détail d'un devis
/api/devis/<id>/pdf	GET	Télécharger PDF
/api/devis/<id>/validate	POST	Valider un devis
/api/facture/<id>	POST	Générer une facture
/api/facture/<id>/pay	PUT	Marquer comme payée
/api/facture/<id>/normaliser	POST	Normaliser (e-MCF)
/api/facture/<id>/pdf-normalise	GET	PDF normalisé
/api/abonnement/statut	GET	Statut abonnement
📊 Modèle de données
Tables principales
Table	Description
utilisateur	Utilisateurs
client	Clients
projet	Projets / Chantiers
devis	Devis
ligne_devis	Lignes de devis
facture	Factures
situation_devis	Situations de travaux
abonnements	Abonnements
settings	Paramètres entreprise
notifications	Notifications
🚀 Déploiement sur Render
1. Connecter le dépôt GitHub
Aller sur Render.com

Cliquer sur "New +" → "Web Service"

Connecter le dépôt GitHub

2. Configurer le service
Paramètre	Valeur
Root Directory	backend
Build Command	pip install -r requirements.txt
Start Command	gunicorn app:app
Python Version	3.12 (via runtime.txt)
3. Ajouter les variables d'environnement
env
SUPABASE_URL=https://aoqiveekzucqjhqdwiql.supabase.co
SUPABASE_KEY=ta_clé_supabase
JWT_SECRET_KEY=ta_clé_jwt
EMCEF_JWT_TOKEN=ton_token_dgi
4. Déployer
Render déploie automatiquement à chaque git push.

🎯 Fonctionnalités clés
✅ Devis professionnels
Création rapide avec articles

Calcul automatique (matériaux + main-d'œuvre 20%)

Export PDF

Validation

✅ Facturation normalisée (e-MCF)
Intégration API DGI

QR Code fiscal

NIM (Numéro d'Identification)

Code MECeF

Conforme à la réglementation béninoise

✅ Suivi des chantiers
Statut (En attente/En cours/Terminé)

Dates de début/fin

Progression (%)

✅ Acomptes et situations
Acompte à la commande (%)

Situations de travaux

Suivi des paiements

✅ Archivage
Archiver/Restaurer les factures

2 types d'archives (simples / normalisées)

✅ Administration
Gestion des utilisateurs

Gestion des abonnements

Statistiques

Export des données

📦 Offres d'abonnement
Offre	Prix	Clients	Projets	Devis	Factures normalisées
Artisan 🛠️	7 000 F/mois	5	5	10	❌
Starter 🟢	15 000 F/mois	10	10	20	✅
Pro 🔵	30 000 F/mois	Illimité	Illimité	Illimité	✅
Annuel 🔴	250 000 F/an	Illimité	Illimité	Illimité	✅
🤝 Contribution
Les contributions sont les bienvenues !

Fork le projet

Créer une branche (git checkout -b feature/ma-fonctionnalite)

Commit (git commit -m 'Ajout fonctionnalité')

Push (git push origin feature/ma-fonctionnalite)

Ouvrir une Pull Request

📝 Licence
MIT License - voir LICENSE pour plus d'informations.

📞 Contact
Email : devisbtp496@gmail.com

WhatsApp : +229 01 51 59 63 97

Démo : https://btp-devis-pro-1.onrender.com

🙏 Remerciements
Supabase - Base de données

Render - Hébergement

Flask - Framework web