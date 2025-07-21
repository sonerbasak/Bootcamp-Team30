document.addEventListener('DOMContentLoaded', function() {
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
                    userDiv.innerHTML = `
                        <a href="${user.profile_url}">
                            <strong>${user.username}</strong>
                            <p class="text-muted mb-0">${user.bio || 'Bio yok.'}</p>
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
            // Arama inputu veya sonuçlar tıklanmadığında sonuçları gizle
            if (!navbarUserSearchInput.contains(event.target) && !userSearchResults.contains(event.target)) {
                userSearchResults.style.display = 'none';
            }
        });

        navbarUserSearchInput.addEventListener('focus', function() {
            if (navbarUserSearchInput.value.trim().length >= 2) {
                searchUsers();
            } else if (userSearchResults.innerHTML.trim() !== '' && userSearchResults.innerHTML.trim() !== '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>' && userSearchResults.innerHTML.trim() !== '<div class="text-muted p-2">Kullanıcı bulunamadı.</div>') {
                 userSearchResults.style.display = 'block';
            }
        });

        navbarUserSearchInput.addEventListener('input', function() {
             if (navbarUserSearchInput.value.trim().length >= 2) {
                 searchUsers();
             } else {
                 userSearchResults.innerHTML = '<div class="text-muted p-2">Lütfen en az 2 karakter girin.</div>';
                 userSearchResults.style.display = 'block';
             }
             if (navbarUserSearchInput.value.trim() === '') {
                 userSearchResults.style.display = 'none';
             }
         });
    }

    // Profil Sayfası Özel Fonksiyonlar
    // HTML'den Jinja2 ile gelen kullanıcı adını global değişkene atıyoruz
    const profilePageUsernameElement = document.querySelector('h2.mb-0'); 
    const username = profilePageUsernameElement ? profilePageUsernameElement.textContent.trim() : null;

    if (!username) {
        console.error("Kullanıcı adı HTML'den alınamadı. Profil sayfası düzgün yüklenmemiş olabilir.");
        // Eğer kullanıcı adı yoksa, bu sayfadaki diğer JS bağımlılıkları çalışmayacağı için erken çıkıyoruz.
        return; 
    }

    const followButton = document.getElementById('followButton');
    const unfollowButton = document.getElementById('unfollowButton');
    const editProfileForm = document.getElementById('editProfileForm');
    const editBioInput = document.getElementById('editBio');
    const profilePictureUploadInput = document.getElementById('profilePictureUpload'); // YENİ: Profil resmi inputu
    const userBioDisplay = document.getElementById('userBio');
    const profileAvatarImage = document.querySelector('.profile-avatar'); // YENİ: Profil resmi img elementi
    const editProfileModalElement = document.getElementById('editProfileModal'); 
    // `editProfileModalElement` null değilse Bootstrap Modal nesnesini oluştur
    const editProfileModal = editProfileModalElement ? new bootstrap.Modal(editProfileModalElement) : null; 
    const editProfileMessage = document.getElementById('editProfileMessage');

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
                    location.reload(); // Sayfayı yenile
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
                    location.reload(); // Sayfayı yenile
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
    if (editProfileForm) {
        editProfileForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const newBio = editBioInput.value;
            const profilePictureFile = profilePictureUploadInput.files[0]; // YENİ: Yüklenen dosyayı al

            const formData = new FormData(); // YENİ: FormData nesnesi oluştur
            formData.append('bio', newBio); // Biyoğrafiyi FormData'ya ekle

            if (profilePictureFile) {
                formData.append('profile_picture', profilePictureFile); // YENİ: Dosyayı FormData'ya ekle
            }

            try {
                const response = await fetch('/api/profile/edit', {
                    method: 'POST',
                    // YENİ: FormData kullandığımız için 'Content-Type' header'ını ayarlamıyoruz.
                    // Tarayıcı otomatik olarak 'multipart/form-data' olarak ayarlar.
                    body: formData // YENİ: FormData nesnesini doğrudan gönderiyoruz
                });

                if (response.ok) {
                    const data = await response.json();
                    editProfileMessage.className = 'mt-2 text-success';
                    editProfileMessage.textContent = data.message || 'Profil başarıyla güncellendi! 🎉';
                    userBioDisplay.textContent = newBio; // Sayfadaki biyoğrafiyi anında güncelle
                    
                    // YENİ: Profil fotoğrafı güncellendiyse anında önizlemeyi güncelle
                    if (data.profile_picture_url) {
                        // Tarayıcı önbelleğini aşmak için timestamp ekle
                        profileAvatarImage.src = data.profile_picture_url + '?' + new Date().getTime(); 
                    }

                    // Eğer modal nesnesi oluşturulabildiyse gizle
                    if (editProfileModal) {
                        // Modal tamamen gizlendikten sonra sayfayı yenile
                        // removeEventListener'a gerek kalmadan sadece bir kez tetiklenmesini sağlar.
                        editProfileModalElement.addEventListener('hidden.bs.modal', function handler() {
                            location.reload(); 
                            this.removeEventListener('hidden.bs.modal', handler); // Dinleyiciyi kaldır
                        }); 
                        editProfileModal.hide(); 
                    } else {
                        // Eğer modal nesnesi oluşturulamadıysa doğrudan sayfayı yenile (yedek)
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

    // Modalları açıldığında listeleri yükle
    const followersModalElement = document.getElementById('followersModal');
    const followingModalElement = document.getElementById('followingModal');

    // Bu URL'yi dinamik olarak almak için bir yardımcı fonksiyon
    function getProfileUrl(username) {
        // Jinja2 tarafından oluşturulan URL şablonunu kullan
        // Flask/Jinja2'de url_for() çıktısı bir string olacaktır.
        // Python tarafında `url_for("user_profile", username="_TEMP_")` gibi bir şeyle gelmeli.
        // Bu yüzden burada '_TEMP_' yerine `username` koyarak dinamik URL oluşturulur.
        return `{{ url_for("user_profile", username='_TEMP_') }}`.replace('_TEMP_', username);
    }


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
                        li.classList.add('list-group-item');
                        // Jinja2 stringini doğrudan kullanmak yerine, getProfileUrl fonksiyonunu çağırıyoruz
                        li.innerHTML = `<a href="${getProfileUrl(f.username)}">${f.username}</a><p class="text-muted mb-0 ms-2" style="display:inline;">${f.bio || ''}</p>`;
                        followersList.appendChild(li);
                    });
                }
            } catch (error) {
                console.error('Takipçileri yükleme hatası:', error);
                followersList.innerHTML = `<li class="list-group-item text-danger">Hata: ${error.message}</li>`;
            }
        });
    }

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
                        li.classList.add('list-group-item');
                        // Jinja2 stringini doğrudan kullanmak yerine, getProfileUrl fonksiyonunu çağırıyoruz
                        li.innerHTML = `<a href="${getProfileUrl(f.username)}">${f.username}</a><p class="text-muted mb-0 ms-2" style="display:inline;">${f.bio || ''}</p>`;
                        followingList.appendChild(li);
                    });
                }
            } catch (error) {
                console.error('Takip edilenleri yükleme hatası:', error);
                followingList.innerHTML = `<li class="list-group-item text-danger">Hata: ${error.message}</li>`;
            }
        });
    }

});