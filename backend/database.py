import sqlite3
import os
from datetime import datetime, timedelta
import threading
import platform

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # Chemin de la base de données (compatible Windows et Linux)
        if platform.system() == 'Windows':
            app_data = os.path.join(os.environ['APPDATA'], 'BTPDevisPro')
        else:
            app_data = os.path.join(os.path.expanduser('~'), '.btpdevispro')
        
        os.makedirs(app_data, exist_ok=True)
        self.db_path = os.path.join(app_data, 'btp_devis.db')
        self.local = threading.local()
        self.create_tables()
        print(f"✅ Connecté à SQLite: {self.db_path}")
    
    def get_connection(self):
        if not hasattr(self.local, 'connection') or self.local.connection is None:
            self.local.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection
    
    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Table UTILISATEUR
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS UTILISATEUR (
                id_user INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT,
                email TEXT UNIQUE,
                mot_de_passe TEXT,
                mot_de_passe_hash TEXT,
                entreprise TEXT,
                telephone TEXT
            )
        ''')
        
        # Table CLIENT
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS CLIENT (
                id_client INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT,
                telephone TEXT,
                email TEXT,
                adresse TEXT
            )
        ''')
        
        # Table PROJET
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS PROJET (
                id_projet INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_projet TEXT,
                description TEXT,
                localisation TEXT
            )
        ''')
        
        # Table DEVIS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS DEVIS (
                id_devis INTEGER PRIMARY KEY AUTOINCREMENT,
                date_creation DATETIME,
                total REAL,
                statut TEXT DEFAULT 'brouillon',
                id_client INTEGER,
                id_user INTEGER,
                id_projet INTEGER
            )
        ''')
        
        # Table LIGNE_DEVIS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS LIGNE_DEVIS (
                id_ligne INTEGER PRIMARY KEY AUTOINCREMENT,
                designation TEXT,
                quantite INTEGER,
                prix_unitaire REAL,
                total_ligne REAL,
                id_devis INTEGER
            )
        ''')
        
        # Table FACTURE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS FACTURE (
                id_facture INTEGER PRIMARY KEY AUTOINCREMENT,
                date_facture DATETIME,
                montant REAL,
                statut TEXT DEFAULT 'non payée',
                id_devis INTEGER UNIQUE
            )
        ''')
        
        # Table ABONNEMENTS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ABONNEMENTS (
                id_abonnement INTEGER PRIMARY KEY AUTOINCREMENT,
                id_user INTEGER NOT NULL,
                statut TEXT DEFAULT 'actif',
                date_debut DATETIME,
                date_fin DATETIME,
                type_abonnement TEXT DEFAULT 'mensuel'
            )
        ''')
        
        # Table SETTINGS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS SETTINGS (
                id_setting INTEGER PRIMARY KEY AUTOINCREMENT,
                id_user INTEGER NOT NULL,
                company_name TEXT,
                company_logo TEXT,
                company_email TEXT,
                company_phone TEXT,
                company_address TEXT,
                primary_color TEXT DEFAULT '#1E3A8A',
                secondary_color TEXT DEFAULT '#7C3AED',
                accent_color TEXT DEFAULT '#06B6D4',
                created_at DATETIME,
                updated_at DATETIME
            )
        ''')
        
        # Table NOTIFICATIONS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id_notification INTEGER PRIMARY KEY AUTOINCREMENT,
                id_user INTEGER NOT NULL,
                message TEXT,
                type TEXT DEFAULT 'info',
                est_lue INTEGER DEFAULT 0,
                date_creation DATETIME
            )
        ''')
        
        # Table PAIEMENTS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS paiements (
                id_paiement INTEGER PRIMARY KEY AUTOINCREMENT,
                id_user INTEGER NOT NULL,
                montant REAL,
                date_paiement DATETIME,
                reference_paiement TEXT,
                methode TEXT,
                statut TEXT DEFAULT 'valide'
            )
        ''')
        
        conn.commit()
        
        # === CRÉATION DE L'ADMIN ===
        import bcrypt
        admin = self.fetch_one("SELECT * FROM UTILISATEUR WHERE email = 'bylgaitb@gmail.com'")
        if not admin:
            hashed = bcrypt.hashpw(b'000000', bcrypt.gensalt())
            cursor.execute('''
                INSERT INTO UTILISATEUR (id_user, nom, email, mot_de_passe, mot_de_passe_hash, entreprise, telephone)
                VALUES (1, 'Admin BTP', 'bylgaitb@gmail.com', '000000', ?, 'BTP Pro', '+229 90000000')
            ''', (hashed,))
            
            # Ajouter l'abonnement illimité pour admin (100 ans)
            date_fin_100ans = datetime.now() + timedelta(days=365*100)
            cursor.execute('''
                INSERT INTO ABONNEMENTS (id_user, statut, date_debut, date_fin, type_abonnement)
                VALUES (1, 'actif', ?, ?, 'illimite')
            ''', (datetime.now(), date_fin_100ans))
            
            # Ajouter les settings par défaut
            cursor.execute('''
                INSERT INTO SETTINGS (id_user, company_name, created_at, updated_at)
                VALUES (1, 'BTP Devis Pro', ?, ?)
            ''', (datetime.now(), datetime.now()))
            
            conn.commit()
            print("✅ Admin créé (bylgaitb@gmail.com / 000000)")
    
    def execute_query(self, query, params=None):
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
            return cursor
        except Exception as e:
            print(f"❌ Erreur: {e}")
            conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
    
    def fetch_all(self, query, params=None):
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def fetch_one(self, query, params=None):
        conn = self.get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return None
        finally:
            if cursor:
                cursor.close()