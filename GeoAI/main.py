from fastapi import FastAPI, Request, Form, Query, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai
import json
import sqlite3
from typing import List, Optional
from werkzeug.security import generate_password_hash, check_password_hash

# .env dosyasını yükle
load_dotenv()

# Gemini API anahtarını yapılandır
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Gemini modelini tanımla
model = genai.GenerativeModel("models/gemini-2.5-flash")

# FastAPI uygulamasını başlat
app = FastAPI()

# Statik dosyaları (CSS, JS, resimler vb.) sunmak için dizinleri bağla
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

# HTML template'leri için dizini bağla
templates = Jinja2Templates(directory="templates")

# Veritabanı dosyasının yolu (Yanlış sorular için)
QUIZ_DATABASE_FILE = "quiz_errors.db"
# Kullanıcı veritabanı dosyası
USERS_DATABASE_FILE = "users.db"

# Veritabanı bağlantısını kurma ve tablo oluşturma fonksiyonu (Yanlış sorular için)
def init_quiz_db():
    conn = None
    try:
        conn = sqlite3.connect(QUIZ_DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wrong_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, -- Kullanıcı ID'si (users tablosu ile ilişkilendirilebilir)
                city TEXT NOT NULL,
                category TEXT,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_answer_letter TEXT NOT NULL,
                user_answer_letter TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Wrong questions veritabanı başlatılırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

# Kullanıcı veritabanı bağlantısını kurma ve tablo oluşturma fonksiyonu
def init_users_db():
    conn = None
    try:
        conn = sqlite3.connect(USERS_DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Users veritabanı başlatılırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

# Uygulama başlamadan önce veritabanlarını başlat
init_quiz_db()
init_users_db()

# Pydantic modeli: Frontend'den gelecek yanlış soru verilerini doğrulamak için
class WrongQuestionData(BaseModel):
    city: str
    category: str
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer_letter: str
    user_answer_letter: str

# Anasayfa rotası (turkey.html'i sunar)
@app.get("/", response_class=HTMLResponse, name="read_root")
async def read_root(request: Request):
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")

    # If user is not logged in, redirect to login page
    if not user_id: # Check if user_id cookie exists
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("turkey.html", {"request": request, "user_id": user_id, "username": username})

# Dünya haritası sayfası
@app.get("/world", name="world_page")
async def world_page(request: Request):
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    # Also protect this page if needed
    if not user_id:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("world.html", {"request": request, "user_id": user_id, "username": username})

# Yapay zeka quiz oluşturma sayfası (ai.html)
@app.get("/ai", name="ai_page")
async def ai_page(request: Request):
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    # Also protect this page
    if not user_id:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    query = request.query_params
    city = query.get("city") or query.get("country") or ""
    return templates.TemplateResponse("ai.html", {"request": request, "city": city, "user_id": user_id, "username": username})

# Eski generate-quiz endpoint'i, artık kullanılmıyor olabilir, ancak bırakıldı.
@app.post("/generate-quiz", response_class=HTMLResponse, name="create_quiz") # Name added for consistency
async def create_quiz(request: Request, topic: str = Form(...), count: int = Form(3)):
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    if not user_id:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    prompt = f"{topic} hakkında {count} adet çoktan seçmeli soru hazırla."
    response = await model.generate_content_async(prompt) # Asenkron model çağrısı
    return templates.TemplateResponse("ai.html", {"request": request, "quiz": response.text, "user_id": user_id, "username": username})

# Quiz oynatma sayfası
@app.get("/quiz", response_class=HTMLResponse, name="quiz_page")
async def quiz_page(request: Request, city: str = None, type: str = None):
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    if not user_id:
        # For a *page* request, if the user is not logged in, you *should* redirect them.
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    # If authenticated, render the page
    return templates.TemplateResponse("quiz.html", {"request": request, "city": city, "type": type, "user_id": user_id, "username": username})

# Gemini API'den quiz soruları üretme endpoint'i
@app.get("/api/gemini-quiz", name="generate_quiz_api")
async def generate_quiz_api(request: Request, city: str = Query(default=""), count: int = 10):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required for API access.")
    categories = [
        "Tarih",
        "Doğal Güzellikler",
        "Yapılar",
        "Tarım Ürünü ve Yemekler",
        "Genel Bilgiler"
    ]
    questions_per_category = count // len(categories)
    remaining_questions = count % len(categories)

    prompt_parts = []
    for i, category in enumerate(categories):
        num_questions = questions_per_category
        if i < remaining_questions:
            num_questions += 1
        prompt_parts.append(f"**{category}** kategorisinden {num_questions} adet soru oluştur.")

    base_prompt = f"""
    {city} hakkında aşağıdaki kategorilerden belirtilen sayıda Türkçe çoktan seçmeli soru oluştur.
    Toplamda **tam olarak {count} adet** soru oluşturduğunu kontrol et. Ne bir eksik ne bir fazla.
    Her soru kesin olarak 4 şıklı olsun (A, B, C, D). 4 şıktan az veya fazla şık olmasın.
    Her sorunun cevabı, sadece doğru şıkkın harfi (A, B, C veya D) olsun.

    Her soruyu, şıklarını, doğru cevabı ve **gizli kategori bilgisini** ardında bir boş satır olacak şekilde,
    **kesinlikle aşağıdaki JSON formatına uyarak** oluştur.
    Sadece bir JSON dizisi (array) döndür, başka hiçbir metin veya açıklama ekleme.

    [
      {{
        "kategori": "[Kategori Adı Buraya Gelecek (örn: Tarih)]",
        "soru": "[Soru Metni Buraya Gelecek]",
        "a": "[Şık A Metni]",
        "b": "[Şık B Metni]",
        "c": "[Şık C Metni]",
        "d": "[Şık D Metni]",
        "cevap": "[Sadece doğru şıkkın harfi (örn: A)]"
      }},
      {{
        "kategori": "[Diğer Kategori Adı]",
        "soru": "[Diğer Soru Metni]",
        "a": "[Diğer Şık A Metni]",
        "b": "[Diğer Şık B Metni]",
        "c": "[Diğer Şık C Metni]",
        "d": "[Diğer Şık D Metni]",
        "cevap": "[Diğer Cevap Harfi]"
      }}
      // ... Diğer sorular
    ]

    Oluşturulacak kategoriler ve soru sayıları:
    {"\n".join(prompt_parts)}
    """

    print("\n" + "="*70)
    print("YAPAY ZEKAYA GÖNDERİLEN PROMPT (BACKEND KONSOLU):")
    print(base_prompt)
    print("="*70 + "\n")

    response = await model.generate_content_async(base_prompt)

    try:
        json_start = response.text.find('[')
        json_end = response.text.rfind(']') + 1

        if json_start != -1 and json_end != -1:
            json_string = response.text[json_start:json_end]
            quiz_data_list = json.loads(json_string)
        else:
            raise ValueError("Gemini'den gelen yanıt JSON formatında değil veya hatalı.")

    except json.JSONDecodeError as e:
        print(f"JSON Çözümleme Hatası: {e}")
        print(f"Gemini'den gelen ham yanıt: {response.text}")
        return JSONResponse(
            content={"error": "Quiz verisi JSON olarak çözümlenemedi", "details": str(e)},
            status_code=500
        )
    except ValueError as e:
        print(f"Yanıt Format Hatası: {e}")
        print(f"Gemini'den gelen ham yanıt: {response.text}")
        return JSONResponse(
            content={"error": "Quiz verisi beklenen JSON formatında gelmedi", "details": str(e)},
            status_code=500
        )

    return JSONResponse(content={
        "quiz_data": quiz_data_list,
        "sent_prompt": base_prompt
    })

# Yanlış cevaplanan soruları veritabanına kaydetme endpoint'i
@app.post("/api/save-wrong-question", name="save_wrong_question") # Name added
async def save_wrong_question(question_data: WrongQuestionData, request: Request):
    user_id = request.cookies.get("user_id") # Oturumdaki kullanıcı ID'sini al
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required to save questions.")

    conn = None
    try:
        conn = sqlite3.connect(QUIZ_DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO wrong_questions (
                user_id, city, category, question_text, option_a, option_b, option_c, option_d,
                correct_answer_letter, user_answer_letter
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, # user_id'yi de kaydet
                question_data.city,
                question_data.category,
                question_data.question_text,
                question_data.option_a,
                question_data.option_b,
                question_data.option_c,
                question_data.option_d,
                question_data.correct_answer_letter,
                question_data.user_answer_letter,
            ),
        )
        conn.commit()
        return JSONResponse(content={"message": "Wrong question saved successfully"}, status_code=200)
    except sqlite3.Error as e:
        print(f"Error saving wrong question: {e}")
        return JSONResponse(content={"message": "Failed to save wrong question", "error": str(e)}, status_code=500)
    finally:
        if conn:
            conn.close()

# Kaydedilen yanlış soruları çekme endpoint'i
@app.get("/api/get-wrong-questions", name="get_wrong_questions")
async def get_wrong_questions(request: Request):
    user_id = request.cookies.get("user_id")
    if not user_id:
        # ÖNEMLİ DEĞİŞİKLİK BURADA: JSONResponse yerine HTTPException kullanıyoruz
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı girişi yapılmamış. Yanlış sorular görüntülenemez.")

    conn = None
    try:
        conn = sqlite3.connect(QUIZ_DATABASE_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wrong_questions WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
        rows = cursor.fetchall()

        wrong_questions = []
        for row in rows:
            question_dict = dict(row)

            if 'timestamp' in question_dict and question_dict['timestamp'] is not None:
                question_dict['timestamp'] = str(question_dict['timestamp'])

            wrong_questions.append(question_dict)

        return JSONResponse(content={"wrong_questions": wrong_questions}, status_code=200)
    except sqlite3.Error as e:
        print(f"Error fetching wrong questions: {e}")
        # Hata durumunda da HTTPException kullanmak daha tutarlı olacaktır.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Yanlış soruları çekerken hata oluştu: {str(e)}")
    finally:
        if conn:
            conn.close()
            
# Yanlış sorular sayfası için yönlendirme rotası
@app.get("/wrong-questions", response_class=HTMLResponse, name="serve_wrong_questions_page")
async def serve_wrong_questions_page(request: Request):
    """
    Yanlış cevaplanan sorular sayfasını, 'quiz.html'i kullanarak ve type=wrong-questions
    parametresi ile yönlendirerek render eder.
    """
    user_id = request.cookies.get("user_id")
    username = request.cookies.get("username")
    if not user_id:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("quiz.html", {"request": request, "type": "wrong-questions", "user_id": user_id, "username": username})

# Yeni: Doğru cevaplanan yanlış soruları veritabanından silme endpoint'i
@app.post("/api/remove-correctly-answered-questions", name="remove_correctly_answered_questions") # Name added
async def remove_correctly_answered_questions(
    question_ids: List[int], # JavaScript'ten gelecek olan doğru cevaplanan yanlış soru kayıtlarının ID'leri
    request: Request
):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Kullanıcı girişi yapılmamış.")

    conn = None
    try:
        conn = sqlite3.connect(QUIZ_DATABASE_FILE)
        cursor = conn.cursor()
        deleted_count = 0
        for q_id in question_ids:
            # Sadece belirli bir ID'ye ve mevcut user_id'ye sahip yanlış soruyu sil
            cursor.execute("DELETE FROM wrong_questions WHERE id = ? AND user_id = ?", (q_id, user_id))
            deleted_count += cursor.rowcount # Silinen satır sayısını alır
        conn.commit()
        return JSONResponse(
            content={"message": f"{deleted_count} yanlış soru kaydı başarıyla veritabanından kaldırıldı."},
            status_code=200
        )
    except sqlite3.Error as e:
        print(f"Yanlış soruları kaldırırken hata oluştu: {e}")
        raise HTTPException(status_code=500, detail=f"Soruları kaldırırken hata oluştu: {str(e)}")
    finally:
        if conn:
            conn.close()

# Giriş Sayfası (GET)
@app.get("/login", response_class=HTMLResponse, name="login_page")
async def login_page(request: Request):
    # Eğer kullanıcı zaten giriş yapmışsa, anasayfaya yönlendir
    if request.cookies.get("user_id"):
        return RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request})

# Giriş İşlemi (POST)
@app.post("/login", response_class=HTMLResponse, name="login_user")
async def login_user(request: Request, username: str = Form(...), password: str = Form(...)):
    conn = None
    try:
        conn = sqlite3.connect(USERS_DATABASE_FILE) # Corrected typo: sqlite3.connect
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone() # Kullanıcıyı al

        if user and check_password_hash(user[2], password):
            # Giriş başarılı, çerezleri ayarla ve anasayfaya yönlendir
            response = RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
            # secure=True in set_cookie should only be used if you are serving via HTTPS
            response.set_cookie(key="user_id", value=str(user[0]), httponly=True, samesite="Lax", secure=False)
            response.set_cookie(key="username", value=user[1], httponly=True, samesite="Lax", secure=False)
            return response
        else:
            # Hatalı giriş durumunda hata mesajı ile giriş sayfasını tekrar göster
            return templates.TemplateResponse("login.html", {"request": request, "error": "Kullanıcı adı veya şifre hatalı."})
    except sqlite3.Error as e:
        print(f"Giriş hatası: {e}")
        return templates.TemplateResponse("login.html", {"request": request, "error": f"Bir sunucu hatası oluştu: {str(e)}"})
    finally:
        if conn:
            conn.close()

# Kayıt Ol Sayfası (GET)
@app.get("/register", response_class=HTMLResponse, name="register_page")
async def register_page(request: Request):
    # Eğer kullanıcı zaten giriş yapmışsa, anasayfaya yönlendir
    if request.cookies.get("user_id"):
        return RedirectResponse(url=request.url_for("read_root"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("register.html", {"request": request})

# Hesap Oluşturma İşlemi (POST)
@app.post("/register", response_class=HTMLResponse, name="register_user")
async def register_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    conn = None
    try:
        conn = sqlite3.connect(USERS_DATABASE_FILE)
        cursor = conn.cursor()

        # Kullanıcı adı veya e-posta zaten mevcut mu kontrol et
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            return templates.TemplateResponse("register.html", {"request": request, "error": "Bu kullanıcı adı veya e-posta zaten kullanılıyor."})

        # Şifreyi hash'le
        hashed_password = generate_password_hash(password)

        # Kullanıcıyı veritabanına ekle
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                       (username, email, hashed_password))
        conn.commit()

        # Başarılı kayıt sonrası giriş sayfasına yönlendir ve mesaj göster
        return templates.TemplateResponse("login.html", {"request": request, "message": "Hesabınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz."})
    except sqlite3.Error as e:
        print(f"Kayıt hatası: {e}")
        return templates.TemplateResponse("register.html", {"request": request, "error": f"Kayıt olurken bir hata oluştu: {str(e)}"})
    finally:
        if conn:
            conn.close()

# Çıkış Yapma (GET)
@app.get("/logout", name="logout_user")
async def logout_user():
    # Anasayfaya yönlendir ve çerezleri sil
    response = RedirectResponse(url=app.url_path_for("read_root"), status_code=status.HTTP_302_FOUND)
    response.delete_cookie("user_id")
    response.delete_cookie("username")
    return response