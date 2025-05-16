document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatBtn = document.querySelector('.new-chat-btn');
    const historyList = document.getElementById('history-list');
    const themeToggle = document.getElementById('theme-toggle');
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const currentChatTitle = document.querySelector('.current-chat-title');
    
    // Constants
    const WEBHOOK_URL = 'https://mgcapra314.app.n8n.cloud/webhook/Colepa2025';
    const MAX_HISTORY_ITEMS = 10;
    
    // State
    let chatHistory = loadChatHistory();
    let currentChatId = generateChatId();
    let currentChat = [];
    let isDarkMode = localStorage.getItem('darkMode') === 'true';
    
    // Initialize
    initTheme();
    renderChatHistory();
    adjustTextareaHeight();
    
    // Event Listeners
    userInput.addEventListener('input', function() {
        adjustTextareaHeight();
        sendButton.disabled = userInput.value.trim() === '';
    });
    
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!sendButton.disabled) {
                sendMessage();
            }
        }
    });
    
    sendButton.addEventListener('click', sendMessage);
    newChatBtn.addEventListener('click', startNewChat);
    themeToggle.addEventListener('click', toggleTheme);
    mobileMenuToggle.addEventListener('click', toggleSidebar);
    
    // Functions
    function initTheme() {
        if (isDarkMode) {
            document.body.classList.add('dark-mode');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        } else {
            document.body.classList.remove('dark-mode');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        }
    }
    
    function toggleTheme() {
        isDarkMode = !isDarkMode;
        localStorage.setItem('darkMode', isDarkMode);
        initTheme();
    }
    
    function toggleSidebar() {
        sidebar.classList.toggle('open');
    }
    
    function generateChatId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
    
    function startNewChat() {
        currentChatId = generateChatId();
        currentChat = [];
        currentChatTitle.textContent = 'Nueva Consulta';
        chatMessages.innerHTML = '';
        
        // Add welcome message
        const welcomeMessage = {
            role: 'assistant',
            content: '¡Bienvenido a COLEPA! Estoy aquí para ayudarte con consultas sobre leyes paraguayas. ¿En qué puedo asistirte hoy?'
        };
        addMessageToChat(welcomeMessage);
        
        if (window.innerWidth < 768) {
            sidebar.classList.remove('open');
        }
    }
    
    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;
        
        // Add user message to UI
        const userMessage = {
            role: 'user',
            content: message
        };
        addMessageToChat(userMessage);
        currentChat.push(userMessage);
        
        // Clear input
        userInput.value = '';
        userInput.style.height = 'auto';
        sendButton.disabled = true;
        
        // Add "typing" indicator
        const typingId = addTypingIndicator();
        
        // Update chat title with first few words of first message
        if (currentChat.length === 1) {
            const title = message.slice(0, 30) + (message.length > 30 ? '...' : '');
            currentChatTitle.textContent = title;
            
            // Add to history
            addChatToHistory(currentChatId, title);
        }
        
        // Send message to webhook
        fetchResponse(message, typingId);
    }
    
    function addMessageToChat(message) {
        const messageEl = document.createElement('div');
        messageEl.className = `message ${message.role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (message.role === 'assistant') {
            avatar.innerHTML = '<i class="fas fa-balance-scale"></i>';
        } else {
            avatar.innerHTML = '<i class="fas fa-user"></i>';
        }
        
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        const headerEl = document.createElement('div');
        headerEl.className = 'message-header';
        
        const authorEl = document.createElement('div');
        authorEl.className = 'message-author';
        authorEl.textContent = message.role === 'assistant' ? 'Asistente COLEPA' : 'Tú';
        
        headerEl.appendChild(authorEl);
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.innerHTML = `<p>${message.content}</p>`;
        
        contentEl.appendChild(headerEl);
        contentEl.appendChild(textEl);
        
        messageEl.appendChild(avatar);
        messageEl.appendChild(contentEl);
        
        chatMessages.appendChild(messageEl);
        scrollToBottom();
    }
    
    function addTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const typingEl = document.createElement('div');
        typingEl.className = 'message assistant typing';
        typingEl.id = typingId;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-balance-scale"></i>';
        
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        const headerEl = document.createElement('div');
        headerEl.className = 'message-header';
        
        const authorEl = document.createElement('div');
        authorEl.className = 'message-author';
        authorEl.textContent = 'Asistente COLEPA';
        
        headerEl.appendChild(authorEl);
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.innerHTML = '<p><span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></p>';
        
        contentEl.appendChild(headerEl);
        contentEl.appendChild(textEl);
        
        typingEl.appendChild(avatar);
        typingEl.appendChild(contentEl);
        
        chatMessages.appendChild(typingEl);
        scrollToBottom();
        
        return typingId;
    }
    
    function removeTypingIndicator(typingId) {
        const typingEl = document.getElementById(typingId);
        if (typingEl) {
            typingEl.remove();
        }
    }
    
    async function fetchResponse(message, typingId) {
        try {
            const response = await fetch(WEBHOOK_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    chatId: currentChatId
                })
            });
            
            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }
            
            const data = await response.json();
            removeTypingIndicator(typingId);
            
            // Add assistant message to UI
            const assistantMessage = {
                role: 'assistant',
                content: data.response || '¡Disculpa! No he podido procesar tu consulta. Por favor, intenta nuevamente.'
            };
            
            addMessageToChat(assistantMessage);
            currentChat.push(assistantMessage);
            saveChatHistory();
            
        } catch (error) {
            console.error('Error:', error);
            removeTypingIndicator(typingId);
            
            // Add error message
            const errorMessage = {
                role: 'assistant',
                content: 'Lo siento, ha ocurrido un error al procesar tu consulta. Por favor, intenta nuevamente más tarde.'
            };
            
            addMessageToChat(errorMessage);
        }
    }
    
    function adjustTextareaHeight() {
        userInput.style.height = 'auto';
        userInput.style.height = (userInput.scrollHeight) + 'px';
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function loadChatHistory() {
        const history = localStorage.getItem('chatHistory');
        return history ? JSON.parse(history) : [];
    }
    
    function saveChatHistory() {
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    }
    
    function addChatToHistory(id, title) {
        // Add new chat to beginning of array
        chatHistory.unshift({
            id: id,
            title: title,
            timestamp: Date.now()
        });
        
        // Limit history size
        if (chatHistory.length > MAX_HISTORY_ITEMS) {
            chatHistory = chatHistory.slice(0, MAX_HISTORY_ITEMS);
        }
        
        saveChatHistory();
        renderChatHistory();
    }
    
    function renderChatHistory() {
        historyList.innerHTML = '';
        
        if (chatHistory.length === 0) {
            const emptyEl = document.createElement('li');
            emptyEl.className = 'history-empty';
            emptyEl.textContent = 'No hay consultas previas';
            historyList.appendChild(emptyEl);
            return;
        }
        
        chatHistory.forEach(chat => {
            const chatEl = document.createElement('li');
            chatEl.className = 'history-item';
            chatEl.dataset.id = chat.id;
            
            const chatTitle = document.createElement('div');
            chatTitle.className = 'history-item-title';
            chatTitle.textContent = chat.title;
            
            const chatDate = document.createElement('div');
            chatDate.className = 'history-item-date';
            chatDate.textContent = formatDate(chat.timestamp);
            
            chatEl.appendChild(chatTitle);
            chatEl.appendChild(chatDate);
            
            chatEl.addEventListener('click', () => {
                loadChat(chat.id);
            });
            
            historyList.appendChild(chatEl);
        });
    }
    
    function formatDate(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleDateString('es-PY', { 
            day: '2-digit', 
            month: '2-digit', 
            year: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    function loadChat(chatId) {
        // This is a placeholder - in a real application, you'd fetch the chat from the server
        // For this demo, we'll just show that the chat was selected
        currentChatId = chatId;
        
        // Find the chat in history
        const chat = chatHistory.find(c => c.id === chatId);
        if (chat) {
            currentChatTitle.textContent = chat.title;
        }
        
        // Clear current chat
        chatMessages.innerHTML = '';
        
        // Add a placeholder message
        const placeholderMessage = {
            role: 'assistant',
            content: 'Has cargado una consulta previa. En una versión completa, aquí se mostrarían los mensajes de esta conversación.'
        };
        addMessageToChat(placeholderMessage);
        
        if (window.innerWidth < 768) {
            sidebar.classList.remove('open');
        }
    }
});
