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
    fetch("/data/countries.json").then((res) => res.json()),
    fetch("/data/world-provinces.json").then((res) => res.json()),
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
    const country = countriesInfo.find(
        (c) => c.name.trim().toLowerCase() === countryName.trim().toLowerCase()
    );

    const content = country
        ? `
        <div class="swiper mySwiper">
            <div class="swiper-wrapper">
                <div class="swiper-slide">
                    <img src="${country.resim || ''}" alt="${countryName}" class="img-fluid rounded" />
                </div>
                <div class="swiper-slide"><h3>Tarihçe</h3><p>${country.tarih || 'Bilgi yok.'}</p></div>
                <div class="swiper-slide"><h3>Eserler</h3><p>${country.eserler || 'Bilgi yok.'}</p></div>
                <div class="swiper-slide"><h3>Öneriler</h3><p>${country.oneriler || 'Bilgi yok.'}</p></div>
                <div class="swiper-slide">
                    <h3>Bilgiler</h3>
                    <p><strong>Nüfus:</strong> ${country.nufus || 'N/A'}</p>
                    <p><strong>Plaka Kodu:</strong> ${country.plakaKodu || 'N/A'}</p>
                    <p><strong>Yemekler:</strong> ${country.unluYemekler || 'N/A'}</p>
                </div>
                <div class="swiper-slide">
                    <h3>Üniversiteler</h3>
                    <ul>${(country.universiteler || []).map(u => `<li>${u}</li>`).join('')}</ul>
                </div>
            </div>
            <div class="swiper-pagination"></div>
        </div>
        `
        : "<p>Bu ülke için içerik bulunamadı.</p>";

    document.getElementById("modalTitle").innerText = countryName;
    document.getElementById("modalContent").innerHTML = content;

    // AI quiz linkini güncelle
    const aiBtn = document.getElementById("aiLink");
    if (aiBtn) {
        aiBtn.href = `ai.html?country=${encodeURIComponent(countryName)}`;
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
                perSlideOffset: 10,
                perSlideRotate: 2,
                slideShadows: false,
            },
            loop: false,
            pagination: {
                el: ".swiper-pagination",
                clickable: true,
            },
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
}, 5000);

// Global erişim için
window.closeModal = closeModal;
window.slidePrev = slidePrev;
window.slideNext = slideNext;
window.openCountryModal = openCountryModal;
