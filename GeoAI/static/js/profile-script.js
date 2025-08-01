document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });


    function getProfileUrl(usernameToUse) {
        if (window.STATIC_URLS && window.STATIC_URLS.userProfileTemplate) {
            return window.STATIC_URLS.userProfileTemplate.replace('_USERNAME_PLACEHOLDER_', usernameToUse);
        }
        console.warn("WARN: window.STATIC_URLS.userProfileTemplate bulunamadı. Varsayılan profil URL şablonu kullanılıyor.");
        return `/profile/${usernameToUse}`; // Yedek URL
    }


    function showToast(message, type = 'success') {
        alert(message);
    }

    // HTML'den global değişkenleri al
    const username = window.CURRENT_PROFILE_USERNAME;
    const currentUserId = window.CURRENT_USER_ID; 
    const isMyProfile = window.IS_MY_PROFILE; 

    if (!username) {
        console.error("HATA: Kullanıcı adı HTML'den alınamadı. Profil sayfası düzgün yüklenmemiş olabilir.");
    }
    if (currentUserId === null) {
        console.warn("UYARI: window.CURRENT_USER_ID null. Misafir kullanıcı veya oturum açmamış.");
    }

    // --- Navbar Arama Fonksiyonları ---
    const navbarUserSearchInput = document.getElementById('navbarUserSearchInput');
    const userSearchResults = document.getElementById('userSearchResults');

    let searchTimeout;

    async function searchUsers() {
        const searchTerm = navbarUserSearchInput.value.trim();
        if (searchTerm.length < 2) {
            userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
            userSearchResults.style.display = 'block';
            return;
        }

        try {
            const response = await fetch(`/api/search_users?search_term=${encodeURIComponent(searchTerm)}`); 
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error:', response.status, errorText);
                throw new Error(`Kullanıcılar aranırken bir hata oluştu: ${response.status} ${response.statusText}. Detay: ${errorText}`);
            }
            const users = await response.json();
            
            userSearchResults.innerHTML = ''; 

            if (users.length === 0) {
                userSearchResults.innerHTML = '<div class="text-muted p-2">Kullanıcı bulunamadı.</div>';
            } else {
                users.forEach(user => {
                    const userDiv = document.createElement('div');
                    userDiv.classList.add('list-group-item', 'search-result-item');
                    const profileUrl = getProfileUrl(user.username);
                    const userProfilePicture = user.profile_picture_url || (window.STATIC_URLS && window.STATIC_URLS.sampleUserImage ? window.STATIC_URLS.sampleUserImage : '/static/images/sample_user.png');
                    
                    userDiv.innerHTML = `
                        <a href="${profileUrl}" class="d-flex align-items-center text-decoration-none text-dark">
                            <img src="${userProfilePicture}" alt="${user.username}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">
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

    // Arama kutusu ve buton event listener'ları
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
            } else if (navbarUserSearchInput.value.trim().length > 0) { 
                userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
                userSearchResults.style.display = 'block';
            }
        });

        navbarUserSearchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const searchTerm = this.value.trim();
            if (searchTerm.length >= 2) {
                searchTimeout = setTimeout(() => searchUsers(), 300);
            } else if (searchTerm === '') {
                userSearchResults.style.display = 'none'; 
            } else {
                userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
                userSearchResults.style.display = 'block';
            }
        });
    }
    
    const navbarSearchUserButton = document.getElementById('navbarSearchUserButton');
    if (navbarSearchUserButton) {
        navbarSearchUserButton.addEventListener('click', searchUsers);
    }

    // --- Profil Düzenleme Fonksiyonları ---
    const editProfileForm = document.getElementById('editProfileForm');
    const editBioInput = document.getElementById('editBio');
    const profilePictureUploadInput = document.getElementById('profilePictureUpload');
    const userBioDisplay = document.getElementById('userBio');
    const profileAvatarImage = document.querySelector('.profile-avatar');
    const editProfileModalElement = document.getElementById('editProfileModal'); 
    const editProfileModal = editProfileModalElement ? new bootstrap.Modal(editProfileModalElement) : null; 
    const editProfileMessage = document.getElementById('editProfileMessage');

    if (isMyProfile && editProfileForm) {
        const currentProfilePicInModal = document.getElementById('currentProfilePic');
        
        if (editProfileModalElement) {
            editProfileModalElement.addEventListener('show.bs.modal', function() {
                currentProfilePicInModal.src = profileAvatarImage.src;
            });
        }

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

    // --- Takip Et/Takibi Bırak İşlevselliği (Ana Profil Butonları) ---
    const followButton = document.getElementById('followButton');
    const unfollowButton = document.getElementById('unfollowButton');

    async function performFollowUnfollow(targetUsername, actionType, listItemElement = null) {
        const url = actionType === 'follow' ? `/api/follow/${targetUsername}` : `/api/unfollow/${targetUsername}`;
        const method = 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' }
            });
            const result = await response.json();

            if (response.ok) {
                showToast(result.message);
                if (!listItemElement) {
                    location.reload(); 
                } else {
                    const button = listItemElement.querySelector('.follow-unfollow-btn');
                    if (button) {
                        if (actionType === 'follow') {
                            button.classList.remove('btn-success', 'follow-btn');
                            button.classList.add('btn-danger', 'unfollow-btn');
                            button.textContent = 'Takibi Bırak';
                            button.dataset.isFollowing = 'true';
                        } else {
                            button.classList.remove('btn-danger', 'unfollow-btn');
                            button.classList.add('btn-success', 'follow-btn');
                            button.textContent = 'Takip Et';
                            button.dataset.isFollowing = 'false';
                        }
                    }
                }
            } else {
                showToast(result.detail || `İşlem başarısız: ${actionType}`);
            }
        } catch (error) {
            console.error(`Error during ${actionType} operation:`, error);
            showToast('Bir ağ hatası oluştu. Lütfen tekrar deneyin.');
        }
    }

    if (followButton) {
        followButton.addEventListener('click', () => performFollowUnfollow(username, 'follow'));
    }
    if (unfollowButton) {
        unfollowButton.addEventListener('click', () => performFollowUnfollow(username, 'unfollow'));
    }

    // --- Önerilen Arkadaşlar Takip/Takibi Bırak Butonları ---
    document.querySelectorAll('.recommended-friends-section .follow-btn, .recommended-friends-section .unfollow-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const targetUsername = this.dataset.username; 
            const actionType = this.classList.contains('unfollow-btn') ? 'unfollow' : 'follow';
            await performFollowUnfollow(targetUsername, actionType); 
        });
    });

    // --- Modals: Takipçiler ve Takip Edilenler ---
    const followersModalElement = document.getElementById('followersModal');
    const followersList = document.getElementById('followersList');

    if (followersModalElement) {
        followersModalElement.addEventListener('show.bs.modal', async function () {
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
                        li.classList.add('list-group-item', 'd-flex', 'align-items-center', 'justify-content-between');
                        const userProfilePicture = f.profile_picture_url || (window.STATIC_URLS ? window.STATIC_URLS.sampleUserImage : '/static/images/sample_user.png');
                        
                        let buttonsHtml = '';

                        
                        if (isMyProfile && currentUserId !== null && f.id !== currentUserId) {
                            buttonsHtml += `
                                <button class="btn btn-sm btn-danger ms-2 remove-follower-btn" 
                                        data-username="${f.username}" 
                                        data-id="${f.id}">
                                    Takipçiyi Çıkar
                                </button>
                            `;
                        } 
                        
                        if (currentUserId !== null && f.id !== currentUserId) {
                            const isFollowedByCurrentUser = f.is_followed_by_current_user === true; 
                            buttonsHtml += `
                                <button class="btn btn-sm ${isFollowedByCurrentUser ? 'btn-danger unfollow-btn' : 'btn-success follow-btn'} follow-unfollow-btn" 
                                        data-username="${f.username}" 
                                        data-is-following="${isFollowedByCurrentUser}">
                                    ${isFollowedByCurrentUser ? 'Takibi Bırak' : 'Takip Et'}
                                </button>
                            `;
                        }

                        li.innerHTML = `
                            <div class="d-flex align-items-center">
                                <img src="${userProfilePicture}" alt="${f.username}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">
                                <a href="${getProfileUrl(f.username)}" class="text-decoration-none text-dark"><strong>${f.username}</strong></a>
                            </div>
                            <div class="profile-list-actions">
                                ${buttonsHtml}
                            </div>
                        `;
                        followersList.appendChild(li);
                    });

                    
                    followersList.querySelectorAll('.remove-follower-btn').forEach(button => {
                        button.addEventListener('click', async function() {
                            const targetUsername = this.dataset.username;
                            const confirmRemove = confirm(`${targetUsername} adlı takipçiyi listenizden çıkarmak istediğinize emin misiniz?`);
                            if (confirmRemove) {
                                try {
                                    const removeResponse = await fetch(`/api/remove_follower/${targetUsername}`, {
                                        method: 'POST'
                                    });
                                    const removeResult = await removeResponse.json();

                                    if (removeResponse.ok) {
                                        showToast(removeResult.message);
                    
                                        this.closest('li').remove();
                                        
                                        location.reload(); 
                                    } else {
                                        showToast(removeResult.detail || 'Takipçiyi çıkarma başarısız oldu.', 'error');
                                    }
                                } catch (error) {
                                    console.error('Error removing follower:', error);
                                    showToast('Takipçiyi çıkarırken bir ağ hatası oluştu.', 'error');
                                }
                            }
                        });
                    });

                    
                    followersList.querySelectorAll('.follow-unfollow-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            const targetUsername = this.dataset.username;
                            const isFollowing = this.dataset.isFollowing === 'true';
                            const actionType = isFollowing ? 'unfollow' : 'follow';
                            performFollowUnfollow(targetUsername, actionType, this.closest('li'));
                        });
                    });
                }
            } catch (error) {
                console.error('Takipçileri yükleme hatası:', error);
                followersList.innerHTML = `<li class="list-group-item text-danger">Hata: ${error.message}</li>`;
            }
        });
    }

    const followingModalElement = document.getElementById('followingModal');
    const followingList = document.getElementById('followingList');

    if (followingModalElement) {
        followingModalElement.addEventListener('show.bs.modal', async function () {
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
                        li.classList.add('list-group-item', 'd-flex', 'align-items-center', 'justify-content-between');
                        const userProfilePicture = f.profile_picture_url || (window.STATIC_URLS ? window.STATIC_URLS.sampleUserImage : '/static/images/sample_user.png');
                        
                        let buttonsHtml = '';
                        
                        if (currentUserId !== null && f.id !== currentUserId) { 
                            const isFollowedByCurrentUser = f.is_followed_by_current_user === true;
                            buttonsHtml += `
                                <button class="btn btn-sm ${isFollowedByCurrentUser ? 'btn-danger unfollow-btn' : 'btn-success follow-btn'} follow-unfollow-btn" 
                                        data-username="${f.username}" 
                                        data-is-following="${isFollowedByCurrentUser}">
                                    ${isFollowedByCurrentUser ? 'Takibi Bırak' : 'Takip Et'}
                                </button>
                            `;
                        }
                        
                        li.innerHTML = `
                            <div class="d-flex align-items-center">
                                <img src="${userProfilePicture}" alt="${f.username}" class="rounded-circle me-2" style="width: 40px; height: 40px; object-fit: cover;">
                                <a href="${getProfileUrl(f.username)}" class="text-decoration-none text-dark"><strong>${f.username}</strong></a>
                            </div>
                            <div class="profile-list-actions">
                                ${buttonsHtml}
                            </div>
                        `;
                        followingList.appendChild(li);
                    });

                    
                    followingList.querySelectorAll('.follow-unfollow-btn').forEach(button => {
                        button.addEventListener('click', function() {
                            const targetUsername = this.dataset.username;
                            const isFollowing = this.dataset.isFollowing === 'true';
                            const actionType = isFollowing ? 'unfollow' : 'follow';
                            performFollowUnfollow(targetUsername, actionType, this.closest('li'));
                        });
                    });
                }
            } catch (error) {
                console.error('Takip edilenleri yükleme hatası:', error);
                followingList.innerHTML = `<li class="list-group-item text-danger">Hata: ${error.message}</li>`;
            }
        });
    }
});