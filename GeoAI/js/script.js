// Harita oluşturuluyor
const map = L.map("map").setView([39, 35], 6);

L.tileLayer("https://{s}.basemaps.cartocdn.com/watercolor/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 18,
}).addTo(map);

// Değişkenler
let illerBilgi = [];
let swiperInstance = null;
let secilenIl = "";

// AI Panel öğeleri
const modal = document.getElementById("modal");
const openAiFromModalBtn = document.getElementById("openAiFromModalBtn");
const closeAiBtn = document.getElementById("closeAiBtn");
const aiPanel = document.getElementById("aiPanel");
const mapCol = document.getElementById("mapCol");
const generateBtn = document.getElementById("generateQuestionBtn");
const aiOutput = document.getElementById("aiOutput");
const aiQuestionInput = document.getElementById("aiQuestionInput");
const aiPanelTitle = document.getElementById("aiPanelTitle");

// Harita ve iller verileri
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
            onEachFeature: handleProvinceFeature,
        }).addTo(map);

        map.fitBounds(illerLayer.getBounds(), { padding: [20, 20] });
    })
    .catch((err) => console.error("Veriler yüklenirken hata:", err));

// Her il için olay tanımlayıcı
function handleProvinceFeature(feature, layer) {
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
}

// İl modalı aç
function openIlModal(ilAdi) {
    const ilVerisi = illerBilgi.find(
        (i) => i.name.trim().toLowerCase() === ilAdi.trim().toLowerCase()
    );

    let icerik = ilVerisi
        ? `
    <div class="swiper mySwiper" style="width:100%; height: 300px;">
      <div class="swiper-wrapper">
        <div class="swiper-slide"><img src="${ilVerisi.resim
        }" alt="${ilAdi}" /></div>
        <div class="swiper-slide"><h3>Tarihçe</h3><p>${ilVerisi.tarih}</p></div>
        <div class="swiper-slide"><h3>Eserler</h3><p>${ilVerisi.eserler
        }</p></div>
        <div class="swiper-slide"><h3>Öneriler</h3><p>${ilVerisi.oneriler
        }</p></div>
        <div class="swiper-slide"><h3>Bilgiler</h3>
          <p><strong>Nüfus:</strong> ${ilVerisi.nufus}</p>
          <p><strong>Plaka Kodu:</strong> ${ilVerisi.plakaKodu}</p>
          <p><strong>Yemekler:</strong> ${ilVerisi.unluYemekler}</p>
        </div>
        <div class="swiper-slide"><h3>Üniversiteler</h3><ul>${ilVerisi.universiteler
            .map((u) => `<li>${u}</li>`)
            .join("")}</ul></div>
      </div>
      <div class="swiper-pagination"></div>
    </div>
  `
        : "<p>İçerik bulunamadı.</p>";

    document.getElementById("modalTitle").innerText = ilAdi;
    document.getElementById("modalContent").innerHTML = icerik;
    // BURAYI KONTROL EDİN:
    // Daha önce 'block' ise, 'flex' olarak değiştirin.
    modal.style.display = "flex"; // <-- Önemli değişiklik

    if (swiperInstance) swiperInstance.destroy(true, true);

    if (ilVerisi) {
        swiperInstance = new Swiper(".mySwiper", {
            pagination: { el: ".swiper-pagination", clickable: true },
            loop: false,
        });
    }
}

// Modal kapat
function closeModal() {
    modal.style.display = "none";
    if (swiperInstance) {
        swiperInstance.destroy(true, true);
        swiperInstance = null;
    }
}

// AI Panel Aç
function openAiPanel(ilAdi) {
    secilenIl = ilAdi;
    aiPanelTitle.innerText = `${ilAdi} ile ilgili soru oluştur`;
    aiPanel.classList.remove("d-none");
    mapCol.classList.replace("col-12", "col-9");
}

// AI Panel Kapat
function closeAiPanel() {
    aiPanel.classList.add("d-none");
    mapCol.classList.replace("col-9", "col-12");
    aiOutput.innerText = "";
    aiQuestionInput.value = "";
    aiPanelTitle.innerText = "AI ile Soru Oluştur";
    secilenIl = "";
}

// Soru oluştur
function generateQuestion() {
    const question = aiQuestionInput.value.trim();
    if (!question) {
        alert("Lütfen soru yazınız.");
        return;
    }

    aiOutput.innerText = `"${secilenIl}" hakkında oluşturulan soru:\n\n${question}\n\n(AI cevabı burada görünecek.)`;
}

// Etkinlikler
openAiFromModalBtn.addEventListener("click", () => {
    closeModal();
    openAiPanel(document.getElementById("modalTitle").innerText);
});

closeAiBtn.addEventListener("click", closeAiPanel);
generateBtn.addEventListener("click", generateQuestion);

// Modal dışına tıklanınca kapat
window.onclick = (e) => {
    if (e.target === modal) closeModal();
};

// Splash ve intro animasyonları
window.addEventListener("load", () => {
    const splash = document.getElementById("splash");
    const fixedHeader = document.getElementById("fixedHeader");

    splash.addEventListener("animationend", () => {
        splash.style.display = "none";
        fixedHeader.style.display = "block";
    });
});

setTimeout(() => {
    const intro = document.getElementById("introOverlay");
    intro.style.transition = "opacity 1s ease";
    intro.style.opacity = 0;
    setTimeout(() => {
        intro.style.display = "none";
    }, 1000);
}, 5000);
