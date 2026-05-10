import psycopg2
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host='dpg-d8097lho3t8c73di9j80-a.virginia-postgres.render.com',
                port=5432,
                database='btp_devis',
                user='btp_user',
                password='6Rezh4lvx9HyeAvUKEDZwBtyF9s8wUTC'
            )
            self.create_tables()
            print("✅ Connecté à PostgreSQL (données persistantes)")
            return True
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False
    
    def create_tables(self):
        cursor = self.connection.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utilisateur (
                id_user SERIAL PRIMARY KEY,
                nom TEXT,
                email TEXT UNIQUE,
                mot_de_passe TEXT,
                mot_de_passe_hash TEXT,
                entreprise TEXT,
                telephone TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS client (
                id_client SERIAL PRIMARY KEY,
                nom TEXT,
                telephone TEXT,
                email TEXT,
                adresse TEXT,
                id_user INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projet (
                id_projet SERIAL PRIMARY KEY,
                nom_projet TEXT,
                description TEXT,
                localisation TEXT,
                id_user INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devis (
                id_devis SERIAL PRIMARY KEY,
                date_creation TIMESTAMP,
                total REAL,
                statut TEXT DEFAULT 'brouillon',
                id_client INTEGER,
                id_user INTEGER,
                id_projet INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ligne_devis (
                id_ligne SERIAL PRIMARY KEY,
                designation TEXT,
                quantite INTEGER,
                prix_unitaire REAL,
                total_ligne REAL,
                id_devis INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS facture (
                id_facture SERIAL PRIMARY KEY,
                date_facture TIMESTAMP,
                montant REAL,
                statut TEXT DEFAULT 'non payée',
                id_devis INTEGER UNIQUE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS abonnements (
                id_abonnement SERIAL PRIMARY KEY,
                id_user INTEGER NOT NULL,
                statut TEXT DEFAULT 'actif',
                date_debut TIMESTAMP,
                date_fin TIMESTAMP,
                type_abonnement TEXT DEFAULT 'mensuel'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id_setting SERIAL PRIMARY KEY,
                id_user INTEGER NOT NULL,
                company_name TEXT,
                company_logo TEXT,
                company_email TEXT,
                company_phone TEXT,
                company_address TEXT,
                primary_color TEXT DEFAULT '#1E3A8A',
                secondary_color TEXT DEFAULT '#7C3AED',
                accent_color TEXT DEFAULT '#06B6D4',
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id_notification SERIAL PRIMARY KEY,
                id_user INTEGER NOT NULL,
                message TEXT,
                type TEXT DEFAULT 'info',
                est_lue INTEGER DEFAULT 0,
                date_creation TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS paiements (
                id_paiement SERIAL PRIMARY KEY,
                id_user INTEGER NOT NULL,
                montant REAL,
                date_paiement TIMESTAMP,
                reference_paiement TEXT,
                methode TEXT,
                statut TEXT DEFAULT 'valide'
            )
        ''')
        
        self.connection.commit()
        
        # Créer l'admin UNIQUEMENT si la table est vide
        cursor.execute("SELECT COUNT(*) FROM utilisateur")
        count = cursor.fetchone()[0]
        
        if count == 0:
            import bcrypt
            password = "000000"
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            cursor.execute("""
                INSERT INTO utilisateur (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
                VALUES (1, 'Admin BTP', 'bylgaitb@gmail.com', %s, %s, 'BTP Pro', '+229 90000000')
            """, (password, hashed.decode()))
            
            date_fin = datetime.now() + timedelta(days=365*100)
            cursor.execute("""
                INSERT INTO abonnements (id_user, statut, date_debut, date_fin, type_abonnement)
                VALUES (1, 'actif', %s, %s, 'illimite')
            """, (datetime.now(), date_fin))
            
            cursor.execute("""
                INSERT INTO settings (id_user, company_name, created_at, updated_at)
                VALUES (1, 'BTP Devis Pro', %s, %s)
            """, (datetime.now(), datetime.now()))
            
            self.connection.commit()
            print("✅ Admin créé (bylgaitb@gmail.com / 000000)")
        
        print("✅ Tables PostgreSQL créées/vérifiées")
    
    def execute_query(self, query, params=None):
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()
            return cursor
        except Exception as e:
            print(f"❌ Erreur: {e}")
            self.connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
    
    def fetch_all(self, query, params=None):
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            return [dict(zip(colnames, row)) for row in rows]
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def fetch_one(self, query, params=None):
        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            if row:
                colnames = [desc[0] for desc in cursor.description]
                return dict(zip(colnames, row))
            return None
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return None
        finally:
            if cursor:
                cursor.close()