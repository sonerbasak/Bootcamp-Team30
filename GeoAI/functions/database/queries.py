# functions/database/queries.py

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

        # users tablosu - Artık genel quiz istatistik sütunları YOK
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT 'Merhaba! GeoAI kullanıcısıyım.',
                profile_picture_url TEXT DEFAULT '/static/images/sample_user.png',
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

    # QUIZ_STATS_DATABASE_FILE İÇİN TABLOLAR
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # quiz_summary tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quiz_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                quiz_type TEXT NOT NULL,
                quiz_name TEXT,
                total_questions INTEGER NOT NULL,
                correct_answers INTEGER NOT NULL,
                score INTEGER NOT NULL,
                completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # category_stats tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category_name TEXT NOT NULL,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category_name),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()


# --- KULLANICI SORGULARI ---
def get_user_by_username(username: str) -> Optional[Dict]:
    """Kullanıcı adıyla kullanıcı bilgilerini ve genel quiz istatistiklerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, password_hash, bio, profile_picture_url, created_at
            FROM users
            WHERE username = ?
        """, (username,))
        user_row = cursor.fetchone()

    if user_row:
        user_data = {
            "id": user_row["id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "password_hash": user_row["password_hash"],
            "bio": user_row["bio"],
            "profile_picture_url": user_row["profile_picture_url"],
            "created_at": user_row["created_at"]
        }
        
        # Kullanıcının genel quiz istatistiklerini al ve ekle
        overall_stats = get_user_overall_quiz_stats(user_data["id"])
        user_data.update(overall_stats)
        
        return user_data
    return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Kullanıcı ID'siyle kullanıcı bilgilerini ve genel quiz istatistiklerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, bio, profile_picture_url, created_at
            FROM users
            WHERE id = ?
        """, (user_id,))
        user_row = cursor.fetchone()

    if user_row:
        user_data = {
            "id": user_row["id"],
            "username": user_row["username"],
            "email": user_row["email"],
            "bio": user_row["bio"],
            "profile_picture_url": user_row["profile_picture_url"],
            "created_at": user_row["created_at"]
        }

        # Kullanıcının genel quiz istatistiklerini al ve ekle
        overall_stats = get_user_overall_quiz_stats(user_data["id"])
        user_data.update(overall_stats)

        return user_data
    return None

def create_user(username: str, email: str, password_hash: str) -> int:
    """Yeni bir kullanıcı oluşturur."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, bio, profile_picture_url)
            VALUES (?, ?, ?, ?, ?)
        """, (username, email, password_hash, "Merhaba! GeoAI kullanıcısıyım.", "/static/images/sample_user.png"))
        conn.commit()
        return cursor.lastrowid

# --- TAKİPÇİ SORGULARI ---
def follow_user(follower_id: int, followed_id: int) -> bool:
    """Bir kullanıcının başka bir kullanıcıyı takip etmesini sağlar."""
    if follower_id == followed_id:
        return False
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO followers (follower_id, followed_id) VALUES (?, ?)", (follower_id, followed_id))
            conn.commit()
            # Takip aktivitesi ekle
            follower_user_data = get_user_by_id(follower_id)
            followed_user_data = get_user_by_id(followed_id)
            if follower_user_data and followed_user_data:
                add_user_activity(follower_id, f"{follower_user_data['username']} kişisi {followed_user_data['username']} kişisini takip etmeye başladı.")
            return True
        except sqlite3.IntegrityError:
            return False

def unfollow_user(follower_id: int, followed_id: int) -> bool:
    """Bir kullanıcının başka bir kullanıcıyı takibi bırakmasını sağlar."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM followers WHERE follower_id = ? AND followed_id = ?", (follower_id, followed_id))
        conn.commit()
        if cursor.rowcount > 0:
            # Takip bırakma aktivitesi ekle
            follower_user_data = get_user_by_id(follower_id)
            followed_user_data = get_user_by_id(followed_id)
            if follower_user_data and followed_user_data:
                add_user_activity(follower_id, f"{follower_user_data['username']} kişisi {followed_user_data['username']} kişisini takibi bıraktı.")
            return True
        return False

def is_following(follower_id: int, followed_id: int) -> bool:
    """Bir kullanıcının diğerini takip edip etmediğini kontrol eder."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?", (follower_id, followed_id))
        return cursor.fetchone() is not None

def get_followers(user_id: int) -> List[Dict]:
    """Belirli bir kullanıcının takipçilerini döndürür."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.bio, u.profile_picture_url
            FROM users u
            JOIN followers f ON u.id = f.follower_id
            WHERE f.followed_id = ?
            ORDER BY u.username ASC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # sqlite3.Row objelerini dict'e çevir

def get_following(user_id: int) -> List[Dict]:
    """Belirli bir kullanıcının takip ettiklerini döndürür."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.bio, u.profile_picture_url
            FROM users u
            JOIN followers f ON u.id = f.followed_id
            WHERE f.follower_id = ?
            ORDER BY u.username ASC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # sqlite3.Row objelerini dict'e çevir

def update_user_profile(user_id: int, bio: Optional[str] = None, profile_picture_url: Optional[str] = None) -> bool:
    """Kullanıcının biyografisini ve/veya profil fotoğrafını günceller."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        
        if bio is not None:
            updates.append("bio = ?")
            params.append(bio)
        
        if profile_picture_url is not None:
            updates.append("profile_picture_url = ?")
            params.append(profile_picture_url)
        
        if not updates:
            return False
            
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0:
            add_user_activity(user_id, "Profilini güncelledi.")
            return True
        return False

# --- QUIZ HATA SORGULARI ---
def save_wrong_question_to_db(
    user_id: int, city: str, category: str, question_text: str,
    option_a: str, option_b: str, option_c: str, option_d: str,
    correct_answer_letter: str, user_answer_letter: str
) -> None:
    """Yanlış cevaplanan bir soruyu veritabanına kaydeder."""
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
    """Bir kullanıcının yanlış cevapladığı soruları getirir."""
    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wrong_questions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # sqlite3.Row objelerini dict'e çevir

def delete_wrong_questions_from_db(user_id: int, question_ids: List[int]) -> int:
    """Belirli yanlış soruları kullanıcının listesinden siler."""
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
    """Yeni bir mesaj oluşturur."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender_id, receiver_id, content, timestamp) VALUES (?, ?, ?, ?)",
                       (sender_id, receiver_id, content, datetime.now()))
        conn.commit()
        return cursor.lastrowid

def get_messages_between_users(user1_id: int, user2_id: int) -> List[Dict]:
    """İki kullanıcı arasındaki mesajlaşma geçmişini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sender_id, receiver_id, content, timestamp FROM messages
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp ASC
        """, (user1_id, user2_id, user2_id, user1_id))
        rows = cursor.fetchall()
        return [dict(row) for row in rows] # sqlite3.Row objelerini dict'e çevir

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
        """, (user_id, user_id, user_id))
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]

# --- PROFİL AKTİVİTE SORGULARI ---
def get_user_activities(user_id: int) -> List[Dict]:
    """Belirli bir kullanıcının son aktivitelerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT activity_description, timestamp FROM user_activities WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10',
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def add_user_activity(user_id: int, description: str) -> None:
    """Kullanıcı için yeni bir aktivite kaydeder."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO user_activities (user_id, activity_description) VALUES (?, ?)',
            (user_id, description)
        )
        conn.commit()

def search_users_by_username(search_term: str) -> List[Dict]:
    """Kullanıcı adlarına göre arama yapar ve genel quiz istatistiklerini ekler."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, username, bio, profile_picture_url
            FROM users
            WHERE LOWER(username) LIKE ?
            ORDER BY username ASC
        """, (f"%{search_term.lower()}%",))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            user_data = {
                "id": row["id"],
                "username": row["username"],
                "bio": row["bio"],
                "profile_picture_url": row["profile_picture_url"]
            }
            # Arama sonuçlarına da genel quiz istatistiklerini ekleyelim
            overall_stats = get_user_overall_quiz_stats(user_data["id"])
            user_data.update(overall_stats)
            results.append(user_data)
        return results

# --- QUIZ İSTATİSTİK SORGULARI (quiz_stats.db ile çalışır) ---

def add_quiz_summary(user_id: int, quiz_type: str, quiz_name: str, total_questions: int, correct_answers: int, score: int) -> None:
    """Bir tamamlanmış quiz'in özetini kaydeder ve kullanıcı aktivitesi ekler."""
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quiz_summary (user_id, quiz_type, quiz_name, total_questions, correct_answers, score, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, quiz_type, quiz_name, total_questions, correct_answers, score)
        )
        conn.commit()
    # Quiz tamamlandığında bir aktivite ekleyelim
    add_user_activity(user_id, f"'{quiz_name}' ({quiz_type}) quizini tamamladı ve {score} puan kazandı.")


def update_category_stats(user_id: int, category_name: str, is_correct: bool) -> None:
    """Belirli bir kategori için doğru/yanlış cevap sayılarını günceller."""
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT correct_count, wrong_count FROM category_stats WHERE user_id = ? AND category_name = ?",
            (user_id, category_name)
        )
        existing_stats = cursor.fetchone()

        if existing_stats:
            if is_correct:
                cursor.execute(
                    """
                    UPDATE category_stats
                    SET correct_count = correct_count + 1, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND category_name = ?
                    """,
                    (user_id, category_name)
                )
            else:
                cursor.execute(
                    """
                    UPDATE category_stats
                    SET wrong_count = wrong_count + 1, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND category_name = ?
                    """,
                    (user_id, category_name)
                )
        else:
            if is_correct:
                cursor.execute(
                    """
                    INSERT INTO category_stats (user_id, category_name, correct_count, wrong_count, last_updated)
                    VALUES (?, ?, 1, 0, CURRENT_TIMESTAMP)
                    """,
                    (user_id, category_name)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO category_stats (user_id, category_name, correct_count, wrong_count, last_updated)
                    VALUES (?, ?, 0, 1, CURRENT_TIMESTAMP)
                    """,
                    (user_id, category_name)
                )
        conn.commit()

def get_user_quiz_summaries(user_id: int, limit: int = 10) -> List[Dict]:
    """Bir kullanıcının tamamladığı son quiz özetlerini getirir."""
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, quiz_type, quiz_name, total_questions, correct_answers, score, completed_at
            FROM quiz_summary
            WHERE user_id = ?
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_user_category_stats(user_id: int) -> List[Dict]:
    """Bir kullanıcının kategori bazındaki doğru/yanlış cevap istatistiklerini getirir."""
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT category_name, correct_count, wrong_count
            FROM category_stats
            WHERE user_id = ?
            ORDER BY category_name ASC
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_user_overall_quiz_stats(user_id: int) -> Dict[str, int]:
    """Bir kullanıcının tüm quizlerdeki genel istatistiklerini hesaplar ve döndürür."""
    # FIX: Use 'with' statement to properly get the connection object
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(id) FROM quiz_summary WHERE user_id = ?",
            (user_id,)
        )
        total_quizzes_completed = cursor.fetchone()[0]

        cursor.execute(
            "SELECT SUM(correct_answers) FROM quiz_summary WHERE user_id = ?",
            (user_id,)
        )
        total_correct_answers = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT SUM(score) FROM quiz_summary WHERE user_id = ?",
            (user_id,)
        )
        total_score = cursor.fetchone()[0] or 0

        cursor.execute(
            "SELECT MAX(score) FROM quiz_summary WHERE user_id = ?",
            (user_id,)
        )
        highest_score = cursor.fetchone()[0] or 0

    # No need for conn.close() here, the 'with' statement handles it automatically
    
    return {
        "total_quizzes_completed": total_quizzes_completed,
        "total_correct_answers": total_correct_answers,
        "total_score": total_score,
        "highest_score": highest_score
    }