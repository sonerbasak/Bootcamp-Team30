// GeoAI/static/js/messages-script.js
document.addEventListener('DOMContentLoaded', function() {
    const conversationItemsContainer = document.getElementById('conversationItems');
    const chatHeader = document.getElementById('chatHeader');
    const chatMessages = document.getElementById('chatMessages');
    const messageInputArea = document.getElementById('messageInputArea');
    const messageInput = document.getElementById('messageInput');
    const sendMessageButton = document.getElementById('sendMessageButton');

    // Yeni mesaj modalı elemanları
    const newMessageButton = document.getElementById('newMessageButton');
    const newMessageModal = new bootstrap.Modal(document.getElementById('newMessageModal'));
    const userSearchInput = document.getElementById('userSearchInput');
    const searchResults = document.getElementById('searchResults');
    const selectedUserContainer = document.getElementById('selectedUserContainer');
    const selectedUsernameDisplay = document.getElementById('selectedUsernameDisplay');
    const selectedNewMessageUserId = document.getElementById('selectedNewMessageUserId');
    const newMessageContent = document.getElementById('newMessageContent');
    const sendNewMessageButton = document.getElementById('sendNewMessageButton');

    let selectedOtherUserId = null;
    let selectedOtherUsername = '';
    let selectedOtherProfilePic = '';

    // Navbar arama işlevi
    const navbarUserSearchInput = document.getElementById('navbarUserSearchInput');
    const navbarSearchUserButton = document.getElementById('navbarSearchUserButton');

    if (navbarUserSearchInput && navbarSearchUserButton) {
        navbarSearchUserButton.addEventListener('click', function() {
            const searchTerm = navbarUserSearchInput.value.trim();
            if (searchTerm) {
                window.location.href = `/profile/${searchTerm}`; // Kullanıcı profiline yönlendir
            }
        });

        navbarUserSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                navbarSearchUserButton.click();
            }
        });
    }

    // Konuşma öğelerine tıklama dinleyicilerini ekle
    function attachConversationItemListeners() {
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', function() {
                // Önceki aktif öğeyi temizle
                document.querySelectorAll('.conversation-item.active').forEach(activeItem => {
                    activeItem.classList.remove('active');
                });
                // Yeni aktif öğeyi ayarla
                item.classList.add('active');

                selectedOtherUserId = item.dataset.otherUserId;
                const username = item.querySelector('h6').textContent;
                const profilePic = item.querySelector('img').src;
                selectedOtherUsername = username;
                selectedOtherProfilePic = profilePic;

                updateChatHeader(username, profilePic);
                messageInputArea.classList.remove('d-none'); // Mesaj giriş alanını göster
                loadMessages(selectedOtherUserId);
            });
        });
    }

    // Sohbet başlığını güncelleme
    function updateChatHeader(username, profilePic) {
        chatHeader.innerHTML = `
            <img src="${profilePic}" alt="Profil" class="profile-pic-small me-2">
            <h5 class="mb-0">${username}</h5>
        `;
    }

    // Mesajları yükle
    async function loadMessages(otherUserId) {
        chatMessages.innerHTML = '<p class="text-center text-muted">Mesajlar yükleniyor...</p>';
        try {
            const response = await fetch(`/api/messages/${otherUserId}`);
            if (!response.ok) {
                throw new Error('Mesajlar yüklenirken hata oluştu.');
            }
            const messages = await response.json();
            displayMessages(messages);
        } catch (error) {
            chatMessages.innerHTML = `<p class="text-center text-danger">Mesajlar yüklenemedi: ${error.message}</p>`;
        }
    }

    // Mesajları göster
    function displayMessages(messages) {
        chatMessages.innerHTML = ''; // Önceki mesajları temizle
        if (messages.length === 0) {
            chatMessages.innerHTML = '<p class="text-center text-muted">Bu sohbet için henüz mesaj yok.</p>';
            return;
        }

        // Mesajları tersten döngüye alarak eskiden yeniye doğru sırala
        messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message-bubble');
            if (msg.sender_id === currentUserId) { // currentUserId global olarak Jinja2'den geliyor
                messageDiv.classList.add('sent');
                messageDiv.style.marginLeft = 'auto'; // Sağa hizala
            } else {
                messageDiv.classList.add('received');
                messageDiv.style.marginRight = 'auto'; // Sola hizala
            }
            messageDiv.textContent = msg.content;
            chatMessages.prepend(messageDiv); // Yeni mesajları en üste ekle (flex-direction-reverse ile aşağıda görünür)
        });
        chatMessages.scrollTop = chatMessages.scrollHeight; // En alta kaydır
    }

    // Mesaj gönderme işlevi
    async function sendMessage(receiverId, content) {
        if (!content.trim()) {
            alert('Boş mesaj gönderemezsiniz.');
            return;
        }

        try {
            const formData = new FormData();
            formData.append('receiver_id', receiverId);
            formData.append('content', content);

            const response = await fetch('/api/messages/send', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Mesaj gönderilemedi.');
            }

            const responseData = await response.json();

            // Mesaj gönderildikten sonra sohbeti yeniden yükle
            if (selectedOtherUserId == receiverId) { // Eğer mevcut sohbetse
                loadMessages(receiverId);
            } else { // Yeni başlatılan bir sohbetse, konuşmalar listesini güncelle
                 updateConversationsList();
            }
            return true;

        } catch (error) {
            alert(`Mesaj gönderilemedi: ${error.message}`);
            return false;
        } finally {
            messageInput.value = ''; // Mesaj kutusunu temizle
            newMessageContent.value = ''; // Yeni mesaj modalı kutusunu temizle
        }
    }

    // Sohbet listesini güncelleme fonksiyonu
    async function updateConversationsList() {
        try {
            const response = await fetch('/api/conversations');
            if (!response.ok) {
                throw new Error('Konuşmalar yüklenirken hata oluştu.');
            }
            const conversations = await response.json();
            conversationItemsContainer.innerHTML = ''; // Mevcut listeyi temizle

            if (conversations.length === 0) {
                conversationItemsContainer.innerHTML = '<p class="p-3 text-muted">Henüz hiç mesajınız yok.</p>';
                return;
            }

            conversations.forEach(conv => {
                const conversationItem = document.createElement('div');
                conversationItem.classList.add('d-flex', 'align-items-center', 'conversation-item');
                conversationItem.dataset.otherUserId = conv.other_user_id;

                // Tarih formatını ayarla
                let lastMessageTime = new Date(conv.last_message_timestamp);
                let timeString = lastMessageTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                let dateString = lastMessageTime.toLocaleDateString();

                conversationItem.innerHTML = `
                    <img src="${conv.other_user_profile_picture_url}" alt="Profil" class="profile-pic-small">
                    <div>
                        <h6 class="mb-0">${conv.other_username}</h6>
                        <small class="text-muted text-truncate" style="max-width: 200px; display: block;">${conv.last_message_content} - ${timeString} ${dateString}</small>
                    </div>
                `;
                conversationItemsContainer.appendChild(conversationItem);
            });
            attachConversationItemListeners(); // Yeni eklenen öğelere olay dinleyicilerini tekrar ata
        } catch (error) {
            console.error('Konuşma listesi güncellenirken hata:');
        }
    }


    // Mesaj gönderme butonu dinleyicisi (mevcut sohbet için)
    sendMessageButton.addEventListener('click', function() {
        if (selectedOtherUserId) {
            sendMessage(selectedOtherUserId, messageInput.value);
        } else {
            alert('Lütfen bir kullanıcı seçin.');
        }
    });

    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && selectedOtherUserId) {
            sendMessage(selectedOtherUserId, messageInput.value);
        }
    });

    // Sayfa yüklendiğinde mevcut konuşmaları göster ve dinleyicileri ata
    attachConversationItemListeners();

    // --- Yeni Mesaj Modalı İşlevselliği ---

    let searchTimeout = null; // Arama gecikmesi için
    userSearchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const searchTerm = userSearchInput.value.trim();
        if (searchTerm.length > 2) { // 2 karakterden fazla girilirse ara
            searchTimeout = setTimeout(() => searchUsers(searchTerm), 300); // 300ms gecikme
        } else {
            searchResults.innerHTML = '';
        }
    });

    async function searchUsers(searchTerm) {
        try {
            const response = await fetch(`/api/search_users?search_term=${encodeURIComponent(searchTerm)}`);
            if (!response.ok) {
                throw new Error('Kullanıcı arama hatası.');
            }
            const users = await response.json();
            displaySearchResults(users);
        } catch (error) {
            console.error('Kullanıcı arama hatası:');
            searchResults.innerHTML = `<div class="p-2 text-danger">Arama sırasında hata oluştu.</div>`;
        }
    }

    function displaySearchResults(users) {
        searchResults.innerHTML = '';
        if (users.length === 0) {
            searchResults.innerHTML = `<div class="p-2 text-muted">Kullanıcı bulunamadı.</div>`;
            return;
        }

        users.forEach(user => {
            // Mevcut kullanıcıyı arama sonuçlarında gösterme
            if (user.id === currentUserId) {
                return; 
            }

            const userItem = document.createElement('div');
            userItem.classList.add('d-flex', 'align-items-center', 'search-result-item');
            userItem.dataset.userId = user.id;
            userItem.dataset.username = user.username;
            userItem.dataset.profilePic = user.profile_picture_url;
            userItem.innerHTML = `
                <img src="${user.profile_picture_url}" alt="Profil" class="profile-pic-small me-2">
                <span>${user.username}</span>
            `;
            userItem.addEventListener('click', function() {
                selectedNewMessageUserId.value = user.id;
                selectedUsernameDisplay.textContent = user.username;
                selectedUserContainer.style.display = 'block';
                searchResults.innerHTML = ''; // Arama sonuçlarını temizle
                userSearchInput.value = ''; // Arama kutusunu temizle
            });
            searchResults.appendChild(userItem);
        });
    }

    sendNewMessageButton.addEventListener('click', async function() {
        const receiverId = selectedNewMessageUserId.value;
        const content = newMessageContent.value;

        if (!receiverId) {
            alert('Lütfen mesaj göndermek için bir kullanıcı seçin.');
            return;
        }

        const success = await sendMessage(receiverId, content);
        if (success) {
            newMessageModal.hide(); // Modalı kapat
            // Yeni başlatılan sohbeti hemen seç ve mesajları yükle
            selectedOtherUserId = receiverId;
            selectedOtherUsername = selectedUsernameDisplay.textContent;
            // Profil resmini de bulup ayarlamak gerekebilir, şimdilik varsayılan veya boş bırakılabilir
            selectedOtherProfilePic = '/static/images/sample_user.png'; // Varsayılan bir resim kullan
            
            updateChatHeader(selectedOtherUsername, selectedOtherProfilePic);
            messageInputArea.classList.remove('d-none');
            loadMessages(selectedOtherUserId);
            
            // Modal kapandıktan sonra temizlik
            userSearchInput.value = '';
            searchResults.innerHTML = '';
            selectedUserContainer.style.display = 'none';
            selectedUsernameDisplay.textContent = '';
            selectedNewMessageUserId.value = '';
            newMessageContent.value = '';
        }
    });

    // Modal gizlendiğinde formu sıfırla
    const newMessageModalElement = document.getElementById('newMessageModal');
    newMessageModalElement.addEventListener('hidden.bs.modal', function () {
        userSearchInput.value = '';
        searchResults.innerHTML = '';
        selectedUserContainer.style.display = 'none';
        selectedUsernameDisplay.textContent = '';
        selectedNewMessageUserId.value = '';
        newMessageContent.value = '';
    });
});