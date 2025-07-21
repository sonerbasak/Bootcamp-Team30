# functions/database/queries.py
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from functions.database.connections import get_db_connection
from functions.config import settings

# Kullanıcı sorguları
def get_user_by_username(username: str) -> Optional[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, username, email, password_hash, bio, 
                total_quizzes_completed, total_correct_answers, total_score, highest_score, created_at
            FROM users 
            WHERE username = ?
        """, (username,))
        user = cursor.fetchone()
        return dict(user) if user else None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, username, email, bio, 
                total_quizzes_completed, total_correct_answers, total_score, highest_score, created_at
            FROM users 
            WHERE id = ?
        """, (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None

def create_user(username: str, email: str, password_hash: str) -> int:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, bio, total_quizzes_completed, total_correct_answers, total_score, highest_score) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, "Merhaba! GeoAI kullanıcısıyım.", 0, 0, 0, 0)) # Varsayılan değerlerle ekleme
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

# Mesajlaşma sorguları
def create_message(sender_id: int, receiver_id: int, content: str) -> int:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
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
        cursor.execute("""
            SELECT
                users_other.username AS other_username,
                users_other.id AS other_user_id,
                MAX(m.timestamp) AS last_message_timestamp,
                (SELECT content FROM messages WHERE id = MAX(m.id)) AS last_message_content
            FROM messages AS m
            INNER JOIN users AS users_other
                ON (m.sender_id = ? AND users_other.id = m.receiver_id)
                OR (m.receiver_id = ? AND users_other.id = m.sender_id)
            WHERE m.sender_id = ? OR m.receiver_id = ?
            GROUP BY other_username, other_user_id
            ORDER BY last_message_timestamp DESC
        """, (user_id, user_id, user_id, user_id))
        return [dict(row) for row in cursor.fetchall()]


# Profil istatistik ve aktivite sorguları

def get_user_activities(user_id: int) -> List[Dict]:
    """Belirli bir kullanıcının son aktivitelerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT activity_description, timestamp FROM user_activities WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10', # Son 10 aktivite
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def add_user_activity(user_id: int, description: str) -> None:
    """Kullanıcı için yeni bir aktivite kaydeder."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO user_activities (user_id, activity_description) VALUES (?, ?)',
            (user_id, description)
        )
        conn.commit()

def update_user_quiz_stats(user_id: int, score_earned: int, correct_answers_count: int) -> None:
    """Kullanıcının quiz istatistiklerini günceller."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET
                total_quizzes_completed = total_quizzes_completed + 1,
                total_correct_answers = total_correct_answers + ?,
                total_score = total_score + ?,
                highest_score = MAX(highest_score, ?)
            WHERE id = ?
            """,
            (correct_answers_count, score_earned, score_earned, user_id)
        )
        conn.commit()
    # Quiz istatistikleri güncellendiğinde bir aktivite kaydı ekle
    add_user_activity(user_id, f"Quiz'i tamamladı ve {score_earned} puan kazandı.")

def search_users_by_username(search_term: str) -> List[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # Bu kısım zaten doğru: Hem veritabanındaki kullanıcı adını hem de arama terimini küçük harfe çevirip karşılaştırıyor.
        cursor.execute("""
            SELECT 
                id, username, bio, total_quizzes_completed, total_score
            FROM users 
            WHERE LOWER(username) LIKE ?
            ORDER BY username ASC
        """, (f"%{search_term.lower()}%",)) # Arama terimini küçük harfe çevir
        rows = cursor.fetchall()
        return [dict(row) for row in rows]