function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

let quizQuestions = [];
let currentQuestionIndex = 0;
let timerInterval;
const quizDuration = 10 * 60;
let timeLeft = quizDuration;
let quizSwiper;

// Kullanıcı cevaplarını tutacak yeni dizi. Artık sadece şık harfini (A, B, C, D) tutacak.
let userSelections = [];

document.addEventListener('DOMContentLoaded', async () => {
    const city = getQueryParam("city");
    const quizTitle = document.querySelector(".quiz-title");

    if (city && quizTitle) {
        quizTitle.textContent = `${city} Hakkında Quiz!`;
    } else {
        quizTitle.textContent = `Genel Kültür Quiz!`;
    }

    await loadQuestions(city);

    setTimeout(() => {
        initializeSwiper();
    }, 50);

    startTimer();

    const swiperWrapper = document.getElementById('quiz-questions-container');
    if (swiperWrapper) {
    }
});

function initializeSwiper() {
    const swiperContainerEl = document.querySelector(".mySwiperQuiz");

    if (!swiperContainerEl || swiperContainerEl.offsetWidth === 0) {
        setTimeout(initializeSwiper, 100);
        return;
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
            init: function() {
                this.update();
                this.updateAutoHeight();
            },
            resize: function() {
                this.update();
                this.updateAutoHeight();
            }
        }
    });
}

async function loadQuestions(city) {
    let rawQuizText = sessionStorage.getItem(`aiQuizData-${city}`);

    if (!rawQuizText) {
        try {
            const res = await fetch(`/api/gemini-quiz?city=${encodeURIComponent(city)}`);
            if (!res.ok) {
                const errorText = await res.text();
                console.error("API yanıt hatası:", res.status, errorText);
                throw new Error(`API yanıt vermedi: ${res.status} - ${errorText}`);
            }

            const data = await res.json();
            rawQuizText = data.quiz_text;

            sessionStorage.setItem(`aiQuizData-${city}`, rawQuizText);
        } catch (error) {
            console.error("Sorular alınırken hata oluştu:", error);
            alert("Sorular alınamadı: " + error.message);
            rawQuizText = "";
        }
    }

    quizQuestions = rawQuizText ? parseQuizText(rawQuizText) : [];
    
    // userSelections dizisini quizQuestions uzunluğunda başlat
    userSelections = new Array(quizQuestions.length).fill(null); 

    renderQuestions(quizQuestions);
}

function parseQuizText(text) {
    const questions = [];
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);

    let currentQuestion = null;
    let quizContentStarted = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];
        const isQuestionStart = /^(?:\*\*Soru\s*\d+:\*\*|Soru:)\s*/i.test(line);

        if (!quizContentStarted && isQuestionStart) {
            quizContentStarted = true;
        }

        if (quizContentStarted) {
            if (isQuestionStart) {
                if (currentQuestion && currentQuestion.question && currentQuestion.options.length === 4 && currentQuestion.answer) {
                    questions.push(currentQuestion);
                }
                currentQuestion = { question: "", options: [], answer: "" };
                currentQuestion.question = line.replace(/^(?:\*\*Soru\s*\d+:\*\*|Soru:)\s*/i, '').trim();

                if (lines[i + 1] && !/^[A-D]\)/.test(lines[i + 1]) && !/(?:^Doğru Cevap:|^D\))/i.test(lines[i + 1].toLowerCase().replace(/\*\*/g, ''))) {
                   currentQuestion.question += " " + lines[i + 1].replace(/\*\*/g, '').trim();
                   i++;
                }

            } else if (currentQuestion) {
                if (/^[A-D]\)/i.test(line)) {
                    currentQuestion.options.push(line.replace(/^[A-D]\)\s*/i, '').trim());
                }
                else if (line.toLowerCase().startsWith('doğru cevap:') || line.toLowerCase().startsWith('**doğru cevap:')) {
                    let rawAnswer = line.replace(/^(?:\*\*doğru cevap:|doğru cevap:)\s*/i, '').replace(/\*\*/g, '').trim();
                    // Doğru cevabın sadece şık harfini sakla (örneğin "A", "B", "C", "D")
                    currentQuestion.answer = rawAnswer; 
                }
            }
        }
    }

    if (currentQuestion && currentQuestion.question && currentQuestion.options.length === 4 && currentQuestion.answer) {
        questions.push(currentQuestion);
    }
    return questions;
}

function renderQuestions(questions) {
    const questionsContainer = document.getElementById('quiz-questions-container');
    questionsContainer.innerHTML = '';

    if (questions.length === 0) {
        questionsContainer.innerHTML = '<p class="text-center text-danger">Sorular yüklenemedi veya bulunamadı.</p>';
        return;
    }

    questions.forEach((q, index) => {
        const slide = document.createElement('div');
        slide.classList.add('swiper-slide', 'quiz-slide');

        let optionsHtml = '';
        // Şıkların yerlerini karıştırmayı kaldırıyoruz.
        // Artık orijinal sırasıyla (A, B, C, D) render edilecekler.
        const orderedOptions = [...q.options]; 

        orderedOptions.forEach((option, optionIndex) => {
            // Şık harfini doğrudan indeksten alıyoruz (0=A, 1=B, ...)
            const optionLetter = String.fromCharCode(65 + optionIndex); 
            
            // Kullanıcının daha önceki seçimini kontrol et ve işaretle
            // userSelections artık şık harfi tuttuğu için karşılaştırmayı buna göre yapıyoruz.
            const isChecked = (userSelections[index] === optionLetter) ? 'checked' : ''; 
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
            <p class="question-text">${q.question}</p>
            <div class="options">
                ${optionsHtml}
            </div>
        `;

        questionsContainer.appendChild(slide);
    });

    if (quizSwiper) {
        quizSwiper.update();
        quizSwiper.updateAutoHeight();
    }
}

// Kullanıcının bir seçeneği işaretlemesi durumunda çağrılacak fonksiyon
// Sadece şık harfini (A, B, C, D) tutacağız.
function handleOptionChange(questionIndex, selectedLetter) {
    userSelections[questionIndex] = selectedLetter;
}

function startTimer() {
    const timerDisplay = document.getElementById('timer');
    timerInterval = setInterval(() => {
        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;

        minutes = minutes < 10 ? '0' + minutes : minutes;
        seconds = seconds < 10 ? '0' + seconds : seconds;

        timerDisplay.textContent = `Kalan Süre: ${minutes}:${seconds}`;

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            alert('Süreniz doldu! Quiz otomatik olarak tamamlanıyor.');
            submitQuiz();
        }
        timeLeft--;
    }, 1000);
}

function submitQuiz() {
    clearInterval(timerInterval);
    let score = 0;
    const reviewAnswers = [];

    quizQuestions.forEach((q, index) => {
        // userSelections artık doğrudan şık harfini tutuyor
        const userAnswerLetter = userSelections[index]; 
        
        const correctAnswerFromAPI = q.answer; // Bu zaten 'C' gibi şık harfi

        // reviewAnswers'a hem şık harfini hem de metni eklemek için q.options'ı kullanabiliriz
        let userAnswerText = null;
        if (userAnswerLetter) {
            const optionIndex = userAnswerLetter.charCodeAt(0) - 'A'.charCodeAt(0);
            if (optionIndex >= 0 && optionIndex < q.options.length) {
                userAnswerText = q.options[optionIndex];
            }
        }
        // Doğru cevabın metnini de almak için
        let correctOptionText = null;
        if (correctAnswerFromAPI) {
            const correctOptionIndex = correctAnswerFromAPI.charCodeAt(0) - 'A'.charCodeAt(0);
            if (correctOptionIndex >= 0 && correctOptionIndex < q.options.length) {
                correctOptionText = q.options[correctOptionIndex];
            }
        }


        reviewAnswers.push({ 
            question: q.question, 
            userAnswerLetter: userAnswerLetter, 
            userAnswerText: userAnswerText,
            correctAnswerLetter: correctAnswerFromAPI, 
            correctAnswerText: correctOptionText,
            isCorrect: false
        });

        if (userAnswerLetter) {
            // Doğrudan şık harflerini karşılaştırıyoruz (büyük/küçük harf duyarsız)
            if (userAnswerLetter.toLowerCase().trim() === correctAnswerFromAPI.toLowerCase().trim()) {
                score++;
                reviewAnswers[index].isCorrect = true;
            }
        }
    });

    const totalQuestions = quizQuestions.length;
    alert(`Quiz tamamlandı! ${totalQuestions} sorudan ${score} doğru cevap verdiniz.`);
    
    console.log("Quiz Detaylı Sonuçları:", reviewAnswers);

    goBackToAI();
}

function prevQuestion() {
    if (quizSwiper) {
        quizSwiper.slidePrev();
    }
}

function nextQuestion() {
    if (quizSwiper) {
        quizSwiper.slideNext();
    }
}

function goBackToAI() {
    if (confirm("Quizi yarıda bırakmak istediğinize emin misiniz?")) {
        clearInterval(timerInterval);
        window.location.href = 'http://127.0.0.1:8000/';
    }
}

window.submitQuiz = submitQuiz;
window.goBackToAI = goBackToAI;
window.prevQuestion = prevQuestion;
window.nextQuestion = nextQuestion;
window.handleOptionChange = handleOptionChange;