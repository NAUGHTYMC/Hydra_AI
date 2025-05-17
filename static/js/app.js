// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatContainer = document.getElementById('chatContainer');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const imageInput = document.getElementById('imageInput');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    const uploadPreview = document.getElementById('uploadPreview');
    const previewImage = document.getElementById('previewImage');
    const removeImageBtn = document.getElementById('removeImage');
    const typingIndicator = document.getElementById('typingIndicator');
    const errorModal = document.getElementById('errorModal');
    const systemTime = document.getElementById('systemTime');
    
    // Templates
    const userMessageTemplate = document.getElementById('userMessageTemplate');
    const botMessageTemplate = document.getElementById('botMessageTemplate');

    // State Management
    let isProcessing = false;
    let currentImage = null;

    // Event Listeners
    userInput.addEventListener('input', updateSendButtonState);
    imageInput.addEventListener('change', handleImageUpload);
    removeImageBtn.addEventListener('click', clearImagePreview);
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !isProcessing) sendMessage();
    });
    clearHistoryBtn.addEventListener('click', clearConversationHistory);
    document.querySelector('.close-button').addEventListener('click', closeErrorModal);
    errorModal.addEventListener('click', (e) => {
        if (e.target === errorModal) closeErrorModal();
    });

    // Initialize real-time clock
    setInterval(updateSystemTime, 1000);
    updateSystemTime();

    // Initialize connection monitoring
    setInterval(checkConnectionStatus, 5000);
    checkConnectionStatus();

    function updateSystemTime() {
        const now = new Date();
        systemTime.textContent = `System Time: ${now.toLocaleTimeString()}`;
    }

    async function checkConnectionStatus() {
        try {
            const response = await fetch('/health');
            const statusElement = document.getElementById('connectionStatus');
            if (response.ok) {
                statusElement.classList.remove('disconnected');
                statusElement.classList.add('connected');
                statusElement.textContent = 'Connected';
            } else {
                throw new Error('Connection failed');
            }
        } catch (error) {
            document.getElementById('connectionStatus').classList.add('disconnected');
            document.getElementById('connectionStatus').textContent = 'Disconnected';
        }
    }

    function updateSendButtonState() {
        sendButton.disabled = !(userInput.value.trim() || currentImage);
    }

    function handleImageUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                uploadPreview.style.display = 'block';
                currentImage = file;
                updateSendButtonState();
            };
            reader.readAsDataURL(file);
        }
    }

    function clearImagePreview() {
        previewImage.src = '';
        uploadPreview.style.display = 'none';
        imageInput.value = '';
        currentImage = null;
        updateSendButtonState();
    }

    async function sendMessage() {
        if (isProcessing) return;
        
        const message = userInput.value.trim();
        if (!message && !currentImage) return;

        try {
            isProcessing = true;
            typingIndicator.classList.remove('hidden');
            addMessageToChat(message, currentImage, true);

            const formData = new FormData();
            if (message) formData.append('message', message);
            if (currentImage) formData.append('image', currentImage);

            const response = await fetch('/chat', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (data.error) throw new Error(data.error);

            addMessageToChat(data.response, null, false);
            clearImagePreview();
            userInput.value = '';
        } catch (error) {
            showErrorModal(`Error: ${error.message}`);
        } finally {
            isProcessing = false;
            typingIndicator.classList.add('hidden');
            updateSendButtonState();
            chatContainer.scrollTop = chatContainer.scrollTop + 1000;
        }
    }

    function addMessageToChat(content, image, isUser) {
        const template = isUser ? userMessageTemplate : botMessageTemplate;
        const clone = template.content.cloneNode(true);
        const messageElement = clone.querySelector('.message');
        const timeElement = clone.querySelector('.message-time');

        if (isUser) {
            const textElement = clone.querySelector('.message-text');
            const imageElement = clone.querySelector('.message-image');
            
            if (content) textElement.textContent = content;
            if (image) {
                imageElement.classList.remove('hidden');
                imageElement.querySelector('img').src = URL.createObjectURL(image);
            }
        } else {
            const textElement = clone.querySelector('.message-text');
            textElement.innerHTML = formatBotResponse(content);
        }

        timeElement.textContent = new Date().toLocaleTimeString();
        chatContainer.appendChild(clone);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function formatBotResponse(text) {
        // Convert markdown-like formatting to HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/(\d+\.\s+.*)/g, '<p>$1</p>')
            .replace(/- (.*)/g, '<li>$1</li>')
            .replace(/(Confidence: \d+%)/g, '<span class="confidence">$1</span>')
            .replace(/\n/g, '<br>');
    }

    async function clearConversationHistory() {
        try {
            const response = await fetch('/clear_history', {
                method: 'POST'
            });
            
            if (!response.ok) throw new Error('Failed to clear history');
            
            chatContainer.innerHTML = document.querySelector('.welcome-message').outerHTML;
        } catch (error) {
            showErrorModal(`Error clearing history: ${error.message}`);
        }
    }

    function showErrorModal(message) {
        document.getElementById('errorMessage').textContent = message;
        errorModal.style.display = 'block';
    }

    function closeErrorModal() {
        errorModal.style.display = 'none';
    }

    // Initial welcome message
    chatContainer.innerHTML = document.querySelector('.welcome-message').outerHTML;
});