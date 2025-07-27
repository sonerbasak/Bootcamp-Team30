# functions/auth/routes.py
from fastapi import APIRouter, Request, Form, Depends, status, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict

# Dosya yollarını yönetmek için Path, dosya kopyalamak için shutil
from pathlib import Path
import os # Dosyaları silmek için
import uuid # Benzersiz dosya adları için
import shutil # Dosya kopyalamak için

from functions.database.queries import (
    get_user_by_username, create_user, get_user_by_id, search_users_by_username,
    follow_user, unfollow_user, is_following, get_followers, get_following,
    update_user_profile, get_user_activities, # db_queries'den doğrudan alabileceğimiz fonksiyonlar
    get_user_category_stats, # Quiz istatistikleri için bu fonksiyon da gerekli
    get_user_quiz_summaries # Quiz özetleri için bu fonksiyon da gerekli
)
from functions.auth.services import hash_password, verify_password, set_auth_cookies, clear_auth_cookies
from functions.auth.dependencies import require_auth, CurrentUser

# --- ML tabanlı öneri fonksiyonunu import ediyoruz ---
from functions.ml.recommendations import get_recommended_friends_kmeans

# --- Pydantic Modelleri ---
from pydantic import BaseModel, EmailStr
from datetime import datetime

class ActivityResponse(BaseModel):
    activity_description: str
    timestamp: datetime

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    bio: Optional[str] = None
    profile_picture_url: str = "/static/images/sample_user.png" # YENİ ALAN: Profil resmi URL'si
    total_quizzes_completed: int
    total_correct_answers: int
    total_score: int
    highest_score: int
    recent_activities: List[ActivityResponse] = []

    class Config:
        from_attributes = True

router = APIRouter(tags=["Auth"])
templates = Jinja2Templates(directory="templates")

# --- Statik Dosya Yükleme Dizini ---
UPLOAD_DIR = Path("static/uploads/profile_pictures")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True) # Dizin yoksa oluştur

@router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if current_user:
        return RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse, name="login_user")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    user_data = get_user_by_username(username)
    if user_data and verify_password(user_data['password_hash'], password):
        response = RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
        set_auth_cookies(response, user_data['id'], user_data['username'])
        return response
    else:
        return templates.TemplateResponse("auth/login.html", {"request": request, "error": "Kullanıcı adı veya şifre hatalı."})

@router.get("/register", response_class=HTMLResponse, name="register_page")
async def register_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if current_user:
        return RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("auth/register.html", {"request": request})

@router.post("/register", response_class=HTMLResponse, name="register_user")
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    if get_user_by_username(username):
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": "Bu kullanıcı adı zaten kullanılıyor."})

    hashed_password = hash_password(password)
    try:
        new_user_id = create_user(username, email, hashed_password)
        
        user_data = get_user_by_id(new_user_id)
        response = RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
        set_auth_cookies(response, user_data['id'], user_data['username'])
        return response
        
    except Exception as e:
        return templates.TemplateResponse("auth/register.html", {"request": request, "error": f"Kayıt olurken bir hata oluştu: {str(e)}"})

@router.get("/logout", name="logout_user")
async def logout_user(request: Request):
    response = RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    clear_auth_cookies(response)
    return response

@router.get("/api/search-users", name="api_search_users")
async def api_search_users(request: Request, q: Optional[str] = None, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    
    if not q:
        return JSONResponse([])

    users = search_users_by_username(q)
    
    safe_users = []
    for user_data in users:
        safe_users.append({
            "id": user_data["id"],
            "username": user_data["username"],
            "bio": user_data.get("bio", "Bio yok."),
            "profile_url": str(request.url_for("user_profile", username=user_data["username"])),
            "profile_picture_url": user_data.get("profile_picture_url", "/static/images/sample_user.png")
        })
    
    return JSONResponse(safe_users)

@router.get("/profile/{username}", response_class=HTMLResponse, name="user_profile")
async def user_profile(request: Request, username: str, current_user: CurrentUser = Depends(require_auth)):
    profile_user = get_user_by_username(username)
    if not profile_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı")

    is_my_profile = False
    if current_user and current_user.username == username:
        is_my_profile = True
    
    is_following_user = False
    if current_user and not is_my_profile:
        is_following_user = is_following(current_user.id, profile_user["id"])

    # Kullanıcının quiz istatistiklerini ve özetlerini al
    # Bu fonksiyonlar functions/database/queries.py içinde olmalı
    user_id = profile_user["id"] # Profilini görüntülediğimiz kullanıcının ID'si
    category_stats = get_user_category_stats(user_id)
    quiz_summaries = get_user_quiz_summaries(user_id)

    # Toplam istatistikleri hesapla
    total_quizzes_completed = len(quiz_summaries) # Her bir özet bir quiz ise
    total_correct_answers = sum(s['correct_answers'] for s in quiz_summaries)
    total_score = sum(s['score'] for s in quiz_summaries)
    highest_score = max(s['score'] for s in quiz_summaries) if quiz_summaries else 0


    profile_user_data = {
        "id": profile_user["id"],
        "username": profile_user["username"],
        "email": profile_user["email"],
        "bio": profile_user.get("bio", "Merhaba! Coğrafya ve AI quizleri ile ilgileniyorum. Yeni şeyler öğrenmeyi ve kendimi geliştirmeyi seviyorum."),
        "profile_picture_url": profile_user.get("profile_picture_url", "/static/images/sample_user.png"),
        "total_quizzes_completed": total_quizzes_completed, # Artık hesaplanan değerler kullanılıyor
        "total_correct_answers": total_correct_answers,
        "total_score": total_score,
        "highest_score": highest_score,
        "recent_activities": get_user_activities(profile_user["id"])
    }

    followers_count = len(get_followers(profile_user["id"]))
    following_count = len(get_following(profile_user["id"]))

    # Sadece kendi profilini görüntülerken arkadaş önerilerini göster
    recommended_friends = []
    if is_my_profile:
        # Arkadaş önerilerini K-Means fonksiyonunu çağırarak al
        # num_clusters değerini kullanıcı sayınıza ve veri yapınıza göre ayarlayabilirsiniz.
        recommended_friends = get_recommended_friends_kmeans(
            current_user_id=current_user.id, 
            num_recommendations=5, 
            num_clusters=5 
        )

    return templates.TemplateResponse(
        "social/profile.html",
        {
            "request": request,
            "profile_user": profile_user_data,
            "user": current_user,
            "is_my_profile": is_my_profile,
            "is_following_user": is_following_user,
            "followers_count": followers_count,
            "following_count": following_count,
            "category_stats": category_stats, # Kategori istatistiklerini şablona gönder
            "quiz_summaries": quiz_summaries, # Quiz özetlerini şablona gönder
            "recommended_friends": recommended_friends # Arkadaş önerilerini şablona gönder
        }
    )

@router.post("/api/follow/{username}", status_code=status.HTTP_200_OK)
async def api_follow_user(username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    followed_user = get_user_by_username(username)
    if not followed_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Takip edilecek kullanıcı bulunamadı.")
    
    if current_user.id == followed_user["id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendinizi takip edemezsiniz.")

    if follow_user(current_user.id, followed_user["id"]):
        return {"message": f"{username} takip edildi."}
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu kullanıcıyı zaten takip ediyorsunuz.")
    
@router.post("/api/unfollow/{username}", status_code=status.HTTP_200_OK)
async def api_unfollow_user(username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    followed_user = get_user_by_username(username)
    if not followed_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Takibi bırakılacak kullanıcı bulunamadı.")
    
    if unfollow_user(current_user.id, followed_user["id"]):
        return {"message": f"{username} takibi bırakıldı."}
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bu kullanıcıyı takip etmiyorsunuz.")
    

@router.get("/api/profile/{username}/followers", name="api_get_followers")
async def api_get_followers(username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    
    followers = get_followers(user["id"])
    
    formatted_followers = []
    for f_user in followers:
        formatted_followers.append({
            "id": f_user["id"],
            "username": f_user["username"],
            "bio": f_user.get("bio", ""),
            "profile_picture_url": f_user.get("profile_picture_url", "/static/images/sample_user.png")
        })
    return JSONResponse(formatted_followers)

@router.get("/api/profile/{username}/following", name="api_get_following")
async def api_get_following(username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    
    following = get_following(user["id"])
    
    formatted_following = []
    for f_user in following:
        formatted_following.append({
            "id": f_user["id"],
            "username": f_user["username"],
            "bio": f_user.get("bio", ""),
            "profile_picture_url": f_user.get("profile_picture_url", "/static/images/sample_user.png")
        })
    return JSONResponse(formatted_following)

@router.post("/api/profile/edit", status_code=status.HTTP_200_OK, response_model=UserResponse)
async def api_edit_profile(
    bio: Optional[str] = Form(None),
    profile_picture: Optional[UploadFile] = File(None),
    current_user: CurrentUser = Depends(require_auth)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    user_data = get_user_by_id(current_user.id)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    
    updated_profile_picture_url = user_data.get("profile_picture_url", "/static/images/sample_user.png")

    if profile_picture and profile_picture.filename:
        extension = profile_picture.filename.split(".")[-1].lower() if "." in profile_picture.filename else "png"
        allowed_extensions = ["jpg", "jpeg", "png", "gif"]
        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Desteklenmeyen dosya formatı. Sadece {', '.join(allowed_extensions)} kabul edilir."
            )

        file_name = f"{uuid.uuid4()}.{extension}"
        file_path = UPLOAD_DIR / file_name

        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(profile_picture.file, buffer)
            
            old_picture_url = user_data.get("profile_picture_url")
            # Varsayılan resim değilse ve eski resim yükleme dizinindeyse sil
            if old_picture_url and old_picture_url != "/static/images/sample_user.png" and old_picture_url.startswith("/static/uploads/profile_pictures/"):
                old_file_name = old_picture_url.split('/')[-1]
                old_picture_full_path = UPLOAD_DIR / old_file_name
                if old_picture_full_path.exists() and old_picture_full_path.is_file():
                    os.remove(old_picture_full_path)
            
            updated_profile_picture_url = f"/static/uploads/profile_pictures/{file_name}"

        except Exception as e:
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Profil fotoğrafı yüklenirken hata oluştu: {e}")
    
    if update_user_profile(
        user_id=current_user.id,
        bio=bio,
        profile_picture_url=updated_profile_picture_url
    ):
        updated_user_data = get_user_by_id(current_user.id)
        
        # Kullanıcının quiz istatistiklerini ve özetlerini al
        updated_total_quizzes_completed = updated_user_data.get("total_quizzes_completed", 0) # Eğer doğrudan DB'den geliyorsa
        updated_total_correct_answers = updated_user_data.get("total_correct_answers", 0) # Eğer doğrudan DB'den geliyorsa
        updated_total_score = updated_user_data.get("total_score", 0) # Eğer doğrudan DB'den geliyorsa
        updated_highest_score = updated_user_data.get("highest_score", 0) # Eğer doğrudan DB'den geliyorsa

        # Eğer bu istatistikler `get_user_by_id` içinde gelmiyorsa, onları ayrıca çekmelisiniz.
        # Örneğin:
        quiz_summaries_after_update = get_user_quiz_summaries(current_user.id)
        updated_total_quizzes_completed = len(quiz_summaries_after_update)
        updated_total_correct_answers = sum(s['correct_answers'] for s in quiz_summaries_after_update)
        updated_total_score = sum(s['score'] for s in quiz_summaries_after_update)
        updated_highest_score = max(s['score'] for s in quiz_summaries_after_update) if quiz_summaries_after_update else 0


        return UserResponse(
            id=updated_user_data["id"],
            username=updated_user_data["username"],
            email=updated_user_data["email"],
            bio=updated_user_data.get("bio", None),
            profile_picture_url=updated_user_data.get("profile_picture_url", "/static/images/sample_user.png"),
            total_quizzes_completed=updated_total_quizzes_completed,
            total_correct_answers=updated_total_correct_answers,
            total_score=updated_total_score,
            highest_score=updated_highest_score,
            recent_activities=[] # Aktivite listesi burada gönderilmez, ayrı bir endpoint'ten alınır
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profil güncellenemedi veya hiçbir değişiklik yapılmadı.")