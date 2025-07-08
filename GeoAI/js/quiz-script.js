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
        allowTouchMove: false, // Dokunmatik kaydırmayı devre dışı bırakır
        on: {
            slideChange: function () {
                currentQuestionIndex = this.realIndex;
            }
        }
    });
}

/**
 * Soruları yükleme fonksiyonu (API'den veya sabit bir diziden).
 * @param {string} city - Soruların hangi şehirle ilgili olacağı.
 */
async function loadQuestions(city) {
    // Burada dilerseniz AI'dan veya bir veritabanından dinamik olarak
    // şehre özel quiz soruları çekebilirsiniz.
    // Şimdilik örnek sorular kullanalım ve şehre göre basit bir filtreleme yapalım.

    const allQuestions = [
        {
            question: "Türkiye'nin en yüksek dağı hangisidir?",
            options: ["Kaçkar Dağı", "Erciyes Dağı", "Ağrı Dağı", "Uludağ"],
            answer: "Ağrı Dağı",
            city_keywords: [] // Genel soru
        },
        {
            question: "Türkiye Cumhuriyeti'nin kurucusu kimdir?",
            options: ["İsmet İnönü", "Fevzi Çakmak", "Mustafa Kemal Atatürk", "Celal Bayar"],
            answer: "Mustafa Kemal Atatürk",
            city_keywords: [] // Genel soru
        },
        {
            question: "Akdeniz Bölgesi'nin en büyük ili hangisidir?",
            options: ["Antalya", "Adana", "Mersin", "Hatay"],
            answer: "Antalya",
            city_keywords: ["Antalya"]
        },
        {
            question: "Ayasofya hangi şehirdedir?",
            options: ["Bursa", "İzmir", "İstanbul", "Edirne"],
            answer: "İstanbul",
            city_keywords: ["İstanbul"]
        },
        {
            question: "Galata Kulesi hangi şehirdedir?",
            options: ["Ankara", "İstanbul", "İzmir", "Trabzon"],
            answer: "İstanbul",
            city_keywords: ["İstanbul"]
        },
        {
            question: "Efes Antik Kenti hangi ilimizdedir?",
            options: ["Denizli", "Muğla", "İzmir", "Aydın"],
            answer: "İzmir",
            city_keywords: ["İzmir"]
        },
        {
            question: "Pamukkale Travertenleri hangi şehirdedir?",
            options: ["Antalya", "Denizli", "Muğla", "Burdur"],
            answer: "Denizli",
            city_keywords: ["Denizli"]
        },
        {
            question: "Kapadokya hangi ilimizde yer almaktadır?",
            options: ["Konya", "Kayseri", "Nevşehir", "Sivas"],
            answer: "Nevşehir",
            city_keywords: ["Nevşehir"]
        },
        {
            question: "Anıtkabir hangi şehirdedir?",
            options: ["İstanbul", "İzmir", "Ankara", "Bursa"],
            answer: "Ankara",
            city_keywords: ["Ankara"]
        },
        {
            question: "Boğaz Köprüsü hangi şehirde yer almaktadır?",
            options: ["İzmir", "İstanbul", "Çanakkale", "Bursa"],
            answer: "İstanbul",
            city_keywords: ["İstanbul"]
        }
    ];

    const filteredQuestions = allQuestions.filter(q =>
        !city || q.city_keywords.length === 0 || q.city_keywords.some(keyword => city.toLowerCase().includes(keyword.toLowerCase()))
    );

    if (filteredQuestions.length < 5) { 
        const generalQuestions = allQuestions.filter(q => q.city_keywords.length === 0);
        quizQuestions = [...new Set([...filteredQuestions, ...generalQuestions])].slice(0, 10); 
    } else {
        quizQuestions = filteredQuestions.slice(0, 10);
    }

    quizQuestions.sort(() => Math.random() - 0.5);

    const questionsContainer = document.getElementById('quiz-questions-container');
    questionsContainer.innerHTML = '';

    quizQuestions.forEach((q, index) => {
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

    // İsterseniz burada kullanıcıyı bir sonuç sayfasına yönlendirebilirsiniz.
    // Örneğin: window.location.href = `quiz-result.html?score=${score}&total=${totalQuestions}`;
    
    // Geçici olarak ana sayfaya yönlendiriyoruz
    goBackToAI();
}

/**
 * Swiper'da bir önceki soruya gider.
 */
function prevQuestion() {
    if (quizSwiper) {
        quizSwiper.slidePrev();
    }
}

/**
 * Swiper'da bir sonraki soruya gider.
 */
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

// Global scope'a fonksiyonları ekliyoruz ki HTML'den erişilebilsinler
window.submitQuiz = submitQuiz;
window.goBackToAI = goBackToAI;
window.prevQuestion = prevQuestion; // Yeni eklenen fonksiyon
window.nextQuestion = nextQuestion; // Yeni eklenen fonksiyon