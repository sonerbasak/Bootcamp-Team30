document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap Tooltipleri etkinleştir
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Navbar Arama Fonksiyonları
    const navbarUserSearchInput = document.getElementById('navbarUserSearchInput');
    const navbarSearchUserButton = document.getElementById('navbarSearchUserButton');
    const userSearchResults = document.getElementById('userSearchResults');

    async function searchUsers() {
        const searchTerm = navbarUserSearchInput.value.trim();
        if (searchTerm.length < 2) {
            userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
            userSearchResults.style.display = 'block';
            return;
        }

        try {
            const response = await fetch(`/api/search-users?q=${encodeURIComponent(searchTerm)}`);
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error:', response.status, errorText);
                throw new Error(`Kullanıcılar aranırken bir hata oluştu: ${response.status} ${response.statusText}`);
            }
            const users = await response.json();
            
            userSearchResults.innerHTML = ''; 

            if (users.length === 0) {
                userSearchResults.innerHTML = '<div class="text-muted p-2">Kullanıcı bulunamadı.</div>';
            } else {
                users.forEach(user => {
                    const userDiv = document.createElement('div');
                    userDiv.classList.add('list-group-item', 'search-result-item');
                    // Kullanıcı profil URL'sini oluşturmak için dinamik yol
                    const profileUrl = getProfileUrl(user.username);
                    userDiv.innerHTML = `
                        <a href="${profileUrl}" class="d-flex align-items-center text-decoration-none text-dark">
                            <img src="${user.profile_picture_url || window.STATIC_URLS.sampleUserImage}" alt="${user.username}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">
                            <div>
                                <strong>${user.username}</strong>
                                <p class="text-muted mb-0 small">${user.bio || 'Bio yok.'}</p>
                            </div>
                        </a>
                    `;
                    userSearchResults.appendChild(userDiv);
                });
            }
            userSearchResults.style.display = 'block';

        } catch (error) {
            console.error('Kullanıcı arama hatası:', error);
            userSearchResults.innerHTML = `<div class="text-danger p-2">Hata: ${error.message}</div>`;
            userSearchResults.style.display = 'block';
        }
    }

    if (navbarSearchUserButton) {
        navbarSearchUserButton.addEventListener('click', searchUsers);
    }

    if (navbarUserSearchInput) {
        navbarUserSearchInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                searchUsers();
            }
        });

        document.addEventListener('click', function(event) {
            if (!navbarUserSearchInput.contains(event.target) && !userSearchResults.contains(event.target)) {
                userSearchResults.style.display = 'none';
            }
        });

        navbarUserSearchInput.addEventListener('focus', function() {
            if (navbarUserSearchInput.value.trim().length >= 2) {
                searchUsers();
            } else if (userSearchResults.innerHTML.trim() !== '' && userSearchResults.innerHTML.trim().includes('text-muted')) {
                 userSearchResults.style.display = 'block';
            }
        });

        navbarUserSearchInput.addEventListener('input', function() {
             if (navbarUserSearchInput.value.trim().length >= 2) {
                 searchUsers();
             } else if (navbarUserSearchInput.value.trim() === '') {
                 userSearchResults.style.display = 'none';
             } else {
                 userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
                 userSearchResults.style.display = 'block';
             }
         });
    }

    // Profil Sayfası Özel Fonksiyonlar
    // Jinja2 tarafından doğrudan render edilen kullanıcı adını alıyoruz
    // window.CURRENT_PROFILE_USERNAME artık HTML'den geldiği için burayı kullanabiliriz
    const username = window.CURRENT_PROFILE_USERNAME;

    if (!username) {
        console.error("Kullanıcı adı HTML'den alınamadı. Profil sayfası düzgün yüklenmemiş olabilir.");
        return; 
    }

    // Takip et/bırak butonları için doğru ID'leri kullanıyoruz
    const followButton = document.getElementById('followButton');
    const unfollowButton = document.getElementById('unfollowButton');
    
    const editProfileForm = document.getElementById('editProfileForm');
    const editBioInput = document.getElementById('editBio');
    const profilePictureUploadInput = document.getElementById('profilePictureUpload');
    const userBioDisplay = document.getElementById('userBio');
    const profileAvatarImage = document.querySelector('.profile-avatar');
    const editProfileModalElement = document.getElementById('editProfileModal'); 
    const editProfileModal = editProfileModalElement ? new bootstrap.Modal(editProfileModalElement) : null; 
    const editProfileMessage = document.getElementById('editProfileMessage');

    // Kullanıcı profil URL şablonunu global değişkenden al
    function getProfileUrl(usernameToUse) {
        return window.STATIC_URLS.userProfileTemplate.replace('_USERNAME_PLACEHOLDER_', usernameToUse);
    }

    // Takip Et Butonu İşlevi
    if (followButton) {
        followButton.addEventListener('click', async function() {
            try {
                const response = await fetch(`/api/follow/${username}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    alert('Takip edildi! ✅');
                    location.reload(); 
                } else {
                    const errorData = await response.json();
                    alert('Takip etme hatası: ' + (errorData.detail || 'Bir hata oluştu.'));
                }
            } catch (error) {
                console.error('Takip etme isteği hatası:', error);
                alert('Takip etme isteği gönderilirken bir sorun oluştu.');
            }
        });
    }

    // Takibi Bırak Butonu İşlevi
    if (unfollowButton) {
        unfollowButton.addEventListener('click', async function() {
            try {
                const response = await fetch(`/api/unfollow/${username}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (response.ok) {
                    alert('Takip bırakıldı! 👋');
                    location.reload(); 
                } else {
                    const errorData = await response.json();
                    alert('Takibi bırakma hatası: ' + (errorData.detail || 'Bir hata oluştu.'));
                }
            } catch (error) {
                console.error('Takibi bırakma isteği hatası:', error);
                alert('Takibi bırakma isteği gönderilirken bir sorun oluştu.');
            }
        });
    }

    // Profili Düzenle Formu İşlevi
    // isMyProfile kontrolünü HTML'den gelen global değişkenden alıyoruz
    if (window.IS_MY_PROFILE && editProfileForm) {
        // Modal açıldığında mevcut rozet ID'lerini ve seçim durumunu ayarla
        let selectedBadges = new Set(window.DISPLAYED_BADGE_IDS || []); // Güvenli başlangıç

        const currentProfilePicInModal = document.getElementById('currentProfilePic');
        const availableBadgesContainer = document.getElementById('availableBadgesContainer');
        const selectedBadgeIdsInput = document.getElementById('selectedBadgeIdsInput');

        // Mevcut rozetleri yükle ve seçim kutularını oluşturma fonksiyonu
        function loadAvailableBadgesForEdit() {
            availableBadgesContainer.innerHTML = ''; // Her açılışta önceki içeriği temizle
            const achievedBadges = window.ACHIEVED_BADGES || []; // Güvenli başlangıç

            achievedBadges.forEach(badge => {
                const badgeInfo = badge.badge_info;
                const isSelected = selectedBadges.has(badgeInfo.id);

                const badgeDiv = document.createElement('div');
                badgeDiv.classList.add('form-check', 'form-check-inline', 'text-center', 'border', 'rounded', 'p-1', 'badge-selection-item');
                if (isSelected) {
                    badgeDiv.classList.add('selected');
                }
                badgeDiv.style.cursor = 'pointer';
                badgeDiv.style.width = '70px'; 
                badgeDiv.style.height = '70px'; 
                badgeDiv.style.overflow = 'hidden';

                badgeDiv.innerHTML = `
                    <img src="${badgeInfo.image_url}" alt="${badgeInfo.name}" class="img-fluid" style="width: 50px; height: 50px; object-fit: contain;">
                    <small class="d-block text-truncate" title="${badgeInfo.name}">${badgeInfo.name}</small>
                `;
                badgeDiv.dataset.badgeId = badgeInfo.id;

                badgeDiv.addEventListener('click', function() {
                    const id = parseInt(this.dataset.badgeId);
                    if (selectedBadges.has(id)) {
                        selectedBadges.delete(id);
                        this.classList.remove('selected');
                    } else {
                        if (selectedBadges.size < 5) {
                            selectedBadges.add(id);
                            this.classList.add('selected');
                        } else {
                            alert("En fazla 5 rozet sergileyebilirsiniz.");
                        }
                    }
                    selectedBadgeIdsInput.value = JSON.stringify(Array.from(selectedBadges));
                });
                
                new bootstrap.Tooltip(badgeDiv, {
                    title: `${badgeInfo.name}: ${badgeInfo.description}`,
                    placement: 'top'
                });

                availableBadgesContainer.appendChild(badgeDiv);
            });
            selectedBadgeIdsInput.value = JSON.stringify(Array.from(selectedBadges));
        }

        if (editProfileModalElement) {
            editProfileModalElement.addEventListener('show.bs.modal', function() {
                // Modalı açarken mevcut profil resmini ayarla
                currentProfilePicInModal.src = profileAvatarImage.src;
                // Rozetleri yükle
                loadAvailableBadgesForEdit();
            });
        }

        // Profil fotoğrafı önizlemesi
        profilePictureUploadInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                currentProfilePicInModal.src = URL.createObjectURL(this.files[0]);
            }
        });

        editProfileForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const newBio = editBioInput.value;
            const profilePictureFile = profilePictureUploadInput.files[0];

            const formData = new FormData();
            formData.append('bio', newBio);
            formData.append('displayed_badge_ids', selectedBadgeIdsInput.value); // Rozetleri ekle

            if (profilePictureFile) {
                formData.append('profile_picture', profilePictureFile);
            }

            try {
                const response = await fetch('/api/profile/edit', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    const data = await response.json();
                    editProfileMessage.className = 'mt-2 text-success';
                    editProfileMessage.textContent = data.message || 'Profil başarıyla güncellendi! 🎉';
                    userBioDisplay.textContent = newBio;
                    
                    if (data.profile_picture_url) {
                        profileAvatarImage.src = data.profile_picture_url + '?' + new Date().getTime(); 
                    }

                    if (editProfileModal) {
                        editProfileModalElement.addEventListener('hidden.bs.modal', function handler() {
                            location.reload(); 
                            this.removeEventListener('hidden.bs.modal', handler);
                        }); 
                        editProfileModal.hide(); 
                    } else {
                        location.reload();
                    }

                } else {
                    const errorData = await response.json();
                    editProfileMessage.className = 'mt-2 text-danger';
                    editProfileMessage.textContent = errorData.detail || 'Profil güncellenemedi. 😢';
                }
            } catch (error) {
                console.error('Profil düzenleme isteği hatası:', error);
                editProfileMessage.className = 'mt-2 text-danger';
                editProfileMessage.textContent = 'Profil güncelleme isteği gönderilirken bir sorun oluştu. 🚨';
            }
        });
    }

    // Takipçiler modalı açıldığında veri yükle
    const followersModalElement = document.getElementById('followersModal');
    if (followersModalElement) {
        followersModalElement.addEventListener('show.bs.modal', async function () {
            const followersList = document.getElementById('followersList');
            followersList.innerHTML = '<li class="list-group-item text-muted">Yükleniyor...</li>';
            try {
                const response = await fetch(`/api/profile/${username}/followers`);
                if (!response.ok) {
                    throw new Error('Takipçiler yüklenemedi. 😞');
                }
                const followers = await response.json();
                followersList.innerHTML = '';
                if (followers.length === 0) {
                    followersList.innerHTML = '<li class="list-group-item text-muted">Henüz takipçi yok.</li>';
                } else {
                    followers.forEach(f => {
                        const li = document.createElement('li');
                        li.classList.add('list-group-item', 'd-flex', 'align-items-center');
                        li.innerHTML = `
                            <img src="${f.profile_picture_url || window.STATIC_URLS.sampleUserImage}" alt="${f.username}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">
                            <a href="${getProfileUrl(f.username)}">${f.username}</a><p class="text-muted mb-0 ms-2" style="display:inline;">${f.bio || ''}</p>`;
                        followersList.appendChild(li);
                    });
                }
            } catch (error) {
                console.error('Takipçileri yükleme hatası:', error);
                followersList.innerHTML = `<li class="list-group-item text-danger">Hata: ${error.message}</li>`;
            }
        });
    }

    // Takip edilenler modalı açıldığında veri yükle
    const followingModalElement = document.getElementById('followingModal');
    if (followingModalElement) {
        followingModalElement.addEventListener('show.bs.modal', async function () {
            const followingList = document.getElementById('followingList');
            followingList.innerHTML = '<li class="list-group-item text-muted">Yükleniyor...</li>';
            try {
                const response = await fetch(`/api/profile/${username}/following`);
                if (!response.ok) {
                    throw new Error('Takip edilenler yüklenemedi. 😞');
                }
                const following = await response.json();
                followingList.innerHTML = '';
                if (following.length === 0) {
                    followingList.innerHTML = '<li class="list-group-item text-muted">Henüz kimseyi takip etmiyorsunuz.</li>';
                } else {
                    following.forEach(f => {
                        const li = document.createElement('li');
                        li.classList.add('list-group-item', 'd-flex', 'align-items-center');
                        li.innerHTML = `
                            <img src="${f.profile_picture_url || window.STATIC_URLS.sampleUserImage}" alt="${f.username}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">
                            <a href="${getProfileUrl(f.username)}">${f.username}</a><p class="text-muted mb-0 ms-2" style="display:inline;">${f.bio || ''}</p>`;
                        followingList.appendChild(li);
                    });
                }
            } catch (error) {
                console.error('Takip edilenleri yükleme hatası:', error);
                followingList.innerHTML = `<li class="list-group-item text-danger">Hata: ${error.message}</li>`;
            }
        });
    }

    // Önerilen Arkadaşlar Takip/Takibi Bırak Butonları
    document.querySelectorAll('.recommended-friends-section .follow-btn, .recommended-friends-section .unfollow-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const usernameToModify = this.dataset.username;
            const isFollowing = this.classList.contains('unfollow-btn');
            
            const url = isFollowing ? `/api/unfollow/${usernameToModify}` : `/api/follow/${usernameToModify}`;
            const method = 'POST';

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    alert(data.message);
                    location.reload(); 
                } else {
                    const errorData = await response.json();
                    alert(`Hata: ${errorData.detail}`);
                }
            } catch (error) {
                console.error('Fetch error:', error);
                alert('Bir hata oluştu. Lütfen tekrar deneyin.');
            }
        });
    });
});