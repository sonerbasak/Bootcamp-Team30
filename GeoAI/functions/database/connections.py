# functions/database/connections.py
import sqlite3
from contextlib import contextmanager
from functions.config import settings

@contextmanager
def get_db_connection(db_file: str):
    """Veritabanı bağlantısını yöneten bir context manager."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row # Kolayca sütun isimleriyle erişim için
        yield conn
    except sqlite3.Error as e:
        print(f"Veritabanı bağlantı hatası ({db_file}): {e}")
        raise # Hatayı yukarı fırlat
    finally:
        if conn:
            conn.close()

def init_dbs():
    """Uygulama başlangıcında tüm veritabanlarını başlatır."""
    print("DEBUG: init_dbs() fonksiyonu çalışıyor...")
    for db_file in [settings.QUIZ_DATABASE_FILE, settings.USERS_DATABASE_FILE]:
        print(f"DEBUG: Veritabanı dosyası kontrol ediliyor: {db_file}")
        with get_db_connection(db_file) as conn:
            cursor = conn.cursor()
            if db_file == settings.QUIZ_DATABASE_FILE:
                print(f"DEBUG: {db_file} için 'wrong_questions' tablosu kontrol ediliyor/oluşturuluyor.")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS wrong_questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        city TEXT NOT NULL,
                        category TEXT,
                        question_text TEXT NOT NULL,
                        option_a TEXT NOT NULL,
                        option_b TEXT NOT NULL,
                        option_c TEXT NOT NULL,
                        option_d TEXT NOT NULL,
                        correct_answer_letter TEXT NOT NULL,
                        user_answer_letter TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(f"DEBUG: 'wrong_questions' tablosu tamamlandı.")
            elif db_file == settings.USERS_DATABASE_FILE:
                print(f"DEBUG: {db_file} için 'users' tablosu kontrol ediliyor/oluşturuluyor.")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        bio TEXT,
                        profile_picture_url TEXT DEFAULT '/static/images/sample_user.png', -- BURASI GÜNCELLENDİ!
                        total_quizzes_completed INTEGER DEFAULT 0,
                        total_correct_answers INTEGER DEFAULT 0,
                        total_score INTEGER DEFAULT 0,
                        highest_score INTEGER DEFAULT 0,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                print(f"DEBUG: 'users' tablosu tamamlandı.")

                print(f"DEBUG: {db_file} için 'messages' tablosu kontrol ediliyor/oluşturuluyor.")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id INTEGER NOT NULL,
                        receiver_id INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sender_id) REFERENCES users(id),
                        FOREIGN KEY (receiver_id) REFERENCES users(id)
                    )
                """)
                print(f"DEBUG: 'messages' tablosu tamamlandı.")

                print(f"DEBUG: {db_file} için 'user_activities' tablosu kontrol ediliyor/oluşturuluyor.")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        activity_description TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                print(f"DEBUG: 'user_activities' tablosu tamamlandı.")

                print(f"DEBUG: {db_file} için 'followers' tablosu kontrol ediliyor/oluşturuluyor.")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS followers (
                        follower_id INTEGER NOT NULL,
                        followed_id INTEGER NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (follower_id, followed_id),
                        FOREIGN KEY (follower_id) REFERENCES users(id),
                        FOREIGN KEY (followed_id) REFERENCES users(id)
                    )
                """)
                print(f"DEBUG: 'followers' tablosu tamamlandı.")
            conn.commit()
            print(f"DEBUG: {db_file} için değişiklikler kaydedildi.")
    print("Veritabanları başarıyla başlatıldı/kontrol edildi.")