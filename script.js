// Archivo: script.js (Tu versión, actualizada con Memoria de Chat e Historial)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. IDENTIFICACIÓN DE ELEMENTOS DEL HTML (Sin cambios) ---
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');
    const chatHistoryContainer = document.querySelector('.chat-history');

    // --- 2. URL PÚBLICA DE TU API EN RAILWAY (Sin cambios) ---
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // --- 3. NUEVAS VARIABLES PARA LA MEMORIA DEL CHAT ---
    let currentChatId = null;
    let allChats = {}; // Un objeto para guardar todas las conversaciones

    // --- LÓGICA DE INICIO ---
    function initializeApp() {
        loadChatsFromLocalStorage();
        renderChatHistorySidebar();
        const chatIds = Object.keys(allChats);
        if (chatIds.length > 0) {
            currentChatId = chatIds.sort().pop(); // Carga el último chat
        } else {
            startNewChat(); // Si no hay chats, empieza uno nuevo
        }
        renderCurrentChat();
    }
    
    initializeApp();

    // --- 4. MANEJADORES DE EVENTOS (Sin cambios en la lógica principal) ---
    chatInput.addEventListener('input', () => sendButton.disabled = chatInput.value.trim() === '');
    
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

        // Añade la pregunta al historial actual
        addMessageToCurrentChat('user', pregunta);
        renderCurrentChat(); // Muestra la pregunta del usuario inmediatamente

        chatInput.value = '';
        sendButton.disabled = true;

        // Añade y muestra el mensaje "pensando..."
        const typingMessage = { role: 'bot', content: 'COLEPA está pensando...' };
        allChats[currentChatId].messages.push(typingMessage);
        renderCurrentChat();

        try {
            // Prepara el historial para la API (sin el mensaje "pensando")
            const historyForApi = allChats[currentChatId].messages.slice(0, -1)
                                        .map(msg => ({ role: msg.role, content: msg.content }));

            const apiResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ historial: historyForApi }) // Envía el historial
            });

            const data = await apiResponse.json();
            
            // Actualiza el mensaje "pensando..." con la respuesta real de la API
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
            // Renderiza todo por última vez para mostrar la respuesta final
            renderCurrentChat();
            renderChatHistorySidebar(); // Actualiza el título si era la primera pregunta
            saveChatsToLocalStorage();
            sendButton.disabled = false;
        }
    });

    // --- 5. FUNCIONES PARA MANEJAR EL ESTADO Y LA PERSISTENCIA ---

    function loadChatsFromLocalStorage() {
        const chatsGuardados = localStorage.getItem('colepa_chats_v1');
        allChats = chatsGuardados ? JSON.parse(chatsGuardados) : {};
    }

    function saveChatsToLocalStorage() {
        localStorage.setItem('colepa_chats_v1', JSON.stringify(allChats));
    }

    function startNewChat() {
        currentChatId = `chat_${Date.now()}`;
        allChats[currentChatId] = {
            id: currentChatId,
            title: "Nueva Consulta",
            messages: []
        };
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

    // --- 6. FUNCIONES DE RENDERIZADO (MOSTRAR EN PANTALLA) ---

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
