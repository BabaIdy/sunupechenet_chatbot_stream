"""
Configuration PostgreSQL pour stocker l'historique des conversations
Fichier: database.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class ChatHistoryDB:
    def __init__(self):
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'sunupechenet'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'your_password')
        }

    def get_connection(self):
        """Établit une connexion à la base de données"""
        return psycopg2.connect(**self.conn_params)

    def init_database(self):
        """Crée les tables nécessaires si elles n'existent pas"""
        create_tables_sql = """
        -- Table pour stocker les sessions de chat
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id SERIAL PRIMARY KEY,
            user_identifiant VARCHAR(100) NOT NULL,
            user_name VARCHAR(255),
            user_role VARCHAR(50),
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );

        -- Table pour stocker les messages
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
            user_identifiant VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL, -- 'user' ou 'assistant'
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB -- Pour stocker des infos supplémentaires
        );

        -- Index pour améliorer les performances
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_identifiant);
        CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_user ON chat_messages(user_identifiant);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON chat_messages(created_at);
        """

        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(create_tables_sql)
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Tables créées avec succès")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la création des tables: {e}")
            return False

    def create_session(self, user_identifiant, user_name=None, user_role=None):
        """Crée une nouvelle session de chat pour un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO chat_sessions (user_identifiant, user_name, user_role)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (user_identifiant, user_name, user_role))

            session_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()

            return session_id
        except Exception as e:
            print(f"Erreur lors de la création de la session: {e}")
            return None

    def get_active_session(self, user_identifiant):
        """Récupère la session active d'un utilisateur ou en crée une nouvelle"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Chercher une session active récente (moins de 24h)
            cursor.execute("""
                SELECT id FROM chat_sessions
                WHERE user_identifiant = %s
                AND is_active = TRUE
                AND last_activity > NOW() - INTERVAL '24 hours'
                ORDER BY last_activity DESC
                LIMIT 1
            """, (user_identifiant,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return result['id']
            else:
                # Créer une nouvelle session
                return self.create_session(user_identifiant)
        except Exception as e:
            print(f"Erreur lors de la récupération de la session: {e}")
            return None

    def save_message(self, session_id, user_identifiant, role, content, metadata=None):
        """Enregistre un message dans l'historique"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO chat_messages
                (session_id, user_identifiant, role, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (session_id, user_identifiant, role, content,
                  psycopg2.extras.Json(metadata) if metadata else None))

            # Mettre à jour la dernière activité de la session
            cursor.execute("""
                UPDATE chat_sessions
                SET last_activity = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (session_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Erreur lors de l'enregistrement du message: {e}")
            return False

    def get_user_history(self, user_identifiant, limit=50, session_id=None):
        """Récupère l'historique des conversations d'un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            if session_id:
                # Récupérer l'historique d'une session spécifique
                query = """
                    SELECT role, content, created_at, metadata
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                """
                cursor.execute(query, (session_id, limit))
            else:
                # Récupérer l'historique général de l'utilisateur
                query = """
                    SELECT cm.role, cm.content, cm.created_at, cm.metadata,
                           cs.started_at as session_start
                    FROM chat_messages cm
                    JOIN chat_sessions cs ON cm.session_id = cs.id
                    WHERE cm.user_identifiant = %s
                    ORDER BY cm.created_at DESC
                    LIMIT %s
                """
                cursor.execute(query, (user_identifiant, limit))

            messages = cursor.fetchall()
            cursor.close()
            conn.close()

            return messages
        except Exception as e:
            print(f"Erreur lors de la récupération de l'historique: {e}")
            return []

    def get_user_sessions(self, user_identifiant, limit=10):
        """Récupère la liste des sessions d'un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT
                    cs.id,
                    cs.started_at,
                    cs.last_activity,
                    cs.is_active,
                    COUNT(cm.id) as message_count
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cs.id = cm.session_id
                WHERE cs.user_identifiant = %s
                GROUP BY cs.id
                ORDER BY cs.last_activity DESC
                LIMIT %s
            """, (user_identifiant, limit))

            sessions = cursor.fetchall()
            cursor.close()
            conn.close()

            return sessions
        except Exception as e:
            print(f"Erreur lors de la récupération des sessions: {e}")
            return []

    def format_history_for_ai(self, user_identifiant, max_messages=20):
        """Formate l'historique pour le contexte de l'IA"""
        messages = self.get_user_history(user_identifiant, limit=max_messages)

        if not messages:
            return ""

        context = "\n=== HISTORIQUE DES CONVERSATIONS PRÉCÉDENTES ===\n\n"
        context += f"Utilisateur: {user_identifiant}\n"
        context += f"Nombre de messages récents: {len(messages)}\n\n"

        for msg in reversed(messages):  # Inverser pour avoir l'ordre chronologique
            timestamp = msg['created_at'].strftime("%d/%m/%Y %H:%M")
            role_label = "Utilisateur" if msg['role'] == 'user' else "Assistant"
            context += f"[{timestamp}] {role_label}: {msg['content']}\n\n"

        context += "=== FIN DE L'HISTORIQUE ===\n\n"
        return context

    def close_session(self, session_id):
        """Marque une session comme inactive"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE chat_sessions
                SET is_active = FALSE
                WHERE id = %s
            """, (session_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Erreur lors de la fermeture de la session: {e}")
            return False

    def get_user_stats(self, user_identifiant):
        """Récupère les statistiques d'utilisation d'un utilisateur"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT
                    COUNT(DISTINCT cs.id) as total_sessions,
                    COUNT(cm.id) as total_messages,
                    MIN(cs.started_at) as first_session,
                    MAX(cs.last_activity) as last_activity
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cs.id = cm.session_id
                WHERE cs.user_identifiant = %s
            """, (user_identifiant,))

            stats = cursor.fetchone()
            cursor.close()
            conn.close()

            return stats
        except Exception as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            return None