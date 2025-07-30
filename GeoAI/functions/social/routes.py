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

class PostCreate(BaseModel):
    content: str
    image_url: Optional[str] = None 
    topic: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    user_id: int
    username: str # Post sahibinin kullanıcı adı
    profile_picture_url: str # Post sahibinin profil resmi URL'si
    content: str
    timestamp: datetime  # Post oluşturulma zamanı
    image_url: Optional[str] = None
    topic: str

    class Config:
        from_attributes = True
        # Datetime objelerini otomatik olarak ISO formatına çevirmek için
        json_encoders = {datetime: lambda dt: dt.isoformat()}

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
    
    profile_user = profile_user_data 

    # Takipçi ve Takip Edilenler listelerini çekin
    # Her bir kullanıcı için 'is_followed_by_current_user' bilgisini ekleyin
    raw_followers = db_queries.get_followers(profile_user['id'])
    followers_with_status = []
    for follower in raw_followers:
        follower_data = db_queries.get_user_by_id(follower['follower_id']) # Takipçinin tam bilgilerini al
        if follower_data:
            # Oturum açmış kullanıcı, bu takipçiyi takip ediyor mu?
            is_followed_by_current_user = False
            if current_user and current_user.id:
                is_followed_by_current_user = db_queries.is_following(current_user.id, follower_data['id'])
            
            # Burada 'id' alanını da döndürüyoruz, JavaScript'te currentUserId ile karşılaştırmak için önemli
            followers_with_status.append({
                "id": follower_data['id'],
                "username": follower_data['username'],
                "profile_picture_url": follower_data.get('profile_picture_url', "/static/images/sample_user.png"),
                "bio": follower_data.get('bio', ''),
                "is_followed_by_current_user": is_followed_by_current_user
            })
    
    raw_following = db_queries.get_following(profile_user['id'])
    following_with_status = []
    for followed in raw_following:
        followed_data = db_queries.get_user_by_id(followed['followed_id']) # Takip edilenin tam bilgilerini al
        if followed_data:
            # Oturum açmış kullanıcı, bu takip edileni takip ediyor mu? (Bu zaten true olmalı, ama tutarlılık için)
            is_followed_by_current_user = False
            if current_user and current_user.id:
                is_followed_by_current_user = db_queries.is_following(current_user.id, followed_data['id'])
            
            following_with_status.append({
                "id": followed_data['id'],
                "username": followed_data['username'],
                "profile_picture_url": followed_data.get('profile_picture_url', "/static/images/sample_user.png"),
                "bio": followed_data.get('bio', ''),
                "is_followed_by_current_user": is_followed_by_current_user # Her zaman true olmalı bu listede
            })

    followers_count = len(followers_with_status)
    following_count = len(following_with_status)

    is_following_user = False
    if current_user and current_user.id != profile_user['id']:
        is_following_user = db_queries.is_following(current_user.id, profile_user['id'])

    profile_user['recent_activities'] = db_queries.get_user_activities(profile_user['id'])

    user_id = profile_user['id']
    quiz_summaries = db_queries.get_user_quiz_summaries(user_id, limit=5)
    category_stats = db_queries.get_user_category_stats(user_id)

    return templates.TemplateResponse(
        "profile.html", {
            "request": request,
            "profile_user": profile_user,
            "user": current_user, 
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following_user": is_following_user,
            "quiz_summaries": quiz_summaries, 
            "category_stats": category_stats,
            # Bu listeleri JavaScript'e JSON API aracılığıyla göndereceğiz, doğrudan template'e değil.
            # "followers_list": followers_with_status,
            # "following_list": following_with_status,
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
    
    # Gönderici ve alıcı bilgilerini toplamak için
    # Performans için, ilgili tüm kullanıcıların bilgilerini tek seferde çekip bir map oluşturmak daha iyi.
    all_involved_user_ids = set()
    for msg in messages:
        all_involved_user_ids.add(msg['sender_id'])
        # other_user_id de listeye eklendiğinden emin olun (mesajlarda receiver_id olarak gelir)
        all_involved_user_ids.add(other_user_id) 
        all_involved_user_ids.add(current_user.id) # current_user da gerekebilir

    user_info_map = {}
    for user_id in all_involved_user_ids:
        user_data = db_queries.get_user_by_id(user_id)
        if user_data:
            user_info_map[user_id] = {
                "username": user_data["username"],
                "profile_picture_url": user_data["profile_picture_url"]
            }

    formatted_messages = []
    for msg in messages:
        sender_info = user_info_map.get(msg['sender_id'], {})
        
        formatted_messages.append({
            "id": msg['id'],
            "sender_id": msg['sender_id'],
            "receiver_id": msg['receiver_id'],
            "content": msg['content'],
            # Timestamp'ı kontrol et ve ISO formatına çevir
            "timestamp": msg['timestamp'].isoformat() if isinstance(msg.get('timestamp'), datetime) else str(msg['timestamp']),
            "sender_username": sender_info.get("username", "Bilinmeyen Kullanıcı"),
            "sender_profile_picture_url": sender_info.get("profile_picture_url", "/static/images/sample_user.png")
        })
    
    return formatted_messages # Güncellenmiş listeyi döndür

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

@router.post("/api/remove_follower/{follower_username}", response_model=Dict[str, str], name="remove_follower_api")
async def remove_follower_api(
    follower_username: str,
    current_user: CurrentUser = Depends(require_auth)
):
    """
    Oturum açmış kullanıcının takipçi listesinden belirli bir takipçiyi çıkarır.
    Yani, o kişinin sizi takip etmesini engeller.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")

    # Kendi kendinizi takipçi listenizden çıkaramazsınız
    if follower_username == current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kendinizi takipçilerinizden çıkaramazsınız.")

    # Çıkarılacak takipçinin bilgilerini al
    follower_data = db_queries.get_user_by_username(follower_username)
    if not follower_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Takipçi bulunamadı.")
    
    follower_id = follower_data['id']

    # Bu kullanıcının gerçekten current_user'ı takip ettiğinden emin olalım
    # (yani follower_id, current_user.id'yi takip ediyor mu?)
    is_following_me = db_queries.check_if_user_follows(follower_id, current_user.id)
    if not is_following_me:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{follower_username} zaten sizi takip etmiyor.")

    # Takip ilişkisini kaldır
    success = db_queries.remove_follower_relationship(follower_id=follower_id, followed_id=current_user.id)

    if success:
        return JSONResponse(content={"message": f"{follower_username} başarıyla takipçilerinizden çıkarıldı."}, status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Takipçiyi çıkarma işlemi başarısız oldu.")

# --- YENİ EKLENEN API ROTLARI ---
@router.get("/api/posts", response_model=List[PostResponse], name="get_posts_api")
async def get_posts_api(
    request: Request,
    limit: int = 10,
    offset: int = 0,
    topic: Optional[str] = "Tümü",
    current_user: CurrentUser = Depends(require_auth)
):
    """Sosyal akış gönderilerini listeler."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")

    posts = db_queries.get_posts(limit=limit, offset=offset, topic=topic)

    formatted_posts = []
    for post in posts:
        user_data = db_queries.get_user_by_id(post['user_id'])
        if user_data:
            formatted_posts.append(PostResponse(
                id=post['id'],
                user_id=post['user_id'],
                username=user_data.get('username', 'Bilinmeyen Kullanıcı'),
                profile_picture_url=user_data.get('profile_picture_url', "/static/images/sample_user.png"),
                content=post['content'],
                timestamp=post['timestamp'], # BURASI: format_time_ago fonksiyonunu kullanın
                image_url=post.get('image_url'),
                topic=post.get('topic', 'Genel'),
                likes=post.get('likes', 0), # Eğer likes/comments sütunları varsa
                comments=post.get('comments', 0)
            ))
        else:
            # Kullanıcı bulunamazsa varsayılan bilgilerle ekle
            formatted_posts.append(PostResponse(
                id=post['id'],
                user_id=post['user_id'],
                username='Bilinmeyen Kullanıcı',
                profile_picture_url="/static/images/sample_user.png",
                content=post['content'],
                timestamp=db_queries.format_time_ago(post['timestamp']), # BURASI: format_time_ago fonksiyonunu kullanın
                image_url=post.get('image_url'),
                topic=post.get('topic', 'Genel'),
                likes=post.get('likes', 0),
                comments=post.get('comments', 0)
            ))

    return formatted_posts


@router.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED, name="create_post_api")
async def create_post_api(
    content: str = Form(...), # Form veri olarak içeriği al
    topic: Optional[str] = Form("Genel"), # Form veri olarak konuyu al, isteğe bağlı yapıldı
    image: Optional[UploadFile] = File(None), # Dosya yüklemesi için UploadFile kullanın
    current_user: CurrentUser = Depends(require_auth)
):
    """Yeni bir sosyal akış gönderisi oluşturur."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")

    if not content.strip(): # post_data.content yerine doğrudan content kullanıyoruz
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Gönderi içeriği boş olamaz.")

    image_url = None
    if image:
        try:
            upload_dir = Path("static/images/posts") # Görseli kaydedeceğiniz klasör
            upload_dir.mkdir(parents=True, exist_ok=True) # Klasörü yoksa oluştur

            file_extension = Path(image.filename).suffix.lower()
            if file_extension not in [".jpg", ".jpeg", ".png", ".gif"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sadece JPG, JPEG, PNG veya GIF formatında görseller yüklenebilir.")

            # Benzersiz dosya adı oluştur
            image_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = upload_dir / image_filename

            # Dosyayı sunucuya kaydet
            with open(file_path, "wb") as buffer:
                while contents := await image.read(1024 * 1024): # 1MB'lık parçalar halinde oku
                    buffer.write(contents)
            
            image_url = f"/static/images/posts/{image_filename}" # Frontend'in erişebileceği URL

        except Exception as e:
            # Dosya yükleme hatasını yakala ve daha açıklayıcı bir mesajla döndür
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Görsel yüklenirken bir hata oluştu: {e}")

    # db_queries.create_post fonksiyonunu çağır
    new_post_id = db_queries.create_post(
        user_id=current_user.id,
        content=content, # content doğrudan kullanılıyor
        image_url=image_url, # image_url kullanılıyor
        topic=topic # topic doğrudan kullanılıyor
    )

    if not new_post_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gönderi oluşturulurken bir hata oluştu.")

    # Oluşturulan postu döndürmek için veritabanından tekrar çekin
    created_post_data = db_queries.get_post_by_id(new_post_id)
    if not created_post_data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Oluşturulan gönderi bulunamadı.")
    
    # PostResponse modeli için gerekli kullanıcı bilgilerini ekleyin
    post_owner_data = db_queries.get_user_by_id(created_post_data['user_id'])
    if not post_owner_data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gönderi sahibinin bilgileri bulunamadı.")

    # created_post_data'yı PostResponse modeline uygun hale getir
    final_post_response = PostResponse(
        id=created_post_data['id'],
        user_id=created_post_data['user_id'],
        username=post_owner_data.get('username', 'Bilinmeyen Kullanıcı'),
        profile_picture_url=post_owner_data.get('profile_picture_url', "/static/images/sample_user.png"),
        content=created_post_data['content'],
        timestamp=created_post_data['timestamp'],
        image_url=created_post_data.get('image_url'),
        topic=created_post_data.get('topic', 'Genel')
    )
    
    return final_post_response
