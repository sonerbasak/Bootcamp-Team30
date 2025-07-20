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
    const quizType = getQueryParam("type"); // URL'den type parametresini oku (örn: 'wrong-questions')
    const city = getQueryParam("city");

    isReviewMode = (quizType === "wrong-questions");

    const quizTitleEl = document.querySelector(".quiz-title");
    if (quizTitleEl) {
        if (isReviewMode) {
            quizTitleEl.textContent = "Yanlış Cevapladığınız Sorular - Tekrar Çöz!";
        } else {
            quizTitleEl.textContent = city ? `${city} Hakkında Quiz!` : `Genel Kültür Quiz!`;
        }
    } else {
        console.warn("Element with class 'quiz-title' not found.");
    }

    const questionsContainer = document.getElementById("quiz-questions-container");
    if (!questionsContainer) {
        console.error("Element with ID 'quiz-questions-container' not found. Cannot render questions.");
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
        await loadQuestions(city);
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
    startTimer();

    // Geri butonu
    const backButton = document.querySelector(".back-button");
    if (backButton) {
        backButton.addEventListener("click", (event) => {
            event.preventDefault();
            // Moddan bağımsız olarak session storage temizliği
            const currentParam = isReviewMode ? "wrong-questions" : (getQueryParam("city") || 'null');
            sessionStorage.removeItem(`aiQuizData-${currentParam}`);
            sessionStorage.removeItem(`aiQuizPrompt-${currentParam}`);
            console.log(`Geri giderken quiz verisi temizlendi: aiQuizData-${currentParam}`);
            window.location.href = backButton.href;
        });
    } else {
        console.warn("Element with class 'back-button' not found.");
    }

    // Buton event listener'ları - sadece bir kez eklenmeli
    document.querySelector(".quiz-actions .prev-button").addEventListener("click", () => {
        if (quizSwiper) quizSwiper.slidePrev();
    });
    document.querySelector(".quiz-actions .next-button").addEventListener("click", () => {
        if (quizSwiper) quizSwiper.slideNext();
    });
    document.querySelector(".quiz-actions .btn-success").addEventListener("click", submitQuiz);
});

// --- Swiper Başlatma Fonksiyonu ---
function initializeSwiper() {
    const swiperContainerEl = document.querySelector(".mySwiperQuiz");

    if (!swiperContainerEl || swiperContainerEl.offsetWidth === 0 || quizQuestions.length === 0) {
        console.log("Swiper konteyneri henüz hazır değil veya soru yok, yeniden deniyor...");
        // Soru yoksa Swiper'ı başlatmaya çalışma
        if (quizQuestions.length === 0) {
            console.warn("Hiç soru bulunamadı, Swiper başlatılmıyor.");
            return;
        }
        setTimeout(initializeSwiper, 100);
        return;
    }

    if (quizSwiper) {
        quizSwiper.destroy(true, true); // Mevcut Swiper'ı yok et
        console.log("Mevcut Swiper örneği yok edildi.");
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
        slidesPerGroup: 1, // Burası 1 olmalı ki tek tek atlasın
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
                console.log("Swiper init edildi.");
            },
            resize: function () {
                this.update();
                this.updateAutoHeight();
                console.log("Swiper yeniden boyutlandırıldı.");
            },
            observerUpdate: function () {
                console.log("Swiper observer güncellendi.");
            }
        },
    });

    if (quizSwiper && quizQuestions.length > 0) {
        quizSwiper.slideTo(0, 0); // İlk slayta anında git
        console.log("Swiper başlatıldı ve ilk soruya geçildi.");
    } else {
        console.warn("Swiper başlatılamadı veya hiç soru yok.");
    }
}

// --- Soruları Yükleme Fonksiyonu (Normal Quiz) ---
async function loadQuestions(city) {
    console.log("loadQuestions başladı. City:", city);

    let quizDataArray = [];
    let sentPromptText = null;

    try {
        const res = await fetch(`/api/gemini-quiz?city=${encodeURIComponent(city || '')}`);
        if (!res.ok) {
            let errorDetails;
            try { errorDetails = await res.json(); } catch (jsonError) { errorDetails = { error: await res.text() }; }
            throw new Error(`API yanıt vermedi: ${res.status} - ${errorDetails.error || "Bilinmeyen Hata"}`);
        }
        const data = await res.json();
        quizDataArray = data.quiz_data || [];
        sentPromptText = data.sent_prompt;

        console.log("Gemini API'den Gelen Quiz Verisi:", quizDataArray);
        console.log("YAPAY ZEKAYA GÖNDERİLEN PROMPT:", sentPromptText);

        sessionStorage.setItem(`aiQuizData-${city || 'null'}`, JSON.stringify(quizDataArray));
        sessionStorage.setItem(`aiQuizPrompt-${city || 'null'}`, sentPromptText);
        console.log("Yeni quiz ve prompt verileri sessionStorage'a kaydedildi.");

    } catch (error) {
        console.error("Sorular alınırken hata oluştu:", error);
        alert("Sorular alınamadı: " + error.message);
        quizDataArray = [];
        sessionStorage.removeItem(`aiQuizData-${city || 'null'}`);
        sessionStorage.removeItem(`aiQuizPrompt-${city || 'null'}`);
    }

    quizQuestions = quizDataArray;
    userSelections = new Array(quizQuestions.length).fill(null);
    quizDuration = TIME_PER_QUESTION_SECONDS_QUIZ; // Ana quiz süresi
    timeLeft = quizDuration;

    renderQuestions(quizQuestions);
}

// --- Yanlış Soruları Yükleme Fonksiyonu (İnceleme Modu) ---
async function loadWrongQuestionsForReview() {
    console.log("Yanlış sorular yükleniyor (İnceleme Modu)...");
    let wrongQuestions = [];
    try {
        const res = await fetch("/api/get-wrong-questions");
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(`Sorular alınamadı: ${res.status} - ${errorData.message}`);
        }
        const data = await res.json();
        wrongQuestions = data.wrong_questions || [];

        if (wrongQuestions.length === 0) {
            const questionsContainer = document.getElementById("quiz-questions-container");
            questionsContainer.innerHTML = `
                <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                    <p class="text-center">Henüz yanlış cevapladığınız soru bulunmamaktadır. Harika!</p>
                </div>
            `;
            // Boş durumda Swiper'ı başlatmaya gerek yok, veya destroy et
            if (quizSwiper) {
                quizSwiper.destroy(true, true);
                quizSwiper = null;
            }
            return; // Sorular olmadığı için buradan çık
        }

        if (wrongQuestions.length > MAX_QUESTIONS_TO_REVIEW) {
            console.log(`${wrongQuestions.length} soru bulundu, rastgele ${MAX_QUESTIONS_TO_REVIEW} tanesi seçiliyor.`);
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
        console.error("Yanlış soruları çekerken hata oluştu:", error);
        alert("Yanlış sorular yüklenirken bir hata oluştu: " + error.message);
        quizQuestions = []; // Hata durumunda soruları boşalt
        const questionsContainer = document.getElementById("quiz-questions-container");
        questionsContainer.innerHTML = `
            <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                <p class="text-center text-danger">Sorular yüklenirken bir hata oluştu: ${error.message}</p>
            </div>
        `;
        if (quizSwiper) {
            quizSwiper.destroy(true, true);
            quizSwiper = null;
        }
    }
}

// --- Soruları HTML'e Render Etme Fonksiyonu ---
function renderQuestions(questions) {
    const questionsContainer = document.getElementById("quiz-questions-container");
    if (!questionsContainer) {
        console.error("Hata: 'quiz-questions-container' ID'li eleman bulunamadı. Sorular render edilemiyor.");
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
        // Soruların yapısı modlara göre değiştiği için kontrol et
        const questionText = isReviewMode ? q.question_text : q.soru;
        const options = isReviewMode ? [q.option_a, q.option_b, q.option_c, q.option_d] : [q.a, q.b, q.c, q.d];
        const category = isReviewMode ? q.category : q.kategori;
        const correctAnsLetter = isReviewMode ? q.correct_answer_letter : q.cevap;
        const questionId = isReviewMode ? q.id : null; // Yanlış sorular için ID

        options.forEach((option, optionIndex) => {
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
            <div class="question-category" style="display: none;">${category}</div>
            ${questionId ? `<div class="wrong-question-id" style="display: none;">${questionId}</div>` : ''}
            `;
        questionsContainer.appendChild(slide);
    });

    // Sorular DOM'a eklendikten sonra Swiper'ı güncelle
    // initializeSwiper fonksiyonu DOMContentLoaded'da çağrıldığı için burada sadece update
    if (quizSwiper) {
        quizSwiper.update();
        quizSwiper.updateAutoHeight();
        quizSwiper.slideTo(currentQuestionIndex, 0); // Mevcut soruya git
        console.log("Swiper renderQuestions içinde güncellendi.");
    }
}

// --- Seçenek Değişikliğini Yönetme Fonksiyonu ---
function handleOptionChange(questionIndex, selectedLetter) {
    userSelections[questionIndex] = selectedLetter;
    console.log(`Question ${questionIndex}: Selected ${selectedLetter}`);
    if (quizSwiper) {
        quizSwiper.updateAutoHeight();
    }
}

// --- Zamanlayıcı Başlatma Fonksiyonu ---
function startTimer() {
    const timerDisplay = document.getElementById("timer");
    if (!timerDisplay) {
        console.warn("Zamanlayıcı gösterge elemanı bulunamadı.");
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
    console.log("Zamanlayıcı başlatıldı.");
}

// --- Quizi Tamamlama Fonksiyonu ---
function submitQuiz() {
    clearInterval(timerInterval);
    let score = 0;
    const reviewAnswers = [];
    const questionsToProcessForDB = []; // Veritabanına kaydedilecek/silinecek sorular

    quizQuestions.forEach((q, index) => {
        const userAnswerLetter = userSelections[index];
        // Doğru cevap harfini moda göre al
        const correctAnswerLetter = isReviewMode ? q.correct_answer_letter : q.cevap;

        let userAnswerText = null;
        if (userAnswerLetter) {
            const optionKey = `option_${userAnswerLetter.toLowerCase()}`;
            userAnswerText = isReviewMode ? q[optionKey] : q[userAnswerLetter.toLowerCase()];
        }

        let correctOptionText = null;
        if (correctAnswerLetter) {
            const correctOptionKey = `option_${correctAnswerLetter.toLowerCase()}`;
            correctOptionText = isReviewMode ? q[correctOptionKey] : q[correctAnswerLetter.toLowerCase()];
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
                    city: getQueryParam("city") || "Genel Kültür",
                    category: q.kategori,
                    question_text: q.soru,
                    option_a: q.a,
                    option_b: q.b,
                    option_c: q.c,
                    option_d: q.d,
                    correct_answer_letter: q.cevap,
                    user_answer_letter: userAnswerLetter || "BOŞ",
                });
            }
            // İnceleme modunda yanlış cevaplananları tekrar kaydetmeye gerek yok, zaten DB'deler.
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
        if (questionsToProcessForDB.length > 0) {
            saveWrongQuestionsToDatabase(questionsToProcessForDB);
        }
    }

    showResults(score, reviewAnswers);
}

// --- Yanlış Soruları Veritabanına Kaydetme Fonksiyonu (Normal Quiz için) ---
async function saveWrongQuestionsToDatabase(questions) {
    for (const q of questions) {
        try {
            const res = await fetch("/api/save-wrong-question", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(q),
            });
            if (!res.ok) {
                const errorData = await res.json();
                console.error("Yanlış soru kaydedilirken hata:", errorData);
            } else {
                console.log("Yanlış soru başarıyla kaydedildi:", q.question_text);
            }
        } catch (error) {
            console.error("Yanlış soru kaydetme API çağrısı sırasında hata:", error);
        }
    }
}

// --- Doğru Cevaplanan Yanlış Soruları Veritabanından Kaldırma Fonksiyonu (İnceleme Modu için) ---
async function removeCorrectlyAnsweredWrongQuestionsFromDatabase(questionIds) {
    if (questionIds.length === 0) {
        console.log("Kaldırılacak yanlış soru ID'si bulunmuyor.");
        return;
    }
    console.log("Doğru cevaplanan yanlış soru ID'leri veritabanından kaldırılıyor:", questionIds);
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
        console.log('API yanıtı (silme işlemi):', data.message);
    } catch (error) {
        console.error('Doğru cevaplanan yanlış soruları kaldırırken hata oluştu:', error);
        alert('Bazı doğru cevaplanan yanlış soruları veritabanından kaldırırken bir sorun oluştu: ' + error.message);
    }
}

// --- Sonuçları Gösterme Fonksiyonu ---
function showResults(score, reviewAnswers) {
    const swiperElement = document.querySelector(".mySwiperQuiz");
    const actionsElement = document.querySelector(".quiz-actions");
    const resultsContainer = document.getElementById("quiz-results");

    if (swiperElement) swiperElement.classList.add("d-none");
    if (actionsElement) actionsElement.classList.add("d-none");

    if (!resultsContainer) {
        console.error("Element with ID 'quiz-results' not found. Cannot display results.");
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
                style="border-radius: 25px; box-shadow: 0 5px 15px rgba(255, 193, 7, 0.4);"
                onclick="window.location.href='/wrong-questions'"
            >
                Yanlış Cevapladıklarım
            </button>
        `}
    </div>
    `;

    resultsContainer.innerHTML = html;
    resultsContainer.classList.remove("d-none");
    console.log("Quiz sonuçları gösteriliyor.");
}

// --- Ana Sayfaya Dönme Fonksiyonu ---
function goHome() {
    // Session Storage temizliği moddan bağımsız
    const paramToClear = isReviewMode ? "wrong-questions" : (getQueryParam("city") || 'null');
    sessionStorage.removeItem(`aiQuizData-${paramToClear}`);
    sessionStorage.removeItem(`aiQuizPrompt-${paramToClear}`);
    console.log(`Quiz data cleared for: ${paramToClear}`);
    window.location.href = "/";
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
    // Bu fonksiyon muhtemelen artık doğrudan kullanılmıyor, ancak ReferenceError'ı önlemek için
    // Eğer ana sayfa yönlendirmesi veya benzer bir işlev görmesi gerekiyorsa içini doldurun
    console.warn("goBackToAI fonksiyonu çağrıldı, ancak şu anda bir işlevi yok. Ana sayfaya yönlendiriliyor.");
    goHome(); // Veya farklı bir yönlendirme yapın
}


// Fonksiyonları global kapsamda erişilebilir yap (HTML'den 'onclick' ile çağrıldıkları için)
window.submitQuiz = submitQuiz;
window.goBackToAI = goBackToAI;
window.prevQuestion = prevQuestion;
window.nextQuestion = nextQuestion;
window.handleOptionChange = handleOptionChange;
window.goHome = goHome;