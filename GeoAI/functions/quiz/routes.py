# functions/quiz/routes.py
from fastapi import APIRouter, Request, Query, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List

# importu get_current_user_dependency yerine require_auth olarak değiştirildi
from functions.auth.dependencies import require_auth, CurrentUser 
from functions.database.queries import save_wrong_question_to_db, get_wrong_questions_from_db, delete_wrong_questions_from_db
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

@router.get("/ai", name="ai_page")
async def ai_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    query = request.query_params
    city = query.get("city") or query.get("country") or ""
    print(f"DEBUG: AI Page - current_user: {current_user.username if current_user else 'None'}, City: {city}")
    return templates.TemplateResponse("ai.html", {"request": request, "city": city, "user": current_user})

@router.get("/quiz", response_class=HTMLResponse, name="quiz_page")
async def quiz_page(request: Request, city: str = None, type: str = None, current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("quiz.html", {"request": request, "city": city, "type": type, "user": current_user})

@router.get("/api/gemini-quiz", name="generate_quiz_api")
async def generate_quiz_api(request: Request, city: str = Query(default=""), count: int = 10, current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        quiz_data_list = await generate_quiz_from_gemini(city, count)
        return JSONResponse(content={"quiz_data": quiz_data_list})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/api/save-wrong-question", name="save_wrong_question")
async def save_wrong_question(question_data: WrongQuestionData, current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
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
async def get_wrong_questions(current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
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
async def serve_wrong_questions_page(request: Request, current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("quiz.html", {"request": request, "type": "wrong-questions", "user": current_user})

@router.post("/api/remove-correctly-answered-questions", name="remove_correctly_answered_questions")
async def remove_correctly_answered_questions(question_ids: List[int], current_user: CurrentUser = Depends(require_auth)): # Bağımlılık adı require_auth oldu
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