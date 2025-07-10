from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import google.generativeai as genai

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


@app.get("/world.html")
async def world_page(request: Request):
    return templates.TemplateResponse("world.html", {"request": request})


@app.get("/ai.html")
async def ai_page(request: Request):
    city = request.query_params.get("city", "")
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
async def generate_quiz(city: str = Query(default="")):
    prompt = f"""
    {city} hakkında 5 adet Türkçe çoktan seçmeli bilgi sorusu oluştur.
    Her bir soru şu şekilde olsun:

    Soru: ...
    A) ...
    B) ...
    C) ...
    D) ...
    Doğru Cevap: X
    """
    response = await model.generate_content_async(prompt)
    return JSONResponse(content={"quiz_text": response.text})
