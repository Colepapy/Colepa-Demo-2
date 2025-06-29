// Archivo: script.js (Versión Final con Historial de Chat y Memoria)

document.addEventListener('DOMContentLoaded', function() {

    // --- 1. ELEMENTOS DEL HTML ---
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');
    const chatHistoryContainer = document.querySelector('.chat-history');

    // --- 2. URL PÚBLICA DE TU API EN RAILWAY ---
    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';

    // --- 3. ESTADO DEL CHAT (La Memoria) ---
    let currentChatId = null;
    let allChats = {}; // Un objeto para guardar todas las conversaciones

    // --- LÓGICA DE INICIO ---
    // Carga los chats guardados del navegador al iniciar
    loadChatsFromLocalStorage();
    // Muestra los chats en la barra lateral
    renderChatHistorySidebar();
    // Decide si continuar un chat o empezar uno nuevo
    if (Object.keys(allChats).length > 0) {
        // Carga el chat más reciente
        currentChatId = Object.keys(allChats).sort().pop();
        renderCurrentChat();
    } else {
        // Si no hay chats, empieza uno nuevo
        startNewChat();
    }

    // --- 4. MANEJADORES DE EVENTOS ---
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

        // Añade la pregunta del usuario al historial y actualiza la pantalla
        addMessageToCurrentChat('user', pregunta);
        renderCurrentChat();
        
        // Limpia el input y deshabilita el botón
        chatInput.value = '';
        sendButton.disabled = true;

        // Muestra el indicador "pensando..."
        const typingMessage = { role: 'bot', content: 'COLEPA está pensando...' };
        allChats[currentChatId].messages.push(typingMessage);
        renderCurrentChat();

        try {
            // Prepara el historial para enviar a la API (sin el mensaje "pensando")
            const historyForApi = allChats[currentChatId].messages.slice(0, -1)
                                        .map(msg => ({ role: msg.role, content: msg.content }));

            const apiResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ historial: historyForApi })
            });

            const data = await apiResponse.json();
            
            // Actualiza el mensaje "pensando..." con la respuesta real
            if (apiResponse.ok) {
                typingMessage.content = data.respuesta;
                typingMessage.fuente = data.fuente; // Añade la fuente si existe
            } else {
                typingMessage.content = `Error: ${data.detail}`;
            }

        } catch (error) {
            console.error('Error de conexión:', error);
            typingMessage.content = 'Error de Conexión: No se pudo contactar al servidor de Colepa.';
        } finally {
            // Vuelve a renderizar todo para mostrar la respuesta final y actualizar la barra lateral
            renderCurrentChat();
            renderChatHistorySidebar();
            saveChatsToLocalStorage();
            sendButton.disabled = false;
        }
    });

    // --- 5. FUNCIONES PARA MANEJAR DATOS Y PANTALLA ---

    function loadChatsFromLocalStorage() {
        const chatsGuardados = localStorage.getItem('colepa_chats');
        if (chatsGuardados) {
            allChats = JSON.parse(chatsGuardados);
        }
    }

    function saveChatsToLocalStorage() {
        localStorage.setItem('colepa_chats', JSON.stringify(allChats));
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
        // Si el chat está vacío, actualiza el título con la primera pregunta
        if (allChats[currentChatId].messages.length === 0 && role === 'user') {
            allChats[currentChatId].title = content.substring(0, 35) + (content.length > 35 ? '...' : '');
        }
        allChats[currentChatId].messages.push({ role, content });
    }

    function renderCurrentChat() {
        chatMessages.innerHTML = '';
        const currentMessages = allChats[currentChatId]?.messages || [];
        
        if (currentMessages.length === 0) {
            chatMessages.innerHTML = `<div class="message system"><div class="message-content"><div class="message-header"><div class="bot-avatar"><i class="fas fa-balance-scale"></i></div><div class="bot-name">COLEPA</div></div><div class="message-text"><p>¡Bienvenido a COLEPA!</p><p>¿En qué puedo ayudarte hoy?</p></div></div></div>`;
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
            const chatLink = document.createElement('div'); // Usamos div para más estilo
            chatLink.classList.add('chat-history-item');
            if (chat.id === currentChatId) {
                chatLink.classList.add('active');
            }
            chatLink.innerHTML = `<i class="far fa-comment-dots"></i> ${chat.title}`;
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
            contentHTML += `<div class="fuente">---<br>Fuente: ${msg.fuente.ley}, Art. ${msg.fuente.articulo_numero}</div>`;
        }

        messageWrapper.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <div class="bot-avatar"><i class="fas ${avatarIcon}"></i></div>
                    <div class="sender-name">${senderName}</div>
                </div>
                <div class="message-text">${contentHTML}</div>
            </div>`;
        return messageWrapper;
    }
});
