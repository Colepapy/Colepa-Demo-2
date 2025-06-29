// Archivo: script.js (Versión Final con Memoria Persistente y Conexión a FastAPI)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML (Usando tus IDs) ---
    const chatForm = document.getElementById('chat-form'); // Tu ID era 'chatForm'
    const chatInput = document.getElementById('chat-input'); // Tu ID era 'userInput'
    const sendButton = document.getElementById('send-button'); // Tu ID era 'sendBtn'
    const chatMessages = document.getElementById('chat-messages'); // Tu ID era 'chatMessages'
    const newChatButton = document.querySelector('.new-chat-btn'); // Tu selector
    const chatHistoryContainer = document.querySelector('.chat-history'); // Tu selector

    // --- 2. URL DE LA API EN RAILWAY ---
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // --- 3. ESTADO DEL CHAT (La Memoria) ---
    let currentChatId = null;
    let allChats = {};

    // --- LÓGICA DE INICIO ---
    function initializeApp() {
        loadChatsFromLocalStorage();
        renderChatHistorySidebar();
        const chatIds = Object.keys(allChats);
        if (chatIds.length > 0) {
            currentChatId = chatIds.sort().pop();
            renderCurrentChat();
        } else {
            startNewChat();
        }
    }
    initializeApp();

    // --- 4. MANEJADORES DE EVENTOS ---
    chatInput.addEventListener('input', () => {
        sendButton.disabled = chatInput.value.trim() === '';
    });
    
    chatInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    newChatButton.addEventListener('click', startNewChat);
    
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;

        addMessageToCurrentChat('user', pregunta);
        renderCurrentChat();
        
        chatInput.value = '';
        sendButton.disabled = true;

        const typingMessage = { role: 'bot', content: 'COLEPA está pensando...' };
        allChats[currentChatId].messages.push(typingMessage);
        renderCurrentChat();

        try {
            const historyForApi = allChats[currentChatId].messages.slice(0, -1)
                                        .map(msg => ({role: msg.role, content: msg.content }));

            const apiResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ historial: historyForApi })
            });

            const data = await apiResponse.json();
            
            if (apiResponse.ok) {
                typingMessage.content = data.respuesta;
                typingMessage.fuente = data.fuente;
            } else {
                typingMessage.content = `Error: ${data.detail}`;
            }

        } catch (error) {
            console.error('Error de conexión:', error);
            typingMessage.content = 'Error de Conexión: No se pudo contactar al servidor de Colepa.';
        } finally {
            renderCurrentChat();
            renderChatHistorySidebar();
            saveChatsToLocalStorage();
            sendButton.disabled = false;
        }
    });

    // --- 5. FUNCIONES PARA MANEJAR DATOS Y PANTALLA ---
    function loadChatsFromLocalStorage() {
        const chatsGuardados = localStorage.getItem('colepa_chats_v2'); // Nueva versión para evitar conflictos
        allChats = chatsGuardados ? JSON.parse(chatsGuardados) : {};
    }

    function saveChatsToLocalStorage() {
        localStorage.setItem('colepa_chats_v2', JSON.stringify(allChats));
    }

    function startNewChat() {
        currentChatId = `chat_${Date.now()}`;
        allChats[currentChatId] = { id: currentChatId, title: "Nueva Consulta", messages: [] };
        renderCurrentChat();
        renderChatHistorySidebar();
        saveChatsToLocalStorage();
    }
    
    function addMessageToCurrentChat(role, content) {
        if (allChats[currentChatId].messages.length === 0 && role === 'user') {
            allChats[currentChatId].title = content.substring(0, 35) + (content.length > 35 ? '...' : '');
        }
        allChats[currentChatId].messages.push({ role, content, fuente: null });
    }

    function renderCurrentChat() {
        chatMessages.innerHTML = '';
        const currentMessages = allChats[currentChatId]?.messages || [];
        
        if (currentMessages.length === 0) {
            const welcomeHTML = `<div class="message system"><div class="message-content"><div class="message-header"><div class="bot-avatar"><i class="fas fa-balance-scale"></i></div><div class="bot-name">COLEPA</div></div><div class="message-text"><p>Bienvenido a COLEPA. ¿En qué puedo ayudarte?</p></div></div></div>`;
            chatMessages.innerHTML = welcomeHTML;
        } else {
            currentMessages.forEach(msg => {
                chatMessages.appendChild(createMessageElement(msg));
            });
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function renderChatHistorySidebar() {
        chatHistoryContainer.innerHTML = '';
        Object.values(allChats).sort((a,b) => b.id.localeCompare(a.id)).forEach(chat => {
            const chatLink = document.createElement('div');
            chatLink.classList.add('chat-history-item');
            if (chat.id === currentChatId) chatLink.classList.add('active');
            chatLink.innerHTML = `<i class="far fa-comment-dots"></i> <span>${chat.title}</span>`;
            chatLink.dataset.chatId = chat.id;

            chatLink.addEventListener('click', (e) => {
                e.preventDefault();
                currentChatId = chat.id;
                renderCurrentChat();
                renderChatHistorySidebar();
            });
            chatHistoryContainer.appendChild(chatLink);
        });
    }

    function createMessageElement(msg) {
        const messageWrapper = document.createElement('div');
        let typeClass = msg.role;
        if (msg.content === 'COLEPA está pensando...') typeClass += ' typing';

        messageWrapper.className = `message ${typeClass}`;
        
        const senderName = msg.role === 'user' ? 'Tú' : 'COLEPA';
        const avatarIcon = msg.role === 'user' ? 'fa-user' : 'fa-balance-scale';
        
        let contentHTML = msg.content.replace(/\n/g, '<br>');
        
        if (msg.fuente) {
            contentHTML += `<div class="fuente">---<br>Fuente: ${msg.fuente.ley}, Artículo ${msg.fuente.articulo_numero}</div>`;
        }

        messageWrapper.innerHTML = `<div class="message-content"><div class="message-header"><div class="bot-avatar"><i class="fas ${avatarIcon}"></i></div><div class="sender-name">${senderName}</div></div><div class="message-text">${contentHTML}</div></div>`;
        return messageWrapper;
    }
});
