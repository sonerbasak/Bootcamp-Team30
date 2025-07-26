# GeoAI/functions/social/routes.py
from fastapi import APIRouter, Request, Form, HTTPException, status, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict, Any
from functions.auth.dependencies import CurrentUser, require_auth
from functions.database import queries as db_queries # db_queries import edildi
from functions.config import settings
import uuid
import os
from pathlib import Path
from pydantic import BaseModel, EmailStr
from datetime import datetime

router = APIRouter(tags=["Social"])

templates = Jinja2Templates(directory=settings.BASE_DIR / "templates")

# Pydantic modelleri
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
    profile_picture_url: str = "/static/images/sample_user.png"
    # Genel quiz istatistikleri, artık doğrudan queries.py'den gelen dict'e eklenecek
    total_quizzes_completed: int
    total_correct_answers: int
    total_score: int
    highest_score: int
    # recent_activities doğrudan HTML template'ine gönderildiği için burada zorunlu değil
    # ancak API yanıtları için tutmak istersen uncomment edebilirsin:
    # recent_activities: List[ActivityResponse] = [] 
    
    class Config:
        from_attributes = True

class QuizSummaryResponse(BaseModel):
    id: int
    quiz_type: str
    quiz_name: Optional[str]
    total_questions: int
    correct_answers: int
    score: int
    completed_at: datetime

    class Config:
        from_attributes = True

class CategoryStatResponse(BaseModel):
    category_name: str
    correct_count: int
    wrong_count: int

    class Config:
        from_attributes = True

# --- HTML SAYFA ROTLARI ---

@router.get("/social-feed", response_class=HTMLResponse, name="social_feed_page")
async def social_feed_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    """Sosyal akış sayfasını gösterir."""
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("social/social_feed.html", {"request": request, "user": current_user})

@router.get("/profile/{username}", response_class=HTMLResponse, name="user_profile")
async def user_profile(request: Request, username: str, current_user: CurrentUser = Depends(require_auth)):
    """Belirli bir kullanıcının profil sayfasını gösterir."""
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    profile_user_data = db_queries.get_user_by_username(username)
    if not profile_user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı.")
    
    # db_queries.get_user_by_username fonksiyonu zaten quiz istatistiklerini eklediği için
    # profile_user doğrudan template'e gönderilebilir.
    profile_user = profile_user_data 

    followers = db_queries.get_followers(profile_user['id'])
    following = db_queries.get_following(profile_user['id'])
    followers_count = len(followers)
    following_count = len(following)

    is_following_user = False
    if current_user and current_user.id != profile_user['id']:
        is_following_user = db_queries.is_following(current_user.id, profile_user['id'])

    # Son aktiviteleri çek ve profile_user objesine ekle
    profile_user['recent_activities'] = db_queries.get_user_activities(profile_user['id'])

    # Quiz İstatistiklerini Çek (quiz_stats.db'den)
    user_id = profile_user['id']
    quiz_summaries = db_queries.get_user_quiz_summaries(user_id, limit=5) # Son 5 quiz özeti
    category_stats = db_queries.get_user_category_stats(user_id) # Kategori bazlı istatistikler

    return templates.TemplateResponse(
        "profile.html", {
            "request": request,
            "profile_user": profile_user, # Artık tüm istatistikler burada
            "user": current_user, # Giriş yapmış kullanıcıyı template'e gönder
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following_user": is_following_user,
            "quiz_summaries": quiz_summaries, 
            "category_stats": category_stats,
        }
    )

@router.get("/messages", response_class=HTMLResponse, name="message_list")
async def message_list(request: Request, current_user: CurrentUser = Depends(require_auth)):
    """Kullanıcının mesaj listesi sayfasını gösterir."""
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    
    conversations = db_queries.get_user_conversations(current_user.id)
    
    return templates.TemplateResponse("social/messages.html", {
        "request": request,
        "user": current_user,
        "conversations": conversations
    })

# --- API ROTLARI ---

@router.get("/api/search_users", response_class=JSONResponse, name="search_users_api")
async def search_users(search_term: str) -> List[UserResponse]:
    """Kullanıcı adlarına göre arama yapar ve uygun kullanıcıları döndürür."""
    if not search_term:
        return []
    users = db_queries.search_users_by_username(search_term)
    # db_queries.search_users_by_username zaten istatistikleri döndürüyor
    return users # Pydantic otomatik olarak listeyi doğrular

@router.post("/api/follow/{followed_id}", name="follow_user_api")
async def follow_user_api(followed_id: int, current_user: CurrentUser = Depends(require_auth)):
    """Belirtilen kullanıcıyı takip etme işlemini gerçekleştirir."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    if db_queries.follow_user(current_user.id, followed_id):
        return JSONResponse(content={"message": "Takip edildi."}, status_code=status.HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zaten takip ediliyor veya hata oluştu.")

@router.post("/api/unfollow/{followed_id}", name="unfollow_user_api")
async def unfollow_user_api(followed_id: int, current_user: CurrentUser = Depends(require_auth)):
    """Belirtilen kullanıcıyı takibi bırakma işlemini gerçekleştirir."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    if db_queries.unfollow_user(current_user.id, followed_id):
        return JSONResponse(content={"message": "Takibi bırakıldı."}, status_code=status.HTTP_200_OK)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Takip edilmiyor veya hata oluştu.")

@router.post("/api/profile/edit", response_model=UserResponse, name="edit_profile_api")
async def edit_profile_api(
    profile_picture: Optional[UploadFile] = File(None),
    bio: Optional[str] = Form(None),
    current_user: CurrentUser = Depends(require_auth)
):
    """Kullanıcı profilini (biyografi ve profil fotoğrafı) günceller."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    user_data = db_queries.get_user_by_id(current_user.id)
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
        
        upload_dir = settings.STATIC_DIR / "uploads" / "profile_pictures"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file_name
        
        try:
            with open(file_path, "wb") as buffer:
                while True:
                    chunk = await profile_picture.read(1024)
                    if not chunk:
                        break
                    buffer.write(chunk)
            
            old_picture_url = user_data.get("profile_picture_url")
            # Yalnızca önceden yüklenmiş bir dosya ise sil
            if old_picture_url and old_picture_url.startswith("/static/uploads/profile_pictures/"):
                old_file_name = old_picture_url.split('/')[-1]
                old_picture_full_path = upload_dir / old_file_name
                if old_picture_full_path.exists() and old_picture_full_path.is_file():
                    os.remove(old_picture_full_path)
            
            updated_profile_picture_url = f"/static/uploads/profile_pictures/{file_name}"

        except Exception as e:
            # Yükleme hatası durumunda kısmen yüklenmiş dosyayı temizle
            if file_path.exists():
                os.remove(file_path)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Profil fotoğrafı yüklenirken hata: {e}")

    success = db_queries.update_user_profile(
        user_id=current_user.id,
        bio=bio,
        profile_picture_url=updated_profile_picture_url
    )

    if success:
        updated_user_data = db_queries.get_user_by_id(current_user.id)
        # updated_user_data zaten genel istatistikleri içeriyor
        updated_user_data['recent_activities'] = db_queries.get_user_activities(current_user.id)
        return UserResponse(**updated_user_data)
    
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Profil güncellenemedi.")

@router.get("/api/messages/{other_user_id}", response_class=JSONResponse, name="get_messages_api")
async def get_messages_api(other_user_id: int, current_user: CurrentUser = Depends(require_auth)):
    """İki kullanıcı arasındaki mesajlaşma geçmişini JSON olarak döndürür."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    messages = db_queries.get_messages_between_users(current_user.id, other_user_id)
    # Datetime objelerini ISO formatına çevir (JSON serileştirme için)
    for msg in messages:
        if isinstance(msg.get('timestamp'), datetime):
            msg['timestamp'] = msg['timestamp'].isoformat()
    
    return messages

@router.post("/api/messages/send", response_class=JSONResponse, name="send_message_api")
async def send_message_api(receiver_id: int = Form(...), content: str = Form(...), current_user: CurrentUser = Depends(require_auth)):
    """Yeni bir mesaj gönderir."""
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
    """Kullanıcının tüm sohbetlerini ve son mesajlarını JSON olarak döndürür."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")
    
    conversations = db_queries.get_user_conversations(current_user.id)
    
    # Datetime objelerini ISO formatına çevir (JSON serileştirme için)
    for conv in conversations:
        if isinstance(conv.get('last_message_timestamp'), datetime):
            conv['last_message_timestamp'] = conv['last_message_timestamp'].isoformat()
            
    return conversations