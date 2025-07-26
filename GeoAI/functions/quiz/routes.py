# functions/quiz/routes.py
from fastapi import APIRouter, Request, Query, HTTPException, status, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Dict, Optional # Optional eklendi
import random # random modülü eklendi

from functions.auth.dependencies import require_auth, CurrentUser
from functions.database.queries import (
    save_wrong_question_to_db,
    get_wrong_questions_from_db,
    delete_wrong_questions_from_db,
    add_quiz_summary,       # <-- New function for overall quiz stats
    update_category_stats   # <-- New function for category-specific stats
)
from functions.quiz.services import generate_quiz_from_gemini # This function will be updated
from functions.database import queries as db_queries # Renamed for clarity to avoid conflict with imported functions

router = APIRouter(tags=["Quiz"])
templates = Jinja2Templates(directory="templates")

class WrongQuestionData(BaseModel):
    quiz_type: str # Changed from 'type' to 'quiz_type' for consistency
    quiz_name: str # Changed from 'name' to 'quiz_name' for consistency
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
    id: Optional[int] = None # 'question_id' yerine 'id' olarak adlandıralım, WrongQuestion modelindeki gibi
    user_answer: str # Kullanıcının verdiği cevap (örneğin 'A', 'B', 'C', 'D')
    correct_answer: str # Doğru cevap (örneğin 'C') - Bu veritabanına kaydedilirken `correct_answer_letter` olacak
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    quiz_type: str # Changed from 'type' to 'quiz_type'
    quiz_name: str # Changed from 'name' to 'quiz_name'
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

    # Variables to track quiz_type and quiz_name for the overall summary
    # Assuming all questions in a single submission belong to the same quiz_type and quiz_name
    # If not, you might need to make quiz_type/name part of QuizResultRequest directly
    submission_quiz_type = "unknown"
    submission_quiz_name = "Unnamed Quiz"

    if quiz_results.answers:
        # Take the type and name from the first answer as representative for the quiz summary
        submission_quiz_type = quiz_results.answers[0].quiz_type
        submission_quiz_name = quiz_results.answers[0].quiz_name

    for answer_data in quiz_results.answers:
        # Doğru cevabı kontrol et
        if answer_data.user_answer == answer_data.correct_answer:
            correct_answers_count += 1
            score_earned += 10 # Her doğru cevap için varsayılan 10 puan
            # Eğer bu soru daha önce yanlış cevaplanan bir sorudan geliyorsa (tekrar çöz modunda),
            # o sorunun ID'sini topla.
            if answer_data.id:
                correctly_answered_wrong_question_ids.append(answer_data.id)
            
            # Kategori istatistiklerini güncelle (doğru cevap)
            db_queries.update_category_stats(current_user.id, answer_data.category, True)
        else:
            # Yanlış cevapları 'wrong_questions' tablosuna kaydet
            wrong_answers_details.append(answer_data)
            db_queries.save_wrong_question_to_db(
                user_id=current_user.id,
                # In queries.py, this is 'city' (for location) and 'category'.
                # Mapping 'quiz_name' to 'city' and 'category' to 'category' seems logical here.
                city=answer_data.quiz_name,
                category=answer_data.category,
                question_text=answer_data.question_text,
                option_a=answer_data.option_a,
                option_b=answer_data.option_b,
                option_c=answer_data.option_c,
                option_d=answer_data.option_d,
                correct_answer_letter=answer_data.correct_answer,
                user_answer_letter=answer_data.user_answer
            )
            # Kategori istatistiklerini güncelle (yanlış cevap)
            db_queries.update_category_stats(current_user.id, answer_data.category, False)
            
    # QUIZ ÖZETİNİ KAYDET
    db_queries.add_quiz_summary(
        user_id=current_user.id,
        quiz_type=submission_quiz_type,
        quiz_name=submission_quiz_name,
        total_questions=total_questions,
        correct_answers=correct_answers_count,
        score=score_earned
    )

    # Eğer tekrar çözme modunda doğru cevaplanan yanlış sorular varsa, bunları veritabanından sil
    if correctly_answered_wrong_question_ids:
        db_queries.delete_wrong_questions_from_db(current_user.id, correctly_answered_wrong_question_ids)

    return JSONResponse({
        "message": "Quiz sonuçları başarıyla kaydedildi.",
        "total_questions": total_questions,
        "correct_answers": correct_answers_count,
        "score_earned": score_earned,
        "wrong_answers_count": len(wrong_answers_details),
        "profile_updated": True # This is still technically true as stats are updated in quiz_stats.db
    })

@router.get("/ai", name="ai_page")
async def ai_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    quiz_type = request.query_params.get("type")
    quiz_name = request.query_params.get("name")
    print(f"DEBUG: AI Page - current_user: {current_user.username if current_user else 'None'}, Type: {quiz_type}, Name: {quiz_name}")
    return templates.TemplateResponse("ai.html", {"request": request, "type": quiz_type, "name": quiz_name, "user": current_user})

@router.get("/quiz", response_class=HTMLResponse, name="quiz_page")
async def quiz_page(request: Request, name: str = Query(None), type: str = Query(None), current_user: CurrentUser = Depends(require_auth)):
    wrong_questions = []
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "name": name, # 'city' yerine 'name'
        "type": type,
        "user": current_user,
        "wrong_questions": wrong_questions
    })

@router.get("/api/gemini-quiz", name="generate_quiz_api")
async def generate_quiz_api(request: Request, type: str = Query("general"), name: str = Query(""), count: int = 10, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        quiz_data_list = await generate_quiz_from_gemini(quiz_type=type, quiz_name=name, count=count)
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
            city=question_data.quiz_name, # Map 'quiz_name' to 'city' in db_queries
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


# YENİ EKLENEN ROTA: Yanlış cevaplanan soruları quiz formatında döndürür (BU ZATEN VARDI, KALSIN)
@router.get("/api/wrong_quiz_questions", response_model=List[Dict], name="get_wrong_quiz_questions")
async def get_wrong_quiz_questions(
    request: Request,
    current_user: CurrentUser = Depends(require_auth)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Yetkilendirme gereklidir.")

    all_wrong_questions = db_queries.get_wrong_questions_from_db(current_user.id)

    if not all_wrong_questions:
        return []

    num_questions_to_select = min(len(all_wrong_questions), 10)
    selected_questions = random.sample(all_wrong_questions, num_questions_to_select)

    quiz_questions = []
    for q_data in selected_questions:
        question_text = q_data.get('question_text', '')
        option_a = q_data.get('option_a', '')
        option_b = q_data.get('option_b', '')
        option_c = q_data.get('option_c', '')
        option_d = q_data.get('option_d', '')
        correct_answer_letter = q_data.get('correct_answer_letter', '').upper()
        # BURADA DEĞİŞİKLİK: city yerine type ve name alıyoruz
        quiz_type = q_data.get('type', 'general') # Varsayılan değerler önemli
        quiz_name = q_data.get('name', '') # Use 'name' from DB for quiz_name
        category = q_data.get('category', 'Quiz')
        wrong_question_id = q_data.get('id')

        options = [option_a, option_b, option_c, option_d]
        original_options_map = {'A': option_a, 'B': option_b, 'C': option_c, 'D': option_d}
        random.shuffle(options)

        correct_answer_text_from_original = original_options_map.get(correct_answer_letter)

        try:
            correct_index_in_shuffled = options.index(correct_answer_text_from_original)
            correct_letter_in_shuffled = chr(65 + correct_index_in_shuffled)
        except ValueError:
            correct_letter_in_shuffled = 'N/A'
            print(f"Uyarı: Doğru cevap metni '{correct_answer_text_from_original}' karıştırılmış seçeneklerde bulunamadı.")

        quiz_questions.append({
            "id": wrong_question_id,
            "question_text": question_text,
            "options": options,
            "correct_answer_letter": correct_letter_in_shuffled,
            "explanation": q_data.get('explanation', "Bu soru için açıklama bulunmamaktadır."),
            # BURADA DEĞİŞİKLİK: city yerine type ve name ekliyoruz
            "quiz_type": quiz_type, # Use 'type' from DB for quiz_type
            "quiz_name": quiz_name,
            "category": category,
            "original_correct_answer_letter": correct_answer_letter
        })

    return quiz_questions


@router.get("/wrong-questions", response_class=HTMLResponse, name="serve_wrong_questions_page")
async def serve_wrong_questions_page(request: Request, current_user: CurrentUser = Depends(require_auth)):
    if not current_user:
        return RedirectResponse(url=request.url_for("login_page"), status_code=status.HTTP_302_FOUND)

    wrong_questions = db_queries.get_wrong_questions_from_db(current_user.id)

    if wrong_questions is None:
        wrong_questions = []

    return templates.TemplateResponse(
        "quiz.html",
        {
            "request": request,
            "user": current_user,
            "wrong_questions": wrong_questions,
            "quiz_type": "wrong_answers",
        }
    )

@router.post("/delete-wrong-questions", name="delete_wrong_questions")
async def delete_wrong_questions_route(
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
        deleted_count = db_queries.delete_wrong_questions_from_db(current_user.id, question_ids)
        return JSONResponse(
            content={"message": f"{deleted_count} yanlış soru kaydı başarıyla veritabanından kaldırıldı."},
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Soruları kaldırırken hata oluştu: {str(e)}")