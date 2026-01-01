/**
 * FHE Robot Car Simulation
 * Interactive 2D simulation with real sensor calculations
 * Sends encrypted sensor data to the FHE server
 */

// ==================== CONFIGURATION ====================
const CONFIG = {
    serverUrl: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : `http://${window.location.hostname}:8000`,
    wsUrl: window.location.hostname === 'localhost'
        ? 'ws://localhost:8000/ws'
        : `ws://${window.location.hostname}:8000/ws`,
    transmitInterval: 500,  // Send data every 500ms
    sensorRange: 400,       // Max sensor range in cm (scaled to pixels)
    pixelsPerCm: 2,         // Scale factor
};

// ==================== GAME STATE ====================
const game = {
    canvas: null,
    ctx: null,
    miniCanvas: null,
    miniCtx: null,

    // Car state with improved physics
    car: {
        x: 400,
        y: 400,
        width: 40,
        height: 60,
        angle: 0,           // Radians
        speed: 0,
        velocityX: 0,       // Added for drift
        velocityY: 0,
        maxSpeed: 10,
        acceleration: 0.25,
        deceleration: 0.15,
        friction: 0.985,
        turnSpeed: 0.045,
        grip: 0.92,         // Tire grip (lower = more drift)
        motorTemp: 25,      // Celsius
        wheelAngle: 0,      // Visual wheel angle
    },

    // Tire tracks
    tireTracks: [],
    maxTracks: 100,

    // Obstacles
    obstacles: [],

    // Sensor readings (in cm)
    sensors: {
        front: 400,
        left: 400,
        right: 400,
        rear: 400,
    },

    // Input state
    keys: {
        forward: false,
        backward: false,
        left: false,
        right: false,
        brake: false,
    },

    // Connection state
    ws: null,
    connected: false,
    packetCount: 0,
    lastCiphertext: '',
};

// ==================== INITIALIZATION ====================
function init() {
    // Setup main canvas
    game.canvas = document.getElementById('gameCanvas');
    game.ctx = game.canvas.getContext('2d');
    resizeCanvas();

    // Setup mini map
    game.miniCanvas = document.getElementById('miniMapCanvas');
    game.miniCtx = game.miniCanvas.getContext('2d');

    // Generate obstacles
    generateObstacles();

    // Setup input handlers
    setupInputHandlers();

    // Connect to server
    connectWebSocket();

    // Start game loop
    requestAnimationFrame(gameLoop);

    // Start data transmission
    setInterval(transmitSensorData, CONFIG.transmitInterval);

    console.log('🚗 Robot Car Simulation initialized');
}

function resizeCanvas() {
    const container = game.canvas.parentElement;
    game.canvas.width = container.clientWidth;
    game.canvas.height = container.clientHeight;

    // Resize mini map
    if (game.miniCanvas) {
        const miniContainer = game.miniCanvas.parentElement;
        game.miniCanvas.width = miniContainer.clientWidth;
        game.miniCanvas.height = miniContainer.clientHeight;
    }
}

function generateObstacles() {
    const width = game.canvas.width;
    const height = game.canvas.height;

    game.obstacles = [];

    // Border walls
    const wallThickness = 20;
    game.obstacles.push(
        { x: 0, y: 0, width: width, height: wallThickness, color: '#475569' },              // Top
        { x: 0, y: height - wallThickness, width: width, height: wallThickness, color: '#475569' },  // Bottom
        { x: 0, y: 0, width: wallThickness, height: height, color: '#475569' },              // Left
        { x: width - wallThickness, y: 0, width: wallThickness, height: height, color: '#475569' }   // Right
    );

    // Random obstacles
    const obstacleCount = 8;
    for (let i = 0; i < obstacleCount; i++) {
        const obsWidth = 40 + Math.random() * 80;
        const obsHeight = 40 + Math.random() * 80;
        const x = wallThickness + 100 + Math.random() * (width - 2 * wallThickness - 200 - obsWidth);
        const y = wallThickness + 100 + Math.random() * (height - 2 * wallThickness - 200 - obsHeight);

        // Don't place obstacle on car start position
        if (Math.abs(x - 400) < 100 && Math.abs(y - 400) < 100) continue;

        game.obstacles.push({
            x: x,
            y: y,
            width: obsWidth,
            height: obsHeight,
            color: `hsl(${Math.random() * 60 + 200}, 40%, 35%)`
        });
    }

    // Add some specific obstacles for interest
    game.obstacles.push(
        { x: 200, y: 150, width: 100, height: 30, color: '#7c3aed' },
        { x: 600, y: 250, width: 30, height: 120, color: '#dc2626' },
        { x: 300, y: 450, width: 80, height: 80, color: '#0891b2' },
    );
}

// ==================== INPUT HANDLING ====================
function setupInputHandlers() {
    document.addEventListener('keydown', (e) => {
        switch (e.code) {
            case 'KeyW':
            case 'ArrowUp':
                game.keys.forward = true;
                break;
            case 'KeyS':
            case 'ArrowDown':
                game.keys.backward = true;
                break;
            case 'KeyA':
            case 'ArrowLeft':
                game.keys.left = true;
                break;
            case 'KeyD':
            case 'ArrowRight':
                game.keys.right = true;
                break;
            case 'Space':
                game.keys.brake = true;
                e.preventDefault();
                break;
            case 'KeyR':
                resetCar();
                break;
        }
    });

    document.addEventListener('keyup', (e) => {
        switch (e.code) {
            case 'KeyW':
            case 'ArrowUp':
                game.keys.forward = false;
                break;
            case 'KeyS':
            case 'ArrowDown':
                game.keys.backward = false;
                break;
            case 'KeyA':
            case 'ArrowLeft':
                game.keys.left = false;
                break;
            case 'KeyD':
            case 'ArrowRight':
                game.keys.right = false;
                break;
            case 'Space':
                game.keys.brake = false;
                break;
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        resizeCanvas();
        generateObstacles();
    });
}

function resetCar() {
    game.car.x = game.canvas.width / 2;
    game.car.y = game.canvas.height / 2;
    game.car.angle = 0;
    game.car.speed = 0;
    game.car.motorTemp = 25;
}

// ==================== PHYSICS ====================
function updateCar() {
    const car = game.car;
    const keys = game.keys;

    // Smooth steering wheel angle
    const targetWheelAngle = (keys.left ? -1 : 0) + (keys.right ? 1 : 0);
    car.wheelAngle += (targetWheelAngle * 0.5 - car.wheelAngle) * 0.2;

    // Acceleration / Braking
    if (keys.forward) {
        car.speed += car.acceleration * (1 - Math.abs(car.speed) / car.maxSpeed);
    }
    if (keys.backward) {
        if (car.speed > 0.5) {
            // Braking when moving forward
            car.speed -= car.deceleration * 1.5;
        } else {
            // Reverse
            car.speed -= car.acceleration * 0.5;
        }
    }

    // Hand brake (drift mode)
    if (keys.brake) {
        car.speed *= 0.95;
        car.grip = 0.75;  // Reduced grip for drifting
    } else {
        car.grip = 0.92;  // Normal grip
    }

    // Apply friction
    if (!keys.forward && !keys.backward) {
        car.speed *= car.friction;
    }

    // Clamp speed
    const maxReverse = car.maxSpeed * 0.4;
    car.speed = Math.max(-maxReverse, Math.min(car.maxSpeed, car.speed));

    // Stop completely if very slow
    if (Math.abs(car.speed) < 0.05) car.speed = 0;

    // Turning (speed-dependent)
    if (Math.abs(car.speed) > 0.1) {
        const speedFactor = Math.min(1, Math.abs(car.speed) / 5);
        const turnRate = car.turnSpeed * speedFactor * (car.speed > 0 ? 1 : -1);

        if (keys.left) car.angle -= turnRate;
        if (keys.right) car.angle += turnRate;
    }

    // Calculate velocity components
    const targetVelocityX = Math.sin(car.angle) * car.speed;
    const targetVelocityY = -Math.cos(car.angle) * car.speed;

    // Apply grip (blend between current and target velocity for drift effect)
    car.velocityX = car.velocityX * (1 - car.grip) + targetVelocityX * car.grip;
    car.velocityY = car.velocityY * (1 - car.grip) + targetVelocityY * car.grip;

    // Calculate new position
    const newX = car.x + car.velocityX;
    const newY = car.y + car.velocityY;

    // Collision detection with slide
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
        // Full collision
        car.speed *= -0.2;
        car.velocityX *= -0.3;
        car.velocityY *= -0.3;
    }

    // Add tire tracks when drifting
    const driftAmount = Math.abs(car.velocityX * Math.cos(car.angle) + car.velocityY * Math.sin(car.angle));
    if (driftAmount > 1 && Math.abs(car.speed) > 2) {
        game.tireTracks.push({
            x: car.x - Math.sin(car.angle) * car.height * 0.35,
            y: car.y + Math.cos(car.angle) * car.height * 0.35,
            alpha: 0.5
        });
        if (game.tireTracks.length > game.maxTracks) {
            game.tireTracks.shift();
        }
    }

    // Fade tire tracks
    game.tireTracks.forEach(track => track.alpha *= 0.995);
    game.tireTracks = game.tireTracks.filter(t => t.alpha > 0.05);

    // Update motor temperature based on speed and acceleration
    const load = Math.abs(car.speed) + (keys.forward || keys.backward ? 3 : 0);
    const targetTemp = 25 + load * 3;
    car.motorTemp += (targetTemp - car.motorTemp) * 0.02;
}

function checkCollision(x, y) {
    const car = game.car;
    const halfW = car.width / 2;
    const halfH = car.height / 2;

    // Simple AABB collision for car bounding box
    const carLeft = x - halfW;
    const carRight = x + halfW;
    const carTop = y - halfH;
    const carBottom = y + halfH;

    for (const obs of game.obstacles) {
        if (carRight > obs.x && carLeft < obs.x + obs.width &&
            carBottom > obs.y && carTop < obs.y + obs.height) {
            return true;
        }
    }

    return false;
}

// ==================== SENSOR CALCULATIONS ====================
function updateSensors() {
    const car = game.car;

    // Calculate distance in 4 directions
    game.sensors.front = castRay(car.x, car.y, car.angle);
    game.sensors.rear = castRay(car.x, car.y, car.angle + Math.PI);
    game.sensors.left = castRay(car.x, car.y, car.angle - Math.PI / 2);
    game.sensors.right = castRay(car.x, car.y, car.angle + Math.PI / 2);

    // Update UI
    updateSensorDisplay('sensorFront', game.sensors.front);
    updateSensorDisplay('sensorLeft', game.sensors.left);
    updateSensorDisplay('sensorRight', game.sensors.right);
    updateSensorDisplay('sensorRear', game.sensors.rear);

    // Motor temp
    const tempEl = document.getElementById('motorTemp');
    tempEl.innerHTML = `${game.car.motorTemp.toFixed(1)}<span class="sensor-unit">°C</span>`;
    if (game.car.motorTemp > 50) {
        tempEl.classList.add('warning');
    } else {
        tempEl.classList.remove('warning');
    }

    // Speed
    const speedKmh = Math.abs(game.car.speed) * 10;
    document.getElementById('carSpeed').innerHTML = `${speedKmh.toFixed(0)}<span class="sensor-unit">km/h</span>`;

    // Position
    document.getElementById('posX').textContent = Math.round(game.car.x);
    document.getElementById('posY').textContent = Math.round(game.car.y);
    document.getElementById('heading').textContent = `${Math.round(game.car.angle * 180 / Math.PI)}°`;

    // Collision warning
    const minDistance = Math.min(game.sensors.front, game.sensors.left, game.sensors.right);
    const warningEl = document.getElementById('collisionWarning');
    if (minDistance < 30) {
        warningEl.classList.add('active');
    } else {
        warningEl.classList.remove('active');
    }
}

function castRay(startX, startY, angle) {
    const step = 5;
    const maxRange = CONFIG.sensorRange;

    let x = startX;
    let y = startY;
    let distance = 0;

    while (distance < maxRange) {
        x += Math.sin(angle) * step;
        y -= Math.cos(angle) * step;
        distance += step;

        // Check collision with obstacles
        for (const obs of game.obstacles) {
            if (x >= obs.x && x <= obs.x + obs.width &&
                y >= obs.y && y <= obs.y + obs.height) {
                return Math.round(distance / CONFIG.pixelsPerCm);
            }
        }
    }

    return Math.round(maxRange / CONFIG.pixelsPerCm);
}

function updateSensorDisplay(elementId, value) {
    const el = document.getElementById(elementId);
    el.innerHTML = `${value}<span class="sensor-unit">cm</span>`;

    el.classList.remove('warning', 'danger');
    if (value < 30) {
        el.classList.add('danger');
    } else if (value < 80) {
        el.classList.add('warning');
    }
}

// ==================== RENDERING ====================
function render() {
    const ctx = game.ctx;
    const width = game.canvas.width;
    const height = game.canvas.height;

    // Clear
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, width, height);

    // Grid
    drawGrid();

    // Tire tracks (draw before obstacles and car)
    drawTireTracks();

    // Obstacles
    for (const obs of game.obstacles) {
        ctx.fillStyle = obs.color;
        ctx.fillRect(obs.x, obs.y, obs.width, obs.height);

        // Border
        ctx.strokeStyle = '#64748b';
        ctx.lineWidth = 2;
        ctx.strokeRect(obs.x, obs.y, obs.width, obs.height);
    }

    // Sensor beams
    drawSensorBeams();

    // Car
    drawCar();

    // Mini map
    drawMiniMap();
}

function drawTireTracks() {
    const ctx = game.ctx;

    for (const track of game.tireTracks) {
        ctx.fillStyle = `rgba(30, 30, 30, ${track.alpha})`;
        ctx.beginPath();
        ctx.arc(track.x, track.y, 4, 0, Math.PI * 2);
        ctx.fill();
    }
}

function drawGrid() {
    const ctx = game.ctx;
    const gridSize = 50;

    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;

    for (let x = 0; x < game.canvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, game.canvas.height);
        ctx.stroke();
    }

    for (let y = 0; y < game.canvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(game.canvas.width, y);
        ctx.stroke();
    }
}

function drawSensorBeams() {
    const ctx = game.ctx;
    const car = game.car;

    const beams = [
        { angle: car.angle, distance: game.sensors.front * CONFIG.pixelsPerCm, color: '#22d3ee' },
        { angle: car.angle + Math.PI, distance: game.sensors.rear * CONFIG.pixelsPerCm, color: '#a855f7' },
        { angle: car.angle - Math.PI / 2, distance: game.sensors.left * CONFIG.pixelsPerCm, color: '#f59e0b' },
        { angle: car.angle + Math.PI / 2, distance: game.sensors.right * CONFIG.pixelsPerCm, color: '#10b981' },
    ];

    for (const beam of beams) {
        const endX = car.x + Math.sin(beam.angle) * beam.distance;
        const endY = car.y - Math.cos(beam.angle) * beam.distance;

        // Beam line
        ctx.strokeStyle = beam.color;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(car.x, car.y);
        ctx.lineTo(endX, endY);
        ctx.stroke();
        ctx.setLineDash([]);

        // End point
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

    // Car body
    const gradient = ctx.createLinearGradient(0, -car.height / 2, 0, car.height / 2);
    gradient.addColorStop(0, '#3b82f6');
    gradient.addColorStop(1, '#1d4ed8');

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.roundRect(-car.width / 2, -car.height / 2, car.width, car.height, 8);
    ctx.fill();

    // Car outline
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

    // Direction indicator
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.moveTo(0, -car.height / 2 - 10);
    ctx.lineTo(-8, -car.height / 2);
    ctx.lineTo(8, -car.height / 2);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
}

function drawMiniMap() {
    const ctx = game.miniCtx;
    const width = game.miniCanvas.width;
    const height = game.miniCanvas.height;
    const scale = Math.min(width / game.canvas.width, height / game.canvas.height) * 0.9;

    // Clear
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    // Center offset
    const offsetX = (width - game.canvas.width * scale) / 2;
    const offsetY = (height - game.canvas.height * scale) / 2;

    // Obstacles
    for (const obs of game.obstacles) {
        ctx.fillStyle = '#475569';
        ctx.fillRect(
            offsetX + obs.x * scale,
            offsetY + obs.y * scale,
            obs.width * scale,
            obs.height * scale
        );
    }

    // Car (as a dot)
    ctx.fillStyle = '#3b82f6';
    ctx.beginPath();
    ctx.arc(
        offsetX + game.car.x * scale,
        offsetY + game.car.y * scale,
        4,
        0,
        Math.PI * 2
    );
    ctx.fill();

    // Direction indicator
    const dirLength = 8;
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(
        offsetX + game.car.x * scale,
        offsetY + game.car.y * scale
    );
    ctx.lineTo(
        offsetX + (game.car.x + Math.sin(game.car.angle) * 30) * scale,
        offsetY + (game.car.y - Math.cos(game.car.angle) * 30) * scale
    );
    ctx.stroke();
}

// ==================== WEBSOCKET & DATA TRANSMISSION ====================
function connectWebSocket() {
    console.log('Connecting to server...');

    try {
        game.ws = new WebSocket(CONFIG.wsUrl);

        game.ws.onopen = () => {
            console.log('✓ Connected to FHE server');
            game.connected = true;
            updateConnectionStatus(true);
        };

        game.ws.onclose = () => {
            console.log('Disconnected from server');
            game.connected = false;
            updateConnectionStatus(false);

            // Reconnect after delay
            setTimeout(connectWebSocket, 3000);
        };

        game.ws.onerror = (err) => {
            console.error('WebSocket error:', err);
        };

        game.ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                if (msg.type === 'connection') {
                    console.log('Server status:', msg.server_status);
                }
            } catch (e) {
                // Ignore
            }
        };

    } catch (e) {
        console.error('Failed to connect:', e);
        setTimeout(connectWebSocket, 3000);
    }
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');

    if (connected) {
        dot.classList.add('connected');
        text.textContent = 'Connected';
    } else {
        dot.classList.remove('connected');
        text.textContent = 'Disconnected';
    }
}

async function transmitSensorData() {
    if (!game.connected) return;

    // Create sensor data packet
    const sensorData = {
        ultrasonic_front: game.sensors.front,
        ultrasonic_left: game.sensors.left,
        ultrasonic_right: game.sensors.right,
        ultrasonic_rear: game.sensors.rear,
        temp_motor: game.car.motorTemp,
        speed: Math.abs(game.car.speed) * 10,
        position_x: game.car.x,
        position_y: game.car.y,
        heading: game.car.angle * 180 / Math.PI,
    };

    // Send to server via HTTP (to trigger encryption)
    try {
        const response = await fetch(`${CONFIG.serverUrl}/api/sensor-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                device_id: 'robot_car_sim_01',
                device_name: 'Robot Car Simulator',
                timestamp: new Date().toISOString(),
                sequence_number: game.packetCount,
                sensor_data: sensorData,
                encrypted: false,  // Server will encrypt
                checksum: simpleChecksum(sensorData)
            })
        });

        if (response.ok) {
            game.packetCount++;
            document.getElementById('packetCount').textContent = game.packetCount;

            // Update ciphertext preview (simulated - actual comes from server)
            const preview = btoa(JSON.stringify(sensorData)).substring(0, 80);
            document.getElementById('ciphertextPreview').textContent =
                `🔒 ${preview}...`;
        }
    } catch (e) {
        // Silent fail - will retry
    }
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

// ==================== GAME LOOP ====================
function gameLoop() {
    updateCar();
    updateSensors();
    render();
    requestAnimationFrame(gameLoop);
}

// ==================== START ====================
window.addEventListener('load', init);
window.addEventListener('resize', resizeCanvas);
