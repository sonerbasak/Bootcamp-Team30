# functions/quiz/routes.py
from fastapi import APIRouter, Request, Query, HTTPException, status, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict
import random # random modülü eklendi

from functions.auth.dependencies import require_auth, CurrentUser 
from functions.database.queries import save_wrong_question_to_db, get_wrong_questions_from_db, update_user_quiz_stats, delete_wrong_questions_from_db # delete_wrong_questions_from_db eklendi
from functions.quiz.services import generate_quiz_from_gemini
from functions.database import queries as db_queries
# WrongQuestion modelini import edin. Eğer models/wrong_questions.py dosyanız varsa oradan,
# yoksa direkt veritabanı sorgularınızın döndürdüğü dict yapısını kullanırız.
# from functions.models.wrong_questions import WrongQuestion as WrongQuestionModel # Eğer bir modeliniz varsa

router = APIRouter(tags=["Quiz"])
templates = Jinja2Templates(directory="templates")

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

# Quiz cevaplarını almak için Pydantic modeli
class QuizAnswer(BaseModel):
    question_id: int # Eğer her sorunun bir ID'si varsa
    user_answer: str # Kullanıcının verdiği cevap (örneğin 'A', 'B', 'C', 'D')
    correct_answer: str # Doğru cevap (örneğin 'C') - Bu veritabanına kaydedilirken `correct_answer_letter` olacak
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    city: str
    category: str

class QuizResultRequest(BaseModel):
    answers: List[QuizAnswer]
    # Quiz ID'si veya benzeri bilgiler de eklenebilir

# KULLANICI İSTATİSTİKLERİNİ GÜNCELLEYEN ROTA
@router.post("/api/submit-quiz-results", name="submit_quiz_results")
async def submit_quiz_results(request: Request, quiz_results: QuizResultRequest, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    total_questions = len(quiz_results.answers)
    correct_answers_count = 0
    score_earned = 0
    wrong_answers_details = []
    correctly_answered_wrong_question_ids = [] # Daha önce yanlış cevaplanmış ve şimdi doğru cevaplanan soruların ID'leri

    for answer_data in quiz_results.answers:
        # Doğru cevabı kontrol et
        if answer_data.user_answer == answer_data.correct_answer:
            correct_answers_count += 1
            score_earned += 10 # Her doğru cevap için varsayılan 10 puan
            # Eğer bu soru daha önce yanlış cevaplanan bir sorudan geliyorsa (tekrar çöz modunda),
            # o sorunun ID'sini topla.
            if answer_data.question_id: # question_id varsa bu bir WrongQuestion olabilir
                correctly_answered_wrong_question_ids.append(answer_data.question_id)
        else:
            # Yanlış cevapları 'wrong_questions' tablosuna kaydet
            wrong_answers_details.append(answer_data)
            save_wrong_question_to_db(
                user_id=current_user.id,
                city=answer_data.city,
                category=answer_data.category,
                question_text=answer_data.question_text,
                option_a=answer_data.option_a,
                option_b=answer_data.option_b, 
                option_c=answer_data.option_c,
                option_d=answer_data.option_d,
                correct_answer_letter=answer_data.correct_answer,
                user_answer_letter=answer_data.user_answer
            )
    
    # KULLANICI İSTATİSTİKLERİNİ GÜNCELLEME FONKSİYONUNU ÇAĞIR
    update_user_quiz_stats(
        user_id=current_user.id,
        score_earned=score_earned,
        correct_answers_count=correct_answers_count
    )

    # Eğer tekrar çözme modunda doğru cevaplanan yanlış sorular varsa, bunları veritabanından sil
    if correctly_answered_wrong_question_ids:
        delete_wrong_questions_from_db(current_user.id, correctly_answered_wrong_question_ids)

    return JSONResponse({
        "message": "Quiz sonuçları başarıyla kaydedildi.",
        "total_questions": total_questions,
        "correct_answers": correct_answers_count,
        "score_earned": score_earned,
        "wrong_answers_count": len(wrong_answers_details),
        "profile_updated": True 
    })


@router.get("/ai", name="ai_page")
async def ai_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    query = request.query_params
    city = query.get("city") or query.get("country") or ""
    print(f"DEBUG: AI Page - current_user: {current_user.username if current_user else 'None'}, City: {city}")
    return templates.TemplateResponse("ai.html", {"request": request, "city": city, "user": current_user})

@router.get("/quiz", response_class=HTMLResponse, name="quiz_page")
async def quiz_page(request: Request, city: str = None, type: str = None, current_user: CurrentUser = Depends(require_auth)):
    wrong_questions = []
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "city": city,
        "type": type,
        "user": current_user,
        "wrong_questions": wrong_questions # Ensure this is always a list or dict
    })

@router.get("/api/gemini-quiz", name="generate_quiz_api")
async def generate_quiz_api(request: Request, city: str = Query(default=""), count: int = 10, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        quiz_data_list = await generate_quiz_from_gemini(city, count)
        return JSONResponse(content={"quiz_data": quiz_data_list})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/api/save-wrong-question", name="save_wrong_question")
async def save_wrong_question(question_data: WrongQuestionData, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        save_wrong_question_to_db(
            user_id=current_user.id,
            city=question_data.city,
            category=question_data.category,
            question_text=question_data.question_text,
            option_a=question_data.option_a,
            option_b=question_data.option_b,
            option_c=question_data.option_c,
            option_d=question_data.option_d,
            correct_answer_letter=question_data.correct_answer_letter,
            user_answer_letter=question_data.user_answer_letter,
        )
        return JSONResponse(content={"message": "Wrong question saved successfully"}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save wrong question: {str(e)}")

@router.get("/api/get-wrong-questions", name="get_wrong_questions")
async def get_wrong_questions_api(current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        wrong_questions = get_wrong_questions_from_db(current_user.id)
        for q in wrong_questions:
            if 'timestamp' in q and q['timestamp'] is not None:
                q['timestamp'] = str(q['timestamp']) # Ensure timestamp is serializable
        return JSONResponse(content={"wrong_questions": wrong_questions}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Yanlış soruları çekerken hata oluştu: {str(e)}")


# YENİ EKLENEN ROTA: Yanlış cevaplanan soruları quiz formatında döndürür
@router.get("/api/wrong_quiz_questions", response_model=List[Dict], name="get_wrong_quiz_questions")
async def get_wrong_quiz_questions(
    request: Request,
    current_user: CurrentUser = Depends(require_auth) # Kullanıcı oturumunu almak için
):
    if not current_user:
        # Kullanıcı giriş yapmamışsa hata döndür veya boş liste
        raise HTTPException(status_code=401, detail="Yetkilendirme gereklidir.")

    # Kullanıcının yanlış cevapladığı tüm soruları veritabanından çek
    # db_queries.get_wrong_questions_from_db fonksiyonunun liste döndürdüğünü varsayıyoruz
    all_wrong_questions = db_queries.get_wrong_questions_from_db(current_user.id)

    if not all_wrong_questions:
        return [] # Yanlış soru yoksa boş liste döndür

    # Maksimum 10 soru seçin
    num_questions_to_select = min(len(all_wrong_questions), 10)
    # random.sample, bir listeden rastgele öğeleri tekrarsız seçer.
    selected_questions = random.sample(all_wrong_questions, num_questions_to_select)

    # Seçilen soruları quiz formatına dönüştür
    # Not: Bu dönüşüm yapısı, quiz-script.js'deki loadQuizQuestions fonksiyonunuzun beklediği formata uygun olmalı.
    quiz_questions = []
    for q_data in selected_questions:
        # DB'den gelen dict yapısından değerleri al
        question_text = q_data.get('question_text', '')
        option_a = q_data.get('option_a', '')
        option_b = q_data.get('option_b', '')
        option_c = q_data.get('option_c', '')
        option_d = q_data.get('option_d', '')
        correct_answer_letter = q_data.get('correct_answer_letter', '').upper()
        city = q_data.get('city', 'Genel')
        category = q_data.get('category', 'Quiz')
        wrong_question_id = q_data.get('id') # Yanlış sorunun ID'sini al

        # Seçenekleri bir liste olarak al ve karıştır
        options = [option_a, option_b, option_c, option_d]
        original_options_map = {'A': option_a, 'B': option_b, 'C': option_c, 'D': option_d}
        random.shuffle(options) # Seçenekleri karıştır

        # Doğru cevabın yeni indeksini bul
        # Önce doğru cevabın metinsel değerini al
        correct_answer_text_from_original = original_options_map.get(correct_answer_letter)
        
        # Karıştırılmış listedeki doğru cevabın indeksini bul
        try:
            correct_index_in_shuffled = options.index(correct_answer_text_from_original)
            correct_letter_in_shuffled = chr(65 + correct_index_in_shuffled) # Yeni harf karşılığını bul (A, B, C, D)
        except ValueError:
            # Eğer correct_answer_text_from_original karıştırılmış options içinde bulunamazsa (nadiren olası ama koruma amaçlı)
            correct_letter_in_shuffled = 'N/A' 
            print(f"Uyarı: Doğru cevap metni '{correct_answer_text_from_original}' karıştırılmış seçeneklerde bulunamadı.")


        quiz_questions.append({
            "id": wrong_question_id, # Önemli: Yanlış sorunun ID'sini buraya ekliyoruz!
            "question_text": question_text,
            "options": options, # Karıştırılmış seçenekler listesi
            "correct_answer_letter": correct_letter_in_shuffled, # Yeni doğru cevap harfi
            "explanation": q_data.get('explanation', "Bu soru için açıklama bulunmamaktadır."), # Açıklama alanı
            "city": city,
            "category": category,
            "original_correct_answer_letter": correct_answer_letter # Orjinal doğru cevabı da saklayabiliriz (debug için)
        })
    
    return quiz_questions


@router.get("/wrong-questions", response_class=HTMLResponse, name="serve_wrong_questions_page")
async def serve_wrong_questions_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    wrong_questions = db_queries.get_wrong_questions_from_db(current_user.id)
    
    # wrong_questions'ın None olması durumunda boş liste olarak ayarla
    # Bu, tojson filtresinin hata vermesini engeller.
    if wrong_questions is None:
        wrong_questions = []

    return templates.TemplateResponse(
        "quiz.html",
        {
            "request": request,
            "user": current_user,
            "wrong_questions": wrong_questions,       # Şimdi her zaman geçerli bir liste olacak
            "quiz_type": "wrong_answers",             # quiz.html'e doğru tipi gönderiyoruz
        }
    )

@router.post("/delete-wrong-questions", name="delete_wrong_questions")
async def delete_wrong_questions_route( # Fonksiyon adını route ile çakışmayacak şekilde değiştirdik
    request: Request,
    question_ids: List[int] = Form(...),
    current_user: CurrentUser = Depends(require_auth)
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş yapmalısınız.")

    deleted_count = db_queries.delete_wrong_questions_from_db(current_user.id, question_ids)
    if deleted_count > 0:
        return RedirectResponse(url=request.url_for("serve_wrong_questions_page"), status_code=status.HTTP_303_SEE_OTHER)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Silinecek soru bulunamadı veya yetkiniz yok.")


@router.post("/api/remove-correctly-answered-questions", name="remove_correctly_answered_questions")
async def remove_correctly_answered_questions(question_ids: List[int], current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        deleted_count = db_queries.delete_wrong_questions_from_db(current_user.id, question_ids) # db_queries'den çağır
        return JSONResponse(
            content={"message": f"{deleted_count} yanlış soru kaydı başarıyla veritabanından kaldırıldı."},
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Soruları kaldırırken hata oluştu: {str(e)}")