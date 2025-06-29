// Archivo: script.js (Versión Final con Gestión de Memoria Robusta)

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');

    const apiUrl = 'https://colepa-demo-2-production.up.railway.app/consulta';
    
    // La memoria de la conversación actual. La única fuente de verdad.
    let conversationHistory = [];

    // --- LÓGICA DE INICIO ---
    function initializeApp() {
        startNewChat(); // Siempre empieza un chat nuevo al cargar la página
    }
    initializeApp();

    // --- MANEJADORES DE EVENTOS ---
    chatInput.addEventListener('input', () => sendButton.disabled = chatInput.value.trim() === '');
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    newChatButton.addEventListener('click', startNewChat);
    
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;

        // 1. Añade la pregunta del usuario al historial
        conversationHistory.push({ role: 'user', content: pregunta });
        
        // 2. Muestra la conversación actualizada en la pantalla
        renderChat();
        
        chatInput.value = '';
        sendButton.disabled = true;

        try {
            // 3. Envía el historial COMPLETO a la API
            const apiResponse = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ historial: conversationHistory })
            });

            const data = await apiResponse.json();
            
            let botResponse = {};
            if (apiResponse.ok) {
                botResponse = { role: 'bot', content: data.respuesta, fuente: data.fuente };
            } else {
                botResponse = { role: 'bot', content: `Error: ${data.detail}` };
            }

            // 4. Añade la respuesta del bot al historial
            conversationHistory.push(botResponse);

        } catch (error) {
            console.error('Error de conexión:', error);
            conversationHistory.push({ role: 'bot', content: 'Error de Conexión: No se pudo contactar al servidor de Colepa.' });
        } finally {
            // 5. Vuelve a mostrar la conversación completa con la respuesta final
            renderChat();
            sendButton.disabled = false;
        }
    });

    function renderChat() {
        chatMessages.innerHTML = ''; // Borra todo y vuelve a dibujar
        
        if (conversationHistory.length === 0) {
            const welcomeHTML = `<div class="message system"><div class="message-content"><div class="message-header"><div class="bot-avatar"><i class="fas fa-balance-scale"></i></div><div class="bot-name">COLEPA</div></div><div class="message-text"><p>¡Bienvenido a COLEPA! ¿En qué puedo ayudarte?</p></div></div></div>`;
            chatMessages.innerHTML = welcomeHTML;
            return;
        }

        conversationHistory.forEach(msg => {
            const messageWrapper = document.createElement('div');
            messageWrapper.className = `message ${msg.role}`;
            
            const senderName = msg.role === 'user' ? 'Tú' : 'COLEPA';
            const avatarIcon = msg.role === 'user' ? 'fa-user' : 'fa-balance-scale';
            
            // Reemplaza \n con <br> para un formato correcto
            let contentHTML = (msg.content || "").replace(/\n/g, '<br>');
            
            if (msg.fuente) {
                contentHTML += `<div class="fuente">---<br>Fuente: ${msg.fuente.ley}, Art. ${msg.fuente.articulo_numero}</div>`;
            }

            messageWrapper.innerHTML = `<div class="message-content"><div class="message-header"><div class="bot-avatar"><i class="fas ${avatarIcon}"></i></div><div class="sender-name">${senderName}</div></div><div class="message-text">${contentHTML}</div></div>`;
            chatMessages.appendChild(messageWrapper);
        });
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function startNewChat() {
        conversationHistory = [];
        renderChat();
    }
});
