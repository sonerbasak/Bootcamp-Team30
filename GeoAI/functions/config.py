# config.py
import os
from dotenv import load_dotenv

load_dotenv() # .env dosyasını yükle

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    QUIZ_DATABASE_FILE: str = "quiz_errors.db"
    USERS_DATABASE_FILE: str = "users.db"
    SECRET_KEY: str = os.getenv("SECRET_KEY")

settings = Settings()