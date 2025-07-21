# GeoAI/functions/social/routes.py
from fastapi import APIRouter, Request, Form, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from functions.auth.dependencies import CurrentUser, require_auth
from functions.database import queries as db_queries
from functions.config import settings
import uuid
import os
from pathlib import Path
from pydantic import BaseModel, EmailStr # Pydantic modelleri için
from datetime import datetime # datetime objeleri için

router = APIRouter(tags=["Social"])

templates = Jinja2Templates(directory="templates")

# Pydantic modelleri (routes.py içinde tanımlanabilir veya ayrı bir models.py dosyasına taşınabilir)
class ActivityResponse(BaseModel):
    activity_description: str
    timestamp: datetime # datetime objeleri için

    class Config:
        from_attributes = True # Pydantic v2+ için orm_mode yerine

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    bio: Optional[str] = None
    profile_picture_url: str = "/static/images/sample_user.png"
    total_quizzes_completed: int
    total_correct_answers: int
    total_score: int
    highest_score: int
    recent_activities: List[ActivityResponse] = [] # Bu field'ı dahil ediyoruz
    
    class Config:
        from_attributes = True

@router.get("/social-feed", response_class=HTMLResponse, name="social_feed_page")
async def social_feed_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("social/social_feed.html", {"request": request, "user": current_user})

@router.get("/profile/{username}", response_class=HTMLResponse, name="user_profile")
async def user_profile(request: Request, username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    profile_user = db_queries.get_user_by_username(username)
    if not profile_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    
    followers = db_queries.get_followers(profile_user['id'])
    following = db_queries.get_following(profile_user['id'])
    followers_count = len(followers)
    following_count = len(following)

    is_following_user = False
    if current_user and current_user.id != profile_user['id']:
        is_following_user = db_queries.is_following(current_user.id, profile_user['id'])

    # Son aktiviteleri çek
    profile_user['recent_activities'] = db_queries.get_user_activities(profile_user['id'])

    return templates.TemplateResponse(
        "profile.html", { # Bu şablon yolu doğru kabul edilmiştir, eğer social/profile.html ise düzeltilmelidir
            "request": request,
            "profile_user": profile_user,
            "user": current_user, # Giriş yapmış kullanıcıyı template'e gönder
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following_user": is_following_user
        }
    )

@router.get("/api/search_users", response_class=JSONResponse, name="search_users_api")
async def search_users(search_term: str):
    if not search_term:
        return JSONResponse(content=[], status_code=200)
    users = db_queries.search_users_by_username(search_term)
    return JSONResponse(content=users)

@router.post("/api/follow/{followed_id}", name="follow_user_api")
async def follow_user_api(followed_id: int, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    if db_queries.follow_user(current_user.id, followed_id):
        return JSONResponse(content={"message": "Takip edildi."}, status_code=status.HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zaten takip ediliyor veya hata oluştu.")

@router.post("/api/unfollow/{followed_id}", name="unfollow_user_api")
async def unfollow_user_api(followed_id: int, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    if db_queries.unfollow_user(current_user.id, followed_id):
        return JSONResponse(content={"message": "Takibi bırakıldı."}, status_code=status.HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Takip edilmiyor veya hata oluştu.")

@router.post("/api/profile/edit", response_model=UserResponse, name="edit_profile_api") # response_model eklendi
async def edit_profile_api(
    profile_picture: Optional[UploadFile] = File(None),
    bio: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(require_auth)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    user_data = db_queries.get_user_by_id(current_user.id)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")

    # Mevcut profil fotoğrafı URL'sini al
    updated_profile_picture_url = user_data.get("profile_picture_url", "/static/images/sample_user.png")

    if profile_picture and profile_picture.filename:
        # Dosya uzantısını kontrol et
        extension = profile_picture.filename.split(".")[-1].lower() if "." in profile_picture.filename else "png"
        allowed_extensions = ["jpg", "jpeg", "png", "gif"]
        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Desteklenmeyen dosya formatı. Sadece {', '.join(allowed_extensions)} kabul edilir."
            )

        # Benzersiz dosya adı oluştur
        file_name = f"{uuid.uuid4()}.{extension}"
        
        # Yükleme dizini: static/uploads/profile_pictures
        upload_dir = settings.STATIC_DIR / "uploads" / "profile_pictures"
        upload_dir.mkdir(parents=True, exist_ok=True) # Klasör yoksa oluştur

        file_path = upload_dir / file_name
        
        try:
            # Dosyayı asenkron olarak yaz
            with open(file_path, "wb") as buffer:
                # `await profile_picture.read()` yerine chunk'lar halinde okuma
                while True:
                    chunk = await profile_picture.read(1024) # 1KB'lık parçalar halinde oku
                    if not chunk:
                        break
                    buffer.write(chunk)
            
            # Eski profil resmini sil (eğer varsayılan değilse ve uploads klasöründeyse)
            old_picture_url = user_data.get("profile_picture_url")
            if old_picture_url and old_picture_url.startswith("/static/uploads/profile_pictures/"):
                old_file_name = old_picture_url.split('/')[-1]
                old_picture_full_path = upload_dir / old_file_name
                if old_picture_full_path.exists() and old_picture_full_path.is_file():
                    os.remove(old_picture_full_path)
            
            updated_profile_picture_url = f"/static/uploads/profile_pictures/{file_name}"

        except Exception as e:
            # Hata durumunda yüklenen dosyayı temizle
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Profil fotoğrafı yüklenirken hata: {e}")

    success = db_queries.update_user_profile(
        user_id=current_user.id,
        bio=bio,
        profile_picture_url=updated_profile_picture_url
    )

    if success:
        # Güncellenmiş kullanıcı verilerini tekrar alıp Pydantic modeline dönüştürüyoruz
        updated_user_data = db_queries.get_user_by_id(current_user.id)
        # `recent_activities` doğrudan queries'ten gelmediği için boş liste olarak veya başka bir sorgu ile doldurulmalı
        updated_user_data['recent_activities'] = db_queries.get_user_activities(current_user.id)
        return UserResponse(**updated_user_data) # Dict'i modele çevir
    
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profil güncellenemedi.")

# --- MESAJLAŞMA İLE İLGİLİ ROTLAR ---

@router.get("/messages", response_class=HTMLResponse, name="message_list")
async def message_list(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    
    conversations = db_queries.get_user_conversations(current_user.id)
    
    return templates.TemplateResponse("social/messages.html", { # Şablon yolu güncellendi
        "request": request,
        "user": current_user,
        "conversations": conversations
    })

@router.get("/api/messages/{other_user_id}", response_class=JSONResponse, name="get_messages_api")
async def get_messages_api(other_user_id: int, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    messages = db_queries.get_messages_between_users(current_user.id, other_user_id)
    for msg in messages:
        # Tarih objelerini string'e dönüştür (JSON serileştirme için)
        if isinstance(msg['timestamp'], datetime):
            msg['timestamp'] = msg['timestamp'].isoformat()
    
    return JSONResponse(content=messages)

@router.post("/api/messages/send", response_class=JSONResponse, name="send_message_api")
async def send_message_api(receiver_id: int = Form(...), content: str = Form(...), current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    if not content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mesaj boş olamaz.")

    message_id = db_queries.create_message(current_user.id, receiver_id, content)
    if message_id:
        return JSONResponse(content={"message": "Mesaj gönderildi.", "message_id": message_id}, status_code=status.HTTP_200_OK)
    
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mesaj gönderilemedi.")

@router.get("/api/conversations", response_class=JSONResponse, name="get_conversations_api")
async def get_conversations_api(current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    conversations = db_queries.get_user_conversations(current_user.id)
    
    for conv in conversations:
        # Tarih objelerini JSON serileştirme için string'e dönüştür
        if isinstance(conv['last_message_timestamp'], datetime):
            conv['last_message_timestamp'] = conv['last_message_timestamp'].isoformat()
            
    return JSONResponse(content=conversations)