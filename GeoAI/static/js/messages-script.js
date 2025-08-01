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
                window.location.href = `/profile/${searchTerm}`;
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
                
                document.querySelectorAll('.conversation-item.active').forEach(activeItem => {
                    activeItem.classList.remove('active');
                });
                
                item.classList.add('active');

                selectedOtherUserId = item.dataset.otherUserId;
                const username = item.querySelector('h6').textContent;
                const profilePic = item.querySelector('img').src;
                selectedOtherUsername = username;
                selectedOtherProfilePic = profilePic;

                updateChatHeader(username, profilePic);
                messageInputArea.classList.remove('d-none'); 
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
        chatMessages.innerHTML = '';
        if (messages.length === 0) {
            chatMessages.innerHTML = '<p class="text-center text-muted">Bu sohbet için henüz mesaj yok.</p>';
            return;
        }

       
        messages.forEach(msg => {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message-bubble');
            if (msg.sender_id === currentUserId) {
                messageDiv.classList.add('sent');
                messageDiv.style.marginLeft = 'auto';
            } else {
                messageDiv.classList.add('received');
                messageDiv.style.marginRight = 'auto';
            }
            messageDiv.textContent = msg.content;
            chatMessages.prepend(messageDiv);
        });
        chatMessages.scrollTop = chatMessages.scrollHeight;
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

            
            if (selectedOtherUserId == receiverId) {
                loadMessages(receiverId);
            } else { 
                 updateConversationsList();
            }
            return true;

        } catch (error) {
            alert(`Mesaj gönderilemedi: ${error.message}`);
            return false;
        } finally {
            messageInput.value = '';
            newMessageContent.value = '';
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
            conversationItemsContainer.innerHTML = '';

            if (conversations.length === 0) {
                conversationItemsContainer.innerHTML = '<p class="p-3 text-muted">Henüz hiç mesajınız yok.</p>';
                return;
            }

            conversations.forEach(conv => {
                const conversationItem = document.createElement('div');
                conversationItem.classList.add('d-flex', 'align-items-center', 'conversation-item');
                conversationItem.dataset.otherUserId = conv.other_user_id;

                
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
            attachConversationItemListeners(); 
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


    attachConversationItemListeners();


    let searchTimeout = null; 
    userSearchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const searchTerm = userSearchInput.value.trim();
        if (searchTerm.length > 2) { 
            searchTimeout = setTimeout(() => searchUsers(searchTerm), 300); 
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
                searchResults.innerHTML = '';
                userSearchInput.value = '';
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
            newMessageModal.hide();
            
            selectedOtherUserId = receiverId;
            selectedOtherUsername = selectedUsernameDisplay.textContent;
            
            selectedOtherProfilePic = '/static/images/sample_user.png';
            
            updateChatHeader(selectedOtherUsername, selectedOtherProfilePic);
            messageInputArea.classList.remove('d-none');
            loadMessages(selectedOtherUserId);
            
           
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