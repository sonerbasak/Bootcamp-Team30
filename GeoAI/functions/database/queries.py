import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from functions.database.connections import get_db_connection 
from functions.config import settings
import json
import logging
from functions.services.badge_service import badge_service

# --- KULLANICI SORGULARI ---
def get_user_by_username(username: str) -> Optional[Dict]:
    """Kullanıcı adıyla kullanıcı bilgilerini ve genel quiz istatistiklerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, password_hash, bio, profile_picture_url, created_at, displayed_badge_ids
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
            "created_at": user_row["created_at"],
            "displayed_badge_ids": json.loads(user_row["displayed_badge_ids"]) if user_row["displayed_badge_ids"] else [] 
        }
        
        overall_stats = get_user_overall_quiz_stats(user_data["id"])
        user_data.update(overall_stats)
        
        return user_data
    return None

def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Kullanıcı ID'siyle kullanıcı bilgilerini ve genel quiz istatistiklerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, bio, profile_picture_url, created_at, displayed_badge_ids
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
            "created_at": user_row["created_at"],
            "displayed_badge_ids": json.loads(user_row["displayed_badge_ids"]) if user_row["displayed_badge_ids"] else [] 
        }

        overall_stats = get_user_overall_quiz_stats(user_data["id"])
        user_data.update(overall_stats)

        return user_data
    return None

def create_user(username: str, email: str, password_hash: str) -> int:
    """Yeni bir kullanıcı oluşturur."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, bio, profile_picture_url, displayed_badge_ids)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, "Merhaba! GeoAI kullanıcısıyım.", "/static/images/sample_user.png", '[]')) 
        conn.commit()
        return cursor.lastrowid

# --- TAKİPÇİ SORGULARI ---
def follow_user(follower_id: int, followed_id: int) -> bool:
    """Bir kullanıcının başka bir kullanıcıyı takip etmesini sağlar."""
    if follower_id == followed_id:
        logging.warning(f"Kullanıcı {follower_id} kendini takip etmeye çalıştı.")
        return False

    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?", (follower_id, followed_id))
            if cursor.fetchone():
                logging.warning(f"Kullanıcı {follower_id} zaten kullanıcı {followed_id} kişisini takip ediyor.")
                return False

            cursor.execute("INSERT INTO followers (follower_id, followed_id) VALUES (?, ?)", (follower_id, followed_id))
            
            cursor.execute("SELECT COUNT(*) FROM followers WHERE followed_id = ?", (followed_id,))
            current_followers = cursor.fetchone()[0]
            
            cursor.execute("UPDATE users SET social_followers = ? WHERE id = ?", (current_followers, followed_id))
            
            conn.commit() 

            logging.info(f"Kullanıcı {follower_id} kişisi kullanıcı {followed_id} kişisini takip etti. Güncel takipçi sayısı: {current_followers}")

            
            follower_user_data = get_user_by_id(follower_id)
            followed_user_data = get_user_by_id(followed_id)
            if follower_user_data and followed_user_data:
                add_user_activity(follower_id, f"{follower_user_data['username']} kişisi {followed_user_data['username']} kişisini takip etmeye başladı.")
            

            badge_service.check_and_award_badges(followed_id) 
            
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Kullanıcı {follower_id} zaten kullanıcı {followed_id} kişisini takip ediyor. (IntegrityError)")
            return False
        except Exception as e:
            logging.error(f"Takip işlemi sırasında hata oluştu: {e}")
            conn.rollback() 
            return False


def unfollow_user(follower_id: int, followed_id: int) -> bool:
    """Bir kullanıcının başka bir kullanıcıyı takibi bırakmasını sağlar."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM followers WHERE follower_id = ? AND followed_id = ?", (follower_id, followed_id))
        conn.commit()
        if cursor.rowcount > 0:
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
        return [dict(row) for row in rows]

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
        return [dict(row) for row in rows]

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

def update_displayed_badges(user_id: int, badge_ids: List[int]) -> bool:
    """Kullanıcının profilinde gösterilecek rozetleri günceller."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        badge_ids_json = json.dumps(badge_ids)
        cursor.execute("UPDATE users SET displayed_badge_ids = ? WHERE id = ?", (badge_ids_json, user_id))
        conn.commit()
        return cursor.rowcount > 0

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
        return [dict(row) for row in rows]

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
        return [dict(row) for row in rows] 

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
    activities = []
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT activity_description, timestamp FROM user_activities WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10',
            (user_id,)
        )
        rows = cursor.fetchall()
        for row in rows:
            timestamp_str = row['timestamp']
            try:
                dt_object = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                dt_object = timestamp_str
            
            activities.append({
                "activity_description": row['activity_description'],
                "timestamp": dt_object 
            })
    return activities

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
                id, username, email, bio, profile_picture_url, displayed_badge_ids
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
                "email": row["email"],
                "bio": row["bio"],
                "profile_picture_url": row["profile_picture_url"],
                "displayed_badge_ids": json.loads(row["displayed_badge_ids"]) if row["displayed_badge_ids"] else []
            }
            overall_stats = get_user_overall_quiz_stats(user_data["id"])
            user_data.update(overall_stats)
            results.append(user_data)
        return results
    
# --- ROZET SORGULARI ---
def get_user_badges(user_id: int) -> List[Dict]:
    """
    Kullanıcının kazandığı rozetleri ve detaylarını getirir.
    Her rozet tipi (type_name) ve kategori için, sadece kullanıcının ulaştığı en yüksek seviyeye sahip rozeti döndürür.
    """
    badges = []
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                ub.achieved_at,
                bt.id AS badge_id,
                bt.type_name,
                bt.name,
                bt.description,
                bt.image_url,
                bt.type AS badge_type,
                bt.threshold,
                bt.category,
                bt.level
            FROM user_badges ub
            JOIN badge_types bt ON ub.badge_id = bt.id
            WHERE ub.user_id = ?
            AND bt.level = ( -- Her bir rozet tipi ve kategori için en yüksek seviyeyi bul
                SELECT MAX(bt2.level)
                FROM user_badges ub2
                JOIN badge_types bt2 ON ub2.badge_id = bt2.id
                WHERE ub2.user_id = ? AND bt2.type_name = bt.type_name AND bt2.category = bt.category
            )
            ORDER BY bt.category ASC, bt.name ASC, bt.level DESC
        """, (user_id, user_id))
        
        rows = cursor.fetchall()
        
        for row in rows:
            badges.append({
                "achieved_at": row["achieved_at"],
                "badge_info": {
                    "id": row["badge_id"],
                    "type_name": row["type_name"],
                    "name": row["name"],
                    "description": row["description"],
                    "image_url": row["image_url"],
                    "type": row["badge_type"],
                    "threshold": row["threshold"],
                    "category": row["category"],
                    "level": row["level"]
                }
            })
            
    return badges

def add_user_badge(user_id: int, badge_id: int) -> bool:
    """Bir kullanıcıya rozet atar."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO user_badges (user_id, badge_id, achieved_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (user_id, badge_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_badge_by_id(badge_id: int) -> Optional[Dict]:
    """ID'ye göre rozet bilgilerini getirir."""
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, 
                type_name, 
                name, 
                description, 
                image_url, 
                type, 
                threshold,
                category,
                level
            FROM badge_types 
            WHERE id = ?
        """, (badge_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
def get_badge_type_by_name_and_threshold(badge_type_name: str, threshold: float, category: Optional[str] = None) -> Optional[Dict]:
    """
    Tipe (yani badges.json'daki type_name), eşik değerine ve isteğe bağlı olarak kategoriye göre rozet bilgilerini getirir.
    """
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()

        query = """
            SELECT 
                id, 
                type_name, 
                name, 
                description, 
                image_url, 
                type, 
                threshold, 
                category, 
                level 
            FROM badge_types 
            WHERE type_name = ? AND threshold = ?
        """
        params = [badge_type_name, threshold]


        if category is not None and category != "":
            query += " AND category = ?"
            params.append(category)
        else:
            query += " AND (category IS NULL OR category = '')"

        logging.debug(f"Executing query: {query} with params: {params}")

        try:
            cursor.execute(query, tuple(params))
        except Exception as e:
            logging.error(f"Sorgu yürütülürken hata oluştu: {query} - Parametreler: {params} - Hata: {e}")
            return None

        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            found_badge = dict(zip(columns, row))
            logging.debug(f"Rozet bulundu: {found_badge['name']} (Eşik: {found_badge['threshold']}, Kategori: {found_badge.get('category', 'Yok')})")
            return found_badge
        
        logging.debug(f"Rozet bulunamadı: type_name='{badge_type_name}', threshold={threshold}, category='{category}'")
        return None
    
    
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
    
    return {
        "total_quizzes_completed": total_quizzes_completed,
        "total_correct_answers": total_correct_answers,
        "total_score": total_score,
        "highest_score": highest_score
    }

def get_user_category_success_rates(user_id: int) -> Dict[str, float]:
    """
    Belirli bir kullanıcının her kategori için doğru cevap oranlarını (0.0 ile 1.0 arası) döndürür.
    Henüz soru çözülmemiş kategoriler için 0.0 döndürür.
    """
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category_name, correct_count, wrong_count
            FROM category_stats
            WHERE user_id = ?
        """, (user_id,))
        
        category_rates = {}
        for row in cursor.fetchall():
            category_name = row["category_name"]
            correct_count = row["correct_count"]
            wrong_count = row["wrong_count"]
            
            total_questions = correct_count + wrong_count
            if total_questions > 0:
                category_rates[category_name] = correct_count / total_questions
            else:
                category_rates[category_name] = 0.0 # Henüz bu kategoride soru çözülmemiş
    return category_rates

def get_all_users_category_data() -> (Dict[int, List[float]], List[str]):
    """
    Tüm kullanıcıların kategori bazındaki başarı oranlarını içeren vektörleri döndürür.
    Öneri sistemi için kullanılır.
    """
    with get_db_connection(settings.QUIZ_STATS_DATABASE_FILE) as conn:
        cursor = conn.cursor()


        cursor.execute("SELECT DISTINCT category_name FROM category_stats ORDER BY category_name ASC")
        all_categories = [row["category_name"] for row in cursor.fetchall()]


        cursor.execute("SELECT DISTINCT user_id FROM category_stats")
        all_user_ids = [row["user_id"] for row in cursor.fetchall()]

        all_users_category_vectors = {}
        for user_id in all_user_ids:

            user_category_rates = get_user_category_success_rates(user_id)
            
            user_vector = [user_category_rates.get(cat, 0.0) for cat in all_categories]
            all_users_category_vectors[user_id] = user_vector
    
    return all_users_category_vectors, all_categories

def remove_follower_relationship(follower_id: int, followed_id: int) -> bool:
    """
    Belirtilen 'follower_id'nin, 'followed_id'yi takip etme ilişkisini siler.
    Yani, bir takipçiyi kendi takipçi listenizden çıkarır.
    """

    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM followers WHERE follower_id = ? AND followed_id = ?",
                (follower_id, followed_id)
            )
            conn.commit()
            return cursor.rowcount > 0 
        except sqlite3.Error as e:
            print(f"Database error during remove_follower_relationship: {e}")
            conn.rollback()
            return False

def check_if_user_follows(follower_id: int, followed_id: int) -> bool:
    """
    Bir kullanıcının başka bir kullanıcıyı takip edip etmediğini kontrol eder.
    """

    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM followers WHERE follower_id = ? AND followed_id = ?", 
                (follower_id, followed_id)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            print(f"Database error during check_if_user_follows: {e}")
            return False



def create_post(user_id: int, content: str, topic: str, image_url: Optional[str] = None) -> int:
    """Yeni bir gönderi ekler."""
    try:
        with get_db_connection(settings.POSTS_DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO posts (user_id, content, image_url, topic, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, content, image_url, topic, datetime.now().isoformat())) 
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Gönderi eklenirken hata: {e}")
        return 0 


def get_posts(limit: int = 10, offset: int = 0, topic: Optional[str] = None) -> List[Dict]:
    """Belirli bir limitte ve ofsette gönderileri getirir, isteğe bağlı olarak konuya göre filtreler."""
    query = """
        SELECT
            id, user_id, content, image_url, topic,
            created_at, -- created_at'ı yeniden adlandırmayın
            likes, comments
        FROM posts
    """
    
    params = []
    if topic and topic != "Tümü":
        query += " WHERE topic = ?"
        params.append(topic)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        with get_db_connection(settings.POSTS_DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            posts = cursor.fetchall()
        

        return [dict(post) for post in posts]
    except sqlite3.Error as e:
        print(f"Gönderiler çekilirken hata (posts.db): {e}")
        return []

def format_time_ago(timestamp_str: Optional[str]) -> str:
    """Veritabanından gelen zaman damgasını 'x zaman önce' formatına dönüştürür."""
    if not timestamp_str:
        return "Bilinmiyor"
    try:
        post_time = datetime.fromisoformat(timestamp_str)
    except ValueError:

        return "Geçersiz tarih"
    now = datetime.now()
    diff = now - post_time

    seconds = int(diff.total_seconds())


    if seconds < 60:
        return "az önce"
    elif seconds < 3600:  
        minutes = seconds // 60
        return f"{minutes} dakika önce"
    elif seconds < 86400:  
        hours = seconds // 3600
        return f"{hours} saat önce"
    elif seconds < 604800:  
        days = seconds // 86400
        return f"{days} gün önce"
    elif seconds < 2592000:  
        weeks = seconds // 604800
        return f"{weeks} hafta önce"
    elif seconds < 31536000:  
        months = seconds // 2592000
        return f"{months} ay önce"
    else:
        years = seconds // 31536000
        return f"{years} yıl önce"


def search_users(query: str, limit: int = 5) -> List[Dict]:
    """Kullanıcı adında arama yapan fonksiyon."""
    try:
        
        with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, profile_picture_url
                FROM users
                WHERE username LIKE ?
                LIMIT ?
            """, (f'%{query}%', limit))
            users = cursor.fetchall()
        return [dict(u) for u in users]
    except sqlite3.Error as e:
        print(f"Kullanıcı aranırken hata (users.db): {e}")
        return []

def get_post_by_id(post_id: int) -> Optional[Dict]:
    """Belirli bir ID'ye sahip gönderiyi getirir."""
    try:
        with get_db_connection(settings.POSTS_DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, content, image_url, topic, created_at as timestamp, likes, comments
                FROM posts
                WHERE id = ?
            """, (post_id,))
            post = cursor.fetchone()
            if post:
                return dict(post)
            return None
    except sqlite3.Error as e:
        print(f"Gönderi ID'ye göre çekilirken hata: {e}")
        return None