# functions/services/badge_service.py
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

from functions.config import settings
from functions.database import queries as db_queries # db_queries'i kullanacağız
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BadgeService:
    def __init__(self):
        self.badges_data: List[Dict] = []
        self._load_badges_data()

    def _load_badges_data(self):
        """badges.json dosyasından rozet verilerini yükler."""
        try:
            if not settings.BADGES_JSON_PATH.exists():
                logging.error(f"Badges JSON dosyası bulunamadı: {settings.BADGES_JSON_PATH}")
                return

            with open(settings.BADGES_JSON_PATH, 'r', encoding='utf-8') as f:
                self.badges_data = json.load(f)
            logging.info(f"'{settings.BADGES_JSON_PATH}' adresinden {len(self.badges_data)} rozet tipi yüklendi.")
        except json.JSONDecodeError as e:
            logging.error(f"Badges JSON dosyasını ayrıştırma hatası: {e}")
            self.badges_data = [] # Hata durumunda boş liste ile devam et
        except Exception as e:
            logging.error(f"Rozet verileri yüklenirken bilinmeyen bir hata oluştu: {e}")
            self.badges_data = []

    def get_badge_by_type_name_and_threshold(self, type_name: str, threshold: float, category: Optional[str] = None) -> Optional[Dict]:
        """
        type_name ve threshold'a göre rozet bilgisini döndürür.
        category sadece 'category_achievement' tipi rozetler için kullanılır.
        """
        for badge in self.badges_data:
            if badge.get("type_name") == type_name and float(badge.get("threshold")) == threshold:
                if type_name == "category_master":
                    if badge.get("category") == category:
                        return badge
                else:
                    return badge
        return None

    def check_and_award_badges(self, user_id: int) -> List[str]:
        """
        Kullanıcının istatistiklerini kontrol eder ve kazanılan rozetleri atar.
        Yeni kazanılan rozetlerin isimlerini içeren bir liste döndürür.
        """
        newly_awarded_badge_names: List[str] = []
        
        # Kullanıcının mevcut tüm rozetlerini çekin
        current_user_badges = db_queries.get_user_badges(user_id)
        current_achieved_badge_ids = set(b["badge_info"]["id"] for b in current_user_badges)

        # Kullanıcının genel quiz istatistiklerini çekin
        overall_stats = db_queries.get_user_overall_quiz_stats(user_id)
        total_quizzes_completed = overall_stats.get("total_quizzes_completed", 0)
        total_correct_answers = overall_stats.get("total_correct_answers", 0)
        highest_score = overall_stats.get("highest_score", 0) # En yüksek skor
        
        # Kategori bazlı istatistikleri çekin
        category_stats = db_queries.get_user_category_stats(user_id)
        # Category stats'ı dict'e çevirerek daha kolay erişim sağlayalım: {'CategoryName': {'correct_count': X, 'wrong_count': Y}}
        category_stats_map = {item["category_name"]: item for item in category_stats}

        # Takipçi sayısını çekin (users.db'den)
        followers = db_queries.get_followers(user_id)
        follower_count = len(followers)

        # Şu an için sosyal paylaşım sayısını takip etmiyoruz, varsayılan 0
        social_share_count = 0 # Bunu daha sonra bir aktivite/loglama ile takip edebiliriz

        # Giriş serisi için ayrı bir tablo/mekanizma gerekiyor.
        # Basitlik için şu an sabit bir değer veya varsayılan 0 kullanabiliriz.
        # Örneğin, her başarılı login'de bir "last_login_date" alanı güncellenebilir
        # ve bu fonksiyonda günlük giriş serisi hesaplanabilir.
        daily_login_streak = 0 # Gerçek bir uygulama için bu dinamik hesaplanmalı

        for badge_def in self.badges_data:
            badge_type_name = badge_def.get("type_name")
            badge_threshold = float(badge_def.get("threshold")) # JSON'dan gelen threshold float olmalı
            badge_category = badge_def.get("category")
            
            # Rozet zaten kazanılmışsa atla
            # JSON'dan ID'yi almak yerine veritabanından ID'yi almalıyız
            # Veritabanında (badge_types tablosu) tanımlı rozet id'sine ihtiyacımız var.
            # get_badge_type_by_name_and_threshold (queries.py'den) kullanmalıyız.

            # db_queries.get_badge_type_by_name_and_threshold kullanarak veritabanındaki rozeti bulalım
            db_badge_info = db_queries.get_badge_type_by_name_and_threshold(
                badge_type_name, badge_threshold, badge_category if badge_type_name == "category_master" else None
            )

            if not db_badge_info:
                logging.warning(f"Badges.json'daki '{badge_type_name}' (eşik: {badge_threshold}, kategori: {badge_category}) rozeti veritabanında bulunamadı. Lütfen init_dbs() ve badges.json'ın senkronize olduğundan emin olun.")
                continue

            badge_db_id = db_badge_info["id"]

            if badge_db_id in current_achieved_badge_ids:
                continue # Bu rozet zaten kazanılmış, atla

            achieved = False

            if badge_type_name == "total_quizzes_completed":
                if total_quizzes_completed >= badge_threshold:
                    achieved = True
            elif badge_type_name == "total_correct_answers":
                if total_correct_answers >= badge_threshold:
                    achieved = True
            elif badge_type_name == "highest_score_per_quiz":
                if highest_score >= badge_threshold:
                    achieved = True
            elif badge_type_name == "social_follower":
                if follower_count >= badge_threshold:
                    achieved = True
            elif badge_type_name == "social_share":
                # Bu metriği takip etmek için uygulamanızda paylaşım aksiyonlarını loglamanız gerek
                # Şimdilik varsayılan 0 olduğu için bu rozetler kazanılamaz.
                if social_share_count >= badge_threshold:
                    achieved = True
            elif badge_type_name == "daily_login_streak":
                # Bu metriği takip etmek için kullanıcıların son giriş tarihlerini kaydetmeniz ve
                # günlük giriş serisini hesaplamanız gerek.
                if daily_login_streak >= badge_threshold:
                    achieved = True
            elif badge_type_name == "category_master":
                category_stat = category_stats_map.get(badge_category)
                if category_stat and category_stat["correct_count"] >= badge_threshold:
                    achieved = True

            if achieved:
                db_queries.add_user_badge(user_id, badge_db_id)
                newly_awarded_badge_names.append(badge_def["name"])
                logging.info(f"Kullanıcı {user_id} yeni rozet kazandı: '{badge_def['name']}'")

        return newly_awarded_badge_names

# BadgeService sınıfının tek bir örneğini oluştur
badge_service = BadgeService()