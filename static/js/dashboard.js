// Initialize Socket.IO connection
const socket = io();

// Store metrics data
let metrics = {
    prediction_trends: {},
    accuracy: {
        overall: 0,
        by_disease: {},
        total_predictions: 0,
        correct_predictions: 0
    }
};

// Chart instance
let predictionTrendsChart = null;

function updatePredictionTrends(trends) {
    const ctx = document.getElementById('predictionTrendsChart');
    if (!ctx) return;
    
    const ctx2d = ctx.getContext('2d');
    if (!ctx2d) return;

    // Extract data for chart
    const labels = Object.keys(trends).map(date => {
        const [year, month, day] = date.split('-');
        return `${month}/${day}`;
    });
    
    const counts = labels.map(label => trends[label].count);
    const accuracies = labels.map(label => trends[label].accuracy);

    // Create or update chart
    if (predictionTrendsChart) {
        predictionTrendsChart.destroy();
    }

    predictionTrendsChart = new Chart(ctx2d, {
        type: 'line',
        data: {
            labels: labels.length > 0 ? labels : ['01/01', '01/02', '01/03', '01/04', '01/05', '01/06', '01/07'],
            datasets: [
                {
                    label: 'Prediction Count',
                    data: counts.length > 0 ? counts : [0, 0, 0, 0, 0, 0, 0],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                },
                {
                    label: 'Accuracy %',
                    data: accuracies.length > 0 ? accuracies : [0, 0, 0, 0, 0, 0, 0],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 137, 0.1)',
                    fill: false,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#1f2937',
                        boxWidth: 15,
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    position: 'left',
                    beginAtZero: true,
                    max: 10,
                    grid: {
                        color: '#e5e7eb',
                        borderColor: '#d1d5db',
                        drawBorder: true,
                        display: true
                    },
                    ticks: {
                        color: '#1f2937',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        stepSize: 1,
                        callback: function(value) {
                            return Math.round(value);
                        },
                        display: true
                    },
                    title: {
                        display: true,
                        text: 'Prediction Count',
                        color: '#1f2937',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: '#e5e7eb',
                        borderColor: '#d1d5db',
                        drawOnChartArea: false,
                        drawBorder: true,
                        display: true
                    },
                    ticks: {
                        color: '#1f2937',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        stepSize: 10,
                        callback: function(value) {
                            return value + '%';
                        },
                        display: true
                    },
                    title: {
                        display: true,
                        text: 'Accuracy %',
                        color: '#1f2937',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        color: '#e5e7eb',
                        borderColor: '#d1d5db',
                        drawBorder: true,
                        display: true
                    },
                    ticks: {
                        color: '#1f2937',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        display: true
                    },
                    title: {
                        display: true,
                        text: 'Date',
                        color: '#1f2937',
                        font: {
                            size: 14,
                            weight: 'bold'
                        }
                    }
                }
            }
        }
    });
}

// Handle Socket.IO events
socket.on('dashboard_metrics_updated', (data) => {
    metrics.prediction_trends = data.prediction_trends || {};
    metrics.accuracy = data.accuracy || {};
    updatePredictionTrends(metrics.prediction_trends);
});

// Request initial metrics when connected
socket.on('connect', () => {
    console.log('Connected to server');
    socket.emit('get_metrics');
});

// Initialize chart with initial data
document.addEventListener('DOMContentLoaded', () => {
    // Initialize chart with empty data
    updatePredictionTrends(metrics.prediction_trends);
    
    try {
        chatbot.init();
        chatbot.bindEvents();
    } catch (error) {
        console.error('Error initializing components:', error);
    }
});

// Chatbot functionality
const chatbot = {
    messages: [],
    init() {
        this.bindEvents();
    },
    bindEvents() {
        // Chat events
        document.getElementById('send-message').addEventListener('click', () => {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            if (message) {
                this.sendMessage(message);
                input.value = '';
            }
        });

        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('send-message').click();
            }
        });

        document.getElementById('close-chat').addEventListener('click', () => this.closeChat());
    },
    sendMessage(message) {
        // Send message to server
        socket.emit('message', { message, type: 'user' });
        
        // Add to local messages
        this.addMessage({
            content: message,
            type: 'user',
            timestamp: new Date()
        });
    },
    addMessage(message) {
        this.messages.push(message);
        this.renderMessages();
        this.scrollToBottom();
    },
    renderMessages() {
        const chatContainer = document.getElementById('chat-messages');
        chatContainer.innerHTML = this.messages.map(msg => `
            <div class="message ${msg.type === 'user' ? 'user' : 'bot'}">
                <div class="message-content">
                    ${msg.content}
                </div>
                <div class="message-timestamp">
                    ${new Date(msg.timestamp).toLocaleTimeString()}
                </div>
            </div>
        `).join('');
    },
    scrollToBottom() {
        const chatContainer = document.getElementById('chat-messages');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    },
    closeChat() {
        document.getElementById('chat-container').style.display = 'none';
    },
    loadMessages() {
        socket.emit('get_conversations');
    },
    saveMessages() {
        socket.emit('save_messages', this.messages);
    }
};

socket.on('error', (data) => {
    console.error('Error:', data.message);
});
