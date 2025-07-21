# functions/social/routes.py
from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Gerekli sorguları içe aktarın
from functions.database.queries import get_user_by_username, get_user_activities, get_user_conversations
from functions.auth.dependencies import require_auth, CurrentUser

router = APIRouter(tags=["Social"])
templates = Jinja2Templates(directory="templates")

@router.get("/social-feed", name="social_feed_page")
async def social_feed_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    # Sosyal akış verilerini buradan çekebilirsiniz
    return templates.TemplateResponse("social/social_feed.html", {"request": request, "user": current_user})

@router.get("/api/user-posts", name="get_user_posts")
async def get_user_posts(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    # Kullanıcıya ait gönderileri veritabanından çekme mantığı
    return {"posts": [{"id": 1, "text": f"Hello from {current_user.username}"}]}

@router.get("/messages", response_class=HTMLResponse, name="message_list")
async def message_list(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    # Kullanıcının tüm sohbetlerini çek
    conversations = get_user_conversations(current_user.id)
    
    return templates.TemplateResponse("social/messages.html", {
        "request": request,
        "user": current_user,
        "conversations": conversations # Dinamik mesaj listesi
    })

# Kullanıcı profili rotası
@router.get("/profile/{username}", response_class=HTMLResponse, name="user_profile")
async def user_profile(request: Request, username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    profile_data = get_user_by_username(username)

    if not profile_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_activities = get_user_activities(profile_data['id'])

    # `profile_data` bir `sqlite3.Row` objesi olduğundan, dict'e çevirmek en güvenlisidir.
    # Aktivite verilerini de dict'e çevirerek şablona gönderebiliriz.
    profile_dict = dict(profile_data)
    profile_dict['recent_activities'] = [dict(activity) for activity in user_activities]

    return templates.TemplateResponse("social/profile.html", { # Şablon yolu güncellendi
        "request": request,
        "user": current_user,       # Giriş yapmış kullanıcı (CurrentUser objesi)
        "profile_user": profile_dict # Görüntülenen profilin verileri (dict)
    })