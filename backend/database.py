import pymysql
from pymysql import Error
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        try:
            print(" Connexion à MySQL...")
            self.connection = pymysql.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'btp_devis'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', ''),
                port=int(os.getenv('DB_PORT', 3306)),
                cursorclass=pymysql.cursors.DictCursor
            )
            print("Connecté avec succès!")
            return True
        except Error as e:
            print(f" Erreur: {e}")
            self.connection = None
            return False
    
    def get_connection(self):
        if self.connection is None:
            self.connect()
        return self.connection
    
    def execute_query(self, query, params=None):
        conn = self.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Error as e:
            print(f" Erreur: {e}")
            conn.rollback()
            return None
    
    def fetch_all(self, query, params=None):
        conn = self.get_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f" Erreur: {e}")
            return []
    
    def fetch_one(self, query, params=None):
        conn = self.get_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        except Error as e:
            print(f" Erreur: {e}")
            return None