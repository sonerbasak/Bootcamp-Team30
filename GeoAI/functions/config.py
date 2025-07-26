# GeoAI/functions/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path

load_dotenv()

class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).parent.parent

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "") # Eğer yoksa boş string döner
    QUIZ_DATABASE_FILE: Path = BASE_DIR / "quiz_errors.db"
    USERS_DATABASE_FILE: Path = BASE_DIR / "users.db" # <--- BU SATIRI EKLEDİK
    QUIZ_STATS_DATABASE_FILE: Path = BASE_DIR / "quiz_stats.db"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY ortam değişkeni ayarlanmamış! Lütfen .env dosyanızı kontrol edin.")

    STATIC_DIR: Path = BASE_DIR / "static"

settings = Settings()