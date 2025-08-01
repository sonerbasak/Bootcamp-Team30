function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// Harita başlatılıyor
const map = L.map("map").setView([20, 0], 2);

L.tileLayer("https://{s}.basemaps.cartocdn.com/watercolor/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 18,
}).addTo(map);

// Değişkenler
let countriesInfo = []; 
let swiperInstance = null;
const modal = document.getElementById("modal");

// Veriler yükleniyor
Promise.all([
    fetch("/data/world-info.json").then((res) => res.json()),
    fetch("/data/world-geo.json").then((res) => res.json()),
])
    .then(([countriesData, geoJsonData]) => {
        countriesInfo = countriesData;

        const countriesLayer = L.geoJSON(geoJsonData, {
            style: {
                color: "#00695C",
                weight: 1,
                fillColor: "#4DB6AC",
                fillOpacity: 0.6,
            },
            onEachFeature: (feature, layer) => {
                const countryName = feature.properties.NAME_TR || feature.properties.NAME_EN || "Bilinmeyen Ülke";

                layer.on("mouseover", (e) => {
                    e.target.setStyle({ fillColor: "#00796B", weight: 2 });
                    layer
                        .bindTooltip(countryName, {
                            direction: "top",
                            className: "leaflet-tooltip",
                            offset: [0, -10],
                        })
                        .openTooltip(e.latlng);
                });

                layer.on("mouseout", (e) => {
                    e.target.setStyle({ fillColor: "#4DB6AC", weight: 1 });
                    layer.closeTooltip();
                });

                
                layer.on("click", () => openCountryModal(countryName));
            },
        }).addTo(map);

        
    })
    .catch((err) => console.error("Veri yüklenirken hata:", err));

// Modal açma fonksiyonu
function openCountryModal(countryName) {
    const safeCountryName = typeof countryName === 'string' ? countryName.trim().toLowerCase() : '';

    const country = countriesInfo.find(
        (c) => c && c.name && c.name.trim().toLowerCase() === safeCountryName
    );

    let content = "";
    if (country) {
        content = `
        <div class="swiper mySwiper">
            <div class="swiper-wrapper">
                <div class="swiper-slide modal-section">
                    ${country["CountryFlag/Image"] ? `<img src="${country["CountryFlag/Image"]}" alt="${countryName} Bayrağı" class="img-fluid rounded country-flag-img" />` : '<p>Bayrak bilgisi yok.</p>'}
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Genel Bilgiler ℹ️</h3>
                    <p><strong>Başkent:</strong> ${country.Capital || 'N/A'}</p>
                    <p><strong>Yüzölçümü:</strong> ${country.Area || 'N/A'}</p>
                    <p><strong>Nüfus:</strong> ${country.Population ? country.Population.toLocaleString('tr-TR') : 'N/A'}</p>
                    <p><strong>Para Birimi:</strong> ${country.Currency || 'N/A'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Resmi Dil(ler) 🗣️</h3>
                    ${(country["OfficialLanguage(s)"] && country["OfficialLanguage(s)"].length > 0) ? 
                        `<ul>${country["OfficialLanguage(s)"].map(lang => `<li>${lang}</li>`).join('')}</ul>` : 
                        '<p>Dil bilgisi yok.</p>'}
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Coğrafya ve İklim 🌍</h3>
                    <p>${country.GeographyAndClimate || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Tarihçe 📜</h3>
                    <p>${country.History || 'Tarihçe bilgisi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Uluslararası İlişkiler 🤝</h3>
                    <p>${country.InternationalRelations || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Ünlü Yemekler 🍲</h3>
                    ${(country.FamousDishes && country.FamousDishes.length > 0) ? 
                        `<ul>${country.FamousDishes.map(dish => `<li>${dish}</li>`).join('')}</ul>` : 
                        '<p>Yemek bilgisi yok.</p>'}
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Başlıca Turistik Yerler 🗺️</h3>
                    ${(country.MajorTouristAttractions && country.MajorTouristAttractions.length > 0) ? 
                        `<ul>${country.MajorTouristAttractions.map(attraction => `<li>${attraction}</li>`).join('')}</ul>` : 
                        '<p>Turistik yer bilgisi yok.</p>'}
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Kültürel Öne Çıkanlar 🎭</h3>
                    <p>${country.CulturalHighlights || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Üniversiteler ve Eğitim 🎓</h3>
                    <p>${country.UniversitiesAndEducation || 'Üniversite bilgisi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Doğal Kaynaklar 🌳</h3>
                    <p>${country.NaturalResources || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Seyahat İpuçları ✈️</h3>
                    <p>${country.TravelTips || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Başlıca Sporlar 🏆</h3>
                    ${(country.MajorSports && country.MajorSports.length > 0) ? 
                        `<ul>${country.MajorSports.map(sport => `<li>${sport}</li>`).join('')}</ul>` : 
                        '<p>Spor bilgisi yok.</p>'}
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Tipik Mimari 🏛️</h3>
                    <p>${country.TypicalArchitecture || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Vahşi Yaşam 🦌</h3>
                    <p>${country.Wildlife || 'Bilgi yok.'}</p>
                </div>
                <div class="swiper-slide modal-section">
                    <h3>Ünlü Kişilikler 🌟</h3>
                    ${(country.FamousPersonalities && country.FamousPersonalities.length > 0) ? 
                        `<ul>${country.FamousPersonalities.map(person => `<li>${person}</li>`).join('')}</ul>` : 
                        '<p>Ünlü kişilik bilgisi yok.</p>'}
                </div>
            </div>
            </div>
        `;
    } else {
        content = "<p>Bu ülke için içerik bulunamadı.</p>";
    }

    document.getElementById("modalTitle").innerText = countryName;
    document.getElementById("modalContent").innerHTML = content;

    // AI quiz linkini güncelle
    const aiBtn = document.getElementById("aiLink");
    if (aiBtn) {
        aiBtn.href = `ai?country=${encodeURIComponent(countryName)}`;
    }

    // Modal aç
    modal.style.display = "flex";

    // Önceki swiper varsa yok et
    if (swiperInstance) swiperInstance.destroy(true, true);

    if (country) { 
        swiperInstance = new Swiper(".mySwiper", {
            effect: "cards",
            grabCursor: true,
            cardsEffect: {
                perSlideOffset: 8,
                perSlideRotate: 2,
                slideShadows: false,
            },
            loop: false,
            pagination: false, 
            navigation: false, 
        });
    }
}

// Modal kapatma fonksiyonu
function closeModal() {
    modal.style.display = "none";
    if (swiperInstance) {
        swiperInstance.destroy(true, true);
        swiperInstance = null;
    }
}

// Swiper kontrol butonları 
function slidePrev() {
    if (swiperInstance) swiperInstance.slidePrev();
}

function slideNext() {
    if (swiperInstance) swiperInstance.slideNext();
}

// Modal dışına tıklayınca kapat
window.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
});

// Splash ekran ve intro overlay ayarları
window.addEventListener("load", () => {
    const splash = document.getElementById("splash");
    if (splash) {
        splash.addEventListener("animationend", () => {
            splash.style.display = "none";
        });
    }
});

setTimeout(() => {
    const intro = document.getElementById("introOverlay");
    if (intro) {
        intro.style.transition = "opacity 1s ease";
        intro.style.opacity = 0;
        setTimeout(() => {
            intro.style.display = "none";
        }, 1000);
    }
}, 2500);

// --- Rastgele Ülke Seçme Fonksiyonu ---
function selectRandomCountry() {
    if (countriesInfo.length === 0) {
        return;
    }

    const randomIndex = Math.floor(Math.random() * countriesInfo.length);
    const randomCountry = countriesInfo[randomIndex];

    openCountryModal(randomCountry.name);
}

// --- Rastgele Ülke Linki için Olay Dinleyici ---
const randomCityLink = document.getElementById('randomCityLink');
if (randomCityLink) {
    randomCityLink.addEventListener('click', function(event) {
        event.preventDefault(); 
        selectRandomCountry(); 
    });
}

// Global erişim için
window.closeModal = closeModal;
window.slidePrev = slidePrev;
window.slideNext = slideNext;
window.openCountryModal = openCountryModal;
window.selectRandomCountry = selectRandomCountry;