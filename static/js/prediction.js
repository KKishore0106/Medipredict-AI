// Initialize Socket.IO connection
const socket = io();

// Store current filters
let currentFilters = {
    disease_type: '',
    start_date: '',
    end_date: ''
};

// Update URL with filters
function updateUrlFilters() {
    const url = new URL(window.location.href);
    Object.entries(currentFilters).forEach(([key, value]) => {
        if (value) url.searchParams.set(key, value);
        else url.searchParams.delete(key);
    });
    window.history.pushState({}, '', url.toString());
}

// Show loading state
function showLoading() {
    document.getElementById('loading-state').classList.remove('hidden');
    document.getElementById('predictions-tbody').innerHTML = '';
    document.getElementById('empty-state').classList.add('hidden');
}

// Hide loading state
function hideLoading() {
    document.getElementById('loading-state').classList.add('hidden');
}

// Show empty state
function showEmptyState() {
    document.getElementById('empty-state').classList.remove('hidden');
}

// Hide empty state
function hideEmptyState() {
    document.getElementById('empty-state').classList.add('hidden');
}

// Apply filters to table
function applyFilters(predictions) {
    const tbody = document.getElementById('predictions-tbody');
    tbody.innerHTML = '';
    
    if (predictions.length === 0) {
        hideLoading();
        showEmptyState();
        return;
    }

    predictions.forEach(prediction => {
        const row = document.createElement('tr');
        row.dataset.predictionId = prediction.id;
        row.innerHTML = `
            <td>${prediction.id}</td>
            <td>
                <span class="date">${new Date(prediction.created_at).toLocaleDateString()}</span>
                <br>
                <span class="time">${new Date(prediction.created_at).toLocaleTimeString()}</span>
            </td>
            <td>${prediction.disease_type}</td>
            <td>
                <span class="confidence">${(prediction.confidence * 100).toFixed(2)}%</span>
            </td>
            <td>
                <span class="result">${prediction.result || 'Pending'}</span>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="action-button view" data-prediction-id="${prediction.id}">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button class="action-button delete" data-prediction-id="${prediction.id}">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
    hideLoading();
    hideEmptyState();
}

// Handle new prediction
socket.on('prediction_created', function(data) {
    console.log('New prediction received:', data);
    
    // Update predictions
    fetch('/api/predictions', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            applyFilters(data.predictions);
        }
    });
});

// Handle prediction deletion
socket.on('prediction_deleted', function(data) {
    console.log('Prediction deleted:', data);
    
    // Remove row from table
    const row = document.querySelector(`tr[data-prediction-id="${data.prediction_id}"]`);
    if (row) {
        row.remove();
        
        // Check if table is empty
        const tbody = document.getElementById('predictions-tbody');
        if (tbody.children.length === 0) {
            showEmptyState();
        }
    }
});

// Handle prediction updates
socket.on('prediction_updated', function(data) {
    console.log('Prediction updated:', data);
    
    // Update row in table
    const row = document.querySelector(`tr[data-prediction-id="${data.prediction_id}"]`);
    if (row) {
        row.querySelector('.confidence').textContent = `${(data.confidence * 100).toFixed(2)}%`;
        row.querySelector('.result').textContent = data.result || 'Pending';
    }
});

// Handle errors
socket.on('error', function(error) {
    console.error('Socket.IO Error:', error);
    alert('An error occurred with the prediction system');
});

// Initial load
window.addEventListener('load', function() {
    showLoading();
    fetch('/api/predictions', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            applyFilters(data.predictions);
        }
    });
});

// View prediction details
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('view')) {
        const predictionId = e.target.dataset.predictionId;
        if (predictionId) {
            window.location.href = `/prediction/${predictionId}`;
        }
    }
});

// Delete prediction
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('delete')) {
        const predictionId = e.target.dataset.predictionId;
        if (predictionId && confirm('Are you sure you want to delete this prediction?')) {
            socket.emit('delete_prediction', { prediction_id: predictionId });
        }
    }
});

// Filter predictions
document.getElementById('filter-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Get filter values
    currentFilters.disease_type = document.getElementById('disease-filter').value;
    currentFilters.start_date = document.getElementById('start-date').value;
    currentFilters.end_date = document.getElementById('end-date').value;
    
    // Update URL
    updateUrlFilters();
    
    // Fetch filtered predictions
    fetch(`/api/predictions?${new URLSearchParams(currentFilters)}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                applyFilters(data.predictions);
            }
        });
});