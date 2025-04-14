/**
 * SignAI - Main JavaScript File
 * Handles UI interactions, API calls, and webcam functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in
    checkAuthentication();

    // Setup navigation
    setupNavigation();

    // Setup logout functionality
    document.getElementById('logout-button')?.addEventListener('click', logout);

    // Setup webcam functionality if on prediction page
    if (document.getElementById('webcam')) {
        setupWebcam();
    }

    // Setup history functionality if on history page
    if (document.getElementById('history-table')) {
        setupHistoryTable();
    }

    // Setup admin functionality if admin
    if (document.getElementById('admin-section')) {
        setupAdminDashboard();
    }
});

/**
 * Check if user is authenticated, redirect to login if not
 */
function checkAuthentication() {
    // Check if we're on login or register page
    const currentPage = window.location.pathname;
    if (currentPage === '/login.html' || currentPage === '/register.html' || currentPage === '/') {
        return;
    }

    // Check for token
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    // Load user info
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user) {
        // Display user name
        const userNameElements = document.querySelectorAll('#user-name, #welcome-name');
        userNameElements.forEach(el => {
            if (el) el.textContent = user.name || 'User';
        });

        // Show admin links if admin
        if (user.role === 'admin') {
            document.querySelectorAll('.admin-only').forEach(el => {
                el.classList.remove('d-none');
            });
        }
    }

    // Load dashboard data if on dashboard
    if (currentPage === '/dashboard.html' && document.getElementById('dashboard-section')) {
        loadDashboard();
    }
}

/**
 * Setup navigation between different sections
 */
function setupNavigation() {
    const sections = {
        'dashboard-link': 'dashboard-section',
        'predict-link': 'predict-section',
        'history-link': 'history-section',
        'admin-link': 'admin-section',
        'view-all-history': 'history-section'
    };

    for (const [linkId, sectionId] of Object.entries(sections)) {
        const link = document.getElementById(linkId);
        if (link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                showSection(sectionId);
                
                // Load specific data if needed
                if (sectionId === 'history-section') {
                    loadHistory();
                } else if (sectionId === 'admin-section') {
                    loadAdminDashboard();
                }
            });
        }
    }
}

/**
 * Show a specific section and hide others
 */
function showSection(sectionId) {
    const sections = ['dashboard-section', 'predict-section', 'history-section', 'admin-section'];
    
    sections.forEach(id => {
        const section = document.getElementById(id);
        if (section) {
            if (id === sectionId) {
                section.classList.remove('d-none');
            } else {
                section.classList.add('d-none');
            }
        }
    });
    
    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + sectionId || 
            (sectionId === 'dashboard-section' && link.getAttribute('href') === '/dashboard.html')) {
            link.classList.add('active');
        }
    });
}

/**
 * Load dashboard data
 */
function loadDashboard() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Fetch user history
    fetch('/api/user/history?per_page=5', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                refreshToken().then(() => loadDashboard());
                return;
            }
            throw new Error('Failed to fetch history');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) throw new Error(data.error);
        
        // Update stats
        document.getElementById('total-predictions').textContent = data.pagination.total || 0;
        
        // Update recent activity table
        updateRecentActivity(data.predictions);
        
        // Update chart
        updatePredictionChart(data.predictions);
        
        // Update last activity
        if (data.predictions && data.predictions.length > 0) {
            const lastPrediction = new Date(data.predictions[0].timestamp);
            document.getElementById('last-activity').textContent = lastPrediction.toLocaleDateString() + ' ' + lastPrediction.toLocaleTimeString();
        }
        
        // Update common sign
        if (data.predictions && data.predictions.length > 0) {
            // Count occurrences of each label
            const labelCount = {};
            data.predictions.forEach(p => {
                labelCount[p.label] = (labelCount[p.label] || 0) + 1;
            });
            
            // Find most common
            let commonLabel = 'None';
            let maxCount = 0;
            
            for (const [label, count] of Object.entries(labelCount)) {
                if (count > maxCount) {
                    maxCount = count;
                    commonLabel = label;
                }
            }
            
            document.getElementById('common-sign').textContent = commonLabel;
        }
    })
    .catch(error => {
        console.error('Error loading dashboard:', error);
    });
}

/**
 * Update recent activity table
 */
function updateRecentActivity(predictions) {
    const tableBody = document.getElementById('recent-activity-table');
    if (!tableBody) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    if (!predictions || predictions.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="3" class="text-center">No recent activity</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Add rows
    predictions.forEach(prediction => {
        const row = document.createElement('tr');
        
        const date = new Date(prediction.timestamp);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        
        row.innerHTML = `
            <td>${prediction.label}</td>
            <td>${prediction.confidence}%</td>
            <td>${dateStr}</td>
        `;
        
        tableBody.appendChild(row);
    });
}

/**
 * Update prediction chart
 */
function updatePredictionChart(predictions) {
    const chartCanvas = document.getElementById('prediction-chart');
    if (!chartCanvas) return;
    
    // Extract labels and counts
    const labels = [];
    const counts = [];
    
    if (predictions && predictions.length > 0) {
        // Count occurrences of each label
        const labelCount = {};
        predictions.forEach(p => {
            labelCount[p.label] = (labelCount[p.label] || 0) + 1;
        });
        
        // Convert to arrays
        for (const [label, count] of Object.entries(labelCount)) {
            labels.push(label);
            counts.push(count);
        }
    }
    
    // Limit to top 5
    if (labels.length > 5) {
        const pairs = labels.map((label, i) => ({label, count: counts[i]}));
        pairs.sort((a, b) => b.count - a.count);
        
        labels.length = 0;
        counts.length = 0;
        
        pairs.slice(0, 5).forEach(pair => {
            labels.push(pair.label);
            counts.push(pair.count);
        });
    }
    
    // Create chart
    new Chart(chartCanvas, {
        type: 'doughnut',
        data: {
            labels: labels.length > 0 ? labels : ['No Data'],
            datasets: [{
                data: counts.length > 0 ? counts : [1],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(255, 99, 132, 0.7)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        }
    });
}

/**
 * Setup webcam functionality
 */
function setupWebcam() {
    let videoElement = document.getElementById('webcam');
    let canvasElement = document.createElement('canvas');
    let streaming = false;
    let continuousMode = false;
    let mediaStream = null;
    
    // Setup webcam control buttons
    const startCameraBtn = document.getElementById('start-camera');
    const stopCameraBtn = document.getElementById('stop-camera');
    const captureBtn = document.getElementById('capture');
    const continuousModeBtn = document.getElementById('continuous-mode');
    const savePredictionBtn = document.getElementById('save-prediction');
    
    startCameraBtn.addEventListener('click', startCamera);
    stopCameraBtn.addEventListener('click', stopCamera);
    captureBtn.addEventListener('click', captureFrame);
    continuousModeBtn.addEventListener('click', toggleContinuousMode);
    savePredictionBtn.addEventListener('click', savePrediction);
    
    // Current prediction result
    let currentPrediction = null;
    
    function startCamera() {
        if (streaming) return;
        
        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            },
            audio: false
        };
        
        navigator.mediaDevices.getUserMedia(constraints)
            .then(function(stream) {
                mediaStream = stream;
                videoElement.srcObject = stream;
                videoElement.play();
                streaming = true;
                
                // Update UI
                document.getElementById('no-camera').classList.add('d-none');
                startCameraBtn.disabled = true;
                stopCameraBtn.disabled = false;
                captureBtn.disabled = false;
                
                // Start continuous mode if selected
                if (continuousMode) {
                    startContinuousCapture();
                }
            })
            .catch(function(err) {
                console.error("Error accessing camera: ", err);
                document.getElementById('no-camera').classList.remove('d-none');
            });
    }
    
    function stopCamera() {
        if (!streaming) return;
        
        // Stop all video tracks
        if (mediaStream) {
            mediaStream.getVideoTracks().forEach(track => track.stop());
        }
        
        // Reset video element
        videoElement.srcObject = null;
        streaming = false;
        
        // Update UI
        startCameraBtn.disabled = false;
        stopCameraBtn.disabled = true;
        captureBtn.disabled = true;
    }
    
    function captureFrame() {
        if (!streaming) return;
        
        // Set canvas dimensions
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        
        // Draw video frame to canvas
        const context = canvasElement.getContext('2d');
        context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
        
        // Convert to base64
        const imageData = canvasElement.toDataURL('image/jpeg');
        
        // Send to API
        predictFromImage(imageData);
    }
    
    function predictFromImage(imageData) {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        
        // Show loading
        document.getElementById('loading-prediction').classList.remove('d-none');
        document.getElementById('prediction-result').classList.add('d-none');
        document.getElementById('no-prediction').classList.add('d-none');
        
        // Make API request
        fetch('/api/prediction/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                image: imageData,
                save_result: false // Don't save automatically, let user choose
            })
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) {
                    refreshToken().then(() => predictFromImage(imageData));
                    return;
                }
                throw new Error('Prediction failed');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading
            document.getElementById('loading-prediction').classList.add('d-none');
            
            if (data.error) {
                console.error('Prediction error:', data.error);
                return;
            }
            
            // Store current prediction
            currentPrediction = data;
            
            // Show result
            document.getElementById('prediction-result').classList.remove('d-none');
            document.getElementById('prediction-label').textContent = data.label;
            
            // Update confidence bar
            const confidenceEl = document.getElementById('prediction-confidence');
            confidenceEl.style.width = `${data.confidence}%`;
            confidenceEl.textContent = `${data.confidence}%`;
            
            // Enable save button
            savePredictionBtn.disabled = false;
            
            // Set confidence bar color based on confidence level
            if (data.confidence >= 80) {
                confidenceEl.className = 'progress-bar progress-bar-striped bg-success';
            } else if (data.confidence >= 50) {
                confidenceEl.className = 'progress-bar progress-bar-striped bg-warning';
            } else {
                confidenceEl.className = 'progress-bar progress-bar-striped bg-danger';
            }
        })
        .catch(error => {
            console.error('Error making prediction:', error);
            document.getElementById('loading-prediction').classList.add('d-none');
            document.getElementById('no-prediction').classList.remove('d-none');
        });
    }
    
    function toggleContinuousMode() {
        continuousMode = !continuousMode;
        
        if (continuousMode) {
            continuousModeBtn.classList.remove('btn-outline-primary');
            continuousModeBtn.classList.add('btn-primary');
            if (streaming) {
                startContinuousCapture();
            }
        } else {
            continuousModeBtn.classList.remove('btn-primary');
            continuousModeBtn.classList.add('btn-outline-primary');
        }
    }
    
    let captureInterval = null;
    function startContinuousCapture() {
        if (!continuousMode || !streaming) return;
        
        // Capture a frame every 2 seconds
        captureInterval = setInterval(() => {
            captureFrame();
        }, 2000);
    }
    
    function stopContinuousCapture() {
        if (captureInterval) {
            clearInterval(captureInterval);
            captureInterval = null;
        }
    }
    
    function savePrediction() {
        if (!currentPrediction) return;
        
        const token = localStorage.getItem('access_token');
        if (!token) return;
        
        // Make API request to save prediction
        fetch('/api/prediction/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                landmarks: currentPrediction.landmarks || [],
                label: currentPrediction.label,
                confidence: currentPrediction.confidence,
                save_result: true
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to save prediction');
            }
            return response.json();
        })
        .then(data => {
            // Show success message
            alert('Prediction saved successfully!');
            savePredictionBtn.disabled = true;
            
            // Reset current prediction
            currentPrediction = null;
        })
        .catch(error => {
            console.error('Error saving prediction:', error);
            alert('Failed to save prediction');
        });
    }
}

/**
 * Setup history table functionality
 */
function setupHistoryTable() {
    loadHistory();
    
    // Setup search
    const searchInput = document.getElementById('history-search');
    const searchButton = document.getElementById('search-button');
    
    if (searchButton) {
        searchButton.addEventListener('click', () => {
            loadHistory(1, searchInput.value);
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                loadHistory(1, searchInput.value);
            }
        });
    }
}

/**
 * Load prediction history
 */
function loadHistory(page = 1, search = '') {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    const historyTable = document.getElementById('history-table');
    if (!historyTable) return;
    
    // Show loading state
    historyTable.innerHTML = '<tr><td colspan="4" class="text-center">Loading history...</td></tr>';
    
    // Fetch history
    let url = `/api/user/history?page=${page}&per_page=10`;
    if (search) {
        url += `&search=${encodeURIComponent(search)}`;
    }
    
    fetch(url, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                refreshToken().then(() => loadHistory(page, search));
                return;
            }
            throw new Error('Failed to fetch history');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) throw new Error(data.error);
        
        // Update table
        updateHistoryTable(data.predictions);
        
        // Update pagination
        updatePagination(data.pagination, page, search);
    })
    .catch(error => {
        console.error('Error loading history:', error);
        historyTable.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Error: ${error.message}</td></tr>`;
    });
}

/**
 * Update history table with prediction data
 */
function updateHistoryTable(predictions) {
    const tableBody = document.getElementById('history-table');
    if (!tableBody) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    if (!predictions || predictions.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="4" class="text-center">No predictions found</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Add rows
    predictions.forEach(prediction => {
        const row = document.createElement('tr');
        
        const date = new Date(prediction.timestamp);
        const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        
        row.innerHTML = `
            <td>${prediction.label}</td>
            <td>${prediction.confidence}%</td>
            <td>${dateStr}</td>
            <td>
                <button class="btn btn-sm btn-danger delete-prediction" data-id="${prediction._id}">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Setup delete buttons
    document.querySelectorAll('.delete-prediction').forEach(button => {
        button.addEventListener('click', function() {
            const predictionId = this.getAttribute('data-id');
            showDeleteConfirmation('prediction', predictionId);
        });
    });
}

/**
 * Update pagination controls
 */
function updatePagination(pagination, currentPage, search = '') {
    const paginationEl = document.getElementById('history-pagination');
    if (!paginationEl) return;
    
    // Clear pagination
    paginationEl.innerHTML = '';
    
    if (!pagination || pagination.total === 0) return;
    
    // Previous button
    const prevLi = document.createElement('li');
    prevLi.className = `page-item ${currentPage <= 1 ? 'disabled' : ''}`;
    
    const prevLink = document.createElement('a');
    prevLink.className = 'page-link';
    prevLink.href = '#';
    prevLink.textContent = 'Previous';
    
    if (currentPage > 1) {
        prevLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadHistory(currentPage - 1, search);
        });
    }
    
    prevLi.appendChild(prevLink);
    paginationEl.appendChild(prevLi);
    
    // Page buttons
    const totalPages = pagination.pages;
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const pageLi = document.createElement('li');
        pageLi.className = `page-item ${i === currentPage ? 'active' : ''}`;
        
        const pageLink = document.createElement('a');
        pageLink.className = 'page-link';
        pageLink.href = '#';
        pageLink.textContent = i;
        
        if (i !== currentPage) {
            pageLink.addEventListener('click', function(e) {
                e.preventDefault();
                loadHistory(i, search);
            });
        }
        
        pageLi.appendChild(pageLink);
        paginationEl.appendChild(pageLi);
    }
    
    // Next button
    const nextLi = document.createElement('li');
    nextLi.className = `page-item ${currentPage >= totalPages ? 'disabled' : ''}`;
    
    const nextLink = document.createElement('a');
    nextLink.className = 'page-link';
    nextLink.href = '#';
    nextLink.textContent = 'Next';
    
    if (currentPage < totalPages) {
        nextLink.addEventListener('click', function(e) {
            e.preventDefault();
            loadHistory(currentPage + 1, search);
        });
    }
    
    nextLi.appendChild(nextLink);
    paginationEl.appendChild(nextLi);
}

/**
 * Setup admin dashboard functionality
 */
function setupAdminDashboard() {
    // Setup export buttons
    document.getElementById('export-users-btn')?.addEventListener('click', exportUsers);
    document.getElementById('export-predictions-btn')?.addEventListener('click', exportPredictions);
    
    // Setup user modal form
    setupUserModal();
}

/**
 * Load admin dashboard data
 */
function loadAdminDashboard() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.role !== 'admin') {
        alert('Admin access required');
        return;
    }
    
    // Fetch admin dashboard data
    fetch('/api/admin/dashboard', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                refreshToken().then(() => loadAdminDashboard());
                return;
            }
            throw new Error('Failed to fetch admin dashboard');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) throw new Error(data.error);
        
        // Update statistics
        document.getElementById('total-users').textContent = data.statistics.total_users;
        document.getElementById('admin-total-predictions').textContent = data.statistics.total_predictions;
        
        // Load users
        loadUsers();
        
        // Update charts
        updateAdminCharts(data);
    })
    .catch(error => {
        console.error('Error loading admin dashboard:', error);
    });
}

/**
 * Update admin dashboard charts
 */
function updateAdminCharts(data) {
    // Predictions over time chart
    const timeChartCanvas = document.getElementById('admin-predictions-chart');
    if (timeChartCanvas && data.predictions_by_day) {
        const labels = data.predictions_by_day.map(item => item.date);
        const counts = data.predictions_by_day.map(item => item.count);
        
        new Chart(timeChartCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Predictions',
                    data: counts,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    // Popular signs chart
    const signsChartCanvas = document.getElementById('admin-signs-chart');
    if (signsChartCanvas && data.common_predictions) {
        const labels = data.common_predictions.map(item => item._id);
        const counts = data.common_predictions.map(item => item.count);
        
        new Chart(signsChartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(255, 159, 64, 0.7)',
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(255, 205, 86, 0.7)',
                        'rgba(201, 203, 207, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(153, 102, 255, 0.7)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
}

/**
 * Load users for admin dashboard
 */
function loadUsers(page = 1) {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    const usersTable = document.getElementById('users-table');
    if (!usersTable) return;
    
    // Show loading state
    usersTable.innerHTML = '<tr><td colspan="5" class="text-center">Loading users...</td></tr>';
    
    // Fetch users
    fetch(`/api/admin/users?page=${page}&per_page=10`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 401) {
                refreshToken().then(() => loadUsers(page));
                return;
            }
            throw new Error('Failed to fetch users');
        }
        return response.json();
    })
    .then(data => {
        if (data.error) throw new Error(data.error);
        
        // Update table
        updateUsersTable(data.users);
    })
    .catch(error => {
        console.error('Error loading users:', error);
        usersTable.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error: ${error.message}</td></tr>`;
    });
}

/**
 * Update users table with user data
 */
function updateUsersTable(users) {
    const tableBody = document.getElementById('users-table');
    if (!tableBody) return;
    
    // Clear table
    tableBody.innerHTML = '';
    
    if (!users || users.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" class="text-center">No users found</td>';
        tableBody.appendChild(row);
        return;
    }
    
    // Add rows
    users.forEach(user => {
        const row = document.createElement('tr');
        
        const date = new Date(user.created_at);
        const dateStr = date.toLocaleDateString();
        
        const roleBadge = user.role === 'admin' ? 
            '<span class="badge bg-primary">Admin</span>' : 
            '<span class="badge bg-secondary">User</span>';
        
        row.innerHTML = `
            <td>${user.name}</td>
            <td>${user.email}</td>
            <td>${roleBadge}</td>
            <td>${dateStr}</td>
            <td>
                <button class="btn btn-sm btn-primary edit-user" data-id="${user._id}">
                    <i class="fas fa-edit"></i>
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
    
    // Setup edit buttons
    document.querySelectorAll('.edit-user').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            editUser(userId);
        });
    });
}

/**
 * Setup user modal form
 */
function setupUserModal() {
    const saveUserBtn = document.getElementById('save-user-btn');
    const deleteUserBtn = document.getElementById('delete-user-btn');
    
    if (saveUserBtn) {
        saveUserBtn.addEventListener('click', saveUser);
    }
    
    if (deleteUserBtn) {
        deleteUserBtn.addEventListener('click', function() {
            const userId = document.getElementById('user-id').value;
            showDeleteConfirmation('user', userId);
        });
    }
}

/**
 * Show user edit modal with user data
 */
function editUser(userId) {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    // Fetch user details
    fetch(`/api/admin/users/${userId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to fetch user details');
        }
        return response.json();
    })
    .then(user => {
        // Populate form
        document.getElementById('user-id').value = user._id;
        document.getElementById('user-name').value = user.name;
        document.getElementById('user-email').value = user.email;
        document.getElementById('user-role').value = user.role;
        
        // Show modal
        const userModal = new bootstrap.Modal(document.getElementById('user-modal'));
        userModal.show();
    })
    .catch(error => {
        console.error('Error fetching user details:', error);
        alert('Failed to fetch user details');
    });
}

/**
 * Save user changes
 */
function saveUser() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    const userId = document.getElementById('user-id').value;
    const userData = {
        name: document.getElementById('user-name').value,
        email: document.getElementById('user-email').value,
        role: document.getElementById('user-role').value
    };
    
    // Update user
    fetch(`/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(userData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to update user');
        }
        return response.json();
    })
    .then(data => {
        // Hide modal
        const userModal = bootstrap.Modal.getInstance(document.getElementById('user-modal'));
        userModal.hide();
        
        // Reload users
        loadUsers();
        
        // Show success message
        alert('User updated successfully');
    })
    .catch(error => {
        console.error('Error updating user:', error);
        alert('Failed to update user');
    });
}

/**
 * Show confirmation modal for deletion
 */
function showDeleteConfirmation(type, id) {
    const confirmBtn = document.getElementById('confirm-delete-btn');
    const message = document.getElementById('delete-message');
    
    // Set message based on type
    if (type === 'user') {
        message.textContent = 'Are you sure you want to delete this user? This will also delete all their predictions and cannot be undone.';
    } else if (type === 'prediction') {
        message.textContent = 'Are you sure you want to delete this prediction? This action cannot be undone.';
    }
    
    // Setup confirm button
    confirmBtn.onclick = function() {
        if (type === 'user') {
            deleteUser(id);
        } else if (type === 'prediction') {
            deletePrediction(id);
        }
        
        // Hide modal
        const deleteModal = bootstrap.Modal.getInstance(document.getElementById('delete-modal'));
        deleteModal.hide();
    };
    
    // Show modal
    const deleteModal = new bootstrap.Modal(document.getElementById('delete-modal'));
    deleteModal.show();
}

/**
 * Delete a user
 */
function deleteUser(userId) {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    // Delete user
    fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to delete user');
        }
        return response.json();
    })
    .then(data => {
        // Reload users
        loadUsers();
        
        // Show success message
        alert('User deleted successfully');
    })
    .catch(error => {
        console.error('Error deleting user:', error);
        alert('Failed to delete user');
    });
}

/**
 * Delete a prediction
 */
function deletePrediction(predictionId) {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    // Delete prediction
    fetch(`/api/user/history/${predictionId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to delete prediction');
        }
        return response.json();
    })
    .then(data => {
        // Reload history
        loadHistory();
        
        // Show success message
        alert('Prediction deleted successfully');
    })
    .catch(error => {
        console.error('Error deleting prediction:', error);
        alert('Failed to delete prediction');
    });
}

/**
 * Export users data
 */
function exportUsers() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    fetch('/api/admin/export/users', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to export users');
        }
        return response.json();
    })
    .then(data => {
        // Create JSON file for download
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Create download link
        const a = document.createElement('a');
        a.href = url;
        a.download = `users_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    })
    .catch(error => {
        console.error('Error exporting users:', error);
        alert('Failed to export users');
    });
}

/**
 * Export predictions data
 */
function exportPredictions() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    fetch('/api/admin/export/predictions', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to export predictions');
        }
        return response.json();
    })
    .then(data => {
        // Create JSON file for download
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Create download link
        const a = document.createElement('a');
        a.href = url;
        a.download = `predictions_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    })
    .catch(error => {
        console.error('Error exporting predictions:', error);
        alert('Failed to export predictions');
    });
}

/**
 * Refresh JWT token
 */
function refreshToken() {
    return new Promise((resolve, reject) => {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            // Redirect to login if no refresh token
            window.location.href = '/login.html';
            reject(new Error('No refresh token'));
            return;
        }
        
        fetch('/api/auth/refresh-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Update access token
            localStorage.setItem('access_token', data.access_token);
            resolve();
        })
        .catch(error => {
            console.error('Error refreshing token:', error);
            // Redirect to login
            window.location.href = '/login.html';
            reject(error);
        });
    });
}

/**
 * Logout user
 */
function logout() {
    // Clear local storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    
    // Redirect to login
    window.location.href = '/login.html';
}
