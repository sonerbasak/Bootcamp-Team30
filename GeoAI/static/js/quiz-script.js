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

document.addEventListener("DOMContentLoaded", async () => {
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

    const swiperWrapper = document.getElementById("quiz-questions-container");
    if (swiperWrapper) {
    }

    // Geri butonu için event listener
    const backButton = document.querySelector(".back-button");
    if (backButton) {
        backButton.addEventListener("click", (event) => {
            // Varsayılan bağlantı davranışını engelle ki önce temizleme yapılabilsin
            event.preventDefault(); 
            
            const city = getQueryParam("city");
            if (city) {
                sessionStorage.removeItem(`aiQuizData-${city}`);
                console.log(`Geri giderken quiz verisi temizlendi: aiQuizData-${city}`);
            } else {
                // Eğer şehir bilgisi yoksa (genel kültür quizi), yine de genel veriyi temizle
                sessionStorage.removeItem('aiQuizData-null'); // Veya genel bir anahtar kullanıyorsanız onu
                console.log("Geri giderken genel quiz verisi temizlendi.");
            }
            
            // Ana sayfaya yönlendir
            window.location.href = backButton.href; 
        });
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
            init: function () {
                this.update();
                this.updateAutoHeight();
            },
            resize: function () {
                this.update();
                this.updateAutoHeight();
            },
        },
    });
}

async function loadQuestions(city) {
    console.log("loadQuestions başladı. City:", city);

    // sessionStorage kontrolü kaldırıldı, her zaman API çağrılacak.
    // Ancak hata ayıklama için promptu hala kaydetmek isteyebilirsiniz.

    let quizDataArray = null; // API'den gelen quiz soruları dizisini tutacak
    let sentPromptText = null; // Gönderilen prompt metnini tutacak

    console.log("Quiz verisi için API çağrılıyor..."); // Her zaman çağrıldığı için bu mesaj
    try {
        const res = await fetch(
            `/api/gemini-quiz?city=${encodeURIComponent(city)}`
        );
        
        console.log("API yanıtının başarı durumu (res.ok):", res.ok); 
        console.log("API yanıtının Content-Type başlığı:", res.headers.get('Content-Type')); 

        if (!res.ok) {
            // Hata durumunda JSON olarak detayları almaya çalışın
            let errorDetails;
            try {
                errorDetails = await res.json();
            } catch (jsonError) {
                // Eğer yanıt JSON değilse düz metin olarak alın
                errorDetails = { error: await res.text() };
            }
            
            console.error("API yanıt hatası:", res.status, errorDetails);
            throw new Error(`API yanıt vermedi: ${res.status} - ${errorDetails.error || "Bilinmeyen Hata"}`);
        }

        const data = await res.json(); // API'den gelen JSON verisini parse et
        console.log("API'den gelen RAW data objesi:", data); // <<< BURAYI KESİNLİKLE KONTROL ET!
        
        quizDataArray = data.quiz_data; // Artık doğrudan quiz_data dizisini alıyoruz
        sentPromptText = data.sent_prompt; // Promptu JSON yanıtından alıyoruz!

        console.log("Gemini API'den Gelen Quiz Verisi (JSON Array):", quizDataArray);
        
        // Promptu tarayıcı konsoluna yazdırıyoruz:
        console.log("\n" + "=".repeat(70));
        console.log("YAPAY ZEKAYA GÖNDERİLEN PROMPT (FRONTEND KONSOLU - API'den geldi):");
        console.log(sentPromptText); 
        console.log("=".repeat(70) + "\n");

        // Quiz verisini stringify edip sessionStorage'a kaydet
        // Her API çağrısında yenisiyle değiştirilecek
        sessionStorage.setItem(`aiQuizData-${city}`, JSON.stringify(quizDataArray));
        sessionStorage.setItem(`aiQuizPrompt-${city}`, sentPromptText); 
        console.log("Yeni quiz ve prompt verileri sessionStorage'a kaydedildi.");

    } catch (error) {
        console.error("Sorular alınırken hata oluştu:", error);
        alert("Sorular alınamadı: " + error.message);
        quizDataArray = []; // Hata durumunda boş dizi
        // Hata durumunda sessionStorage'ı da temizlemek isteyebilirsiniz,
        // ancak zaten her çağrıda üstüne yazıldığı için zorunlu değil.
        sessionStorage.removeItem(`aiQuizData-${city}`);
        sessionStorage.removeItem(`aiQuizPrompt-${city}`);
    }

    // quizQuestions artık API'den gelen direkt JSON dizisi olacak
    quizQuestions = quizDataArray || []; // Eğer quizDataArray null ise boş bir dizi kullan

    // userSelections dizisini quizQuestions uzunluğunda başlat
    userSelections = new Array(quizQuestions.length).fill(null);

    renderQuestions(quizQuestions);
}

function renderQuestions(questions) {
    const questionsContainer = document.getElementById(
        "quiz-questions-container"
    );
    questionsContainer.innerHTML = "";

    if (questions.length === 0) {
        questionsContainer.innerHTML =
            '<p class="text-center text-danger">Sorular yüklenemedi veya bulunamadı.</p>';
        return;
    }

    questions.forEach((q, index) => {
        const slide = document.createElement("div");
        slide.classList.add("swiper-slide", "quiz-slide");

        let optionsHtml = "";
        // Şıklar artık direkt q.a, q.b, q.c, q.d olarak erişilebilir
        const options = [q.a, q.b, q.c, q.d];

        options.forEach((option, optionIndex) => {
            const optionLetter = String.fromCharCode(65 + optionIndex);
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
            <p class="question-text">${q.soru}</p> <div class="options">
                ${optionsHtml}
            </div>
            <div class="question-category" style="display: none;">${q.kategori}</div>
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
    const timerDisplay = document.getElementById("timer");
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

function submitQuiz() {
    clearInterval(timerInterval);
    let score = 0;
    const reviewAnswers = [];

    quizQuestions.forEach((q, index) => {
        const userAnswerLetter = userSelections[index];
        const correctAnswerLetter = q.cevap; // q.answer yerine q.cevap

        let userAnswerText = null;
        if (userAnswerLetter) {
            const optionKey = userAnswerLetter.toLowerCase(); // 'a', 'b', 'c', 'd'
            userAnswerText = q[optionKey]; // Doğrudan objenin key'inden şık metnine erişim
        }

        let correctOptionText = null;
        if (correctAnswerLetter) {
            const correctOptionKey = correctAnswerLetter.toLowerCase();
            correctOptionText = q[correctOptionKey];
        }

        const isCorrect =
            userAnswerLetter?.toLowerCase().trim() ===
            correctAnswerLetter?.toLowerCase().trim();
        if (isCorrect) score++;

        reviewAnswers.push({
            question: q.soru, // q.question yerine q.soru
            category: q.kategori, // Yeni: Kategori bilgisini ekliyoruz
            userAnswerLetter,
            userAnswerText,
            correctAnswerLetter,
            correctOptionText,
            isCorrect,
        });
    });

    showResults(score, reviewAnswers);
}

function showResults(score, reviewAnswers) {
    const quizContainer = document.querySelector(".quiz-container");
    const resultsContainer = document.getElementById("quiz-results");

    // Quiz içeriğini gizle
    document.querySelector(".mySwiperQuiz").classList.add("d-none");
    document.querySelector(".quiz-actions").classList.add("d-none");

    // Sonuçları derle
    let html = `
        <h2 class="text-success text-center">Quiz Tamamlandı!</h2>
        <p class="text-center fs-5">Toplam Doğru Sayısı: <strong>${score}</strong> / ${quizQuestions.length}</p>
        <hr/>
        <h4 class="text-danger">Yanlış Cevaplar:</h4>
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
    </div>
`;

    resultsContainer.innerHTML = html;
    resultsContainer.classList.remove("d-none");
}

function goHome() {
    const city = getQueryParam("city");
    if (city) {
        sessionStorage.removeItem(`aiQuizData-${city}`);
        console.log(`Quiz verisi temizlendi: aiQuizData-${city}`);
    } else {
        sessionStorage.removeItem('aiQuizData-null');
        console.log("Genel quiz verisi temizlendi.");
    }
    window.location.href = "/";
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
        window.location.href = "http://127.0.0.1:8000/";
    }
}

window.submitQuiz = submitQuiz;
window.goBackToAI = goBackToAI;
window.prevQuestion = prevQuestion;
window.nextQuestion = nextQuestion;
window.handleOptionChange = handleOptionChange;
