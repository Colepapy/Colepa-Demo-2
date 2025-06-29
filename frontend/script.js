// COLEPA - Script JavaScript Mejorado (Versión Final)
// Manejo robusto de conversaciones y experiencia tipo ChatGPT

document.addEventListener('DOMContentLoaded', function() {
    // === ELEMENTOS DEL DOM ===
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const newChatButton = document.querySelector('.new-chat-btn');
    const chatHistory = document.getElementById('chat-history');

    // === CONFIGURACIÓN ===
    const config = {
        apiUrl: 'https://colepa-demo-2-production.up.railway.app/consulta',
        maxHistoryItems: 20,
        maxMessageLength: 2000,
        autoSaveInterval: 5000, // 5 segundos
        typingSpeed: 50 // velocidad de escritura simulada
    };

    // === ESTADO DE LA APLICACIÓN ===
    let appState = {
        conversationHistory: [],
        chatSessions: [],
        currentSessionId: null,
        isTyping: false,
        isLoading: false
    };

    // === INICIALIZACIÓN ===
    function initializeApp() {
        loadChatSessions();
        startNewChat();
        setupEventListeners();
        setupAutoSave();
        setupInputEnhancements();
    }

    // === GESTIÓN DE SESIONES ===
    function loadChatSessions() {
        // En un entorno real, esto vendría de una base de datos
        // Por ahora, simulamos con datos en memoria
        appState.chatSessions = [];
    }

    function saveChatSession() {
        if (appState.conversationHistory.length === 0) return;
        
        const session = {
            id: appState.currentSessionId,
            title: generateSessionTitle(),
            timestamp: new Date().toISOString(),
            messages: [...appState.conversationHistory]
        };

        // Actualizar o agregar sesión
        const existingIndex = appState.chatSessions.findIndex(s => s.id === session.id);
        if (existingIndex >= 0) {
            appState.chatSessions[existingIndex] = session;
        } else {
            appState.chatSessions.unshift(session);
        }

        // Limitar historial
        if (appState.chatSessions.length > config.maxHistoryItems) {
            appState.chatSessions = appState.chatSessions.slice(0, config.maxHistoryItems);
        }

        renderChatHistory();
    }

    function generateSessionTitle() {
        if (appState.conversationHistory.length === 0) return 'Nueva Consulta';
        
        const firstUserMessage = appState.conversationHistory.find(msg => msg.role === 'user');
        if (!firstUserMessage) return 'Nueva Consulta';
        
        const title = firstUserMessage.content.substring(0, 50);
        return title.length === 50 ? title + '...' : title;
    }

    function startNewChat() {
        appState.conversationHistory = [];
        appState.currentSessionId = generateSessionId();
        appState.isTyping = false;
        appState.isLoading = false;
        
        renderChat();
        renderChatHistory();
        focusInput();
    }

    function loadChatSession(sessionId) {
        const session = appState.chatSessions.find(s => s.id === sessionId);
        if (!session) return;

        appState.conversationHistory = [...session.messages];
        appState.currentSessionId = sessionId;
        renderChat();
        renderChatHistory();
    }

    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // === RENDERIZADO ===
    function renderChat() {
        if (appState.conversationHistory.length === 0) {
            renderWelcomeMessage();
            return;
        }

        chatMessages.innerHTML = '';
        appState.conversationHistory.forEach((msg, index) => {
            renderMessage(msg, index);
        });

        scrollToBottom();
    }

    function renderWelcomeMessage() {
        const welcomeHTML = `
            <div class="message system">
                <div class="message-content">
                    <div class="message-header">
                        <div class="avatar bot-avatar">
                            <i class="fas fa-balance-scale"></i>
                        </div>
                        <div class="sender-name">COLEPA</div>
                    </div>
                    <div class="message-text">
                        <p>¡Bienvenido a COLEPA - Asistente Legal Inteligente de Paraguay!</p>
                        <p>Soy tu asistente especializado en legislación paraguaya. Puedo ayudarte con consultas sobre:</p>
                        <ul style="margin: 1rem 0; padding-left: 1.5rem;">
                            <li>Código Civil</li>
                            <li>Código Penal</li>
                            <li>Código Laboral</li>
                            <li>Código Procesal Civil y Penal</li>
                            <li>Código Aduanero</li>
                            <li>Código Electoral</li>
                            <li>Y mucho más...</li>
                        </ul>
                        <p>¿En qué puedo ayudarte hoy?</p>
                    </div>
                </div>
            </div>
        `;
        chatMessages.innerHTML = welcomeHTML;
    }

    function renderMessage(msg, index) {
        const messageWrapper = document.createElement('div');
        messageWrapper.className = `message ${msg.role}`;
        messageWrapper.setAttribute('data-message-id', index);
        
        const isUser = msg.role === 'user';
        const senderName = isUser ? 'Tú' : 'COLEPA';
        const avatarIcon = isUser ? 'fa-user' : 'fa-balance-scale';
        const avatarClass = isUser ? 'user-avatar' : 'bot-avatar';
        
        let contentHTML = formatMessageContent(msg.content || "");
        
        if (msg.fuente && msg.fuente.ley && msg.fuente.articulo_numero) {
            contentHTML += `
                <div class="fuente">
                    <i class="fas fa-book-open"></i>
                    <strong>Fuente Legal:</strong> ${msg.fuente.ley}, Artículo ${msg.fuente.articulo_numero}
                </div>
            `;
        }

        messageWrapper.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <div class="avatar ${avatarClass}">
                        <i class="fas ${avatarIcon}"></i>
                    </div>
                    <div class="sender-name">${senderName}</div>
                    <div class="message-time">${formatTime(msg.timestamp || new Date())}</div>
                </div>
                <div class="message-text">${contentHTML}</div>
            </div>
        `;
        
        chatMessages.appendChild(messageWrapper);
    }

    function formatMessageContent(content) {
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    function formatTime(date) {
        const now = new Date();
        const msgDate = new Date(date);
        const diffMinutes = Math.floor((now - msgDate) / (1000 * 60));
        
        if (diffMinutes < 1) return 'Ahora';
        if (diffMinutes < 60) return `${diffMinutes}m`;
        if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h`;
        return msgDate.toLocaleDateString();
    }

    function renderChatHistory() {
        chatHistory.innerHTML = '';
        
        appState.chatSessions.forEach(session => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            if (session.id === appState.currentSessionId) {
                historyItem.classList.add('active');
            }
            
            historyItem.innerHTML = `
                <div class="history-title">${session.title}</div>
                <div class="history-time">${formatTime(session.timestamp)}</div>
            `;
            
            historyItem.addEventListener('click', () => loadChatSession(session.id));
            chatHistory.appendChild(historyItem);
        });
    }

    function showLoadingIndicator() {
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'message bot loading';
        loadingMessage.id = 'loading-message';
        
        loadingMessage.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <div class="avatar bot-avatar">
                        <i class="fas fa-balance-scale"></i>
                    </div>
                    <div class="sender-name">COLEPA</div>
                </div>
                <div class="message-text">
                    <div class="loading-indicator">
                        <span>Analizando tu consulta</span>
                        <div class="loading-dots">
                            <div class="loading-dot"></div>
                            <div class="loading-dot"></div>
                            <div class="loading-dot"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(loadingMessage);
        scrollToBottom();
    }

    function hideLoadingIndicator() {
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    // === MANEJO DE EVENTOS ===
    function setupEventListeners() {
        // Envío de formulario
        chatForm.addEventListener('submit', handleFormSubmit);
        
        // Botón nueva consulta
        newChatButton.addEventListener('click', startNewChat);
        
        // Eventos del input
        chatInput.addEventListener('input', handleInputChange);
        chatInput.addEventListener('keydown', handleKeyDown);
        
        // Eventos globales
        window.addEventListener('beforeunload', () => {
            saveChatSession();
        });
    }

    function setupInputEnhancements() {
        // Auto-resize del textarea
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    function setupAutoSave() {
        setInterval(() => {
            if (appState.conversationHistory.length > 0) {
                saveChatSession();
            }
        }, config.autoSaveInterval);
    }

    function handleFormSubmit(event) {
        event.preventDefault();
        if (appState.isLoading) return;
        
        const pregunta = chatInput.value.trim();
        if (!pregunta) return;
        
        if (pregunta.length > config.maxMessageLength) {
            showError('La consulta es demasiado larga. Por favor, hazla más concisa.');
            return;
        }

        sendMessage(pregunta);
    }

    function handleInputChange() {
        const hasContent = chatInput.value.trim().length > 0;
        sendButton.disabled = !hasContent || appState.isLoading;
        
        // Mostrar contador de caracteres si se acerca al límite
        const charCount = chatInput.value.length;
        if (charCount > config.maxMessageLength * 0.8) {
            showCharacterCount(charCount);
        } else {
            hideCharacterCount();
        }
    }

    function handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    }

    // === FUNCIONALIDAD PRINCIPAL ===
    async function sendMessage(pregunta) {
        if (appState.isLoading) return;
        
        appState.isLoading = true;
        
        // Agregar mensaje del usuario
        const userMessage = {
            role: 'user',
            content: pregunta,
            timestamp: new Date()
        };
        
        appState.conversationHistory.push(userMessage);
        renderChat();
        
        // Limpiar input
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendButton.disabled = true;
        
        // Mostrar indicador de carga
        showLoadingIndicator();
        
        try {
            const response = await fetch(config.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    historial: appState.conversationHistory
                })
            });

            hideLoadingIndicator();
            
            if (!response.ok) {
                throw new Error(`Error ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Agregar respuesta del bot
            const botMessage = {
                role: 'bot',
                content: data.respuesta || 'Lo siento, no pude generar una respuesta.',
                fuente: data.fuente,
                timestamp: new Date()
            };
            
            appState.conversationHistory.push(botMessage);
            
            // Simular escritura progresiva (efecto ChatGPT)
            await simulateTyping(botMessage);
            
        } catch (error) {
            hideLoadingIndicator();
            console.error('Error de conexión:', error);
            
            const errorMessage = {
                role: 'bot',
                content: 'Lo siento, ha ocurrido un error de conexión. Por favor, intenta nuevamente.',
                timestamp: new Date()
            };
            
            appState.conversationHistory.push(errorMessage);
            renderChat();
            showError('Error de conexión con el servidor');
            
        } finally {
            appState.isLoading = false;
            sendButton.disabled = false;
            focusInput();
            saveChatSession();
        }
    }

    async function simulateTyping(message) {
        // Agregar mensaje vacío que se irá llenando
        const emptyMessage = {
            ...message,
            content: ''
        };
        
        appState.conversationHistory[appState.conversationHistory.length - 1] = emptyMessage;
        renderChat();

        const fullContent = message.content;
        let currentContent = '';
        
        for (let i = 0; i < fullContent.length; i++) {
            currentContent += fullContent[i];
            
            // Actualizar el mensaje
            appState.conversationHistory[appState.conversationHistory.length - 1] = {
                ...message,
                content: currentContent
            };
            
            renderChat();
            
            // Pausa para simular escritura
            if (fullContent[i] === ' ' || fullContent[i] === '\n') {
                await sleep(config.typingSpeed * 2);
            } else {
                await sleep(config.typingSpeed);
            }
        }
    }

    // === UTILIDADES ===
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function scrollToBottom() {
        requestAnimationFrame(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }

    function focusInput() {
        setTimeout(() => {
            chatInput.focus();
        }, 100);
    }

    function showError(message) {
        // Crear notificación de error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-notification';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(errorDiv);
        
        // Remover después de 5 segundos
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }

    function showCharacterCount(count) {
        let countDisplay = document.getElementById('char-count');
        if (!countDisplay) {
            countDisplay = document.createElement('div');
            countDisplay.id = 'char-count';
            countDisplay.className = 'character-count';
            chatInput.parentNode.appendChild(countDisplay);
        }
        
        const remaining = config.maxMessageLength - count;
        countDisplay.textContent = `${remaining} caracteres restantes`;
        countDisplay.className = `character-count ${remaining < 100 ? 'warning' : ''}`;
    }

    function hideCharacterCount() {
        const countDisplay = document.getElementById('char-count');
        if (countDisplay) {
            countDisplay.remove();
        }
    }

    // === FUNCIONES DE EXPORTACIÓN/IMPORTACIÓN ===
    function exportChat() {
        if (appState.conversationHistory.length === 0) {
            showError('No hay conversación para exportar');
            return;
        }

        const exportData = {
            title: generateSessionTitle(),
            timestamp: new Date().toISOString(),
            messages: appState.conversationHistory
        };

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        
        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `colepa_chat_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
    }

    // === ATAJOS DE TECLADO ===
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + Enter para enviar
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            if (!appState.isLoading && chatInput.value.trim()) {
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
        
        // Ctrl/Cmd + N para nueva consulta
        if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
            event.preventDefault();
            startNewChat();
        }
        
        // Escape para cancelar si está cargando
        if (event.key === 'Escape' && appState.isLoading) {
            // En una implementación real, aquí cancelarías la petición
            showError('Operación cancelada');
        }
    });

    // === RESPONSIVE DESIGN ===
    function handleResize() {
        const sidebar = document.querySelector('.sidebar');
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile && sidebar) {
            sidebar.classList.add('mobile');
        } else if (sidebar) {
            sidebar.classList.remove('mobile', 'open');
        }
    }

    window.addEventListener('resize', handleResize);
    handleResize(); // Ejecutar al cargar

    // === INICIALIZACIÓN FINAL ===
    initializeApp();

    // === EXPOSICIÓN DE FUNCIONES PARA DEBUGGING ===
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.COLEPA_DEBUG = {
            appState,
            exportChat,
            startNewChat,
            config
        };
    }
});

// === ESTILOS ADICIONALES PARA FUNCIONALIDADES NUEVAS ===
const additionalStyles = `
    .error-notification {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #e74c3c, #c0392b);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        animation: slideIn 0.3s ease;
        max-width: 300px;
    }

    .character-count {
        position: absolute;
        bottom: -25px;
        right: 0;
        font-size: 0.75rem;
        color: #7f8c8d;
        transition: color 0.3s ease;
    }

    .character-count.warning {
        color: #e74c3c;
        font-weight: 600;
    }

    .message-time {
        font-size: 0.75rem;
        color: #95a5a6;
        margin-left: auto;
    }

    .history-title {
        font-weight: 500;
        margin-bottom: 0.25rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .history-time {
        font-size: 0.75rem;
        color: #95a5a6;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    .loading {
        opacity: 0.8;
    }

    .sidebar.mobile {
        box-shadow: 2px 0 10px rgba(0,0,0,0.1);
    }

    /* Mejoras para el indicador de carga */
    .loading-indicator {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0;
    }

    .loading-dots {
        display: flex;
        gap: 4px;
    }

    .loading-dot {
        width: 6px;
        height: 6px;
        background: #3498db;
        border-radius: 50%;
        animation: bounce 1.4s infinite ease-in-out both;
    }

    .loading-dot:nth-child(1) { animation-delay: -0.32s; }
    .loading-dot:nth-child(2) { animation-delay: -0.16s; }
    .loading-dot:nth-child(3) { animation-delay: 0s; }

    @keyframes bounce {
        0%, 80%, 100% { 
            transform: scale(0);
            opacity: 0.5;
        }
        40% { 
            transform: scale(1);
            opacity: 1;
        }
    }
`;

// Inyectar estilos adicionales
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);
