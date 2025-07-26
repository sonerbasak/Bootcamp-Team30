import sqlite3
import logging
import json
from contextlib import contextmanager
from functions.config import settings
import os # os modülünü import edin

# Logging yapılandırması
# Bu satır, uygulamanız başladığında tüm logların INFO seviyesinden itibaren gösterilmesini sağlar.
# Eğer sadece bu dosyada değil, tüm uygulamada logging seviyesini kontrol etmek isterseniz
# bu ayarı main.py gibi ana giriş noktanızda bir kez yapabilirsiniz.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@contextmanager
def get_db_connection(db_file: str):
    """Veritabanı bağlantısını yöneten bir context manager."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row # Kolayca sütun isimleriyle erişim için
        yield conn
    except sqlite3.Error as e:
        # print yerine logging kullanıldı
        logging.error(f"Veritabanı bağlantı hatası ({db_file}): {e}")
        raise # Hatayı yukarı fırlat
    finally:
        if conn:
            conn.close()

def init_dbs():
    """Uygulama başlangıcında tüm veritabanlarını başlatır ve gerekli tabloları oluşturur."""
    logging.info("Veritabanları başlatılıyor...") # print yerine logging kullanıldı

    # Önce USERS_DATABASE_FILE tablolarını oluşturun, çünkü diğer DB'ler buna Foreign Key ile bağlı olabilir.
    with get_db_connection(settings.USERS_DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # users tablosu - 'total_quizzes_completed' vb. istatistik sütunları kaldırıldı
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT 'Merhaba! GeoAI kullanıcısıyım.',
                profile_picture_url TEXT DEFAULT '/static/images/sample_user.png',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                displayed_badge_ids TEXT DEFAULT '[]' -- JSON string olarak saklanacak
            )
        """)
        # Mevcut users tablosuna displayed_badge_ids sütununu ekle (eğer yoksa)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN displayed_badge_ids TEXT DEFAULT '[]'")
            logging.info("users tablosuna 'displayed_badge_ids' sütunu eklendi (eğer yoktuysa).")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                logging.error(f"Error altering users table for 'displayed_badge_ids': {e}")
                raise

        # badge_types tablosu (ROZET TİPLERİ)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS badge_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '', -- Burası değişti: category artık NOT NULL ve varsayılan boş string
                level INTEGER NOT NULL,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                image_url TEXT NOT NULL,
                threshold REAL NOT NULL,
                UNIQUE(type_name, category, level) -- Burası değişti: COALESCE kaldırıldı
            )
        """)


        # user_badges tablosu (KULLANICILARIN KAZANDIĞI ROZETLER)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge_type_id INTEGER NOT NULL,
                achieved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_type_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (badge_type_id) REFERENCES badge_types(id) ON DELETE CASCADE
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


    # QUIZ_DATABASE_FILE için bağlantı ve tablolar (Eski adıyla quiz_errors.db)
    # settings.QUIZ_DATABASE_FILE'ın gerçekten quiz_errors.db'yi işaret ettiğinden emin olun.
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

    # Tüm tablolar oluşturulduktan sonra rozet tiplerini ekle
    # Bu fonksiyon şimdi connections.py içinde tanımlı
    insert_initial_badge_types()
    logging.info("İlk rozet tipleri yüklendi (eğer yoktularsa).")
    logging.info("Tüm veritabanı başlatma ve tablo oluşturma işlemleri tamamlandı.")

def insert_initial_badge_types():
    """
    Uygulama ilk kez başlatıldığında veya badge_types tablosu boşsa
    varsayılan rozet tiplerini veritabanına ekler.
    Rozet tanımlarını 'data/badges.json' dosyasından okur.
    """
    # Mevcut dosya yoluna göre 'data/badges.json' dosyasının yolu
    # os.path.dirname(os.path.abspath(__file__)) -> .../GeoAI/functions/database
    # ../../data/badges.json -> .../GeoAI/data/badges.json
    badge_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data/badges.json')

    initial_badges = []
    try:
        if os.path.exists(badge_file_path):
            with open(badge_file_path, 'r', encoding='utf-8') as f:
                initial_badges = json.load(f)
            logging.info(f"Rozet tanımları '{badge_file_path}' dosyasından yüklendi.")
        else:
            logging.warning(f"Rozet tanımları dosyası bulunamadı: '{badge_file_path}'. Başlangıç rozetleri eklenmeyecek.")
            return # Dosya yoksa erken çık
    except json.JSONDecodeError:
        logging.error(f"Hata: '{badge_file_path}' dosyası geçerli bir JSON değil.")
        return # JSON hatası varsa erken çık
    except Exception as e:
        logging.error(f"Rozet tanımları yüklenirken beklenmeyen bir hata oluştu: {e}")
        return # Diğer hatalarda erken çık


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
                    category_value = badge.get("category")
                    cursor.execute("""
                        INSERT INTO badge_types (type_name, category, level, name, description, image_url, threshold)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (badge["type_name"], category_value, badge["level"],
                          badge["name"], badge["description"], badge["image_url"],
                          badge["threshold"]))
                except sqlite3.IntegrityError as e:
                    logging.warning(f"Rozet eklenirken UNIQUE kısıtlama hatası: {badge.get('name', 'Bilinmeyen Rozet')} - {e}")
                except KeyError as e:
                    logging.error(f"Rozet tanımında eksik alan var: {e}. Rozet: {badge}")
            conn.commit()
            logging.info(f"{len(initial_badges)} adet başlangıç rozet tipi başarıyla eklendi.")
        else:
            logging.info("badge_types tablosu dolu, başlangıç rozetleri eklenmiyor.")