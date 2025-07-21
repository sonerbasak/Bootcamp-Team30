# functions/auth/routes.py
from fastapi import APIRouter, Request, Form, Depends, status, HTTPException # HTTPException eklendi
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse # JSONResponse eklendi
from fastapi.templating import Jinja2Templates
from typing import Optional, List, Dict # Optional, List, Dict eklendi

from functions.database.queries import get_user_by_username, create_user, get_user_by_id, search_users_by_username # search_users_by_username eklendi
from functions.auth.services import hash_password, verify_password, set_auth_cookies, clear_auth_cookies
from functions.auth.dependencies import require_auth, CurrentUser

router = APIRouter(tags=["Auth"])
templates = Jinja2Templates(directory="templates")

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
            # DÜZELTME BURADA: request.url_for() çıktısını string'e çeviriyoruz
            "profile_url": str(request.url_for("user_profile", username=user_data["username"])) 
        })
    
    return JSONResponse(safe_users)