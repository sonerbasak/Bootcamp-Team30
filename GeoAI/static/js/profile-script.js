// static/js/profile-script.js
document.addEventListener('DOMContentLoaded', function() {
    const navbarUserSearchInput = document.getElementById('navbarUserSearchInput');
    const navbarSearchUserButton = document.getElementById('navbarSearchUserButton');
    const userSearchResults = document.getElementById('userSearchResults');

    // Arama fonksiyonu
    async function searchUsers() {
        const searchTerm = navbarUserSearchInput.value.trim();
        if (searchTerm.length < 2) { 
            userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
            userSearchResults.style.display = 'block'; // Sonuçları göster
            return;
        }

        try {
            const response = await fetch(`/api/search-users?q=${encodeURIComponent(searchTerm)}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Kullanıcılar aranırken bir hata oluştu.');
            }
            const users = await response.json();
            
            userSearchResults.innerHTML = ''; // Önceki sonuçları temizle

            if (users.length === 0) {
                userSearchResults.innerHTML = '<div class="text-muted p-2">Kullanıcı bulunamadı.</div>';
            } else {
                users.forEach(user => {
                    const userDiv = document.createElement('div');
                    userDiv.classList.add('list-group-item', 'search-result-item');
                    userDiv.innerHTML = `
                        <a href="${user.profile_url}">
                            <strong>${user.username}</strong>
                            <p class="text-muted mb-0">${user.bio || 'Bio yok.'}</p>
                        </a>
                    `;
                    userSearchResults.appendChild(userDiv);
                });
            }
            userSearchResults.style.display = 'block'; // Sonuçları göster

        } catch (error) {
            console.error('Kullanıcı arama hatası:', error);
            userSearchResults.innerHTML = `<div class="text-danger p-2">Hata: ${error.message}</div>`;
            userSearchResults.style.display = 'block'; // Hata mesajını göster
        }
    }

    // Arama butonuna tıklama olayı
    if (navbarSearchUserButton) {
        navbarSearchUserButton.addEventListener('click', searchUsers);
    }

    // Input alanında "Enter" tuşuna basma olayı
    if (navbarUserSearchInput) {
        navbarUserSearchInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Formun default submit işlemini engelle
                searchUsers();
            }
        });

        // Input dışına tıklayınca sonuçları gizle
        document.addEventListener('click', function(event) {
            if (!navbarUserSearchInput.contains(event.target) && !userSearchResults.contains(event.target)) {
                userSearchResults.style.display = 'none';
            }
        });

        // Input'a odaklanınca veya yazı yazılınca sonuç divini göster
        navbarUserSearchInput.addEventListener('focus', function() {
            if (userSearchResults.innerHTML.trim() !== '' && userSearchResults.innerHTML.trim() !== '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>' && userSearchResults.innerHTML.trim() !== '<div class="text-muted p-2">Kullanıcı bulunamadı.</div>') {
                 userSearchResults.style.display = 'block';
            }
        });

        navbarUserSearchInput.addEventListener('input', function() {
             if (navbarUserSearchInput.value.trim().length >= 2) {
                 searchUsers(); // Her harf girişinde ara
             } else {
                 userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
                 userSearchResults.style.display = 'block';
             }
             if (navbarUserSearchInput.value.trim() === '') {
                 userSearchResults.style.display = 'none'; // Input boşsa gizle
             }
         });
    }

    // Optional: Profili Düzenle butonu için placeholder
    const editProfileButton = document.querySelector('.profile-header .btn-outline-secondary');
    if (editProfileButton) {
        editProfileButton.addEventListener('click', function() {
            alert('Profili düzenleme fonksiyonu yakında eklenecek!');
            // Buraya bir modal açma veya form gösterme mantığı eklenebilir
        });
    }
});