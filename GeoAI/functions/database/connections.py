import sqlite3
import logging
import json
from contextlib import contextmanager
from functions.config import settings
import os

# queries.py'den load_initial_badge_types fonksiyonunu import etmiyoruz artık.
# Çünkü bu fonksiyonu buraya taşıdık ve adını insert_initial_badge_types olarak değiştirdik.
# from functions.database.queries import load_initial_badge_types # BU SATIRI KALDIRIN

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@contextmanager
def get_db_connection(db_file: str):
    """Veritabanı bağlantısını yöneten bir context manager."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logging.error(f"Veritabanı bağlantı hatası ({db_file}): {e}")
        raise # Hatayı yukarı fırlat
    finally:
        if conn:
            conn.close()

def insert_initial_badge_types():
    """
    Uygulama ilk kez başlatıldığında veya badge_types tablosu boşsa
    varsayılan rozet tiplerini veritabanına ekler.
    Rozet tanımlarını 'data/badges.json' dosyasından okur.
    """
    badge_file_path = settings.BADGES_JSON_PATH # settings'ten doğrudan yolu al

    initial_badges = []
    try:
        if os.path.exists(badge_file_path):
            with open(badge_file_path, 'r', encoding='utf-8') as f:
                initial_badges = json.load(f)
            logging.info(f"Rozet tanımları '{badge_file_path}' dosyasından yüklendi.")
        else:
            logging.warning(f"Rozet tanımları dosyası bulunamadı: '{badge_file_path}'. Başlangıç rozetleri eklenmeyecek.")
            return
    except json.JSONDecodeError:
        logging.error(f"Hata: '{badge_file_path}' dosyası geçerli bir JSON değil.")
        return
    except Exception as e:
        logging.error(f"Rozet tanımları yüklenirken beklenmeyen bir hata oluştu: {e}")
        return

    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM badge_types")
        if cursor.fetchone()[0] == 0:
            logging.info("badge_types tablosu boş, başlangıç rozetleri ekleniyor.")
            if not initial_badges:
                logging.warning("Başlangıç rozeti tanımları boş. Rozetler eklenmeyecek.")
                return

            for badge in initial_badges:
                try:
                    # 'id' alanı AUTOINCREMENT olduğu için INSERT sorgusundan çıkarıldı.
                    # 'name' sütununa badges.json'daki 'type_name' değerini kaydediyoruz.
                    # 'category' sütununu ekledik ve .get() kullanarak yoksa boş string atadık.
                    cursor.execute("""
                        INSERT INTO badge_types (name, description, image_url, type, threshold, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (badge["type_name"], badge["description"], badge["image_url"],
                          badge["type"], float(badge["threshold"]), badge.get("category", "")))
                    # Debug amaçlı ek log:
                    logging.debug(f"Veritabanına eklendi: Name='{badge['type_name']}', Category='{badge.get('category', '')}', Threshold={badge['threshold']}")

                except sqlite3.IntegrityError as e:
                    # Bu uyarı artık görülmemeli, çünkü UNIQUE kısıtlamasını değiştirdik.
                    logging.warning(f"Rozet eklenirken UNIQUE kısıtlama hatası (Bu artık görülmemeli!): {badge.get('type_name', 'Bilinmeyen Rozet')} - {e}")
                except KeyError as e:
                    logging.error(f"Rozet tanımında eksik alan var: {e}. Rozet: {badge}")
            conn.commit()
            logging.info(f"{len(initial_badges)} adet başlangıç rozet tipi başarıyla eklendi.")
        else:
            logging.info("badge_types tablosu dolu, başlangıç rozetleri eklenmiyor.")

def init_dbs():
    logging.info("Veritabanları başlatılıyor...")

    # USERS_DATABASE_FILE tablolarını oluşturun
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT 'Merhaba! GeoAI kullanıcısıyım.',
                profile_picture_url TEXT DEFAULT '/static/images/sample_user.png',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                displayed_badge_ids TEXT DEFAULT '[]', -- JSON string olarak saklanır
                daily_login_streak INTEGER DEFAULT 0,
                last_login_date TEXT, -- YYYY-MM-DD formatında son giriş tarihi
                social_followers INTEGER DEFAULT 0, -- YENİ EKLENDİ!
                social_shares INTEGER DEFAULT 0 -- YENİ EKLENDİ!
            )
        """)

        # badge_types tablosu (ROZET TİPLERİ) -- BU KISMI GÜNCELLEYİN!
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS badge_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,          -- ARTIK 'UNIQUE' KISITLAMASI BURADA YOK!
                description TEXT NOT NULL,
                image_url TEXT NOT NULL,
                type TEXT NOT NULL,          -- Bu sütun badges.json'daki 'type' (engagement, quiz_stats vb.) için kullanılacak
                threshold REAL DEFAULT 0,
                category TEXT,
                -- YENİ UNIQUE KISITLAMA EKLEYİN: name, threshold ve category kombinasyonu benzersiz olsun.
                UNIQUE (name, threshold, category)
            )
        """)

        # user_badges tablosu (KULLANICILARIN KAZANDIĞI ROZETLER)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_id INTEGER NOT NULL,
                achieved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (badge_id) REFERENCES badge_types(id) ON DELETE CASCADE
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
        logging.info("users.db tabloları başlatıldı/güncellendi.")


    # QUIZ_DATABASE_FILE için bağlantı ve tablolar
    with get_db_connection(settings.QUIZ_DATABASE_FILE) as conn:
        cursor = conn.cursor()
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
        logging.info("quiz.db (wrong_questions) tabloları başlatıldı/güncellendi.")


    # QUIZ_STATS_DATABASE_FILE için bağlantı ve tablolar
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
        logging.info("quiz_stats.db tabloları başlatıldı/güncellendi.")

    # posts.db için tablo oluşturma 
    with get_db_connection(settings.POSTS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                topic TEXT NOT NULL,
                created_at TEXT NOT NULL ,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        logging.info("posts.db tabloları başlatıldı/güncellendi.")

    # Tüm tablolar oluşturulduktan sonra rozet tiplerini ekle
    insert_initial_badge_types() # Doğrudan buradaki fonksiyonu çağırıyoruz
    logging.info("İlk rozet tipleri yüklendi (eğer yoktularsa).")
    logging.info("Tüm veritabanı başlatma ve tablo oluşturma işlemleri tamamlandı.")