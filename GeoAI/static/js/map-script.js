function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// ==========================
// HARİTA SAYFASI KODLARI (index.html)
// ==========================

// Harita oluşturuluyor
const map = L.map("map").setView([39, 35], 6);

L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/watercolor/{z}/{x}/{y}{r}.png",
    {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 18,
    }
).addTo(map);

// Değişkenler
let illerBilgi = []; // Bu dizi, fetch ile doldurulacak
let swiperInstance = null;
const modal = document.getElementById("modal");

// Veriler yükleniyor
Promise.all([
    fetch("/data/tr-info.json").then((res) => res.json()),
    fetch("/data/tr-geo.json").then((res) => res.json()),
])
    .then(([illerData, geoJsonData]) => {
        illerBilgi = illerData; // illerBilgi artık global olarak erişilebilir

        const illerLayer = L.geoJSON(geoJsonData, {
            style: {
                color: "#00695C",
                weight: 1,
                fillColor: "#4DB6AC",
                fillOpacity: 0.6,
            },
            onEachFeature: (feature, layer) => {
                const ilAdi = feature.properties.name || "İl";

                layer.on("mouseover", (e) => {
                    e.target.setStyle({ fillColor: "#00796B", weight: 2 });
                    layer
                        .bindTooltip(ilAdi, {
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

                layer.on("click", () => openIlModal(ilAdi));
            },
        }).addTo(map);

        map.fitBounds(illerLayer.getBounds(), { padding: [20, 20] });
    })
    .catch((err) => console.error("Veri yüklenirken hata:"));

// İl modalı aç
function openIlModal(ilAdi) {
    const ilVerisi = illerBilgi.find(
        (i) => i.name.trim().toLowerCase() === ilAdi.trim().toLowerCase()
    );

    const icerik = ilVerisi
        ? `
        <div class="swiper mySwiper">
            <div class="swiper-wrapper">
                <div class="swiper-slide"><img src="${ilVerisi['il-resmi']}" alt="${ilAdi}" /></div>
                <div class="swiper-slide">
                    <h3>Bilgiler</h3>
                    <p><strong>İsim:</strong> ${ilVerisi.name}</p>
                    <p><strong>Plaka:</strong> ${ilVerisi.plakaKodu}</p>
                    <p><strong>Nüfus:</strong> ${ilVerisi.nufus}</p>
                </div>
                <div class="swiper-slide"><h3>Tarihçe</h3><p>${ilVerisi.tarih}</p></div>
                <div class="swiper-slide"><h3>Eserler</h3><p>${ilVerisi.eserler}</p></div>
                <div class="swiper-slide"><h3>Müzeler</h3><img src="${ilVerisi['müzeResmi']}" alt="${ilVerisi['müzeResmi']}" /><br><p>${ilVerisi.müzeler}</p></div>
                <div class="swiper-slide"><h3>Öneriler</h3><p>${ilVerisi.oneriler}</p></div>
                <div class="swiper-slide"><h3>Yemekler</h3><p>${ilVerisi.unluYemekler}</p></div>
                <div class="swiper-slide"><h3>Üniversiteler</h3><p>${ilVerisi.universiteler}</p></div>
                <div class="swiper-slide"><h3>Ekonomik Faaliyetler</h3><p>${ilVerisi.ekonomikFaaliyetler}</p></div>
                <div class="swiper-slide"><h3>Tarım Ürünleri</h3><p>${ilVerisi.tarimUrunleri}</p></div>
                <div class="swiper-slide"><h3>Gezilecek Yerler</h3><p>${ilVerisi.gezilecekyerler}</p></div>
                <div class="swiper-slide"><h3>Hangi Ülkede Var Oldu</h3><p>${ilVerisi.hangiülkedevaroldu}</p></div>
                <div class="swiper-slide"><h3>Önemli İnsanlar</h3><p>${ilVerisi.önemliinsanlar}</p></div>
                <div class="swiper-slide"><h3>Hayvancılık</h3><p>${ilVerisi.hayvancılık}</p></div>
                <div class="swiper-slide"><h3>Bitki Örtüsü</h3><p>${ilVerisi.bitkiörtüsü}</p></div>
                <div class="swiper-slide"><h3>Hava Koşulları</h3><p>${ilVerisi.havakoşulları}</p></div>
                <div class="swiper-slide"><h3>Coğrafi İşaretler</h3><p>${ilVerisi.coğrafiişaretler}</p></div>
                <div class="swiper-slide"><h3>Tarihi Olaylar</h3><p>${ilVerisi.tarihiólaylar}</p></div>
                <div class="swiper-slide"><h3>Seyahat Hatırası</h3><p>${ilVerisi.seyahathatirasi}</p></div>
            </div>
        </div>
      `
            : "<p>İçerik bulunamadı.</p>";

    document.getElementById("modalTitle").innerText = ilAdi;
    document.getElementById("modalContent").innerHTML = icerik;

    // AI sayfasına bağlantı
    const aiBtn = document.getElementById("aiLink");
    if (aiBtn) {
        aiBtn.href = `ai?city=${encodeURIComponent(ilAdi)}`;
    }

    // Modalı aç
    modal.style.display = "flex";

    // Swiper'ı başlat
    if (swiperInstance) swiperInstance.destroy(true, true);
    if (ilVerisi) { // Sadece il verisi varsa Swiper'ı başlat
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

// Modal kapatma
function closeModal() {
    modal.style.display = "none";
    if (swiperInstance) {
        swiperInstance.destroy(true, true);
        swiperInstance = null;
    }
}

// Swiper önceki slayta git
function slidePrev() {
    if (swiperInstance) {
        swiperInstance.slidePrev();
    }
}

// Swiper sonraki slayta git
function slideNext() {
    if (swiperInstance) {
        swiperInstance.slideNext();
    }
}

// Modal dışına tıklayınca kapat
window.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
});

// Splash ve intro overlay geçişleri
window.addEventListener("load", () => {
    const splash = document.getElementById("splash");
    const fixedHeader = document.getElementById("fixedHeader"); // Eğer böyle bir element varsa
    if (splash) {
        splash.addEventListener("animationend", () => {
            splash.style.display = "none";
            if (fixedHeader) fixedHeader.style.display = "block";
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

// --- Rastgele Şehir Seçme Fonksiyonu ---
function selectRandomCity() {
    if (illerBilgi.length === 0) {
        console.warn("Şehir verileri henüz yüklenmedi veya boş.");
        return;
    }

    const randomIndex = Math.floor(Math.random() * illerBilgi.length);
    const randomIl = illerBilgi[randomIndex];

    openIlModal(randomIl.name);
}


// --- Rastgele Şehir Linki için Olay Dinleyici ---
const randomCityLink = document.getElementById('randomCityLink');
if (randomCityLink) {
    randomCityLink.addEventListener('click', function(event) {
        event.preventDefault(); // Linkin varsayılan tıklama davranışını engeller (sayfa yenileme)
        selectRandomCity(); // Artık tanımlanmış olan fonksiyonu çağır
    });
}

// Global erişim için fonksiyonları dışa aktar
window.closeModal = closeModal;
window.slidePrev = slidePrev;
window.slideNext = slideNext;
// openIlModal'ı da dışa aktarabilirsiniz, ancak şu an için direkt çağrılıyor.
// window.openIlModal = openIlModal;