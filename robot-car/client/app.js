/**
 * FHE IoT Dashboard - Application Logic
 * Handles WebSocket connection, device registration, and real-time updates
 */

// ==================== CONFIGURATION ====================
const CONFIG = {
    serverUrl: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : `http://${window.location.hostname}:8000`,
    wsUrl: window.location.hostname === 'localhost'
        ? 'ws://localhost:8000/ws'
        : `ws://${window.location.hostname}:8000/ws`,
    reconnectInterval: 3000,
    maxDataPoints: 60,
    storageKeys: {
        deviceId: 'fhe_device_id',
        trustToken: 'fhe_trust_token',
        secretContext: 'fhe_secret_context',
        lastCode: 'fhe_last_code'  // Remember last used code
    }
};

// ==================== STATE ====================
const state = {
    websocket: null,
    isConnected: false,
    isTrusted: false,
    deviceId: null,
    trustToken: null,
    secretContext: null,
    reconnectAttempts: 0,

    // Data source: 'auto', 'esp32', 'sim'
    dataSource: 'auto',
    simOnline: false,
    lastSimData: null,
    lastSimTime: 0,

    // Sensor data history
    sensorHistory: {
        temperature: [],
        distance: [],
        humidity: [],
        light: []
    },

    // Charts
    charts: {
        temp: null,
        dist: null
    }
};

// ==================== DOM ELEMENTS ====================
const elements = {
    // Connection
    connectionStatus: document.getElementById('connectionStatus'),
    trustBadge: document.getElementById('trustBadge'),

    // Modal
    registrationModal: document.getElementById('registrationModal'),
    regCode: document.getElementById('regCode'),
    registerBtn: document.getElementById('registerBtn'),
    skipRegistration: document.getElementById('skipRegistration'),

    // Stats - ESP32
    tempValue: document.getElementById('tempValue'),
    distValue: document.getElementById('distValue'),
    humidValue: document.getElementById('humidValue'),
    lightValue: document.getElementById('lightValue'),
    tempEncrypted: document.getElementById('tempEncrypted'),
    distEncrypted: document.getElementById('distEncrypted'),
    humidEncrypted: document.getElementById('humidEncrypted'),
    lightEncrypted: document.getElementById('lightEncrypted'),

    // Stats - Simulation
    distFront: document.getElementById('distFront'),
    distLeft: document.getElementById('distLeft'),
    distRight: document.getElementById('distRight'),
    distRear: document.getElementById('distRear'),
    motorTemp: document.getElementById('motorTemp'),
    carSpeedDash: document.getElementById('carSpeedDash'),
    riskScore: document.getElementById('riskScore'),
    riskLevel: document.getElementById('riskLevel'),

    // Source toggle
    simStatus: document.getElementById('simStatus'),

    // Charts
    tempChart: document.getElementById('tempChart'),
    distChart: document.getElementById('distChart'),

    // Encrypted section
    encryptedSection: document.getElementById('encryptedSection'),
    ciphertextDisplay: document.getElementById('ciphertextDisplay'),

    // Computed
    computedMean: document.getElementById('computedMean'),
    computedSum: document.getElementById('computedSum'),
    computedFahrenheit: document.getElementById('computedFahrenheit'),

    // Server info
    serverStatus: document.getElementById('serverStatus'),
    contextHash: document.getElementById('contextHash'),
    packetsReceived: document.getElementById('packetsReceived'),
    connectedClients: document.getElementById('connectedClients')
};

// ==================== STORAGE ====================
const storage = {
    get(key) {
        try {
            return localStorage.getItem(key);
        } catch {
            return null;
        }
    },

    set(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch {
            console.warn('LocalStorage not available');
        }
    },

    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch {
            // Ignore
        }
    },

    loadCredentials() {
        state.deviceId = this.get(CONFIG.storageKeys.deviceId);
        state.trustToken = this.get(CONFIG.storageKeys.trustToken);
        state.secretContext = this.get(CONFIG.storageKeys.secretContext);

        if (state.deviceId && state.trustToken) {
            state.isTrusted = true;
        }
    },

    saveCredentials(deviceId, trustToken, secretContext) {
        this.set(CONFIG.storageKeys.deviceId, deviceId);
        this.set(CONFIG.storageKeys.trustToken, trustToken);
        if (secretContext) {
            this.set(CONFIG.storageKeys.secretContext, secretContext);
        }

        state.deviceId = deviceId;
        state.trustToken = trustToken;
        state.secretContext = secretContext;
        state.isTrusted = true;
    },

    clearCredentials() {
        this.remove(CONFIG.storageKeys.deviceId);
        this.remove(CONFIG.storageKeys.trustToken);
        this.remove(CONFIG.storageKeys.secretContext);

        state.deviceId = null;
        state.trustToken = null;
        state.secretContext = null;
        state.isTrusted = false;
    }
};

// ==================== FINGERPRINT ====================
function generateFingerprint() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('FHE IoT', 2, 2);

    const canvasData = canvas.toDataURL();
    const userAgent = navigator.userAgent;
    const screenInfo = `${screen.width}x${screen.height}x${screen.colorDepth}`;
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    const data = `${canvasData}|${userAgent}|${screenInfo}|${timezone}`;

    // Simple hash
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
        const char = data.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }

    return Math.abs(hash).toString(16).padStart(16, '0');
}

// ==================== UI UPDATES ====================
function updateConnectionStatus(connected) {
    state.isConnected = connected;

    elements.connectionStatus.className = 'connection-status ' + (connected ? 'connected' : 'disconnected');
    elements.connectionStatus.querySelector('.status-text').textContent =
        connected ? 'Connected' : 'Disconnected';
}

function updateTrustStatus(trusted) {
    state.isTrusted = trusted;

    elements.trustBadge.className = 'trust-badge ' + (trusted ? 'trusted' : '');
    elements.trustBadge.querySelector('.trust-icon').textContent = trusted ? '✓' : '🔒';
    elements.trustBadge.querySelector('.trust-text').textContent = trusted ? 'Trusted' : 'Untrusted';

    // Show/hide encrypted section
    elements.encryptedSection.className = 'encrypted-section ' + (trusted ? 'hidden' : '');

    // Toggle encrypted display on stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        card.classList.toggle('show-encrypted', !trusted);
    });
}

function updateSensorValue(sensorId, value, encrypted) {
    const valueEl = {
        'temperature': elements.tempValue,
        'temp_room': elements.tempValue,
        'temp_motor': elements.tempValue,
        'ultrasonic': elements.distValue,
        'ultrasonic_front': elements.distValue,
        'humidity': elements.humidValue,
        'humidity_room': elements.humidValue,
        'light': elements.lightValue,
        'light_room': elements.lightValue
    }[sensorId];

    const encryptedEl = {
        'temperature': elements.tempEncrypted,
        'temp_room': elements.tempEncrypted,
        'temp_motor': elements.tempEncrypted,
        'ultrasonic': elements.distEncrypted,
        'ultrasonic_front': elements.distEncrypted,
        'humidity': elements.humidEncrypted,
        'humidity_room': elements.humidEncrypted,
        'light': elements.lightEncrypted,
        'light_room': elements.lightEncrypted
    }[sensorId];

    if (valueEl) {
        if (state.isTrusted && value !== null) {
            // Show decrypted value
            const displayValue = Array.isArray(value) ? value[0] : value;
            valueEl.textContent = typeof displayValue === 'number'
                ? displayValue.toFixed(1)
                : displayValue;
        } else {
            valueEl.textContent = '--';
        }
    }

    if (encryptedEl && encrypted) {
        // Show truncated ciphertext
        const truncated = encrypted.length > 40
            ? encrypted.substring(0, 40) + '...'
            : encrypted;
        encryptedEl.textContent = `🔒 ${truncated}`;
    }
}

function updateCiphertextDisplay(sensorData) {
    const lines = [];

    for (const [sensorId, data] of Object.entries(sensorData)) {
        if (data && data.ciphertext) {
            const truncated = data.ciphertext.substring(0, 80);
            lines.push(`<div class="ciphertext-line"><strong>${sensorId}:</strong> ${truncated}...</div>`);
        }
    }

    if (lines.length > 0) {
        elements.ciphertextDisplay.innerHTML = lines.join('');
    }
}

function updateServerInfo(status) {
    if (status) {
        elements.serverStatus.textContent = status.status || 'unknown';
        elements.contextHash.textContent = status.context_hash || '--';
        elements.packetsReceived.textContent = status.packets_received || 0;
        elements.connectedClients.textContent = status.connected_clients || 0;
    }
}

// ==================== CHARTS ====================
function initCharts() {
    const chartConfig = {
        type: 'line',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 300
            },
            scales: {
                x: {
                    display: false
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.6)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            },
            elements: {
                point: {
                    radius: 2,
                    hoverRadius: 4
                },
                line: {
                    tension: 0.4,
                    borderWidth: 2
                }
            }
        }
    };

    // Temperature chart
    state.charts.temp = new Chart(elements.tempChart, {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                fill: true
            }]
        }
    });

    // Distance chart
    state.charts.dist = new Chart(elements.distChart, {
        ...chartConfig,
        data: {
            labels: [],
            datasets: [{
                data: [],
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                fill: true
            }]
        }
    });
}

function updateChart(chart, historyKey, value) {
    if (!chart) return;

    const history = state.sensorHistory[historyKey];

    if (Array.isArray(value)) {
        // Add all values from batch
        history.push(...value);
    } else {
        history.push(value);
    }

    // Limit history
    while (history.length > CONFIG.maxDataPoints) {
        history.shift();
    }

    // Update chart
    chart.data.labels = history.map((_, i) => i);
    chart.data.datasets[0].data = history;
    chart.update('none');
}

// ==================== WEBSOCKET ====================
function connectWebSocket() {
    const url = state.isTrusted
        ? `${CONFIG.wsUrl}?device_id=${state.deviceId}&trust_token=${state.trustToken}`
        : CONFIG.wsUrl;

    console.log('Connecting to WebSocket:', url);

    try {
        state.websocket = new WebSocket(url);

        state.websocket.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
            state.reconnectAttempts = 0;
        };

        state.websocket.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (e) {
                console.error('Failed to parse message:', e);
            }
        };

        state.websocket.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);
            scheduleReconnect();
        };

        state.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

    } catch (e) {
        console.error('Failed to create WebSocket:', e);
        scheduleReconnect();
    }
}

function scheduleReconnect() {
    state.reconnectAttempts++;
    const delay = Math.min(CONFIG.reconnectInterval * state.reconnectAttempts, 30000);

    console.log(`Reconnecting in ${delay}ms...`);
    setTimeout(connectWebSocket, delay);
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'connection':
            console.log('Connection established:', message);
            updateServerInfo(message.server_status);

            if (message.authenticated) {
                // Server confirmed we are trusted
                updateTrustStatus(true);
            } else {
                // Server says not authenticated - clear invalid cached credentials
                if (state.isTrusted) {
                    console.log('Stored credentials invalid, clearing...');
                    storage.clearCredentials();
                    updateTrustStatus(false);
                    showModal();  // Show registration modal
                }
            }
            break;

        case 'sensor_update':
            handleSensorUpdate(message);
            break;

        case 'compute_result':
            handleComputeResult(message);
            break;

        case 'pong':
            // Heartbeat response
            break;

        default:
            console.log('Unknown message type:', message.type);
    }
}

function handleSensorUpdate(message) {
    const { data, decrypted, device_id, risk_analysis } = message;

    // Check if this is from robot car simulation
    const isSimData = device_id && device_id.includes('robot_car');

    // If it's sim data, we can mark it as online even if we can't see decrypted values
    if (isSimData) {
        if (!state.simOnline) updateSimStatus(true);
        state.lastSimTime = Date.now();

        if (decrypted) {
            // Extract simulation sensor values
            const simData = {};
            for (const [sensorId, sensorInfo] of Object.entries(decrypted)) {
                // Handle both direct values and value objects
                const val = sensorInfo && typeof sensorInfo === 'object' && 'values' in sensorInfo
                    ? sensorInfo.values
                    : sensorInfo;

                simData[sensorId] = Array.isArray(val) ? val[0] : val;
            }
            updateSimSensors(simData);
        }
    }

    // Update Risk Display
    if (risk_analysis) {
        updateRiskDisplay(risk_analysis);
    }

    // Update ciphertext display for untrusted
    if (data) {
        updateCiphertextDisplay(data);
    }

    // Update sensor values (for ESP32 mode)
    if (data && (state.dataSource === 'esp32' || (state.dataSource === 'auto' && !state.simOnline) || !isSimData)) {
        for (const [sensorId, sensorData] of Object.entries(data)) {
            const encrypted = sensorData?.ciphertext?.substring(0, 40);

            let value = null;
            if (decrypted && decrypted[sensorId]) {
                const vals = decrypted[sensorId].values;
                value = Array.isArray(vals) ? vals : [vals];
            }

            updateSensorValue(sensorId, value, encrypted);

            // Update charts
            if (value && value.length > 0) {
                const sensorType = sensorData?.sensor_type || sensorId;

                if (sensorType.includes('temp') || sensorId.includes('temp')) {
                    updateChart(state.charts.temp, 'temperature', value);
                } else if (sensorType.includes('ultrasonic') || sensorId.includes('ultrasonic') || sensorId.includes('dist')) {
                    updateChart(state.charts.dist, 'distance', value);
                }
            }
        }
    }
}

function handleComputeResult(message) {
    const { result, decrypted } = message;

    if (!result) return;

    const displayValue = decrypted && decrypted.length > 0
        ? decrypted[0].toFixed(2)
        : '🔒 (encrypted)';

    switch (result.operation) {
        case 'encrypted_mean':
            elements.computedMean.textContent = displayValue;
            break;
        case 'encrypted_sum':
            elements.computedSum.textContent = displayValue;
            break;
        case 'encrypted_scale_offset':
            elements.computedFahrenheit.textContent = displayValue + '°F';
            break;
    }
}

// ==================== REGISTRATION ====================
async function registerDevice(code) {
    const fingerprint = generateFingerprint();

    try {
        const response = await fetch(`${CONFIG.serverUrl}/api/register/device`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                registration_code: code,
                device_fingerprint: fingerprint
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Registration failed');
        }

        const data = await response.json();

        // Save credentials AND the code for easy re-registration
        storage.saveCredentials(data.device_id, data.trust_token, data.secret_context);
        storage.set(CONFIG.storageKeys.lastCode, code);

        // Update UI
        updateTrustStatus(true);
        hideModal();

        // Reconnect WebSocket with credentials
        if (state.websocket) {
            state.websocket.close();
        }
        connectWebSocket();

        console.log('Device registered successfully:', data.device_name);

    } catch (e) {
        console.error('Registration error:', e);
        alert('Registration failed: ' + e.message);
    }
}

function showModal() {
    elements.registrationModal.classList.remove('hidden');

    // Pre-fill with last used code if available
    const lastCode = storage.get(CONFIG.storageKeys.lastCode);
    if (lastCode && elements.regCode) {
        elements.regCode.value = lastCode;
    }
}

function hideModal() {
    elements.registrationModal.classList.add('hidden');
}

// ==================== COMPUTE REQUESTS ====================
async function requestComputation(operation, sensorId) {
    if (!state.websocket || state.websocket.readyState !== WebSocket.OPEN) {
        console.warn('WebSocket not connected');
        return;
    }

    let params = {};

    if (operation === 'scale') {
        // Celsius to Fahrenheit
        params = { scale: 1.8, offset: 32 };
        operation = 'scale';
    }

    state.websocket.send(JSON.stringify({
        type: 'compute',
        sensor_id: sensorId,
        operation: operation,
        parameters: params
    }));
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    // Registration
    elements.registerBtn.addEventListener('click', () => {
        const code = elements.regCode.value.trim().toUpperCase();
        if (code.length === 6) {
            registerDevice(code);
        } else {
            alert('Please enter a valid 6-character code');
        }
    });

    elements.regCode.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            elements.registerBtn.click();
        }
    });

    elements.skipRegistration.addEventListener('click', () => {
        hideModal();
        updateTrustStatus(false);
        connectWebSocket();
    });

    // Compute buttons
    document.querySelectorAll('.btn-compute').forEach(btn => {
        btn.addEventListener('click', () => {
            const operation = btn.dataset.op;
            const sensorRaw = btn.dataset.sensor;

            // Map to actual sensor IDs
            const sensorMap = {
                'temp': 'temp_room',
                'dist': 'ultrasonic_front'
            };

            const sensorId = sensorMap[sensorRaw] || sensorRaw;
            requestComputation(operation, sensorId);
        });
    });

    // Trust badge click to show registration
    elements.trustBadge.addEventListener('click', () => {
        if (!state.isTrusted) {
            showModal();
        }
    });

    // Chart range buttons
    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const container = btn.closest('.chart-container');
            container.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Could implement range filtering here
        });
    });

    // Logout button with confirmation
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (state.isTrusted) {
                const confirmed = confirm('Are you sure you want to logout?\n\nThis will clear your credentials and you will need to re-register.');
                if (!confirmed) return;
            }

            storage.clearCredentials();
            updateTrustStatus(false);
            showModal();
            // Reconnect as untrusted
            if (state.websocket) {
                state.websocket.close();
            }
            connectWebSocket();
        });
    }

    // Source toggle buttons
    document.querySelectorAll('.source-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const source = btn.dataset.source;
            setDataSource(source);

            // Update active state
            document.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

// ==================== DATA SOURCE MANAGEMENT ====================
function setDataSource(source) {
    state.dataSource = source;
    console.log('Data source set to:', source);

    // Show/hide sensor cards based on mode
    const showSim = source === 'sim' || (source === 'auto' && state.simOnline);
    const showEsp = source === 'esp32' || (source === 'auto' && !state.simOnline);

    // Toggle ESP32 sensors
    document.querySelectorAll('[data-mode*="esp32"]').forEach(card => {
        card.style.display = showEsp ? '' : 'none';
    });

    // Toggle Sim sensors
    document.querySelectorAll('[data-mode="sim"]').forEach(card => {
        card.style.display = showSim ? '' : 'none';
    });
}

function updateSimStatus(online) {
    state.simOnline = online;

    if (elements.simStatus) {
        elements.simStatus.classList.toggle('online', online);
        elements.simStatus.querySelector('.sim-text').textContent =
            online ? 'Sim: Online' : 'Sim: Offline';
    }

    // In auto mode, switch to sim when it comes online
    if (state.dataSource === 'auto') {
        setDataSource('auto');
    }
}

function updateSimSensors(data) {
    state.lastSimData = data;
    state.lastSimTime = Date.now();

    // Mark simulation as online
    updateSimStatus(true);

    // Update simulation sensor displays
    if (elements.distFront && data.ultrasonic_front !== undefined) {
        elements.distFront.textContent = Math.round(data.ultrasonic_front);
    }
    if (elements.distLeft && data.ultrasonic_left !== undefined) {
        elements.distLeft.textContent = Math.round(data.ultrasonic_left);
    }
    if (elements.distRight && data.ultrasonic_right !== undefined) {
        elements.distRight.textContent = Math.round(data.ultrasonic_right);
    }
    if (elements.distRear && data.ultrasonic_rear !== undefined) {
        elements.distRear.textContent = Math.round(data.ultrasonic_rear);
    }
    if (elements.motorTemp && data.temp_motor !== undefined) {
        elements.motorTemp.textContent = data.temp_motor.toFixed(1);
    }
    if (elements.carSpeedDash && data.speed !== undefined) {
        elements.carSpeedDash.textContent = Math.round(data.speed);
    }
}

function updateRiskDisplay(risk) {
    const card = document.getElementById('riskCard');
    if (card) card.style.display = 'flex';

    if (elements.riskScore) elements.riskScore.textContent = risk.risk_score.toFixed(1);

    if (elements.riskLevel) {
        elements.riskLevel.textContent = risk.risk_level.toUpperCase();

        // Color coding
        elements.riskLevel.className = 'risk-badge'; // reset
        switch (risk.risk_level) {
            case 'low':
                elements.riskLevel.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';
                elements.riskLevel.style.color = '#10b981';
                break;
            case 'medium':
                elements.riskLevel.style.backgroundColor = 'rgba(245, 158, 11, 0.2)';
                elements.riskLevel.style.color = '#f59e0b';
                break;
            case 'high':
                elements.riskLevel.style.backgroundColor = 'rgba(249, 115, 22, 0.2)';
                elements.riskLevel.style.color = '#f97316';
                break;
            case 'critical':
                elements.riskLevel.style.backgroundColor = 'rgba(239, 68, 68, 0.2)';
                elements.riskLevel.style.color = '#ef4444';
                break;
        }
    }
}

// Check for simulation timeout
setInterval(() => {
    if (state.simOnline && Date.now() - state.lastSimTime > 3000) {
        updateSimStatus(false);
    }
}, 1000);

// ==================== INITIALIZATION ====================
async function init() {
    console.log('Initializing FHE IoT Dashboard...');

    // Load stored credentials
    storage.loadCredentials();

    // Initialize charts
    initCharts();

    // Setup event listeners
    setupEventListeners();

    // Check if already registered
    if (state.isTrusted) {
        console.log('Found stored credentials, connecting as trusted device');
        hideModal();
        updateTrustStatus(true);
        connectWebSocket();
    } else {
        // Show registration modal
        showModal();
    }

    // Fetch initial server status
    try {
        const response = await fetch(`${CONFIG.serverUrl}/status`);
        if (response.ok) {
            const status = await response.json();
            updateServerInfo(status);
        }
    } catch (e) {
        console.warn('Could not fetch server status:', e);
    }

    // Heartbeat
    setInterval(() => {
        if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
            state.websocket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Warn before page refresh if trusted (losing session)
window.addEventListener('beforeunload', (e) => {
    if (state.isTrusted) {
        e.preventDefault();
        e.returnValue = 'You are logged in as a trusted device. Are you sure you want to leave?';
        return e.returnValue;
    }
});