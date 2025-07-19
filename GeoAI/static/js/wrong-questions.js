// static/js/wrong-questions.js

let reviewQuizQuestions = []; // Bu sayfadaki soruları tutacak
let currentReviewQuestionIndex = 0;
let reviewUserSelections = []; // Bu sayfadaki kullanıcı cevaplarını tutacak
let reviewTimerInterval;
const reviewQuizDuration = 5 * 60; // 5 dakika olarak ayarlandı
let reviewTimeLeft = reviewQuizDuration;
let reviewQuizSwiper;


document.addEventListener("DOMContentLoaded", async () => {
    // 1. Önce yanlış soruları yükle
    await loadWrongQuestionsForReview();

    // 2. Swiper'ı başlat ve diğer işlemleri Swiper başlatıldıktan sonra yap
    // Swiper'ın DOM üzerinde tamamen render olmasını beklemek için setTimeout
    setTimeout(() => {
        initializeReviewSwiper(); // Swiper başlatılıyor

        // Swiper başarılı bir şekilde başlatıldıysa, diğer işlemlere geç
        if (reviewQuizSwiper) {
            startReviewTimer(); // Zamanlayıcıyı başlat

            // Buton event listener'ları
            document.querySelector(".quiz-actions .prev-button").addEventListener("click", () => {
                if (reviewQuizSwiper) reviewQuizSwiper.slidePrev();
            });
            document.querySelector(".quiz-actions .next-button").addEventListener("click", () => {
                if (reviewQuizSwiper) reviewQuizSwiper.slideNext();
            });
            document.querySelector(".quiz-actions .btn-success").addEventListener("click", submitReviewQuiz);

            // Swiper konteynerini görünür yap
            const swiperContainerEl = document.querySelector(".mySwiperReviewQuiz");
            if (swiperContainerEl) {
                swiperContainerEl.style.opacity = "1"; // CSS'te opacity:0 varsa
                console.log("Swiper başarıyla başlatıldı ve görünür yapıldı.");
            }
        } else {
            console.error("Swiper başlatılamadı. Sayfayı yenilemeyi deneyin.");
        }
    }, 200); // Biraz daha uzun bir gecikme (200ms) ekledik
});


function initializeReviewSwiper() {
    const swiperContainerEl = document.querySelector(".mySwiperReviewQuiz");

    // Swiper konteyneri hala görünmez veya genişliği sıfırsa tekrar dene
    if (!swiperContainerEl || swiperContainerEl.offsetWidth === 0 || swiperContainerEl.offsetHeight === 0) {
        console.warn("Swiper konteyneri henüz hazır değil veya boyutları sıfır. Tekrar deneniyor...");
        setTimeout(initializeReviewSwiper, 200); // Biraz daha uzun bekle
        return;
    }

    // Eğer Swiper zaten başlatıldıysa yeniden başlatma
    if (reviewQuizSwiper) {
        reviewQuizSwiper.destroy(true, true); // Mevcut Swiper'ı yok et
        console.log("Mevcut Swiper örneği yok edildi.");
    }

    reviewQuizSwiper = new Swiper(".mySwiperReviewQuiz", {
        loop: false,
        navigation: {
            nextEl: ".quiz-actions .next-button",
            prevEl: ".quiz-actions .prev-button",
        },
        pagination: {
            el: ".swiper-pagination",
            clickable: true,
        },
        allowTouchMove: false, // Kullanıcının elle kaydırmasını engelle

        slidesPerView: 1,
        slidesPerGroup: 1,
        centeredSlides: true,
        spaceBetween: 20,
        autoHeight: true, // Slayt içeriğine göre yüksekliği ayarlar

        // DOM değişikliklerini gözlemle ve Swiper'ı güncelle
        observer: true,
        observeParents: true,
        observeSlideChildren: true,

        on: {
            slideChange: function () {
                currentReviewQuestionIndex = this.realIndex;
                this.updateAutoHeight(); // Slayt değiştiğinde yüksekliği güncelle
            },
            init: function () {
                this.update(); // Başlangıçta Swiper'ı güncelle
                this.updateAutoHeight(); // Yüksekliği ayarla
                console.log("Swiper init edildi.");
            },
            resize: function () {
                this.update(); // Boyut değiştiğinde güncelle
                this.updateAutoHeight();
                console.log("Swiper yeniden boyutlandırıldı.");
            },
            // Swiper'ın DOM'daki öğeleri bulamadığı durumlarda loglama
            observerUpdate: function() {
                console.log("Swiper observer güncellendi.");
            }
        },
    });
    console.log("Swiper initializeReviewSwiper içinde başlatıldı.");
}

async function loadWrongQuestionsForReview() {
    console.log("Yanlış sorular yükleniyor...");
    const questionsContainer = document.getElementById("review-quiz-questions-container");
    // Yükleniyor spinner'ını göster
    questionsContainer.innerHTML = `
        <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
            <div class="spinner-border text-danger mb-3" role="status" style="width: 4rem; height: 4rem;">
                <span class="visually-hidden">Yükleniyor...</span>
            </div>
            <p class="text-center fs-5 fw-semibold">Yanlış sorularınız yükleniyor...</p>
        </div>
    `;

    try {
        const res = await fetch("/api/get-wrong-questions");
        if (!res.ok) {
            const errorData = await res.json();
            throw new Error(`Sorular alınamadı: ${res.status} - ${errorData.message}`);
        }
        const data = await res.json();
        const wrongQuestions = data.wrong_questions;

        if (wrongQuestions.length === 0) {
            questionsContainer.innerHTML = `
                <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                    <p class="text-center">Henüz yanlış cevapladığınız soru bulunmamaktadır. Harika!</p>
                </div>
            `;
            // Swiper'ı boşken başlatmamak veya ona uygun davranmak önemli
            if (reviewQuizSwiper) {
                reviewQuizSwiper.destroy(true, true);
                reviewQuizSwiper = null; // Swiper nesnesini null yap
            }
            return;
        }

        reviewQuizQuestions = wrongQuestions;
        reviewUserSelections = new Array(reviewQuizQuestions.length).fill(null); // Cevapları sıfırla

        renderReviewQuestions(reviewQuizQuestions);

    } catch (error) {
        console.error("Yanlış soruları çekerken hata oluştu:", error);
        questionsContainer.innerHTML = `
            <div class="swiper-slide d-flex flex-column justify-content-center align-items-center" style="min-height: 300px;">
                <p class="text-center text-danger">Sorular yüklenirken bir hata oluştu: ${error.message}</p>
            </div>
        `;
        if (reviewQuizSwiper) {
            reviewQuizSwiper.destroy(true, true);
            reviewQuizSwiper = null;
        }
    }
}

function renderReviewQuestions(questions) {
    const questionsContainer = document.getElementById("review-quiz-questions-container");
    questionsContainer.innerHTML = ""; // Yükleniyor mesajını temizle

    questions.forEach((q, index) => {
        const slide = document.createElement("div");
        slide.classList.add("swiper-slide", "quiz-slide");

        let optionsHtml = "";
        const options = [q.option_a, q.option_b, q.option_c, q.option_d];

        options.forEach((option, optionIndex) => {
            const optionLetter = String.fromCharCode(65 + optionIndex);
            const isChecked = reviewUserSelections[index] === optionLetter ? "checked" : "";
            optionsHtml += `
                <label>
                    <input type="radio"
                           name="review-question-${index}"
                           value="${optionLetter}"
                           onchange="handleReviewOptionChange(${index}, '${optionLetter}')"
                           ${isChecked}> ${optionLetter}) ${option}
                </label>
            `;
        });

        slide.innerHTML = `
            <div class="question-number">Soru ${index + 1}</div>
            <p class="question-text">${q.question_text}</p>
            <div class="options">
                ${optionsHtml}
            </div>
            <div class="question-category" style="display: none;">${q.category}</div>
        `;
        questionsContainer.appendChild(slide);
    });

    // Sorular yüklendikten sonra Swiper'ı güncelle
    if (reviewQuizSwiper) {
        reviewQuizSwiper.update();
        reviewQuizSwiper.updateAutoHeight();
        reviewQuizSwiper.slideTo(0, 0); // İlk soruya geri dön
        console.log("Swiper renderReviewQuestions içinde güncellendi.");
    } else {
        // Eğer Swiper henüz başlatılmadıysa, render ettikten sonra başlatmayı tetikle
        // Bu durum genelde ilk yüklemede olur
        setTimeout(initializeReviewSwiper, 50);
    }
}

function handleReviewOptionChange(questionIndex, selectedLetter) {
    reviewUserSelections[questionIndex] = selectedLetter;
    console.log(`Soru ${questionIndex + 1} için seçilen: ${selectedLetter}`);
}

function startReviewTimer() {
    const timerDisplay = document.getElementById("timer");
    // Mevcut zamanlayıcı varsa temizle (sayfa yenilendiğinde veya tekrar başlatıldığında çakışmayı önlemek için)
    if (reviewTimerInterval) {
        clearInterval(reviewTimerInterval);
    }

    reviewTimerInterval = setInterval(() => {
        let minutes = Math.floor(reviewTimeLeft / 60);
        let seconds = reviewTimeLeft % 60;

        minutes = minutes < 10 ? "0" + minutes : minutes;
        seconds = seconds < 10 ? "0" + seconds : seconds;

        timerDisplay.textContent = `Kalan Süre: ${minutes}:${seconds}`;

        if (reviewTimeLeft <= 0) {
            clearInterval(reviewTimerInterval);
            alert("Süreniz doldu! Quiz otomatik olarak tamamlanıyor.");
            submitReviewQuiz();
        }
        reviewTimeLeft--;
    }, 1000);
    console.log("Zamanlayıcı başlatıldı.");
}


function submitReviewQuiz() {
    clearInterval(reviewTimerInterval);
    console.log("Quiz değerlendirme başlatılıyor...");
    let correctCount = 0;
    const reviewResultsHtml = [];

    reviewQuizQuestions.forEach((q, index) => {
        const userAnswerLetter = reviewUserSelections[index];
        const correctAnswerLetter = q.correct_answer_letter;

        const isCorrect = userAnswerLetter?.toLowerCase().trim() === correctAnswerLetter?.toLowerCase().trim();
        if (isCorrect) {
            correctCount++;
        }

        // Kullanıcının verdiği cevabın metnini al
        const userOptionKey = 'option_' + (userAnswerLetter ? userAnswerLetter.toLowerCase() : '');
        const userAnswerText = q[userOptionKey] || 'Boş Bırakıldı / Bulunamadı';

        // Doğru cevabın metnini al
        const correctOptionKey = 'option_' + (correctAnswerLetter ? correctAnswerLetter.toLowerCase() : '');
        const correctAnswerText = q[correctOptionKey] || 'Bulunamadı';


        reviewResultsHtml.push(`
            <div class="card mb-3 ${isCorrect ? 'border-success' : 'border-danger'}">
                <div class="card-body">
                    <p><strong>Soru ${index + 1}:</strong> ${q.question_text}</p>
                    <p>A) ${q.option_a}</p>
                    <p>B) ${q.option_b}</p>
                    <p>C) ${q.option_c}</p>
                    <p>D) ${q.option_d}</p>
                    <p class="${isCorrect ? 'text-success' : 'text-danger'}">
                        <strong>Senin Cevabın:</strong> ${userAnswerLetter || 'Cevaplanmadı'} ) ${userAnswerText}
                    </p>
                    <p class="text-success"><strong>Doğru Cevap:</strong> ${correctAnswerLetter} ) ${correctAnswerText}</p>
                </div>
            </div>
        `);
    });

    const resultsContainer = document.getElementById("quiz-review-results");
    resultsContainer.innerHTML = `
        <h2 class="text-center ${correctCount === reviewQuizQuestions.length ? 'text-success' : 'text-primary'}">Değerlendirme Sonucu</h2>
        <p class="text-center fs-5">Doğru Cevap Sayısı: <strong>${correctCount}</strong> / ${reviewQuizQuestions.length}</p>
        <hr/>
        ${reviewResultsHtml.join('')}
        <div class="text-center mt-4">
            <button
                class="btn btn-success px-4 py-2 fs-5 fw-semibold"
                style="border-radius: 25px; box-shadow: 0 5px 15px rgba(0, 77, 64, 0.4);"
                onclick="window.location.href='/'"
            >
                Ana Sayfaya Dön
            </button>
            <button
                class="btn btn-primary px-4 py-2 fs-5 fw-semibold ms-3"
                style="border-radius: 25px; box-shadow: 0 5px 15px rgba(0, 123, 255, 0.4);"
                onclick="window.location.reload()"
            >
                Tekrar Dene
            </button>
        </div>
    `;
    resultsContainer.classList.remove("d-none");

    // Quiz içeriğini gizle
    document.querySelector(".mySwiperReviewQuiz").classList.add("d-none");
    document.querySelector(".quiz-actions").classList.add("d-none");
    console.log("Değerlendirme tamamlandı, sonuçlar gösteriliyor.");
}

// Global olarak erişilebilir hale getir
window.submitReviewQuiz = submitReviewQuiz;
window.handleReviewOptionChange = handleReviewOptionChange;