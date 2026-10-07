import os
import json
import requests
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

GROQ_MODEL = "llama-3.1-70b-versatile"
MISTRAL_MODEL = "mistral-small-latest"

# ============================================================
# PROMPT SYSTÈME
# ============================================================

SYSTEM_PROMPT = """Tu es un assistant spécialisé dans le BTP au Bénin. Tu aides les professionnels du bâtiment à générer des devis.

RÈGLES STRICTES :
1. Tu ne dois JAMAIS inventer de prix. Si tu ne connais pas un prix, utilise le catalogue fourni.
2. Si la description de l'utilisateur est trop vague pour générer un devis précis, tu dois DEMANDER des précisions au lieu d'inventer.
3. Tu dois retourner UNIQUEMENT du JSON valide, sans texte autour.
4. Tu dois respecter le format JSON suivant :

POUR GÉNÉRER UN DEVIS :
{
  "action": "generate",
  "lignes": [
    {"designation": "Ciment (50 kg)", "quantite": 50, "prix_unitaire": 5000},
    {"designation": "Sable", "quantite": 10, "prix_unitaire": 15000}
  ]
}

POUR DEMANDER DES PRÉCISIONS :
{
  "action": "ask",
  "questions": [
    "Quelle est la surface du terrain ?",
    "Combien de pièces souhaitez-vous ?"
  ]
}

CONTEXTE MÉTIER :
- Tu es au Bénin, les prix sont en FCFA.
- Les matériaux courants : ciment, sable, gravier, fer à béton, tôle, carreaux, peinture, etc.
- Pour une maison de 100m², il faut environ 50 sacs de ciment, 10m³ de sable, 100 barres de fer, etc.
- Sois réaliste dans les quantités et les prix.

CATALOGUE DE L'UTILISATEUR (utilise ces prix en priorité) :
{catalogue}

Si le catalogue est vide, utilise les prix moyens du marché béninois.
"""

# ============================================================
# FONCTION PRINCIPALE
# ============================================================

def generate_devis_with_ai(description, catalogue=None):
    """
    Génère un devis à partir d'une description en langage naturel.
    
    Args:
        description (str): Description du projet par l'utilisateur
        catalogue (list): Liste des produits de l'utilisateur (optionnel)
    
    Returns:
        dict: {
            "success": bool,
            "action": "generate" | "ask",
            "lignes": [...],
            "questions": [...],
            "provider": "groq" | "mistral",
            "error": str (si success=False)
        }
    """
    
    # Préparer le catalogue pour le prompt
    catalogue_str = "Aucun catalogue disponible."
    if catalogue and len(catalogue) > 0:
        catalogue_lines = []
        for p in catalogue[:50]:  # Limiter à 50 produits
            designation = p.get('designation', '')
            prix = p.get('prix_unitaire', 0)
            unite = p.get('unite', 'unité')
            catalogue_lines.append(f"- {designation} : {prix} FCFA / {unite}")
        catalogue_str = "\n".join(catalogue_lines)
    
    # Construire le prompt système
    system_prompt = SYSTEM_PROMPT.replace("{catalogue}", catalogue_str)
    
    # Messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": description}
    ]
    
    # ============================================================
    # TENTATIVE 1 : GROQ
    # ============================================================
    
    if GROQ_API_KEY:
        result = _call_groq(messages)
        if result['success']:
            return result
    
    # ============================================================
    # TENTATIVE 2 : MISTRAL (fallback)
    # ============================================================
    
    if MISTRAL_API_KEY:
        result = _call_mistral(messages)
        if result['success']:
            return result
    
    # ============================================================
    # ÉCHEC DES DEUX
    # ============================================================
    
    return {
        "success": False,
        "error": "Les deux fournisseurs IA sont indisponibles. Réessayez dans quelques minutes.",
        "provider": None
    }


# ============================================================
# APPEL GROQ
# ============================================================

def _call_groq(messages):
    """Appelle l'API Groq."""
    try:
        print("🤖 Tentative Groq...")
        
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        
        print(f"📊 Groq status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            parsed = _parse_ai_response(content)
            
            if parsed:
                return {
                    "success": True,
                    "action": parsed.get('action', 'generate'),
                    "lignes": parsed.get('lignes', []),
                    "questions": parsed.get('questions', []),
                    "provider": "groq"
                }
            else:
                print(f"⚠️ Groq: réponse invalide")
                return {"success": False, "error": "Réponse invalide de Groq"}
        
        elif response.status_code == 429:
            print(f"⚠️ Groq: quota dépassé (429)")
            return {"success": False, "error": "Quota Groq dépassé"}
        
        else:
            print(f"⚠️ Groq erreur {response.status_code}: {response.text[:200]}")
            return {"success": False, "error": f"Groq erreur {response.status_code}"}
    
    except requests.exceptions.Timeout:
        print("⚠️ Groq: timeout")
        return {"success": False, "error": "Groq timeout"}
    except Exception as e:
        print(f"⚠️ Groq exception: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# APPEL MISTRAL
# ============================================================

def _call_mistral(messages):
    """Appelle l'API Mistral (fallback)."""
    try:
        print("🤖 Tentative Mistral (fallback)...")
        
        response = requests.post(
            MISTRAL_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MISTRAL_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            },
            timeout=30
        )
        
        print(f"📊 Mistral status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            parsed = _parse_ai_response(content)
            
            if parsed:
                return {
                    "success": True,
                    "action": parsed.get('action', 'generate'),
                    "lignes": parsed.get('lignes', []),
                    "questions": parsed.get('questions', []),
                    "provider": "mistral"
                }
            else:
                print(f"⚠️ Mistral: réponse invalide")
                return {"success": False, "error": "Réponse invalide de Mistral"}
        
        else:
            print(f"⚠️ Mistral erreur {response.status_code}: {response.text[:200]}")
            return {"success": False, "error": f"Mistral erreur {response.status_code}"}
    
    except requests.exceptions.Timeout:
        print("⚠️ Mistral: timeout")
        return {"success": False, "error": "Mistral timeout"}
    except Exception as e:
        print(f"⚠️ Mistral exception: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# PARSING DE LA RÉPONSE IA
# ============================================================

def _parse_ai_response(content):
    """Parse la réponse JSON de l'IA."""
    try:
        # Nettoyer les backticks markdown
        content = content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        # Parser le JSON
        parsed = json.loads(content)
        
        # Valider la structure
        if 'action' not in parsed:
            print(f"⚠️ Réponse sans 'action': {parsed}")
            return None
        
        if parsed['action'] == 'generate':
            if 'lignes' not in parsed or not isinstance(parsed['lignes'], list):
                print(f"⚠️ Réponse 'generate' sans 'lignes'")
                return None
            
            # Valider chaque ligne
            for ligne in parsed['lignes']:
                if 'designation' not in ligne or 'quantite' not in ligne or 'prix_unitaire' not in ligne:
                    print(f"⚠️ Ligne invalide: {ligne}")
                    return None
        
        elif parsed['action'] == 'ask':
            if 'questions' not in parsed or not isinstance(parsed['questions'], list):
                print(f"⚠️ Réponse 'ask' sans 'questions'")
                return None
        
        else:
            print(f"⚠️ Action inconnue: {parsed['action']}")
            return None
        
        return parsed
    
    except json.JSONDecodeError as e:
        print(f"⚠️ Erreur parsing JSON: {e}")
        print(f"Contenu: {content[:500]}")
        return None
    except Exception as e:
        print(f"⚠️ Erreur parsing: {e}")
        return None


# ============================================================
# GESTION DES LIMITES
# ============================================================

# Limites par offre
LIMITES_IA = {
    'artisan': 5,
    'starter': 10,
    'pro': 50,
    'annuel': 50,
    'essai': 10,
    'illimite': 999999
}


def get_limite_ia(offre):
    """Retourne la limite de générations IA pour une offre."""
    return LIMITES_IA.get(offre, 10)


def verifier_limite_ia(user_id, offre):
    """
    Vérifie si l'utilisateur peut encore générer.
    
    Returns:
        dict: {
            "autorise": bool,
            "utilise": int,
            "limite": int,
            "restant": int,
            "message": str (si non autorisé)
        }
    """
    import requests
    
    supabase_url = os.environ.get('SUPABASE_URL', '')
    supabase_key = os.environ.get('SUPABASE_KEY', '')
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json"
    }
    
    # Admin = illimité
    if user_id == 1:
        return {
            "autorise": True,
            "utilise": 0,
            "limite": 999999,
            "restant": 999999
        }
    
    # Compter les générations du jour
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        response = requests.get(
            f"{supabase_url}/rest/v1/ai_generations?id_user=eq.{user_id}&date=eq.{today}",
            headers=headers
        )
        
        if response.status_code == 200:
            generations = response.json()
            utilise = len(generations)
        else:
            utilise = 0
    except Exception as e:
        print(f"⚠️ Erreur vérification limite: {e}")
        utilise = 0
    
    limite = get_limite_ia(offre)
    restant = max(0, limite - utilise)
    
    if utilise >= limite:
        return {
            "autorise": False,
            "utilise": utilise,
            "limite": limite,
            "restant": 0,
            "message": f"⚠️ Vous avez atteint la limite de {limite} générations/jour. Revenez demain ou passez à l'offre supérieure."
        }
    
    return {
        "autorise": True,
        "utilise": utilise,
        "limite": limite,
        "restant": restant
    }


def enregistrer_generation(user_id, provider):
    """Enregistre une génération dans Supabase."""
    import requests
    
    supabase_url = os.environ.get('SUPABASE_URL', '')
    supabase_key = os.environ.get('SUPABASE_KEY', '')
    
    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json"
    }
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        requests.post(
            f"{supabase_url}/rest/v1/ai_generations",
            headers=headers,
            json={
                "id_user": user_id,
                "date": today,
                "provider": provider,
                "created_at": datetime.now().isoformat()
            }
        )
        print(f"✅ Génération enregistrée pour user {user_id}")
    except Exception as e:
        print(f"⚠️ Erreur enregistrement génération: {e}")