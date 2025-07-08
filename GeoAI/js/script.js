// Ortak Fonksiyon: URL parametresi al
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// ==========================
// AI SAYFASI KODLARI (ai.html)
// ==========================
if (window.location.pathname.includes("ai.html")) {
    document.addEventListener("DOMContentLoaded", () => {
        const city = getQueryParam("city");
        const title = document.getElementById("pageTitle");

        if (city && title) {
            title.textContent = `🤖 ${city} hakkında AI ile Soru Oluştur`;
        }
    });

    function generateQuestion() {
        const city = getQueryParam("city") || "Belirtilmemiş şehir";
        const userInput = document.getElementById("userInput").value.trim();
        const outputBox = document.getElementById("outputBox");

        if (!userInput) {
            outputBox.innerHTML = "<strong>Lütfen bir konu giriniz.</strong>";
            outputBox.style.display = "block";
            return;
        }

        outputBox.innerText =
            `"${city}" ile ilgili AI tarafından oluşturulan örnek soru:\n\n` +
            `➤ ${userInput} konusunda ne düşünüyorsunuz?\n\n(AI cevabı burada gösterilecek...)`;

        outputBox.style.display = "block";
    }

    // Global erişim için fonksiyonu dışa aktar
    window.generateQuestion = generateQuestion;
    window.slidePrev = slidePrev;
    window.slideNext = slideNext;
}

// ==========================
// HARİTA SAYFASI KODLARI (index.html)
// ==========================
if (document.getElementById("map")) {
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
    let illerBilgi = [];
    let swiperInstance = null;
    const modal = document.getElementById("modal");

    // Veriler yükleniyor
    Promise.all([
        fetch("iller.json").then((res) => res.json()),
        fetch("tr-provinces.json").then((res) => res.json()),
    ])
        .then(([illerData, geoJsonData]) => {
            illerBilgi = illerData;

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
        .catch((err) => console.error("Veri yüklenirken hata:", err));

    // İl modalı aç
    function openIlModal(ilAdi) {
        const ilVerisi = illerBilgi.find(
            (i) => i.name.trim().toLowerCase() === ilAdi.trim().toLowerCase()
        );

        const icerik = ilVerisi
            ? `
        <div class="swiper mySwiper">
      <div class="swiper-wrapper">
        <div class="swiper-slide"><img src="${ilVerisi.resim
            }" alt="${ilAdi}" /></div>
        <div class="swiper-slide"><h3>Tarihçe</h3><p>${ilVerisi.tarih}</p></div>
        <div class="swiper-slide"><h3>Eserler</h3><p>${ilVerisi.eserler
            }</p></div>
        <div class="swiper-slide"><h3>Öneriler</h3><p>${ilVerisi.oneriler
            }</p></div>
        <div class="swiper-slide">
            <h3>Bilgiler</h3>
            <p><strong>Nüfus:</strong> ${ilVerisi.nufus}</p>
            <p><strong>Plaka:</strong> ${ilVerisi.plakaKodu}</p>
            <p><strong>Yemekler:</strong> ${ilVerisi.unluYemekler}</p>
        </div>
        <div class="swiper-slide">
            <h3>Üniversiteler</h3>
            <ul>${ilVerisi.universiteler
                .map((u) => `<li>${u}</li>`)
                .join("")}</ul>
        </div>
      </div>
    </div>
      `
            : "<p>İçerik bulunamadı.</p>";

        document.getElementById("modalTitle").innerText = ilAdi;
        document.getElementById("modalContent").innerHTML = icerik;

        // AI sayfasına bağlantı
        const aiBtn = document.querySelector(".ai-btn");
        if (aiBtn) {
            aiBtn.href = `ai.html?city=${encodeURIComponent(ilAdi)}`;
        }

        // Modalı aç
        modal.style.display = "flex";

        // Swiper'ı başlat
        if (swiperInstance) swiperInstance.destroy(true, true);
        if (ilVerisi) {
            swiperInstance = new Swiper(".mySwiper", {
                effect: "cards",
                grabCursor: true,
                cardsEffect: {
                    perSlideOffset: 10,
                    perSlideRotate: 2,
                    slideShadows: false,
                },
                loop: false,
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
        const fixedHeader = document.getElementById("fixedHeader");
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
}
