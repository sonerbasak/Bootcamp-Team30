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

document.addEventListener('DOMContentLoaded', async () => {
    const city = getQueryParam("city");
    const quizTitle = document.querySelector(".quiz-title");

    if (city && quizTitle) {
        quizTitle.textContent = `${city} Hakkında Quiz!`;
    } else {
        quizTitle.textContent = `Genel Kültür Quiz!`;
    }

    await loadQuestions(city); 
    initializeSwiper();
    startTimer(); 
});

function initializeSwiper() {
    quizSwiper = new Swiper(".mySwiperQuiz", {
        loop: false, 
        navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
        },
        pagination: {
            el: ".swiper-pagination",
            clickable: true,
        },
        allowTouchMove: false,
        on: {
            slideChange: function () {
                currentQuestionIndex = this.realIndex;
            }
        }
    });
}

async function loadQuestions(city) {
    document.getElementById("loading").style.display = "block";
    let rawQuizText = sessionStorage.getItem(`aiQuizData-${city}`);
    
    if (!rawQuizText) {
        try {
            const res = await fetch(`/api/gemini-quiz?city=${encodeURIComponent(city)}`);
            if (!res.ok) throw new Error("API yanıt vermedi");

            const data = await res.json();
            rawQuizText = data.quiz_text;

            console.log(`API'den ${city} için gelen ham metin:`, rawQuizText);

            // Her şehir için farklı key ile kaydet
            sessionStorage.setItem(`aiQuizData-${city}`, rawQuizText);
        } catch (error) {
            alert("Sorular alınamadı.");
            rawQuizText = "";
        }
    } else {
        console.log(`${city} için SessionStorage'dan quiz verisi alındı.`);
    }

    quizQuestions = rawQuizText ? parseQuizText(rawQuizText) : [];
    console.log("Parse edilmiş sorular:", quizQuestions);
    renderQuestions(quizQuestions);
    document.getElementById("loading").style.display = "none";

    console.log("API raw metin:", rawQuizText);
quizQuestions = rawQuizText ? parseQuizText(rawQuizText) : [];
console.log("Parsed sorular:", quizQuestions);
console.log("Toplam soru sayısı:", quizQuestions.length);

}




// API'den gelen raw metni parse etmek için örnek fonksiyon
function parseQuizText(text) {
    const questions = [];
    
    // Soru bloklarını 'Soru' kelimesine göre böl
    // Örnek: "Soru 1" ile başlayan her blok bir soru
    const splitRegex = /Soru \d+/gi;
    let parts = text.split(splitRegex).map(p => p.trim()).filter(p => p.length > 0);
    
    // "Soru X" ifadelerini ayrıca bulalım ki soru numaraları atlanmasın
    const questionNumbers = text.match(splitRegex);

    if (!parts.length) return [];

    for(let i=0; i<parts.length; i++) {
        let block = parts[i];
        let questionNumber = questionNumbers ? questionNumbers[i] : `Soru ${i+1}`;
        
        // Satırları al
        const lines = block.split('\n').map(l => l.trim()).filter(l => l.length > 0);

        // İlk satır soru metni (çoğunlukla)
        const questionText = lines[0] || "";

        // Şıkları topla
        const options = [];
        let answer = "";

        for(let j=1; j < lines.length; j++) {
            let line = lines[j];
            if (/^[A-D]\)/.test(line)) {
                options.push(line.replace(/^[A-D]\)\s*/, ''));
            } else if (/doğru cevap/i.test(line)) {
                answer = line.split(':')[1].trim();
            }
        }

        if(questionText && options.length > 0 && answer) {
            questions.push({
                question: questionText,
                options: options,
                answer: answer
            });
        }
    }

    return questions;
}





function renderQuestions(questions) {
    const questionsContainer = document.getElementById('quiz-questions-container');
    questionsContainer.innerHTML = '';

    questions.forEach((q, index) => {
        const slide = document.createElement('div');
        slide.classList.add('swiper-slide', 'quiz-slide');

        let optionsHtml = '';
        const shuffledOptions = [...q.options].sort(() => Math.random() - 0.5);

        shuffledOptions.forEach((option) => {
            optionsHtml += `
                <label>
                    <input type="radio" name="question-${index}" value="${option}"> ${option}
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

    // Swiper instance'ı güncelle
    if (quizSwiper) {
        quizSwiper.update();  // Yeni slaytları algılasın diye
    }
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
    const userAnswers = [];

    quizQuestions.forEach((q, index) => {
        const selectedOption = document.querySelector(`input[name="question-${index}"]:checked`);
        const userAnswer = selectedOption ? selectedOption.value : null;
        userAnswers.push({ question: q.question, userAnswer: userAnswer, correctAnswer: q.answer });

        if (userAnswer === q.answer) {
            score++;
        }
    });

    const totalQuestions = quizQuestions.length;
    alert(`Quiz tamamlandı! ${totalQuestions} sorudan ${score} doğru cevap verdiniz.`);
    console.log("Quiz Sonuçları:", userAnswers);

    // Sonuç sayfası yoksa ana sayfaya dön
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
        window.location.href = 'turkey.html'; 
    }
}

// Global scope'a fonksiyonları ekle ki HTML'den erişilsin
window.submitQuiz = submitQuiz;
window.goBackToAI = goBackToAI;
window.prevQuestion = prevQuestion;
window.nextQuestion = nextQuestion;
