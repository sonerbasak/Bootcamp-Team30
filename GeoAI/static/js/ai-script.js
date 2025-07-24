// js/ai-script.js

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

document.addEventListener("DOMContentLoaded", () => {
    // URL'den 'type' ve 'name' parametrelerini alıyoruz
    const quizTypeFromURL = getQueryParam("type");
    const quizNameFromURL = getQueryParam("name");

    const oldCountryParam = getQueryParam("country");
    const oldCityParam = getQueryParam("city");

    let finalQuizType;
    let finalQuizName;

    if (quizTypeFromURL && quizNameFromURL) {
        finalQuizType = quizTypeFromURL;
        finalQuizName = quizNameFromURL;
    } else if (oldCountryParam) {
        finalQuizType = "country";
        finalQuizName = oldCountryParam;
    } else if (oldCityParam) {
        finalQuizType = "city";
        finalQuizName = oldCityParam;
    } else {
        finalQuizType = "general";
        finalQuizName = "";
    }

    const title = document.getElementById("pageTitle");

    if (title) {
        if (finalQuizType === "country" && finalQuizName) {
            title.textContent = `🤖 ${finalQuizName} Hakkında AI ile Quiz Oluştur`;
        } else if (finalQuizType === "city" && finalQuizName) {
            title.textContent = `🤖 ${finalQuizName} Hakkında AI ile Quiz Oluştur`;
        } else {
            title.textContent = `🤖 Genel Kültür AI Quizi Oluştur`;
        }
    }

    const generateQuizBtn = document.getElementById("generate-quiz-btn");
    if (generateQuizBtn) {
        generateQuizBtn.addEventListener("click", () => {
            const targetUrl = `quiz?type=${encodeURIComponent(finalQuizType || 'general')}&name=${encodeURIComponent(finalQuizName || '')}`;
            window.location.href = targetUrl;
        });
    }
});