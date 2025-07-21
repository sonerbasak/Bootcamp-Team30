# functions/quiz/routes.py
from fastapi import APIRouter, Request, Query, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict

from functions.auth.dependencies import require_auth, CurrentUser 
from functions.database.queries import save_wrong_question_to_db, get_wrong_questions_from_db, delete_wrong_questions_from_db, update_user_quiz_stats # update_user_quiz_stats eklendi
from functions.quiz.services import generate_quiz_from_gemini

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

    for answer_data in quiz_results.answers:
        # Doğru cevabı kontrol et
        if answer_data.user_answer == answer_data.correct_answer:
            correct_answers_count += 1
            score_earned += 10 # Her doğru cevap için varsayılan 10 puan
        else:
            # Yanlış cevapları 'wrong_questions' tablosuna kaydet
            wrong_answers_details.append(answer_data)
            save_wrong_question_to_db(
                user_id=current_user.id,
                city=answer_data.city,
                category=answer_data.category,
                question_text=answer_data.question_text,
                option_a=answer_data.option_a,
                option_b=answer_data.option_b, # Düzeltildi
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
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("quiz.html", {"request": request, "city": city, "type": type, "user": current_user})

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
async def get_wrong_questions(current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        wrong_questions = get_wrong_questions_from_db(current_user.id)
        for q in wrong_questions:
            if 'timestamp' in q and q['timestamp'] is not None:
                q['timestamp'] = str(q['timestamp'])
        return JSONResponse(content={"wrong_questions": wrong_questions}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Yanlış soruları çekerken hata oluştu: {str(e)}")

@router.get("/wrong-questions", response_class=HTMLResponse, name="serve_wrong_questions_page")
async def serve_wrong_questions_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("wrong_questions.html", {"request": request, "type": "wrong-questions", "user": current_user})

@router.post("/api/remove-correctly-answered-questions", name="remove_correctly_answered_questions")
async def remove_correctly_answered_questions(question_ids: List[int], current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        deleted_count = delete_wrong_questions_from_db(current_user.id, question_ids)
        return JSONResponse(
            content={"message": f"{deleted_count} yanlış soru kaydı başarıyla veritabanından kaldırıldı."},
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Soruları kaldırırken hata oluştu: {str(e)}")