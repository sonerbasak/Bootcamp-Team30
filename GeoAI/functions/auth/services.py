# auth/services.py
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi.responses import RedirectResponse
from fastapi import status
from typing import Dict, Optional

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(hashed_password: str, password: str) -> bool:
    return check_password_hash(hashed_password, password)

def set_auth_cookies(response: RedirectResponse, user_id: int, username: str):
    # secure=True sadece HTTPS kullanıyorsanız olmalı!
    response.set_cookie(key="user_id", value=str(user_id), httponly=True, samesite="Lax", secure=False)
    response.set_cookie(key="username", value=username, httponly=True, samesite="Lax", secure=False)
    return response

def clear_auth_cookies(response: RedirectResponse):
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    return response