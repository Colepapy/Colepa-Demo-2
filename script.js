// Configuración del Chat
document.getElementById('user-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

function sendMessage() {
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');

    // Mensaje del usuario
    if (userInput.value.trim()) {
        const userDiv = document.createElement('div');
        userDiv.className = 'message user-message';
        userDiv.innerHTML = `
            <div class="message-content">${userInput.value}</div>
            <div class="message-icon">🧑💻</div>
        `;
        chatMessages.appendChild(userDiv);

        // Simular respuesta del bot (conectar luego a tu API de n8n)
        setTimeout(() => {
            const botDiv = document.createElement('div');
            botDiv.className = 'message bot-message';
            botDiv.innerHTML = `
                <div class="message-content">Cargando respuesta...</div>
                <div class="message-icon">⚖️</div>
            `;
            chatMessages.appendChild(botDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }, 1000);

        // Limpiar input
        userInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Conexión a tu API de n8n (EJEMPLO)
async function fetchLawResponse(query) {
    const response = await fetch('TU_ENDPOINT_N8N', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query })
    });
    return await response.json();
}
