import os
from dotenv import load_dotenv
from emcf import EMCFClient

# Charger les variables d'environnement
load_dotenv()

print("=" * 50)
print("🔍 TEST DE CONNEXION À L'API e-MCF")
print("=" * 50)

# 🔥 Diagnostic JWT
jwt = os.environ.get('EMCEF_JWT_TOKEN', '')
print(f"\n🔑 JWT chargé: {'OUI ✅' if jwt else 'NON ❌'}")
print(f"📏 Longueur: {len(jwt)} caractères")
print(f"📝 Début: {jwt[:30]}..." if jwt else "❌ JWT MANQUANT")

# Nettoyer le JWT (enlever espaces, retours à la ligne)
jwt_clean = jwt.strip()
if jwt_clean != jwt:
    print("⚠️ JWT nettoyé (espaces enlevés)")
    os.environ['EMCEF_JWT_TOKEN'] = jwt_clean

print("\n" + "=" * 50)
print("📡 CONNEXION À L'API...")
print("=" * 50)

client = EMCFClient()

# 1. Tester le statut
print("\n📊 Test /status...")
status = client.get_status()
if status:
    print(f"✅ Statut reçu: {status}")
else:
    print("❌ Échec du statut")

# 2. Tester les taux TVA
print("\n📊 Test /taxGroups...")
tax_groups = client.get_tax_groups()
if tax_groups:
    print(f"✅ Tax Groups reçus: {tax_groups}")
else:
    print("❌ Échec des taxGroups")

# 3. Tester les types de factures
print("\n📊 Test /invoiceTypes...")
invoice_types = client.get_invoice_types()
if invoice_types:
    print(f"✅ Invoice Types reçus: {invoice_types}")
else:
    print("❌ Échec des invoiceTypes")

# 4. Tester les modes de paiement
print("\n📊 Test /paymentTypes...")
payment_types = client.get_payment_types()
if payment_types:
    print(f"✅ Payment Types reçus: {payment_types}")
else:
    print("❌ Échec des paymentTypes")

print("\n" + "=" * 50)
print("🏁 TEST TERMINÉ")
print("=" * 50)