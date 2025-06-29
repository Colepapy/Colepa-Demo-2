// Archivo: script.js (Versión Final con Memoria de Chat y localStorage)

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

    // --- 3. VARIABLES PARA MANEJAR EL ESTADO DEL CHAT ---
    let currentChatId = null;
    let allChats = {};

    // --- LÓGICA DE INICIO DE LA APLICACIÓN ---
    loadChatsFromLocalStorage();
    renderChatHistorySidebar();
    startNewChat(); // Inicia un chat nuevo al cargar la página

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

        // Añade el mensaje del usuario al historial actual
        addMessageToCurrentChat('user', pregunta);
        renderCurrentChat(); // Actualiza la pantalla con la pregunta del usuario
        saveChatsToLocalStorage(); // Guarda el cambio
        renderChatHistorySidebar(); // Actualiza el título en la barra lateral

        chatInput.value = '';
        sendButton.disabled = true;

        // Muestra el indicador de "pensando..."
        const typingIndicator = { role: 'bot', content: 'COLEPA está pensando...' };
        allChats[currentChatId].messages.push(typingIndicator);
        renderCurrentChat();

        try {
            // Prepara el historial para enviar a la API (sin el mensaje "pensando")
            const historialParaApi = allChats[currentChatId].messages.slice(0, -1)
                                         .map(({fuente, ...msg}) => msg); // Quita la fuente de los mensajes anteriores

            const respuestaApi = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ historial: historialParaApi }) // Envía el historial completo
            });

            const datos = await respuestaApi.json();
            
            if (respuestaApi.ok) {
                typingIndicator.content = datos.respuesta;
                if (datos.fuente) {
                    typingIndicator.fuente = datos.fuente;
                }
            } else {
                typingIndicator.content = `Error: ${datos.detail}`;
            }

        } catch (error) {
            console.error('Error de conexión:', error);
            typingIndicator.content = 'Error de Conexión: No se pudo contactar al servidor de Colepa.';
        } finally {
            renderCurrentChat(); // Vuelve a renderizar el chat con la respuesta final
            saveChatsToLocalStorage();
        }
    });

    // --- 5. FUNCIONES DE MANEJO DE DATOS ---
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
        const message = { role, content };
        allChats[currentChatId].messages.push(message);
        
        if (allChats[currentChatId].messages.length === 1 && role === 'user') {
            allChats[currentChatId].title = content.substring(0, 35) + (content.length > 35 ? '...' : '');
        }
    }

    // --- 6. FUNCIONES DE RENDERIZADO (MOSTRAR EN PANTALLA) ---
    function renderCurrentChat() {
        chatMessages.innerHTML = '';
        const currentMessages = allChats[currentChatId]?.messages || [];
        
        if (currentMessages.length === 0) {
            chatMessages.innerHTML = `<div class="message system"><div class="message-content"><div class="message-header"><div class="bot-avatar"><i class="fas fa-balance-scale"></i></div><div class="bot-name">COLEPA</div></div><div class="message-text"><p>¡Bienvenido a COLEPA!</p><p>¿En qué puedo ayudarte hoy?</p></div></div></div>`;
        } else {
            currentMessages.forEach(msg => {
                const messageElement = document.createElement('div');
                const classes = msg.role === 'bot' && msg.content === 'COLEPA está pensando...' ? ['bot', 'typing'] : [msg.role];
                messageElement.classList.add('message', ...classes);

                let contentHTML = msg.content.replace(/\n/g, '<br>');
                if (msg.fuente) {
                    contentHTML += `<div class="fuente">---<br>Fuente: ${msg.fuente.ley}, Art. ${msg.fuente.articulo_numero}</div>`;
                }

                messageElement.innerHTML = `
                    <div class="message-content">
                        <div class="message-header">
                            <div class="${msg.role}-avatar"><i class="fas ${msg.role === 'user' ? 'fa-user' : 'fa-balance-scale'}"></i></div>
                            <div class="sender-name">${msg.role === 'user' ? 'Tú' : 'COLEPA'}</div>
                        </div>
                        <div class="message-text">${contentHTML}</div>
                    </div>`;
                chatMessages.appendChild(messageElement);
            });
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function renderChatHistorySidebar() {
        chatHistoryContainer.innerHTML = '';
        Object.values(allChats).sort((a,b) => b.id.localeCompare(a.id)).forEach(chat => {
            const chatLink = document.createElement('a');
            chatLink.href = '#';
            chatLink.classList.add('chat-history-item');
            if (chat.id === currentChatId) chatLink.classList.add('active');
            chatLink.textContent = chat.title;
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
});
