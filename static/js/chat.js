document.addEventListener('DOMContentLoaded', () => {
    // ========================================================================
    // Configuration & Initialization
    // ========================================================================
    
    /**
     * Chat Client Application
     * A modular approach to the chat interface with Socket.IO
     */
    const ChatApp = {
      // ==============================
      // State Management
      // ==============================
      state: {
        userId: null,
        currentConversationId: null,
        isConversationActive: false,
        messages: [],
        recentChats: [],
        isWaitingForResponse: false
      },
      
      // ==============================
      // DOM Elements
      // ==============================
      elements: {
        messageInput: document.getElementById('message-input'),
        sendButton: document.querySelector('.send-button'),
        chatMessages: document.querySelector('.chat-messages-container'),
        recentChatsContainer: document.querySelector('.recent-chats-list'),
        chatTitle: document.querySelector('.chat-title'),
        thinkingAnimation: document.querySelector('.thinking-animation')
      },
      
      // ==============================
      // Initialize the application
      // ==============================
      init() {
        // Initialize socket connection
        this.socket = io();
        
        // Initialize user ID from hidden input
        this.state.userId = document.getElementById('user-id').value;
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Set up socket event handlers
        this.setupSocketHandlers();
        
        // Initialize socket connection
        this.initializeConnection();
      },
      
      // ==============================
      // Core Message Functions
      // ==============================
      sendMessage() {
        const content = this.elements.messageInput.value.trim();
        if (!content) return;
        
        // If no conversation ID exists, create a new conversation
        if (!this.state.currentConversationId) {
          // Show loading animation immediately
          this.updateMessageSending(true);
          this.updateAIResponseState(true);
          this.socket.emit('new_conversation', { content });
          return;
        }
  
        // Show loading animation
        this.updateMessageSending(true);
        this.updateAIResponseState(true);
  
        // Send message to server with conversation ID
        this.socket.emit('message', {
          content: content,
          conversation_id: this.state.currentConversationId,
          type: 'user',
          timestamp: new Date().toISOString()
        });
        
        // Clear input
        this.elements.messageInput.value = '';
      },
      
      createNewConversation() {
        // Show loading animation immediately
        this.updateMessageSending(true);
        this.updateAIResponseState(true);
        this.socket.emit('new_conversation', {});
      },
      
      // ==============================
      // UI Update Functions
      // ==============================
      
      updateActiveConversationUI(conversationId) {
        const allChatItems = document.querySelectorAll('.chat-item');
        allChatItems.forEach(item => {
          item.classList.remove('bg-blue-50', 'border-blue-300');
        });
        
        // Add active class to current conversation
        const activeChat = document.querySelector(`.chat-item[data-conversation-id="${conversationId}"]`);
        if (activeChat) {
          activeChat.classList.add('bg-blue-50', 'border-blue-300');
        }
      },
      updateMessages() {
        const { chatMessages } = this.elements;
        if (!this.state.messages || !chatMessages) return;
        
        chatMessages.innerHTML = '';
        
        this.state.messages.forEach(message => {
          let templateId = message.type === 'user' ? 'user-message-template' : 'ai-message-template';
          const template = document.getElementById(templateId);
          if (!template) return;
          const messageNode = template.content.cloneNode(true);
          
          // Fill in message text
          const textElem = messageNode.querySelector('.message-text');
          if (textElem) textElem.textContent = message.content;
          
          // Fill in timestamp
          const timestampElem = messageNode.querySelector('.timestamp');
          if (timestampElem) timestampElem.textContent = this.formatRelativeTime(message.timestamp);
          
          chatMessages.appendChild(messageNode);
        });
        
        // Scroll to bottom
        chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
      },
      
      displayRecentChats(conversations) {
        const { recentChatsContainer } = this.elements;
        if (!recentChatsContainer) return;
        
        recentChatsContainer.innerHTML = '';
        
        conversations.forEach(conv => {
          const chatItem = document.createElement('div');
          chatItem.className = 'chat-item';
          chatItem.setAttribute('data-conversation-id', conv.id);
  
          // --- Title logic ---
          let displayTitle = conv.title;
          if (!displayTitle || displayTitle === 'New Chat' || displayTitle.trim().length === 0) {
            // Try to generate a title from first three messages
            if (conv.messages && conv.messages.length > 0) {
              const firstThreeMessages = conv.messages.slice(0, 3);
              const uniqueMessages = new Set();
              
              // Get unique messages from first three messages
              firstThreeMessages.forEach(msg => {
                if (msg.content && msg.content.trim()) {
                  uniqueMessages.add(msg.content.trim());
                }
              });
              
              const messagesArray = Array.from(uniqueMessages);
              
              if (messagesArray.length > 0) {
                // If there are multiple unique messages, use the first one
                if (messagesArray.length > 1) {
                  displayTitle = messagesArray[0].length > 10 ? messagesArray[0].slice(0, 10) + '...' : messagesArray[0];
                } else {
                  // If there's only one message, use it
                  displayTitle = messagesArray[0].length > 10 ? messagesArray[0].slice(0, 10) + '...' : messagesArray[0];
                }
              } else {
                displayTitle = 'Conversation';
              }
            } else {
              displayTitle = 'Conversation';
            }
          }
          const title = document.createElement('span');
          title.className = 'chat-title';
          title.textContent = displayTitle;

          const timestamp = document.createElement('span');
          timestamp.className = 'chat-timestamp';
          timestamp.textContent = this.formatRelativeTime(conv.updated_at);

          const chatContent = document.createElement('div');
          chatContent.className = 'chat-item-content';
          chatContent.appendChild(title);
          chatContent.appendChild(timestamp);
  
          chatItem.appendChild(chatContent);
  
          // --- Delete button ---
          const deleteBtn = document.createElement('button');
          deleteBtn.className = 'delete-button';
          deleteBtn.title = 'Delete Conversation';
          deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
          
          // Use bind to preserve 'this' context
          deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent triggering chat open
            if (confirm('Are you sure you want to delete this conversation?')) {
              this.socket.emit('delete_conversation', { conversation_id: conv.id });
              // Do NOT remove from UI yet; wait for backend confirmation
            }
          });
          chatItem.appendChild(deleteBtn);
  
          // Use bind to preserve 'this' context
          chatItem.addEventListener('click', () => {
            this.state.currentConversationId = conv.id;
            this.state.isConversationActive = true;
            this.state.messages = [];
            this.updateMessages();
            this.socket.emit('get_messages', { conversation_id: conv.id });
            this.updateActiveConversationUI(conv.id);
          });
  
          recentChatsContainer.appendChild(chatItem);
        });
      },
      
      updateChatTitle(title) {
        const { chatTitle } = this.elements;
        if (chatTitle) {
          chatTitle.textContent = title || 'New Conversation';
        }
      },
      
      updateMessageSending(isSending) {
        const { sendButton, messageInput } = this.elements;
        sendButton.disabled = isSending;
      },
      
      updateAIResponseState(isResponding) {
        const { thinkingAnimation } = this.elements;
        if (thinkingAnimation) {
          thinkingAnimation.classList.toggle('hidden', !isResponding);
        }
        
        // Update state
        this.state.isWaitingForResponse = isResponding;
      },
      
      // ==============================
      // Helper Functions
      // ==============================
      showError(message) {
        const errorDiv = document.getElementById('error-message');
        if (!errorDiv) return;
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => {
          errorDiv.style.display = 'none';
        }, 3000);
      },
      
      formatRelativeTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        
        const minutes = Math.floor(diff / 60000);
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        const days = Math.floor(hours / 24);
        if (days < 7) return `${days}d ago`;
        return new Date(timestamp).toLocaleDateString();
      },
      
      // ==============================
      // Event Listeners
      // ==============================
      setupEventListeners() {
        const { messageInput, sendButton } = this.elements;
        const newConversationButton = document.querySelector('.new-conversation-button');
  
        // Bind methods to preserve 'this' context
        const boundSendMessage = this.sendMessage.bind(this);
        const boundCreateNewConversation = this.createNewConversation.bind(this);
        
        // Send button click
        sendButton.addEventListener('click', boundSendMessage);
  
        // Enter key press
        messageInput.addEventListener('keypress', (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            boundSendMessage();
          }
        });
  
        // Update send button state based on input
        messageInput.addEventListener('input', () => {
          if (messageInput.value.trim()) {
            sendButton.classList.remove('opacity-50');
            sendButton.disabled = false;
          } else {
            sendButton.classList.add('opacity-50');
            sendButton.disabled = true;
          }
        });
  
        // New conversation button
        if (newConversationButton) {
          newConversationButton.addEventListener('click', boundCreateNewConversation);
        }
  
        // When user clicks message input
        messageInput.addEventListener('click', () => {
          if (!this.state.currentConversationId) {
            // Do nothing if no conversation is active
            return;
          }
        });
        
        // Expose for global usage (for inline HTML)
        window.startNewConversation = boundCreateNewConversation;
      },
      
      // ==============================
      // Socket Event Handlers
      // ==============================
      setupSocketHandlers() {
        this.socket.on('connect', () => {
          console.log('Connected to server');
          this.initializeConnection();
        });
        
        this.socket.on('error', (data) => {
          if (data?.message) {
            alert('Error: ' + data.message);
          }
        });
        
        this.socket.on('conversation_state', (data) => {
          if (data.currentConversation) {
            this.state.currentConversationId = data.currentConversation.id;
            this.updateChatTitle(data.currentConversation.title || 'New Chat');
            
            // Get messages for the current conversation
            this.socket.emit('get_messages', { conversation_id: this.state.currentConversationId });
          }
        });
        
        this.socket.on('conversations_loaded', (data) => {
          console.log('Conversations loaded:', data);
          if (data?.conversations) {
            this.state.recentChats = data.conversations;
            this.displayRecentChats(this.state.recentChats);
            
            if (data.conversations.length > 0) {
              // Set first conversation as active
              this.state.currentConversationId = data.conversations[0].id;
              this.state.isConversationActive = true;
              
              // Get messages for the active conversation
              this.socket.emit('get_messages', { conversation_id: data.conversations[0].id });
            }
          }
        });
        
        this.socket.on('conversation_created', (data) => {
          if (data.conversation) {
            this.state.currentConversationId = data.conversation.id;
            this.updateChatTitle('New Chat');
            
            // Get messages for the new conversation
            this.socket.emit('get_messages', { conversation_id: this.state.currentConversationId });
            // Fetch updated conversation list to show the new conversation in sidebar
            this.socket.emit('get_conversations');
          }
        });
        
        this.socket.on('messages_loaded', (data) => {
          if (data?.conversation_id === this.state.currentConversationId) {
            this.state.messages = data.messages || [];
            this.updateMessages();
          }
        });
        
        this.socket.on('message_saved', (data) => {
          if (data?.conversation_id === this.state.currentConversationId) {
            const message = {
              message_id: data.message_id,
              type: data.type,
              content: data.content,
              timestamp: data.timestamp,
              conversation_id: data.conversation_id,
              metadata: data.metadata || {}
            };
            
            this.state.messages.push(message);
            this.updateMessages();
          }
        });
        
        this.socket.on('ai_response', (data) => {
          if (data?.conversation_id === this.state.currentConversationId) {
            const response = {
              message_id: data.response_id,
              type: data.type,
              content: data.content,
              timestamp: data.timestamp,
              conversation_id: data.conversation_id,
            };
            
            this.state.messages.push(response);
            this.updateMessages();
            this.updateMessageSending(false);
            this.updateAIResponseState(false);
          }
        });
        
        this.socket.on('conversation_deleted', (data) => {
          if (!data?.conversation_id) return;
          // Remove from state
          this.state.recentChats = this.state.recentChats.filter(conv => conv.id !== data.conversation_id);
          // Remove from UI
          const chatItem = document.querySelector(`[data-conversation-id='${data.conversation_id}']`);
          if (chatItem) chatItem.remove();
          // Optionally, clear messages if the deleted conversation was active
          if (this.state.currentConversationId === data.conversation_id) {
            this.state.currentConversationId = null;
            this.state.isConversationActive = false;
            this.state.messages = [];
            this.updateMessages();
          }
        });
      },
      
      // ==============================
      // Initialization
      // ==============================
      initializeConnection() {
        // Get user ID from hidden input
        const userId = document.getElementById('user-id').value;
        if (!userId) {
          this.showError('User ID not found');
          return;
        }
        
        // Initialize conversation state
        this.socket.emit('get_conversation_state', { userId });
        // Emit get_conversations to load recent chats
        this.socket.emit('get_conversations');
      }
    };
    
    // Initialize the application
    ChatApp.init();
  });