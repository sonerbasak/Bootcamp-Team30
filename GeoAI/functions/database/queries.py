import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from functions.database.connections import get_db_connection
from functions.config import settings

# --- TABLO OLUŞTURMA FONKSİYONLARI ---
def create_initial_tables():
    """
    Uygulama başladığında gerekli tüm veritabanı tablolarını oluşturur.
    Tablolar zaten varsa tekrar oluşturmaz.
    """
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()

        # users tablosu
        # profile_picture_url sütunu eklendi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT 'Merhaba! GeoAI kullanıcısıyım.',
                profile_picture_url TEXT DEFAULT '/static/images/sample_user.png', -- YENİ SÜTUN EKLENDİ!
                total_quizzes_completed INTEGER DEFAULT 0,
                total_correct_answers INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                highest_score INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # messages tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # user_activities tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                activity_description TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # followers tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS followers (
                follower_id INTEGER NOT NULL,
                followed_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (follower_id, followed_id),
                FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (followed_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # wrong_questions tablosu (Quiz hata sorguları için)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                city TEXT NOT NULL,
                category TEXT NOT NULL,
                question_text TEXT NOT NULL,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_answer_letter TEXT NOT NULL,
                user_answer_letter TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

# --- KULLANICI SORGULARI ---
def get_user_by_username(username: str) -> Optional[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, username, email, password_hash, bio, profile_picture_url, -- profile_picture_url eklendi
                total_quizzes_completed, total_correct_answers, total_score, highest_score, created_at
            FROM users 
            WHERE username = ?
        """, (username,))
        user = cursor.fetchone()
        # Row objesini Dict'e dönüştürürken sütun adlarını kullan
        if user:
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "password_hash": user[3],
                "bio": user[4],
                "profile_picture_url": user[5], # Yeni eklenen alan
                "total_quizzes_completed": user[6],
                "total_correct_answers": user[7],
                "total_score": user[8],
                "highest_score": user[9],
                "created_at": user[10]
            }
        return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, username, email, bio, profile_picture_url, -- profile_picture_url eklendi
                total_quizzes_completed, total_correct_answers, total_score, highest_score, created_at
            FROM users 
            WHERE id = ?
        """, (user_id,))
        user = cursor.fetchone()
        # Row objesini Dict'e dönüştürürken sütun adlarını kullan
        if user:
            return {
                "id": user[0],
                "username": user[1],
                "email": user[2],
                "bio": user[3],
                "profile_picture_url": user[4], # Yeni eklenen alan
                "total_quizzes_completed": user[5],
                "total_correct_answers": user[6],
                "total_score": user[7],
                "highest_score": user[8],
                "created_at": user[9]
            }
        return None

def create_user(username: str, email: str, password_hash: str) -> int:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # profile_picture_url için varsayılan değer eklendi
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, bio, profile_picture_url, total_quizzes_completed, total_correct_answers, total_score, highest_score) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, "Merhaba! GeoAI kullanıcısıyım.", "/static/images/sample_user.png", 0, 0, 0, 0))
        conn.commit()
        return cursor.lastrowid # Yeni eklenen kullanıcının ID'si

# --- YENİ TAKİPÇİ VE PROFİL SORGULARI ---
def follow_user(follower_id: int, followed_id: int) -> bool:
    if follower_id == followed_id: # Kendini takip etmeyi engelle
        return False
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO followers (follower_id, followed_id) VALUES (?, ?)", (follower_id, followed_id))
            conn.commit()
            # Aktivite kaydı ekle
            follower_user_data = get_user_by_id(follower_id)
            followed_user_data = get_user_by_id(followed_id)
            if follower_user_data and followed_user_data:
                add_user_activity(follower_id, f"{follower_user_data['username']} kişisi {followed_user_data['username']} kişisini takip etmeye başladı.")
            return True
        except sqlite3.IntegrityError: # Zaten takip ediyorsa hata vermesini engelle
            return False # Zaten takip ediliyor

def unfollow_user(follower_id: int, followed_id: int) -> bool:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM followers WHERE follower_id = ? AND followed_id = ?", (follower_id, followed_id))
        conn.commit()
        if cursor.rowcount > 0:
            # Aktivite kaydı ekle
            follower_user_data = get_user_by_id(follower_id)
            followed_user_data = get_user_by_id(followed_id)
            if follower_user_data and followed_user_data:
                add_user_activity(follower_id, f"{follower_user_data['username']} kişisi {followed_user_data['username']} kişisini takibi bıraktı.")
            return True
        return False

def is_following(follower_id: int, followed_id: int) -> bool:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?", (follower_id, followed_id))
        return cursor.fetchone() is not None

def get_followers(user_id: int) -> List[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # profile_picture_url eklendi
        cursor.execute("""
            SELECT u.id, u.username, u.bio, u.profile_picture_url 
            FROM users u
            JOIN followers f ON u.id = f.follower_id
            WHERE f.followed_id = ?
            ORDER BY u.username ASC
        """, (user_id,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "username": row[1],
                "bio": row[2],
                "profile_picture_url": row[3] # Yeni eklenen alan
            } for row in rows
        ]

def get_following(user_id: int) -> List[Dict]:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # profile_picture_url eklendi
        cursor.execute("""
            SELECT u.id, u.username, u.bio, u.profile_picture_url 
            FROM users u
            JOIN followers f ON u.id = f.followed_id
            WHERE f.follower_id = ?
            ORDER BY u.username ASC
        """, (user_id,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "username": row[1],
                "bio": row[2],
                "profile_picture_url": row[3] # Yeni eklenen alan
            } for row in rows
        ]

def update_user_profile(user_id: int, bio: Optional[str] = None, profile_picture_url: Optional[str] = None) -> bool:
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if bio is not None:
            updates.append("bio = ?")
            params.append(bio)
        
        if profile_picture_url is not None: # profile_picture_url'yi güncelle
            updates.append("profile_picture_url = ?")
            params.append(profile_picture_url)
        
        if not updates: # Güncellenecek bir şey yoksa
            return False
            
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0: # Güncelleme başarılıysa aktivite ekle
            add_user_activity(user_id, "Profilini güncelledi.")
            return True
        return False

# --- QUIZ HATA SORGULARI ---
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
        # Buradaki select * yerine sütunları açıkça belirtmek daha iyi olabilir
        cursor.execute("SELECT * FROM wrong_questions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        rows = cursor.fetchall()
        # Sütun adlarını elde etmek için cursor.description kullan
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows] # dict(row) yerine zip kullan

def delete_wrong_questions_from_db(user_id: int, question_ids: List[int]) -> int:
    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        deleted_count = 0
        for q_id in question_ids:
            cursor.execute("DELETE FROM wrong_questions WHERE id = ? AND user_id = ?", (q_id, user_id))
            deleted_count += cursor.rowcount
        conn.commit()
        return deleted_count

# --- MESAJLAŞMA SORGULARI ---
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
            SELECT id, sender_id, receiver_id, content, timestamp FROM messages
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (user1_id, user2_id, user2_id, user1_id))
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

def get_user_conversations(user_id: int) -> List[Dict]:
    """Kullanıcının mesajlaştığı tüm diğer kullanıcıları ve son mesajlarını getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                users_other.id AS other_user_id,
                users_other.username AS other_username,
                users_other.profile_picture_url AS other_user_profile_picture_url,
                m_latest.content AS last_message_content,
                m_latest.timestamp AS last_message_timestamp
            FROM messages AS m_latest
            INNER JOIN (
                SELECT
                    MAX(id) AS max_message_id,
                    CASE
                        WHEN sender_id = ? THEN receiver_id
                        ELSE sender_id
                    END AS interlocutor_id
                FROM messages
                WHERE sender_id = ? OR receiver_id = ?
                GROUP BY interlocutor_id
            ) AS latest_messages
            ON m_latest.id = latest_messages.max_message_id
            INNER JOIN users AS users_other
                ON users_other.id = latest_messages.interlocutor_id
            ORDER BY last_message_timestamp DESC
        """, (user_id, user_id, user_id)) # Pass user_id three times for the subquery's WHERE clause
        rows = cursor.fetchall()
        
        # Since conn.row_factory = sqlite3.Row is set, rows are already like dictionaries.
        # We can directly convert them to dict for consistency if needed, but often not strictly necessary.
        return [dict(row) for row in rows] # Convert Row object to dictionary

# --- PROFİL İSTATİSTİK VE AKTİVİTE SORGULARI ---
def get_user_activities(user_id: int) -> List[Dict]:
    """Belirli bir kullanıcının son aktivitelerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT activity_description, timestamp FROM user_activities WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10', # Son 10 aktivite
            (user_id,)
        )
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return [dict(zip(columns, row)) for row in rows]

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
        # profile_picture_url eklendi
        cursor.execute("""
            SELECT 
                id, username, bio, profile_picture_url, total_quizzes_completed, total_score
            FROM users 
            WHERE LOWER(username) LIKE ?
            ORDER BY username ASC
        """, (f"%{search_term.lower()}%",))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "username": row[1],
                "bio": row[2],
                "profile_picture_url": row[3], # Yeni eklenen alan
                "total_quizzes_completed": row[4],
                "total_score": row[5]
            } for row in rows
        ]