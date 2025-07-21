# database/connection.py
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
    for db_file in [settings.QUIZ_DATABASE_FILE, settings.USERS_DATABASE_FILE]:
        with get_db_connection(db_file) as conn:
            cursor = conn.cursor()
            if db_file == settings.QUIZ_DATABASE_FILE:
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
            elif db_file == settings.USERS_DATABASE_FILE:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    )
                """)
            conn.commit()
    print("Veritabanları başarıyla başlatıldı/kontrol edildi.")

# database/connection.py içinde init_dbs() fonksiyonu
def init_dbs():
    """Uygulama başlangıcında tüm veritabanlarını başlatır."""
    for db_file in [settings.QUIZ_DATABASE_FILE, settings.USERS_DATABASE_FILE]:
        with get_db_connection(db_file) as conn:
            cursor = conn.cursor()
            if db_file == settings.QUIZ_DATABASE_FILE:
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
            elif db_file == settings.USERS_DATABASE_FILE:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL
                    )
                """)
                # Yeni: Messages tablosu
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
            conn.commit()
    print("Veritabanları başarıyla başlatıldı/kontrol edildi.")