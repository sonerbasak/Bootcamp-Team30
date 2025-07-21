# database/queries.py
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from functions.database.connections import get_db_connection
from functions.config import settings

# Kullanıcı sorguları
def get_user_by_username(username: str) -> Optional[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None

def create_user(username: str, email: str, password_hash: str) -> int:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                       (username, email, password_hash))
        conn.commit()
        return cursor.lastrowid # Yeni eklenen kullanıcının ID'si

# Quiz hata sorguları
def save_wrong_question_to_db(
    user_id: int, city: str, category: str, question_text: str,
    option_a: str, option_b: str, option_c: str, option_d: str,
    correct_answer_letter: str, user_answer_letter: str
) -> None:
    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO wrong_questions (
                user_id, city, category, question_text, option_a, option_b, option_c, option_d,
                correct_answer_letter, user_answer_letter
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, city, category, question_text, option_a, option_b, option_c, option_d,
                correct_answer_letter, user_answer_letter,
            ),
        )
        conn.commit()

def get_wrong_questions_from_db(user_id: int) -> List[Dict]:
    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wrong_questions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def delete_wrong_questions_from_db(user_id: int, question_ids: List[int]) -> int:
    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        deleted_count = 0
        for q_id in question_ids:
            cursor.execute("DELETE FROM wrong_questions WHERE id = ? AND user_id = ?", (q_id, user_id))
            deleted_count += cursor.rowcount
        conn.commit()
        return deleted_count

# Mesajlaşma sorguları (Yeni eklenecek)
def create_message(sender_id: int, receiver_id: int, content: str) -> int:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn: # Mesajları da users.db içinde tutalım veya ayrı bir db açabilirsiniz.
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender_id, receiver_id, content, timestamp) VALUES (?, ?, ?, ?)",
                       (sender_id, receiver_id, content, datetime.now()))
        conn.commit()
        return cursor.lastrowid

def get_messages_between_users(user1_id: int, user2_id: int) -> List[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (user1_id, user2_id, user2_id, user1_id))
        return [dict(row) for row in cursor.fetchall()]

def get_user_conversations(user_id: int) -> List[Dict]:
    """Kullanıcının mesajlaştığı tüm diğer kullanıcıları ve son mesajlarını getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # En son mesajı olan benzersiz sohbetleri bul
        cursor.execute("""
            SELECT
                CASE
                    WHEN T1.sender_id = ? THEN T2.username
                    ELSE T3.username
                END AS other_username,
                MAX(T1.timestamp) AS last_message_timestamp,
                T1.content AS last_message_content,
                CASE
                    WHEN T1.sender_id = ? THEN T1.receiver_id
                    ELSE T1.sender_id
                END AS other_user_id
            FROM messages AS T1
            LEFT JOIN users AS T2 ON T1.receiver_id = T2.id
            LEFT JOIN users AS T3 ON T1.sender_id = T3.id
            WHERE T1.sender_id = ? OR T1.receiver_id = ?
            GROUP BY other_username
            ORDER BY last_message_timestamp DESC
        """, (user_id, user_id, user_id, user_id))
        return [dict(row) for row in cursor.fetchall()]