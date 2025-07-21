# main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import status, Depends

from functions.database.connections import init_dbs
# importu get_current_user_dependency yerine require_auth olarak değiştirildi
from functions.auth.dependencies import require_auth, CurrentUser
from functions.auth.routes import router as auth_router
from functions.quiz.routes import router as quiz_router
from functions.social.routes import router as social_router

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_dbs()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(quiz_router)
app.include_router(social_router)

@app.get("/", response_class=HTMLResponse, name="read_root")
async def read_root(request: Request, current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("turkey.html", {"request": request, "user": current_user})

@app.get("/world", name="world_page")
async def world_page(request: Request, current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("world.html", {"request": request, "user": current_user})