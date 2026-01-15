/**
 * FHE Robot Car - Unified Dashboard
 * Combined simulation and FHE data display
 */

// ==================== CONFIGURATION ====================
const CONFIG = {
    serverUrl: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : `http://${window.location.hostname}:8000`,
    wsUrl: window.location.hostname === 'localhost'
        ? 'ws://localhost:8000/ws'
        : `ws://${window.location.hostname}:8000/ws`,
    transmitInterval: 500,
    sensorRange: 400,
    pixelsPerCm: 2,
    storageKeys: {
        deviceId: 'fhe_device_id',
        trustToken: 'fhe_trust_token',
        lastCode: 'fhe_last_code'
    }
};

// ==================== STATE ====================
const state = {
    ws: null,
    connected: false,
    isTrusted: false,
    deviceId: null,
    trustToken: null,
    packetCount: 0,
    lastCiphertext: ''
};

const game = {
    canvas: null,
    ctx: null,
    car: {
        x: 400, y: 300,
        width: 40, height: 60,
        angle: 0, speed: 0,
        velocityX: 0, velocityY: 0,
        maxSpeed: 10, acceleration: 0.25,
        deceleration: 0.15, friction: 0.985,
        turnSpeed: 0.045, grip: 0.92,
        motorTemp: 25, wheelAngle: 0
    },
    obstacles: [],
    sensors: { front: 400, left: 400, right: 400, rear: 400 },
    keys: { forward: false, backward: false, left: false, right: false, brake: false },
    tireTracks: [],
    maxTracks: 100
};

// ==================== ELEMENTS ====================
const el = {
    canvas: () => document.getElementById('gameCanvas'),
    connectionDot: () => document.getElementById('connectionDot'),
    connectionText: () => document.getElementById('connectionText'),
    trustBadge: () => document.getElementById('trustBadge'),
    trustIcon: () => document.getElementById('trustIcon'),
    trustText: () => document.getElementById('trustText'),
    modal: () => document.getElementById('registrationModal'),
    regCode: () => document.getElementById('regCode'),
    registerBtn: () => document.getElementById('registerBtn'),
    skipBtn: () => document.getElementById('skipBtn'),
    collisionWarning: () => document.getElementById('collisionWarning'),
    sensorFront: () => document.getElementById('sensorFront'),
    sensorLeft: () => document.getElementById('sensorLeft'),
    sensorRight: () => document.getElementById('sensorRight'),
    sensorRear: () => document.getElementById('sensorRear'),
    riskScore: () => document.getElementById('riskScore'),
    riskBadge: () => document.getElementById('riskBadge'),
    recommendation: () => document.getElementById('recommendation'),
    carSpeed: () => document.getElementById('carSpeed'),
    motorTemp: () => document.getElementById('motorTemp'),
    ciphertextBox: () => document.getElementById('ciphertextBox'),
    packetCount: () => document.getElementById('packetCount'),
    posX: () => document.getElementById('posX'),
    posY: () => document.getElementById('posY'),
    heading: () => document.getElementById('heading'),
    serverStatus: () => document.getElementById('serverStatus')
};

// ==================== INITIALIZATION ====================
function init() {
    game.canvas = el.canvas();
    game.ctx = game.canvas.getContext('2d');
    resizeCanvas();

    loadCredentials();
    generateObstacles();
    setupInputHandlers();
    setupTouchControls();
    connectWebSocket();

    requestAnimationFrame(gameLoop);
    setInterval(transmitSensorData, CONFIG.transmitInterval);

    console.log('🚗 FHE Robot Car initialized');
}

function resizeCanvas() {
    const container = game.canvas.parentElement;
    game.canvas.width = container.clientWidth;
    game.canvas.height = container.clientHeight;

    // Reset car position
    game.car.x = game.canvas.width / 2;
    game.car.y = game.canvas.height / 2;
}

function generateObstacles() {
    const w = game.canvas.width;
    const h = game.canvas.height;
    const t = 20; // wall thickness

    game.obstacles = [
        { x: 0, y: 0, w: w, h: t, color: '#475569' },
        { x: 0, y: h - t, w: w, h: t, color: '#475569' },
        { x: 0, y: 0, w: t, h: h, color: '#475569' },
        { x: w - t, y: 0, w: t, h: h, color: '#475569' },
    ];

    // Random obstacles
    for (let i = 0; i < 6; i++) {
        const ow = 40 + Math.random() * 60;
        const oh = 40 + Math.random() * 60;
        const ox = t + 80 + Math.random() * (w - 2 * t - 160 - ow);
        const oy = t + 80 + Math.random() * (h - 2 * t - 160 - oh);

        if (Math.abs(ox - w / 2) < 80 && Math.abs(oy - h / 2) < 80) continue;

        game.obstacles.push({
            x: ox, y: oy, w: ow, h: oh,
            color: `hsl(${Math.random() * 60 + 200}, 40%, 35%)`
        });
    }
}

// ==================== INPUT HANDLING ====================
function setupInputHandlers() {
    document.addEventListener('keydown', (e) => {
        switch (e.code) {
            case 'KeyW': case 'ArrowUp': game.keys.forward = true; break;
            case 'KeyS': case 'ArrowDown': game.keys.backward = true; break;
            case 'KeyA': case 'ArrowLeft': game.keys.left = true; break;
            case 'KeyD': case 'ArrowRight': game.keys.right = true; break;
            case 'Space': game.keys.brake = true; e.preventDefault(); break;
            case 'KeyR': resetCar(); break;
        }
    });

    document.addEventListener('keyup', (e) => {
        switch (e.code) {
            case 'KeyW': case 'ArrowUp': game.keys.forward = false; break;
            case 'KeyS': case 'ArrowDown': game.keys.backward = false; break;
            case 'KeyA': case 'ArrowLeft': game.keys.left = false; break;
            case 'KeyD': case 'ArrowRight': game.keys.right = false; break;
            case 'Space': game.keys.brake = false; break;
        }
    });

    window.addEventListener('resize', () => {
        resizeCanvas();
        generateObstacles();
    });

    // Registration
    el.registerBtn().addEventListener('click', () => registerDevice());
    el.regCode().addEventListener('keypress', (e) => { if (e.key === 'Enter') registerDevice(); });
    el.skipBtn().addEventListener('click', () => {
        el.modal().classList.add('hidden');
        connectWebSocket();
    });

    // Trust badge click
    el.trustBadge().addEventListener('click', () => {
        if (!state.isTrusted) showModal();
    });
}

function setupTouchControls() {
    const btns = document.querySelectorAll('.touch-btn');
    btns.forEach(btn => {
        const key = btn.dataset.key;

        btn.addEventListener('touchstart', (e) => {
            e.preventDefault();
            game.keys[key] = true;
        });

        btn.addEventListener('touchend', (e) => {
            e.preventDefault();
            game.keys[key] = false;
        });
    });
}

function resetCar() {
    game.car.x = game.canvas.width / 2;
    game.car.y = game.canvas.height / 2;
    game.car.angle = 0;
    game.car.speed = 0;
    game.car.velocityX = 0;
    game.car.velocityY = 0;
    game.car.motorTemp = 25;
}

// ==================== PHYSICS ====================
function updateCar() {
    const car = game.car;
    const keys = game.keys;

    // Acceleration
    if (keys.forward) car.speed += car.acceleration * (1 - Math.abs(car.speed) / car.maxSpeed);
    if (keys.backward) {
        if (car.speed > 0.5) car.speed -= car.deceleration * 1.5;
        else car.speed -= car.acceleration * 0.5;
    }

    // Brake
    if (keys.brake) {
        car.speed *= 0.95;
        car.grip = 0.75;
    } else {
        car.grip = 0.92;
    }

    // Friction
    if (!keys.forward && !keys.backward) car.speed *= car.friction;

    // Speed limits
    car.speed = Math.max(-car.maxSpeed * 0.4, Math.min(car.maxSpeed, car.speed));
    if (Math.abs(car.speed) < 0.05) car.speed = 0;

    // Turning
    if (Math.abs(car.speed) > 0.1) {
        const speedFactor = Math.min(1, Math.abs(car.speed) / 5);
        const turnRate = car.turnSpeed * speedFactor * (car.speed > 0 ? 1 : -1);
        if (keys.left) car.angle -= turnRate;
        if (keys.right) car.angle += turnRate;
    }

    // Velocity
    const targetVX = Math.sin(car.angle) * car.speed;
    const targetVY = -Math.cos(car.angle) * car.speed;
    car.velocityX = car.velocityX * (1 - car.grip) + targetVX * car.grip;
    car.velocityY = car.velocityY * (1 - car.grip) + targetVY * car.grip;

    // Collision
    const newX = car.x + car.velocityX;
    const newY = car.y + car.velocityY;

    if (!checkCollision(newX, newY)) {
        car.x = newX;
        car.y = newY;
    } else if (!checkCollision(newX, car.y)) {
        car.x = newX;
        car.velocityY *= -0.3;
    } else if (!checkCollision(car.x, newY)) {
        car.y = newY;
        car.velocityX *= -0.3;
    } else {
        car.speed *= -0.2;
        car.velocityX *= -0.3;
        car.velocityY *= -0.3;
    }

    // Tire tracks
    const drift = Math.abs(car.velocityX * Math.cos(car.angle) + car.velocityY * Math.sin(car.angle));
    if (drift > 1 && Math.abs(car.speed) > 2) {
        game.tireTracks.push({
            x: car.x - Math.sin(car.angle) * car.height * 0.35,
            y: car.y + Math.cos(car.angle) * car.height * 0.35,
            alpha: 0.5
        });
        if (game.tireTracks.length > game.maxTracks) game.tireTracks.shift();
    }
    game.tireTracks.forEach(t => t.alpha *= 0.995);
    game.tireTracks = game.tireTracks.filter(t => t.alpha > 0.05);

    // Motor temp
    const load = Math.abs(car.speed) + (keys.forward || keys.backward ? 3 : 0);
    const targetTemp = 25 + load * 3;
    car.motorTemp += (targetTemp - car.motorTemp) * 0.02;
}

function checkCollision(x, y) {
    const hw = game.car.width / 2;
    const hh = game.car.height / 2;

    for (const obs of game.obstacles) {
        if (x + hw > obs.x && x - hw < obs.x + obs.w &&
            y + hh > obs.y && y - hh < obs.y + obs.h) {
            return true;
        }
    }
    return false;
}

// ==================== SENSORS ====================
function updateSensors() {
    const car = game.car;

    game.sensors.front = castRay(car.x, car.y, car.angle);
    game.sensors.rear = castRay(car.x, car.y, car.angle + Math.PI);
    game.sensors.left = castRay(car.x, car.y, car.angle - Math.PI / 2);
    game.sensors.right = castRay(car.x, car.y, car.angle + Math.PI / 2);

    // Update display
    updateSensorDisplay('sensorFront', game.sensors.front);
    updateSensorDisplay('sensorLeft', game.sensors.left);
    updateSensorDisplay('sensorRight', game.sensors.right);
    updateSensorDisplay('sensorRear', game.sensors.rear);

    // Speed & temp
    const speedKmh = Math.abs(car.speed) * 10;
    el.carSpeed().textContent = speedKmh.toFixed(0);
    el.motorTemp().textContent = car.motorTemp.toFixed(1);

    // Position
    el.posX().textContent = Math.round(car.x);
    el.posY().textContent = Math.round(car.y);
    el.heading().textContent = `${Math.round(car.angle * 180 / Math.PI)}°`;

    // Risk analysis
    updateRiskAnalysis();

    // Collision warning
    const minDist = Math.min(game.sensors.front, game.sensors.left, game.sensors.right);
    el.collisionWarning().classList.toggle('active', minDist < 30);
}

function castRay(startX, startY, angle) {
    const step = 5;
    const maxRange = CONFIG.sensorRange;
    let x = startX, y = startY, dist = 0;

    while (dist < maxRange) {
        x += Math.sin(angle) * step;
        y -= Math.cos(angle) * step;
        dist += step;

        for (const obs of game.obstacles) {
            if (x >= obs.x && x <= obs.x + obs.w && y >= obs.y && y <= obs.y + obs.h) {
                return Math.round(dist / CONFIG.pixelsPerCm);
            }
        }
    }
    return Math.round(maxRange / CONFIG.pixelsPerCm);
}

function updateSensorDisplay(id, value) {
    const elem = document.getElementById(id);
    elem.textContent = value;
    elem.classList.remove('warning', 'danger');
    if (value < 30) elem.classList.add('danger');
    else if (value < 80) elem.classList.add('warning');
}

function updateRiskAnalysis() {
    const { front, left, right, rear } = game.sensors;
    const speed = Math.abs(game.car.speed) * 10;
    const maxDist = 200;

    // Risk calculation
    const frontRisk = (1 - Math.min(front, maxDist) / maxDist) * 100;
    const leftRisk = (1 - Math.min(left, maxDist) / maxDist) * 100;
    const rightRisk = (1 - Math.min(right, maxDist) / maxDist) * 100;
    const rearRisk = (1 - Math.min(rear, maxDist) / maxDist) * 100;

    let risk = frontRisk * 0.4 + leftRisk * 0.2 + rightRisk * 0.2 + rearRisk * 0.1;
    risk *= 1 + (speed / 100) * 0.3;
    risk = Math.min(100, risk);

    // Update UI
    el.riskScore().textContent = risk.toFixed(0);
    el.riskScore().className = 'risk-score ' + getRiskLevel(risk);
    el.riskBadge().textContent = getRiskLevel(risk).toUpperCase();
    el.riskBadge().className = 'risk-badge ' + getRiskLevel(risk);
    el.recommendation().textContent = getRecommendation(risk);
}

function getRiskLevel(risk) {
    if (risk < 25) return 'low';
    if (risk < 50) return 'medium';
    if (risk < 75) return 'high';
    return 'critical';
}

function getRecommendation(risk) {
    if (risk < 25) return '✅ Clear path ahead';
    if (risk < 50) return '⚠️ Proceed with caution';
    if (risk < 75) return '🚨 Reduce speed';
    return '🛑 STOP - Collision imminent!';
}

// ==================== RENDERING ====================
function render() {
    const ctx = game.ctx;
    const w = game.canvas.width;
    const h = game.canvas.height;

    // Background
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 50) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 50) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Tire tracks
    for (const track of game.tireTracks) {
        ctx.fillStyle = `rgba(30, 30, 30, ${track.alpha})`;
        ctx.beginPath();
        ctx.arc(track.x, track.y, 4, 0, Math.PI * 2);
        ctx.fill();
    }

    // Obstacles
    for (const obs of game.obstacles) {
        ctx.fillStyle = obs.color;
        ctx.fillRect(obs.x, obs.y, obs.w, obs.h);
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 2;
        ctx.strokeRect(obs.x, obs.y, obs.w, obs.h);
    }

    // Sensor beams
    drawSensorBeams();

    // Car
    drawCar();
}

function drawSensorBeams() {
    const ctx = game.ctx;
    const car = game.car;

    const beams = [
        { angle: car.angle, dist: game.sensors.front * CONFIG.pixelsPerCm, color: '#22d3ee' },
        { angle: car.angle + Math.PI, dist: game.sensors.rear * CONFIG.pixelsPerCm, color: '#a855f7' },
        { angle: car.angle - Math.PI / 2, dist: game.sensors.left * CONFIG.pixelsPerCm, color: '#f59e0b' },
        { angle: car.angle + Math.PI / 2, dist: game.sensors.right * CONFIG.pixelsPerCm, color: '#10b981' },
    ];

    for (const beam of beams) {
        const endX = car.x + Math.sin(beam.angle) * beam.dist;
        const endY = car.y - Math.cos(beam.angle) * beam.dist;

        ctx.strokeStyle = beam.color;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(car.x, car.y);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = beam.color;
        ctx.beginPath();
        ctx.arc(endX, endY, 5, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawCar() {
    const ctx = game.ctx;
    const car = game.car;

    ctx.save();
    ctx.translate(car.x, car.y);
    ctx.rotate(car.angle);

    // Body
    const grad = ctx.createLinearGradient(0, -car.height / 2, 0, car.height / 2);
    grad.addColorStop(0, '#3b82f6');
    grad.addColorStop(1, '#1d4ed8');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.roundRect(-car.width / 2, -car.height / 2, car.width, car.height, 8);
    ctx.fill();

    ctx.strokeStyle = '#60a5fa';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Windshield
    ctx.fillStyle = '#0f172a';
    ctx.beginPath();
    ctx.roundRect(-car.width / 2 + 5, -car.height / 2 + 5, car.width - 10, 15, 4);
    ctx.fill();

    // Headlights
    ctx.fillStyle = '#fef08a';
    ctx.beginPath();
    ctx.arc(-car.width / 2 + 8, -car.height / 2 + 3, 4, 0, Math.PI * 2);
    ctx.arc(car.width / 2 - 8, -car.height / 2 + 3, 4, 0, Math.PI * 2);
    ctx.fill();

    // Direction
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.moveTo(0, -car.height / 2 - 10);
    ctx.lineTo(-8, -car.height / 2);
    ctx.lineTo(8, -car.height / 2);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
}

// ==================== WEBSOCKET ====================
function connectWebSocket() {
    const url = state.isTrusted
        ? `${CONFIG.wsUrl}?device_id=${state.deviceId}&trust_token=${state.trustToken}`
        : CONFIG.wsUrl;

    try {
        state.ws = new WebSocket(url);

        state.ws.onopen = () => {
            state.connected = true;
            el.connectionDot().classList.add('connected');
            el.connectionText().textContent = 'Connected';
            el.serverStatus().textContent = 'Online';
        };

        state.ws.onclose = () => {
            state.connected = false;
            el.connectionDot().classList.remove('connected');
            el.connectionText().textContent = 'Disconnected';
            el.serverStatus().textContent = 'Offline';
            setTimeout(connectWebSocket, 3000);
        };

        state.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'connection') {
                    if (msg.authenticated) {
                        updateTrustStatus(true);
                    } else if (state.isTrusted) {
                        clearCredentials();
                        updateTrustStatus(false);
                        showModal();
                    }
                } else if (msg.type === 'sensor_update' && msg.data) {
                    state.lastCiphertext = JSON.stringify(msg.data).substring(0, 120);
                    el.ciphertextBox().textContent = '🔒 ' + state.lastCiphertext + '...';
                }
            } catch (e) { }
        };

        state.ws.onerror = () => { };

    } catch (e) {
        setTimeout(connectWebSocket, 3000);
    }
}

async function transmitSensorData() {
    if (!state.connected) return;

    const data = {
        ultrasonic_front: game.sensors.front,
        ultrasonic_left: game.sensors.left,
        ultrasonic_right: game.sensors.right,
        ultrasonic_rear: game.sensors.rear,
        temp_motor: game.car.motorTemp,
        speed: Math.abs(game.car.speed) * 10,
        position_x: game.car.x,
        position_y: game.car.y,
        heading: game.car.angle * 180 / Math.PI
    };

    try {
        const response = await fetch(`${CONFIG.serverUrl}/api/sensor-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: 'robot_car_sim_01',
                device_name: 'Robot Car',
                timestamp: new Date().toISOString(),
                sequence_number: state.packetCount,
                sensor_data: data,
                encrypted: false,
                checksum: simpleChecksum(data)
            })
        });

        if (response.ok) {
            state.packetCount++;
            el.packetCount().textContent = state.packetCount;
        }
    } catch (e) { }
}

function simpleChecksum(data) {
    const str = JSON.stringify(data);
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash = hash & hash;
    }
    return Math.abs(hash).toString(16).substring(0, 16);
}

// ==================== REGISTRATION ====================
function loadCredentials() {
    state.deviceId = localStorage.getItem(CONFIG.storageKeys.deviceId);
    state.trustToken = localStorage.getItem(CONFIG.storageKeys.trustToken);
    if (state.deviceId && state.trustToken) {
        state.isTrusted = true;
        updateTrustStatus(true);
    }

    // Pre-fill last code
    const lastCode = localStorage.getItem(CONFIG.storageKeys.lastCode);
    if (lastCode) el.regCode().value = lastCode;
}

function saveCredentials(deviceId, trustToken) {
    localStorage.setItem(CONFIG.storageKeys.deviceId, deviceId);
    localStorage.setItem(CONFIG.storageKeys.trustToken, trustToken);
    state.deviceId = deviceId;
    state.trustToken = trustToken;
    state.isTrusted = true;
}

function clearCredentials() {
    localStorage.removeItem(CONFIG.storageKeys.deviceId);
    localStorage.removeItem(CONFIG.storageKeys.trustToken);
    state.deviceId = null;
    state.trustToken = null;
    state.isTrusted = false;
}

function updateTrustStatus(trusted) {
    state.isTrusted = trusted;
    el.trustBadge().classList.toggle('trusted', trusted);
    el.trustIcon().textContent = trusted ? '✓' : '🔒';
    el.trustText().textContent = trusted ? 'Trusted' : 'Untrusted';
}

function showModal() {
    el.modal().classList.remove('hidden');
}

async function registerDevice() {
    const code = el.regCode().value.trim().toUpperCase();
    if (code.length !== 6) {
        alert('Please enter a 6-character code');
        return;
    }

    try {
        const response = await fetch(`${CONFIG.serverUrl}/api/register/device`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                registration_code: code,
                device_fingerprint: generateFingerprint()
            })
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Registration failed');
        }

        const data = await response.json();
        saveCredentials(data.device_id, data.trust_token);
        localStorage.setItem(CONFIG.storageKeys.lastCode, code);
        updateTrustStatus(true);
        el.modal().classList.add('hidden');

        // Reconnect
        if (state.ws) state.ws.close();
        connectWebSocket();

    } catch (e) {
        alert('Registration failed: ' + e.message);
    }
}

function generateFingerprint() {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('FHE', 2, 2);

    const data = `${canvas.toDataURL()}|${navigator.userAgent}|${screen.width}x${screen.height}`;
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
        hash = ((hash << 5) - hash) + data.charCodeAt(i);
        hash = hash & hash;
    }
    return Math.abs(hash).toString(16).padStart(16, '0');
}

// ==================== GAME LOOP ====================
function gameLoop() {
    updateCar();
    updateSensors();
    render();
    requestAnimationFrame(gameLoop);
}

// ==================== START ====================
window.addEventListener('load', init);
window.addEventListener('resize', () => {
    resizeCanvas();
    generateObstacles();
});
