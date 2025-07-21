# GeoAI/main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import status, Depends

from functions.database.connections import init_dbs # Sadece init_dbs'i import ediyoruz
# from functions.database.queries import create_initial_tables # <-- BU SATIR YORUM SATIRI YAPILDI/KALDIRILDI!
from functions.auth.dependencies import require_auth, CurrentUser
from functions.auth.routes import router as auth_router
from functions.quiz.routes import router as quiz_router
from functions.social.routes import router as social_router # Sosyal modül rotaları

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init_dbs() # Sadece bu fonksiyon çağrılsın
    # print("Veritabanı tabloları kontrol edildi/oluşturuldu.") # Bu mesaj init_dbs'ten geliyor zaten

# Statik dosyaların sunulacağı dizinleri belirtiyoruz
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data") # Eğer data klasörünüz varsa

templates = Jinja2Templates(directory="templates")

# Uygulamaya rotaları dahil ediyoruz
app.include_router(auth_router)
app.include_router(quiz_router)
app.include_router(social_router) # Sosyal rotalar dahil edildi

@app.get("/", response_class=HTMLResponse, name="read_root")
async def read_root(request: Request, current_user: CurrentUser = Depends(require_auth)):
    # Kullanıcı giriş yapmamışsa login sayfasına yönlendir
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    # Giriş yapmışsa turkey.html şablonunu render et
    return templates.TemplateResponse("turkey.html", {"request": request, "user": current_user})

@app.get("/world", name="world_page")
async def world_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    # Kullanıcı giriş yapmamışsa login sayfasına yönlendir
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    # Giriş yapmışsa world.html şablonunu render et
    return templates.TemplateResponse("world.html", {"request": request, "user": current_user})