from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai # 'google.generativeai' yerine 'genai' olarak kısaltıldı
import json
import sqlite3 # Veritabanı için eklendi

# .env dosyasını yükle
load_dotenv()

# Gemini API anahtarını yapılandır
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Gemini modelini tanımla
model = genai.GenerativeModel("models/gemini-2.5-flash") # Model adı güncellendi

# FastAPI uygulamasını başlat
app = FastAPI()

# Statik dosyaları (CSS, JS, resimler vb.) sunmak için dizinleri bağla
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data") # Eklenen data klasörü

# HTML template'leri için dizini bağla
templates = Jinja2Templates(directory="templates")

# Veritabanı dosyasının yolu
DATABASE_FILE = "quiz_errors.db"

# Veritabanı bağlantısını kurma ve tablo oluşturma fonksiyonu
def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wrong_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT, -- Kullanıcı ID'si (opsiyonel, oturum yönetimi olursa)
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
    conn.close()

# Uygulama başlamadan önce veritabanını başlat
init_db()


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
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("turkey.html", {"request": request})

# Dünya haritası sayfası
@app.get("/world")
async def world_page(request: Request):
    return templates.TemplateResponse("world.html", {"request": request})

# Yapay zeka quiz oluşturma sayfası (ai.html)
@app.get("/ai.html")
async def ai_page(request: Request):
    query = request.query_params
    city = query.get("city") or query.get("country") or ""
    return templates.TemplateResponse("ai.html", {"request": request, "city": city})

# Eski generate-quiz endpoint'i, artık kullanılmıyor olabilir, ancak bırakıldı.
@app.post("/generate-quiz", response_class=HTMLResponse)
async def create_quiz(request: Request, topic: str = Form(...), count: int = Form(3)):
    prompt = f"{topic} hakkında {count} adet çoktan seçmeli soru hazırla."
    # response = await model.generate_content_async(prompt) # Asenkron model çağrısı
    response = model.generate_content(prompt) # Senkron model çağrısı (daha uygunsa)
    return templates.TemplateResponse("ai.html", {"request": request, "quiz": response.text})

# Quiz oynatma sayfası
@app.get("/quiz.html")
async def quiz_page(request: Request, city: str = ""):
    return templates.TemplateResponse("quiz.html", {"request": request, "city": city})

# Gemini API'den quiz soruları üretme endpoint'i
@app.get("/api/gemini-quiz")
async def generate_quiz(city: str = Query(default=""), count: int = 10):
    categories = [
        "Tarih",
        "Doğal Güzellikler",
        "Yapılar",
        "Tarım Ürünü ve Yemekler",
        "Genel Bilgiler"
    ]
    # Her kategoriden eşit sayıda soru olmasını sağlıyoruz
    # Toplam soru sayısını kategori sayısına bölüyoruz
    questions_per_category = count // len(categories)
    # Kalan soruları ilk kategorilere dağıtmak için
    remaining_questions = count % len(categories)

    prompt_parts = []
    for i, category in enumerate(categories):
        num_questions = questions_per_category
        if i < remaining_questions:
            num_questions += 1 # Kalan soruları ilk kategorilere ekle
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

    # generate_content_async kullanın çünkü FastAPI asenkron çalışır
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
@app.post("/api/save-wrong-question")
async def save_wrong_question(question_data: WrongQuestionData):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO wrong_questions (
                city, category, question_text, option_a, option_b, option_c, option_d,
                correct_answer_letter, user_answer_letter
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
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
        conn.close()
        return JSONResponse(content={"message": "Wrong question saved successfully"}, status_code=200)
    except Exception as e:
        print(f"Error saving wrong question: {e}")
        return JSONResponse(content={"message": "Failed to save wrong question", "error": str(e)}, status_code=500)

# Kaydedilen yanlış soruları çekme endpoint'i
@app.get("/api/get-wrong-questions")
async def get_wrong_questions():
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        conn.row_factory = sqlite3.Row # Bu satırı ekleyin! Satırları dictionary gibi erişilebilir yapar
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM wrong_questions ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        
        wrong_questions = []
        for row in rows:
            question_dict = dict(row) # sqlite3.Row objesini dictionary'ye çevir
            
            # Timestamp'ı string olarak formatla, yoksa None ise de sorun olmasın
            if 'timestamp' in question_dict and question_dict['timestamp'] is not None:
                question_dict['timestamp'] = str(question_dict['timestamp'])
            
            wrong_questions.append(question_dict)
        
        conn.close()
        return JSONResponse(content={"wrong_questions": wrong_questions}, status_code=200)
    except Exception as e:
        print(f"Error fetching wrong questions: {e}")
        return JSONResponse(content={"message": "Failed to fetch wrong questions", "error": str(e)}, status_code=500)

# Yanlış soruları gösteren HTML sayfası rotası
@app.get("/wrong-questions", response_class=HTMLResponse) # <-- .html UZANTISINI KALDIRDIK
async def serve_wrong_questions_page(request: Request):
    return templates.TemplateResponse("wrong_question.html", {"request": request})
