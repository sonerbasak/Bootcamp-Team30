from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai
import json

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-2.5-flash")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("turkey.html", {"request": request})


@app.get("/world")
async def world_page(request: Request):
    return templates.TemplateResponse("world.html", {"request": request})


@app.get("/ai.html")
async def ai_page(request: Request):
    query = request.query_params
    city = query.get("city") or query.get("country") or ""
    return templates.TemplateResponse("ai.html", {"request": request, "city": city})


@app.post("/generate-quiz", response_class=HTMLResponse)
async def create_quiz(request: Request, topic: str = Form(...), count: int = Form(3)):
    prompt = f"{topic} hakkında {count} adet çoktan seçmeli soru hazırla."
    response = model.generate_content(prompt)
    return templates.TemplateResponse("ai.html", {"request": request, "quiz": response.text})

@app.get("/quiz.html")
async def quiz_page(request: Request, city: str = ""):
    return templates.TemplateResponse("quiz.html", {"request": request, "city": city})

class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    answer: str

@app.get("/api/gemini-quiz")
async def generate_quiz(city: str = Query(default=""), count: int = 10):
    # Kategorileri belirtiyoruz
    categories = [
        "Tarih",
        "Doğal Güzellikler",
        "Yapılar",
        "Tarım Ürünü ve Yemekler",
        "Genel Bilgiler"
    ]
    # Her kategoriden eşit sayıda soru olmasını sağlıyoruz
    questions_per_category = count // len(categories)
    
    # Prompt'u daha yapılandırılmış hale getiriyoruz
    prompt_parts = []
    for category in categories:
        prompt_parts.append(f"**{category}** kategorisinden {questions_per_category} adet soru oluştur.")

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
    
    # Prompt'u Python konsoluna yazdırıyoruz (backend tarafı)
    print("\n" + "="*70)
    print("YAPAY ZEKAYA GÖNDERİLEN PROMPT (BACKEND KONSOLU):")
    print(base_prompt)
    print("="*70 + "\n")

    response = await model.generate_content_async(base_prompt)
    
    # Gemini'den gelen metni JSON olarak parse etmeye çalışın
    try:
        # Gemini'nin yanıtı bazen JSON'dan önce/sonra ek metin içerebilir.
        # Sadece JSON bloğunu ayıklamaya çalışın.
        json_start = response.text.find('[')
        json_end = response.text.rfind(']') + 1
        
        if json_start != -1 and json_end != -1:
            json_string = response.text[json_start:json_end]
            quiz_data_list = json.loads(json_string)
        else:
            # JSON formatında gelmezse hata fırlat
            raise ValueError("Gemini'den gelen yanıt JSON formatında değil.")

    except json.JSONDecodeError as e:
        print(f"JSON Çözümleme Hatası: {e}")
        print(f"Gemini'den gelen ham yanıt: {response.text}")
        # Hata durumunda boş bir liste veya hata mesajı döndürebilirsiniz
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
    
    # Frontend'e JSON olarak gönderilecek veriyi oluşturuyoruz
    # Bu sefer quiz_text yerine doğrudan parse edilmiş quiz_data_list'i gönderiyoruz.
    return JSONResponse(content={
        "quiz_data": quiz_data_list, # Parse edilmiş quiz verisi
        "sent_prompt": base_prompt   # Gönderilen prompt metni
    })
