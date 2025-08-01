document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("navbarUserSearchInput");
    const searchButton = document.getElementById("navbarSearchUserButton");
    const searchResultsDiv = document.getElementById("userSearchResults");

    let currentOffset = 0;
    const limit = 5;
    let isLoadingPosts = false;
    let currentTopicFilter = "Tümü";
    const loadingMessage = document.getElementById("loadingMorePosts");

    const performSearch = async (query) => {
        if (query.length < 2) {
            searchResultsDiv.innerHTML = "";
            searchResultsDiv.classList.remove("active");
            return;
        }

        try {
            const response = await fetch(
                `/api/search_users?q=${encodeURIComponent(query)}`
            );
            const users = await response.json();

            if (users.length > 0) {
                let resultsHtml = "";
                users.forEach((user) => {
                    const profilePic =
                        user.profile_picture_url ||
                        "https://via.placeholder.com/30/CCCCCC/FFFFFF?text=KU"; // Varsayılan resim
                    resultsHtml += `
                                <a href="/profile/${user.id}" class="list-group-item list-group-item-action d-flex align-items-center">
                                    <img src="${profilePic}" alt="${user.username}" class="rounded-circle me-2" style="width: 30px; height: 30px;">
                                    ${user.username}
                                </a>
                            `;
                });
                searchResultsDiv.innerHTML = resultsHtml;
                searchResultsDiv.classList.add("active");
            } else {
                searchResultsDiv.innerHTML =
                    '<div class="list-group-item text-muted">Kullanıcı bulunamadı.</div>';
                searchResultsDiv.classList.add("active");
            }
        } catch (error) {
            console.error("Kullanıcı arama hatası:", error);
            searchResultsDiv.innerHTML =
                '<div class="list-group-item text-danger">Arama sırasında bir hata oluştu.</div>';
            searchResultsDiv.classList.add("active");
        }
    };

    if (searchButton) {
        searchButton.addEventListener("click", () =>
            performSearch(searchInput.value)
        );
    }

    if (searchInput) {
        searchInput.addEventListener("input", () =>
            performSearch(searchInput.value)
        );
        searchInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
            }
        });
    }

    document.addEventListener("click", function (event) {
        if (
            !searchResultsDiv.contains(event.target) &&
            !searchInput.contains(event.target) &&
            !searchButton.contains(event.target)
        ) {
            searchResultsDiv.innerHTML = "";
            searchResultsDiv.classList.remove("active");
        }
    });

    const postForm = document.getElementById("postForm");
    const postContent = document.getElementById("postContent");
    const postTopic = document.getElementById("postTopic");
    const postImage = document.getElementById("postImage");
    const imagePreview = document.getElementById("imagePreview");
    const imagePreviewImg = imagePreview.querySelector("img");
    const removeImageBtn = document.getElementById("removeImageBtn");
    const postsContainer = document.getElementById("postsContainer");
    const topicFilterButtons = document.querySelectorAll(
        ".topic-filter-buttons .btn"
    );

    postImage.addEventListener("change", function () {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function (e) {
                imagePreviewImg.src = e.target.result;
                imagePreview.classList.remove("d-none");
            };
            reader.readAsDataURL(this.files[0]);
        } else {
            imagePreview.classList.add("d-none");
            imagePreviewImg.src = "#";
        }
    });

    removeImageBtn.addEventListener("click", function () {
        postImage.value = "";
        imagePreview.classList.add("d-none");
        imagePreviewImg.src = "#";
    });

    postForm.addEventListener("submit", async function (e) {
        e.preventDefault();

        const content = postContent.value.trim();
        const topic = postTopic.value;
        const imageFile = postImage.files[0];

        if (!content && !imageFile) {
            alert("Lütfen gönderi içeriği yazın veya bir görsel ekleyin.");
            return;
        }
        if (!topic) {
            alert("Lütfen bir konu seçin.");
            return;
        }

        const formData = new FormData();
        formData.append("content", content);
        formData.append("topic", topic);
        if (imageFile) {
            formData.append("image", imageFile);
        }

        try {
            const response = await fetch("/api/posts", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                const newPost = await response.json();
                const newPostCard = createPostCard(newPost);
                postsContainer.prepend(newPostCard);

                postContent.value = "";
                postTopic.value = "";
                postImage.value = "";
                imagePreview.classList.add("d-none");
                imagePreviewImg.src = "#";

                if (loadingMessage) {
                    loadingMessage.style.display = "none";
                }

                document
                    .querySelector('.topic-filter-buttons .btn[data-topic="Tümü"]')
                    .click();
            } else if (response.status === 401) {
                alert("Gönderi paylaşmak için giriş yapmalısınız.");
                window.location.href = "/login"; // Giriş sayfasına yönlendir
            } else {
                const errorData = await response.json();
                alert(
                    "Gönderi paylaşılırken bir hata oluştu: " +
                    (errorData.error || "Bilinmeyen Hata")
                );
            }
        } catch (error) {
            console.error("Gönderi hatası:", error);
            alert("Gönderi paylaşılırken bir ağ hatası oluştu.");
        }
    });

    function createPostCard(post) {
        const cardDiv = document.createElement("div");
        cardDiv.classList.add("card", "shadow-sm", "post-item-card", "mb-3");
        cardDiv.dataset.postTopic = post.topic;

        const profilePicUrl =
            post.profile_picture_url ||
            "https://via.placeholder.com/50/FFC107/FFFFFF?text=KU"; // Varsayılan profil resmi

        let imageHtml = "";
        if (post.image_url) {
            imageHtml = `<img src="${post.image_url}" class="img-fluid rounded mb-3 post-image" alt="Gönderi Görseli">`;
        }

        cardDiv.innerHTML = `
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <img src="${profilePicUrl}" class="rounded-circle me-3 profile-pic" alt="Profil Resmi">
                            <div>
                                <h6 class="mb-0 fw-bold post-username">${post.username
            }</h6>
                                <small class="text-muted post-time">${post.created_at
            }</small>
                            </div>
                        </div>
                        <p class="card-text post-content">${post.content}</p>
                        ${imageHtml}
                        <div class="post-actions d-flex justify-content-around mt-3 pt-3 border-top">
                            <button class="btn btn-sm btn-outline-secondary post-action-btn">
                                <i class="far fa-heart me-1"></i> Beğen (${post.likes || 0
            })
                            </button>
                            <button class="btn btn-sm btn-outline-secondary post-action-btn">
                                <i class="far fa-comment me-1"></i> Yorum Yap (${post.comments || 0
            })
                            </button>
                            <button class="btn btn-sm btn-outline-secondary post-action-btn">
                                <i class="fas fa-share me-1"></i> Paylaş
                            </button>
                        </div>
                    </div>
                `;
        return cardDiv;
    }

    // --- Gönderileri Yükleme ve Filtreleme İşlevselliği ---
    async function loadPosts(reset = false) {
        if (isLoadingPosts) return;
        isLoadingPosts = true;
        loadingMessage.style.display = "block";

        if (reset) {
            postsContainer.innerHTML = "";
            currentOffset = 0;
        }

        const url = `/api/posts?limit=${limit}&offset=${currentOffset}&topic=${encodeURIComponent(
            currentTopicFilter
        )}`;

        try {
            const response = await fetch(url);
            const posts = await response.json();

            if (posts.length > 0) {
                posts.forEach((post) => {
                    postsContainer.appendChild(createPostCard(post));
                });
                currentOffset += posts.length;
            } else {
                loadingMessage.querySelector("p").textContent =
                    "Gösterilecek başka gönderi yok.";
            }
        } catch (error) {
            console.error("Gönderiler yüklenirken hata oluştu:", error);
            loadingMessage.querySelector("p").textContent =
                "Gönderiler yüklenirken bir hata oluştu.";
            loadingMessage.querySelector("i").classList.remove("text-primary");
            loadingMessage.querySelector("i").classList.add("text-danger");
        } finally {
            isLoadingPosts = false;

            if (currentOffset > 0 && postsContainer.children.length > currentOffset) {
                loadingMessage.style.display = "none";
            } else if (posts.length === 0 && currentOffset === 0) {
                loadingMessage.querySelector("p").textContent =
                    "Henüz hiç gönderi bulunmamaktadır.";
            }
            if (posts.length === 0 && currentOffset > 0) {
                loadingMessage.querySelector("p").textContent =
                    "Tüm gönderiler yüklendi.";
            }
        }
    }

    // Konu filtreleme işlevselliği
    topicFilterButtons.forEach((button) => {
        button.addEventListener("click", function () {
            topicFilterButtons.forEach((btn) => btn.classList.remove("active"));
            this.classList.add("active");

            currentTopicFilter = this.dataset.topic;
            loadPosts(true);
        });
    });

    loadPosts(true);

    window.addEventListener("scroll", () => {
        const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
        if (scrollTop + clientHeight >= scrollHeight - 500 && !isLoadingPosts) {
            loadPosts();
        }
    });
});
