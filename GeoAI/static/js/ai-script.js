// js/ai-script.js

function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

document.addEventListener("DOMContentLoaded", () => {
    const city = getQueryParam("city");
    const title = document.getElementById("pageTitle");

    if (city && title) {
        title.textContent = `🤖 ${city} hakkında AI ile Quiz Oluştur`;
    }
});

function generateQuestion() {
    const city = getQueryParam("city") || "Genel";
    window.location.href = `quiz?city=${encodeURIComponent(city)}`;
}

window.generateQuestion = generateQuestion;