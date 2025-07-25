// Global değişkenler
let quizQuestions = [];
let currentQuestionIndex = 0;
let timerInterval;
let quizDuration; // Süre artık dinamik olacak
let timeLeft;
let quizSwiper;
let userSelections = [];
let isReviewMode = false; // Yeni bayrak: İnceleme modunda mıyız?

// Her soru için ayrılacak süre (saniye cinsinden)
const TIME_PER_QUESTION_SECONDS_QUIZ = 10 * 60; // Ana quiz için 10 dakika
const TIME_PER_QUESTION_SECONDS_REVIEW = 30; // İnceleme quiz için her soruya 30 saniye
const MAX_QUESTIONS_TO_REVIEW = 10; // İnceleme modunda maks. gösterilecek soru

// --- Yardımcı Fonksiyon: URL Parametrelerini Alma ---
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

document.addEventListener("DOMContentLoaded", async () => {
    const quizType = getQueryParam("type"); // 'country', 'city' veya 'wrong-questions'
    const quizName = getQueryParam("name"); // Ülke veya şehir adı (eski 'city' parametresinin yerini aldı)

    isReviewMode = (quizType === "wrong-questions");

    const quizTitleEl = document.querySelector(".quiz-title");
    if (quizTitleEl) {
        if (isReviewMode) {
            quizTitleEl.textContent = "Yanlış Cevapladığınız Sorular - Tekrar Çöz!";
        } else if (quizName) { // Eğer bir isim (ülke/şehir) varsa başlığı ona göre ayarla
            quizTitleEl.textContent = `${quizName} Hakkında Quiz!`;
        } else {
            quizTitleEl.textContent = `Genel Kültür Quiz!`; // Varsayılan başlık
        }
    } else {
        console.warn("Element with class 'quiz-title' not found.");
    }

    const questionsContainer = document.getElementById("quiz-questions-container");
    if (!questionsContainer) {
        return;
    }

    const loadingSlide = document.getElementById('loading-slide');
    if (loadingSlide) {
        loadingSlide.classList.remove('d-none');
        loadingSlide.style.display = 'flex';
        // Yükleme mesajını moda göre ayarla
        const loadingMessage = loadingSlide.querySelector('p:first-of-type');
        if (loadingMessage) {
            loadingMessage.textContent = isReviewMode ?
                "Yanlış sorularınız yükleniyor..." :
                "Yapay zekâ senin için benzersiz sorular hazırlıyor...";
        }
    }

    if (isReviewMode) {
        await loadWrongQuestionsForReview();
    } else {
        await loadQuestions(quizType, quizName);
    }

    if (loadingSlide) {
        loadingSlide.remove();
    }

    // Yükleme sonrası Swiper konteynerini görünür yap
    const swiperContainerEl = document.querySelector(".mySwiperQuiz");
    if (swiperContainerEl) {
        swiperContainerEl.classList.remove('d-none');
        swiperContainerEl.style.visibility = 'visible';
        swiperContainerEl.style.opacity = '1';
    }

    initializeSwiper();
    // Yalnızca sorular varsa zamanlayıcıyı başlat
    if (quizQuestions.length > 0) {
        startTimer();
    } else {
        // Soru yoksa zamanlayıcıyı gizle veya mesaj göster
        const timerDisplay = document.getElementById("timer");
        if (timerDisplay) {
            timerDisplay.textContent = "Süre: --:--";
            timerDisplay.classList.add('d-none');
        }
    }

    // Geri butonu
    const backButton = document.querySelector(".back-button");
    if (backButton) {
        backButton.addEventListener("click", (event) => {
            event.preventDefault();
            // Moddan bağımsız olarak session storage temizliği
            const currentQuizType = getQueryParam("type");
            const currentQuizName = getQueryParam("name");
            const paramToClear = isReviewMode ? "wrong-questions" : `${currentQuizType || 'general'}-${currentQuizName || 'null'}`;
            sessionStorage.removeItem(`aiQuizData-${paramToClear}`);
            sessionStorage.removeItem(`aiQuizPrompt-${paramToClear}`);

            if (currentQuizType === 'city' && currentQuizName) {
                window.location.href = window.TURKEY_PAGE_URL || window.ROOT_URL;
            } else if (currentQuizType === 'country' && currentQuizName) {
                window.location.href = window.WORLD_PAGE_URL || window.ROOT_URL;
            } else {
                window.location.href = backButton.href || window.ROOT_URL;
            }
        });
    } else {
        console.warn("Element with class 'back-button' not found.");
    }
});

// --- Swiper Başlatma Fonksiyonu ---
function initializeSwiper() {
    const swiperContainerEl = document.querySelector(".mySwiperQuiz");

    if (quizQuestions.length === 0) {
        const questionsContainer = document.getElementById("quiz-questions-container");
        if (questionsContainer && questionsContainer.innerHTML.includes('Sorular yükleniyor')) {
             questionsContainer.innerHTML = `
                <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                    <p class="text-center">Hiç soru bulunamadı. Lütfen daha sonra tekrar deneyin veya ana sayfaya dönün.</p>
                </div>
            `;
            const submitButton = document.querySelector(".submit-button");
            if (submitButton) submitButton.classList.add("d-none"); // Soru yoksa submit butonunu gizle
            const prevButton = document.querySelector(".prev-button");
            if (prevButton) prevButton.classList.add("d-none");
            const nextButton = document.querySelector(".next-button");
            if (nextButton) nextButton.classList.add("d-none");
        }
        return;
    }

    if (!swiperContainerEl || swiperContainerEl.offsetWidth === 0) {
        setTimeout(initializeSwiper, 100);
        return;
    }

    if (quizSwiper) {
        quizSwiper.destroy(true, true); // Mevcut Swiper'ı yok et
    }

    quizSwiper = new Swiper(".mySwiperQuiz", {
        loop: false,
        navigation: {
            nextEl: ".quiz-actions .next-button",
            prevEl: ".quiz-actions .prev-button",
        },
        pagination: {
            el: ".swiper-pagination",
            clickable: true,
        },
        allowTouchMove: false,

        slidesPerView: 1,
        slidesPerGroup: 1,
        centeredSlides: true,
        spaceBetween: 20,
        autoHeight: true,

        observer: true,
        observeParents: true,
        observeSlideChildren: true,

        on: {
            slideChange: function () {
                currentQuestionIndex = this.realIndex;
                this.updateAutoHeight();
            },
            init: function () {
                this.update();
                this.updateAutoHeight();
            },
            resize: function () {
                this.update();
                this.updateAutoHeight();
            },
            observerUpdate: function () {
                console.log("Swiper observer güncellendi.");
            }
        },
    });

    if (quizSwiper && quizQuestions.length > 0) {
        quizSwiper.slideTo(0, 0); // İlk slayta anında git
    } else {
        console.warn("Swiper başlatılamadı veya hiç soru yok.");
    }
}

// --- Soruları Yükleme Fonksiyonu (Normal Quiz) ---
async function loadQuestions(quizType, quizName) {

    let quizDataArray = [];
    let sentPromptText = null;

    try {
        const url = `/api/gemini-quiz?type=${encodeURIComponent(quizType || 'general')}&name=${encodeURIComponent(quizName || '')}`;

        const res = await fetch(url);

        if (res.redirected) {
            window.location.href = res.url;
            return;
        }

        if (!res.ok) {
            if (res.status === 401) {
                window.location.href = window.LOGIN_URL;
                return;
            }
            let errorDetails;
            try { errorDetails = await res.json(); } catch (jsonError) { errorDetails = { error: await res.text() }; }
            throw new Error(`API yanıt vermedi: ${res.status} - ${errorDetails.error || "Bilinmeyen Hata"}`);
        }
        const data = await res.json();
        quizDataArray = data.quiz_data || [];
        sentPromptText = data.sent_prompt;

        const sessionStorageKey = `aiQuizData-${quizType || 'general'}-${quizName || 'null'}`;
        const sessionStoragePromptKey = `aiQuizPrompt-${quizType || 'general'}-${quizName || 'null'}`;

        sessionStorage.setItem(sessionStorageKey, JSON.stringify(quizDataArray));
        sessionStorage.setItem(sessionStoragePromptKey, sentPromptText);

    } catch (error) {
        alert("Sorular alınamadı: " + error.message + "\nLütfen tekrar deneyin veya farklı bir seçim yapın.");
        quizDataArray = [];
        sessionStorage.removeItem(`aiQuizData-${quizType || 'general'}-${quizName || 'null'}`);
        sessionStorage.removeItem(`aiQuizPrompt-${quizType || 'general'}-${quizName || 'null'}`);
    }

    quizQuestions = quizDataArray;
    userSelections = new Array(quizQuestions.length).fill(null);
    quizDuration = TIME_PER_QUESTION_SECONDS_QUIZ;
    timeLeft = quizDuration;

    renderQuestions(quizQuestions);
}

// --- Yanlış Soruları Yükleme Fonksiyonu (İnceleme Modu) ---
async function loadWrongQuestionsForReview() {
    let wrongQuestions = [];
    try {
        const res = await fetch("/api/get-wrong-questions");
        if (res.redirected) {
            window.location.href = res.url;
            return;
        }

        if (!res.ok) {
            if (res.status === 401) {
                window.location.href = window.LOGIN_URL;
                return;
            }
            const errorData = await res.json();
            throw new Error(`Sorular alınamadı: ${res.status} - ${errorData.message}`);
        }
        const data = await res.json();
        wrongQuestions = data.wrong_questions || [];

        if (wrongQuestions.length === 0) {
            const questionsContainer = document.getElementById("quiz-questions-container");
            if (questionsContainer) {
                questionsContainer.innerHTML = `
                    <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                        <p class="text-center">Henüz yanlış cevapladığınız soru bulunmamaktadır. Harika!</p>
                        <button class="btn btn-primary mt-3" onclick="goHome()">Ana Sayfaya Dön</button>
                    </div>
                `;
            }
            // Boş durumda Swiper'ı başlatmaya gerek yok, veya destroy et
            if (quizSwiper) {
                quizSwiper.destroy(true, true);
                quizSwiper = null;
            }
            const quizActions = document.querySelector('.quiz-actions');
            if (quizActions) quizActions.classList.add('d-none');
            const timerDisplay = document.getElementById("timer");
            if (timerDisplay) timerDisplay.classList.add('d-none');
            return; // Sorular olmadığı için buradan çık
        }

        if (wrongQuestions.length > MAX_QUESTIONS_TO_REVIEW) {
            for (let i = wrongQuestions.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [wrongQuestions[i], wrongQuestions[j]] = [wrongQuestions[j], wrongQuestions[i]];
            }
            quizQuestions = wrongQuestions.slice(0, MAX_QUESTIONS_TO_REVIEW);
        } else {
            quizQuestions = wrongQuestions;
        }

        quizDuration = quizQuestions.length * TIME_PER_QUESTION_SECONDS_REVIEW; // İnceleme quiz süresi
        timeLeft = quizDuration;

        renderQuestions(quizQuestions);

    } catch (error) {
        alert("Yanlış sorular yüklenirken bir hata oluştu: " + error.message + "\nLütfen tekrar deneyin.");
        quizQuestions = []; // Hata durumunda soruları boşalt
        const questionsContainer = document.getElementById("quiz-questions-container");
        if (questionsContainer) {
            questionsContainer.innerHTML = `
                <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                    <p class="text-center text-danger">Sorular yüklenirken bir hata oluştu: ${error.message}</p>
                    <button class="btn btn-primary mt-3" onclick="goHome()">Ana Sayfaya Dön</button>
                </div>
            `;
        }
        if (quizSwiper) {
            quizSwiper.destroy(true, true);
            quizSwiper = null;
        }
        const quizActions = document.querySelector('.quiz-actions');
        if (quizActions) quizActions.classList.add('d-none');
        const timerDisplay = document.getElementById("timer");
        if (timerDisplay) timerDisplay.classList.add('d-none');
    }
}

// --- Soruları HTML'e Render Etme Fonksiyonu ---
function renderQuestions(questions) {
    const questionsContainer = document.getElementById("quiz-questions-container");
    if (!questionsContainer) {
        return;
    }

    questionsContainer.innerHTML = ""; // Mevcut içeriği temizle

    if (questions.length === 0) {
        questionsContainer.innerHTML =
            '<p class="text-center text-danger">Sorular yüklenemedi veya bulunamadı.</p>';
        return;
    }

    questions.forEach((q, index) => {
        const slide = document.createElement("div");
        slide.classList.add("swiper-slide", "quiz-slide");

        let optionsHtml = "";
        // Soru metni, seçenekler ve doğru cevap harfi için daha tutarlı erişim
        // Normal modda API'den 'soru', 'a', 'b', 'c', 'd', 'cevap' gelir.
        // İnceleme modunda DB'den 'question_text', 'option_a'...'option_d', 'correct_answer_letter' gelir.
        const questionText = q.question_text || q.soru; // Her iki mod için de uygun olanı al
        const optionA = q.option_a || q.a;
        const optionB = q.option_b || q.b;
        const optionC = q.option_c || q.c;
        const optionD = q.option_d || q.d;
        const options = [optionA, optionB, optionC, optionD];

        const validOptions = options.filter(option => option !== undefined && option !== null);

        const category = q.category || q.kategori;
        const correctAnsLetter = q.correct_answer_letter || q.cevap;
        const questionId = q.id || null; // Yanlış sorular için ID

        validOptions.forEach((option, optionIndex) => {
            const optionLetter = String.fromCharCode(65 + optionIndex);
            // userSelections dizisini her iki mod için de kullan
            const isChecked = userSelections[index] === optionLetter ? "checked" : "";
            optionsHtml += `
                <label>
                    <input type="radio"
                           name="question-${index}"
                           value="${optionLetter}"
                           onchange="handleOptionChange(${index}, '${optionLetter}')"
                           ${isChecked}> ${optionLetter}) ${option}
                </label>
            `;
        });

        slide.innerHTML = `
            <div class="question-number">Soru ${index + 1}</div>
            <p class="question-text">${questionText}</p>
            <div class="options">
                ${optionsHtml}
            </div>
            <div class="question-category" style="display: none;">${category || ''}</div>
            ${questionId ? `<div class="wrong-question-id" style="display: none;">${questionId}</div>` : ''}
            `;
        questionsContainer.appendChild(slide);
    });

    // Sorular DOM'a eklendikten sonra Swiper'ı güncelle
    if (quizSwiper) {
        quizSwiper.update();
        quizSwiper.updateAutoHeight();
        quizSwiper.slideTo(currentQuestionIndex, 0); // Mevcut soruya git
    }
}

// --- Seçenek Değişikliğini Yönetme Fonksiyonu ---
function handleOptionChange(questionIndex, selectedLetter) {
    userSelections[questionIndex] = selectedLetter;
    if (quizSwiper) {
        quizSwiper.updateAutoHeight();
    }
}

// --- Zamanlayıcı Başlatma Fonksiyonu ---
function startTimer() {
    const timerDisplay = document.getElementById("timer");
    if (!timerDisplay) {
        return;
    }

    // Mevcut zamanlayıcı varsa temizle
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    timerInterval = setInterval(() => {
        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        timerDisplay.textContent = `Kalan Süre: ${minutes}:${seconds}`;

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            alert("Süreniz doldu! Quiz otomatik olarak tamamlanıyor.");
            submitQuiz();
        }
        timeLeft--;
    }, 1000);
}

// --- Quizi Tamamlama Fonksiyonu ---
function submitQuiz() {
    clearInterval(timerInterval);
    let score = 0;
    const reviewAnswers = [];
    const questionsToProcessForDB = []; // Veritabanına kaydedilecek/silinecek sorular

    const currentQuizType = getQueryParam("type");
    const currentQuizName = getQueryParam("name"); // 'name' parametresi, 'city'nin yerini aldı

    quizQuestions.forEach((q, index) => {
        const userAnswerLetter = userSelections[index];
        // Doğru cevap harfini moda göre al
        const correctAnswerLetter = isReviewMode ? q.correct_answer_letter : q.cevap;

        let userAnswerText = null;
        if (userAnswerLetter) {
            // Seçenek metnini alma: isReviewMode ise 'option_a' gibi, değilse 'a' gibi
            const optionKey = `option_${userAnswerLetter.toLowerCase()}`;
            userAnswerText = isReviewMode ? (q[optionKey]) : q[userAnswerLetter.toLowerCase()];
        }

        let correctOptionText = null;
        if (correctAnswerLetter) {
            // Doğru seçenek metnini alma: isReviewMode ise 'option_a' gibi, değilse 'a' gibi
            const correctOptionKey = `option_${correctAnswerLetter.toLowerCase()}`;
            correctOptionText = isReviewMode ? (q[correctOptionKey]) : q[correctAnswerLetter.toLowerCase()];
        }

        const isCorrect =
            (userAnswerLetter && correctAnswerLetter) &&
            (userAnswerLetter.trim().toLowerCase() === correctAnswerLetter.trim().toLowerCase());

        if (isCorrect) {
            score++;
            if (isReviewMode && q.id) { // İnceleme modunda doğru cevaplanırsa DB'den silmek için
                questionsToProcessForDB.push(q.id);
            }
        } else {
            if (!isReviewMode) { // Ana quiz'de yanlış cevaplanırsa DB'ye kaydetmek için
                questionsToProcessForDB.push({
                    quiz_type: currentQuizType || "general", // BURASI DÜZELTİLDİ: 'type' yerine 'quiz_type'
                    quiz_name: currentQuizName || "unknown", // BURASI DÜZELTİLDİ: 'name' yerine 'quiz_name'
                    category: q.kategori || "Bilinmeyen", // Normal quiz için 'kategori'
                    question_text: q.soru, // Normal quiz için 'soru'
                    option_a: q.a,
                    option_b: q.b,
                    option_c: q.c,
                    option_d: q.d,
                    correct_answer_letter: q.cevap, // Normal quiz için 'cevap'
                    user_answer_letter: userAnswerLetter || "BOŞ",
                });
            }
        }

        reviewAnswers.push({
            question: isReviewMode ? q.question_text : q.soru,
            category: isReviewMode ? q.category : q.kategori,
            userAnswerLetter,
            userAnswerText,
            correctAnswerLetter,
            correctOptionText,
            isCorrect,
        });
    });

    if (isReviewMode) {
        if (questionsToProcessForDB.length > 0) {
            removeCorrectlyAnsweredWrongQuestionsFromDatabase(questionsToProcessForDB);
        }
    } else {
        // API'ye gönderilecek veriyi tek bir çağrıda göndermek için:
        // FastAPI'nin list of QuizAnswer'ı bekleyen submit-quiz-results endpoint'i var.
        const quizAnswersPayload = quizQuestions.map((q, index) => {
            const userAnswerLetter = userSelections[index];
            const correctAnswerLetter = isReviewMode ? q.correct_answer_letter : q.cevap;

            // `QuizAnswer` modeline uygun veri hazırlığı
            return {
                id: isReviewMode ? q.id : null, // Sadece yanlış sorularda id var
                user_answer: userAnswerLetter || "BOŞ",
                correct_answer: correctAnswerLetter,
                question_text: isReviewMode ? q.question_text : q.soru,
                option_a: isReviewMode ? q.option_a : q.a,
                option_b: isReviewMode ? q.option_b : q.b,
                option_c: isReviewMode ? q.option_c : q.c,
                option_d: isReviewMode ? q.option_d : q.d,
                quiz_type: currentQuizType || "general",
                quiz_name: currentQuizName || "unknown",
                category: isReviewMode ? q.category : q.kategori,
            };
        });
        
        // Tek bir API çağrısı ile tüm sonuçları gönder
        submitFullQuizResultsToDatabase(quizAnswersPayload);
    }

    showResults(score, reviewAnswers);
}


// --- Tüm Quiz Sonuçlarını Veritabanına Gönderme Fonksiyonu (Yeni) ---
async function submitFullQuizResultsToDatabase(answers) {
    try {
        const res = await fetch("/api/submit-quiz-results", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answers: answers }), // FastAPI'nin beklediği format {answers: [...]}
        });
        if (!res.ok) {
            const errorData = await res.json();
        } else {
            const successData = await res.json();
            console.log("Quiz sonuçları başarıyla kaydedildi:", successData);
            // Başarılı kayıttan sonra wrong_questions'a da kaydetmek gerekmez,
            // çünkü `submit_quiz_results` backend'de zaten yanlışları kaydediyor.
        }
    } catch (error) {
    }
}

// --- Doğru Cevaplanan Yanlış Soruları Veritabanından Kaldırma Fonksiyonu (İnceleme Modu için) ---
async function removeCorrectlyAnsweredWrongQuestionsFromDatabase(questionIds) {
    if (questionIds.length === 0) {
        return;
    }
    try {
        const res = await fetch('/api/remove-correctly-answered-questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(questionIds),
        });
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(errorData.detail || 'API yanıt hatası');
        }
        const data = await res.json();
    } catch (error) {
        alert('Bazı doğru cevaplanan yanlış soruları veritabanından kaldırırken bir sorun oluştu: ' + error.message);
    }
}

// --- Sonuçları Gösterme Fonksiyonu ---
function showResults(score, reviewAnswers) {
    const swiperElement = document.querySelector(".mySwiperQuiz");
    const actionsElement = document.querySelector(".quiz-actions");
    const resultsContainer = document.getElementById("quiz-results");
    const timerDisplay = document.getElementById("timer");

    if (swiperElement) swiperElement.classList.add("d-none");
    if (actionsElement) actionsElement.classList.add("d-none");
    if (timerDisplay) timerDisplay.classList.add("d-none");

    if (!resultsContainer) {
        return;
    }

    let html = `
        <h2 class="text-center ${isReviewMode && score === quizQuestions.length ? 'text-success' : 'text-primary'}">
            ${isReviewMode ? 'Değerlendirme Sonucu' : 'Quiz Tamamlandı!'}
        </h2>
        <p class="text-center fs-5">Doğru Cevap Sayısı: <strong>${score}</strong> / ${quizQuestions.length}</p>
        <hr/>
        ${isReviewMode ? '<h4 class="text-danger">Yanlış Yaptıkların / Eksikler:</h4>' : '<h4 class="text-danger">Yanlış Cevaplar:</h4>'}
    `;

    const wrongAnswers = reviewAnswers.filter((r) => !r.isCorrect);
    if (wrongAnswers.length === 0) {
        html += `<p class="text-success">Harika! Tüm soruları doğru cevapladınız 🎉</p>`;
    } else {
        wrongAnswers.forEach((r, i) => {
            html += `
                <div class="card mb-3">
                    <div class="card-body">
                        <p><strong>Soru ${i + 1}:</strong> ${r.question}</p>
                        <p class="text-danger mb-1">Senin Cevabın: ${r.userAnswerLetter
                }) ${r.userAnswerText || "Boş Bırakıldı"}</p>
                        <p class="text-success">Doğru Cevap: ${r.correctAnswerLetter
                }) ${r.correctOptionText}</p>
                    </div>
                </div>
            `;
        });
    }

html += `
    <div class="text-center mt-4">
        <button
            class="btn btn-success px-4 py-2 fs-5 fw-semibold"
            style="border-radius: 25px; box-shadow: 0 5px 15px rgba(0, 77, 64, 0.4);"
            onclick="goHome()"
        >
            Ana Sayfaya Dön
        </button>
        ${isReviewMode ? `
            <button
                class="btn btn-primary px-4 py-2 fs-5 fw-semibold ms-3"
                style="border-radius: 25px; box-shadow: 0 5px 15px rgba(0, 123, 255, 0.4);"
                onclick="window.location.reload()"
            >
                Tekrar Dene
            </button>
        ` : `
            <button
                class="btn btn-warning px-4 py-2 fs-5 fw-semibold ms-3"
                style="border-radius: 25px; box_shadow: 0 5px 15px rgba(255, 193, 7, 0.4);"
                onclick="window.location.href='${window.WRONG_QUESTIONS_URL}?type=wrong-questions'"
            >
                Yanlış Cevapladıklarım
            </button>
        `}
    </div>
    `;

    resultsContainer.innerHTML = html;
    resultsContainer.classList.remove("d-none");
}

// --- Ana Sayfaya Dönme Fonksiyonu ---
function goHome() {
    // Session Storage temizliği moddan bağımsız
    const quizType = getQueryParam("type");
    const quizName = getQueryParam("name"); // 'name' parametresi, 'city'nin yerini aldı
    const paramToClear = isReviewMode ? "wrong-questions" : `${quizType || 'general'}-${quizName || 'null'}`;
    sessionStorage.removeItem(`aiQuizData-${paramToClear}`);
    sessionStorage.removeItem(`aiQuizPrompt-${paramToClear}`);

    // Yönlendirme mantığı: Eğer bir şehir veya ülke quiz'i ise ilgili harita sayfasına dön
    if (quizType === 'city' && quizName) {
        window.location.href = window.TURKEY_PAGE_URL || window.ROOT_URL;
    } else if (quizType === 'country' && quizName) {
        window.location.href = window.WORLD_PAGE_URL || window.ROOT_URL;
    } else {
        window.location.href = window.ROOT_URL; // Diğer durumlarda ana sayfaya dön
    }
}

// --- Önceki Soru Fonksiyonu (Opsiyonel, eğer HTML'de kullanılıyorsa) ---
function prevQuestion() {
    if (quizSwiper) {
        quizSwiper.slidePrev();
    }
}

// --- Sonraki Soru Fonksiyonu (Opsiyonel, eğer HTML'de kullanılıyorsa) ---
function nextQuestion() {
    if (quizSwiper) {
        quizSwiper.slideNext();
    }
}

// --- goBackToAI Fonksiyonu (Placeholder: Kullanılmıyorsa silinebilir, ReferenceError'ı önlemek için eklendi) ---
function goBackToAI() {
    goHome();
}

// Fonksiyonları global kapsamda erişilebilir yap (HTML'den 'onclick' ile çağrıldıkları için)
window.submitQuiz = submitQuiz;
window.goBackToAI = goBackToAI;
window.prevQuestion = prevQuestion;
window.nextQuestion = nextQuestion;
window.handleOptionChange = handleOptionChange;
window.goHome = goHome;