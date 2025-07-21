# functions/social/routes.py
from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Assuming you have a get_user_by_username function
from functions.database.queries import get_user_by_username 
from functions.auth.dependencies import require_auth, CurrentUser

router = APIRouter(tags=["Social"])
templates = Jinja2Templates(directory="templates")

@router.get("/social-feed", name="social_feed_page")
async def social_feed_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("social_feed.html", {"request": request, "user": current_user})

@router.get("/api/user-posts", name="get_user_posts")
async def get_user_posts(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    # Logic to fetch posts for the current_user
    return {"posts": [{"id": 1, "text": f"Hello from {current_user.username}"}]}

@router.get("/messages", response_class=HTMLResponse, name="message_list")
async def message_list(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    messages = [] # Placeholder for actual message data
    return templates.TemplateResponse("messages.html", {"request": request, "user": current_user, "messages": messages})

# New route for user profile
@router.get("/profile/{username}", response_class=HTMLResponse, name="user_profile")
async def user_profile(request: Request, username: str, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    # Fetch profile data for the given username from your database
    profile_data = get_user_by_username(username) # Ensure this function exists in functions.database.queries

    if not profile_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return templates.TemplateResponse("user_profile.html", {
        "request": request,
        "user": current_user,       # The logged-in user
        "profile_user": profile_data # The user whose profile is being viewed
    })