import os
import requests
import json
from datetime import datetime

class EMCFClient:
    def __init__(self):
        # URLs de TEST (à changer en production)
        self.base_invoice_url = 'https://developper.impots.bj/sygmef-emcf/api/invoice'
        self.base_info_url = 'https://developper.impots.bj/sygmef-emcf/api/info'
        
        # Récupérer le JWT depuis les variables d'environnement
        self.jwt_token = os.environ.get('EMCEF_JWT_TOKEN')
        
        if not self.jwt_token:
            print("⚠️ EMCEF_JWT_TOKEN non configuré !")
            self.jwt_token = ""
        
        # Nettoyer le token (enlever les espaces, retours à la ligne)
        self.jwt_token = self.jwt_token.strip()
        
        self.headers = {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    # ============================================================
    # API D'INFORMATION
    # ============================================================
    
    def get_status(self):
        """Vérifie l'état de l'API et les infos du contribuable"""
        try:
            response = requests.get(
                f"{self.base_info_url}/status",
                headers=self.headers,
                timeout=10
            )
            print(f"📊 Status API: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Status: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur get_status: {e}")
            return None
    
    def get_tax_groups(self):
        """Récupère les taux TVA"""
        try:
            response = requests.get(
                f"{self.base_info_url}/taxGroups",
                headers=self.headers,
                timeout=10
            )
            print(f"📊 Tax Groups: {response.status_code}")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erreur get_tax_groups: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur get_tax_groups: {e}")
            return None
    
    def get_invoice_types(self):
        """Récupère les types de factures autorisés"""
        try:
            response = requests.get(
                f"{self.base_info_url}/invoiceTypes",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erreur get_invoice_types: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur get_invoice_types: {e}")
            return None
    
    def get_payment_types(self):
        """Récupère les modes de paiement autorisés"""
        try:
            response = requests.get(
                f"{self.base_info_url}/paymentTypes",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erreur get_payment_types: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur get_payment_types: {e}")
            return None
    
    # ============================================================
    # API DE FACTURATION
    # ============================================================
    
    def create_invoice(self, invoice_data):
        """
        Crée une facture → obtient UID
        """
        try:
            print(f"📤 Envoi facture à la DGI...")
            print(f"📤 URL: {self.base_invoice_url}")
            print(f"📤 Payload: {json.dumps(invoice_data, indent=2)}")
            
            response = requests.post(
                self.base_invoice_url,
                headers=self.headers,
                json=invoice_data,
                timeout=10
            )
            
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Réponse brute: {response.text[:500]}")
            
            if response.status_code == 200:
                return response.json()
            else:
                # Essayer de parser l'erreur
                try:
                    error_data = response.json()
                    return {'error': error_data}
                except:
                    return {'error': f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            print(f"❌ Erreur create_invoice: {e}")
            return {'error': str(e)}
    
    def confirm_invoice(self, uid):
        """
        Finalise une facture → obtient NIM + QR Code + Code MECeF
        """
        try:
            print(f"🔒 Confirmation de la facture {uid}...")
            
            response = requests.put(
                f"{self.base_invoice_url}/{uid}/confirm",
                headers=self.headers,
                timeout=10
            )
            
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Réponse brute: {response.text[:500]}")
            
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    error_data = response.json()
                    return {'error': error_data}
                except:
                    return {'error': f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            print(f"❌ Erreur confirm_invoice: {e}")
            return {'error': str(e)}
    
    def cancel_invoice(self, uid):
        """Annule une facture en attente"""
        try:
            response = requests.put(
                f"{self.base_invoice_url}/{uid}/cancel",
                headers=self.headers,
                timeout=10
            )
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"❌ Erreur cancel_invoice: {e}")
            return False
    
    def get_invoice(self, uid):
        """Récupère les détails d'une facture en attente"""
        try:
            response = requests.get(
                f"{self.base_invoice_url}/{uid}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erreur get_invoice: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur get_invoice: {e}")
            return None
    
    def get_pending_invoices(self):
        """Récupère toutes les factures en attente"""
        try:
            response = requests.get(
                self.base_invoice_url,
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erreur get_pending_invoices: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Erreur get_pending_invoices: {e}")
            return None


# ============================================================
# FONCTION UTILITAIRE POUR CONSTRUIRE LES DONNÉES DE FACTURE
# ============================================================

def build_invoice_data(facture, devis, client, settings, lignes):
    """
    Construit les données JSON pour l'API e-MCF
    """
    # Récupérer l'IFU du vendeur depuis les settings
    ifu_vendeur = settings.get('nif', '').strip()
    if not ifu_vendeur or len(ifu_vendeur) != 13:
        raise ValueError("IFU vendeur invalide. Vérifiez vos paramètres fiscaux.")
    
    # IFU du client (obligatoire)
    ifu_client = facture.get('ifu_client', '').strip()
    if not ifu_client or len(ifu_client) != 13:
        raise ValueError("IFU client invalide. Veuillez saisir un IFU valide de 13 caractères.")
    
    # Construction des articles
    items = []
    for ligne in lignes:
        items.append({
            "name": ligne.get('designation', 'Article'),
            "price": float(ligne.get('prix_unitaire', 0)),
            "quantity": float(ligne.get('quantite', 1)),
            "taxGroup": "B"  # 18% par défaut
        })
    
    # Construction des données
    invoice_data = {
        "ifu": ifu_vendeur,
        "type": "FV",  # Facture de vente
        "items": items,
        "client": {
            "ifu": ifu_client,
            "name": client.get('nom', 'Client'),
            "contact": client.get('telephone', ''),
            "address": client.get('adresse', '')
        }
    }
    
    # Ajouter le paiement si disponible
    payment_method = facture.get('payment_method', 'ESPECES')
    montant_total = sum(item['price'] * item['quantity'] for item in items)
    
    invoice_data["payment"] = [
        {
            "name": payment_method,
            "amount": montant_total
        }
    ]
    
    return invoice_data