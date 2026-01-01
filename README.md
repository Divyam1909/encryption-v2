# Multi-Agent Homomorphic Encryption IoT System

<p align="center">
  <img src="https://img.shields.io/badge/Encryption-FHE%20(CKKS)-blue" alt="FHE CKKS">
  <img src="https://img.shields.io/badge/Security-128--bit-green" alt="128-bit Security">
  <img src="https://img.shields.io/badge/Python-3.9+-yellow" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/License-MIT-orange" alt="MIT License">
</p>

A production-ready **Fully Homomorphic Encryption (FHE)** system for secure IoT sensor data processing. This system enables computations on encrypted data without ever decrypting it, ensuring end-to-end security for sensitive sensor networks.

## 🎯 Key Features

- **Fully Homomorphic Encryption (FHE)** - Perform operations (add, multiply, mean, etc.) on encrypted data
- **TenSEAL CKKS Scheme** - Industry-standard encryption for real numbers with 128-bit security
- **Multi-Agent Architecture** - Simulated ESP32 sensors encrypt data before transmission
- **Real-Time Dashboard** - WebSocket-powered live updates with visualization
- **Trust-Based Access Control** - Only registered devices can decrypt data
- **Homomorphic Computations** - Server processes encrypted data without accessing plaintext

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   IoT Sensors   │────▶│   ESP32 Sim     │────▶│   FHE Server    │
│  (Simulated)    │     │  (Encrypts)     │     │ (Homomorphic    │
│                 │     │                 │     │   Operations)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┴────────┐
                        │                                         │
                        ▼                                         ▼
              ┌─────────────────┐                       ┌─────────────────┐
              │ Trusted Device  │                       │ Untrusted Device│
              │ (Has Secret Key)│                       │ (Public Only)   │
              │ 📊 Real Data    │                       │ 🔒 Ciphertext   │
              └─────────────────┘                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Ubuntu terminal (WSL) or Linux
- pip package manager

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd encryption-iit-dharwad
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/WSL
   # or
   .\venv\Scripts\activate  # Windows PowerShell
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the System

**Start everything with one command:**

```bash
python run_system.py --esp32 environment --open --qr
```

This will:
- ✅ Start the FHE server on port 8000
- ✅ Start an ESP32 simulator with environment sensors
- ✅ Open the dashboard in your browser
- ✅ Show a QR code for mobile access

**Generate a registration code for your phone:**

```bash
python run_system.py --esp32 environment --reg-code "My Phone"
```

The system will display a 6-character code to enter on your mobile device.

### Command Line Options

```bash
python run_system.py [OPTIONS]

Options:
  --host HOST           Server host (default: 0.0.0.0)
  --port PORT           Server port (default: 8000)
  --esp32 TYPE [TYPE...] Start ESP32 with sensor types:
                         - environment (temp, humidity, light, motion)
                         - robot (ultrasonic, motor temp)
                         - security (perimeter, motion, outdoor)
  --open                Open dashboard in browser
  --qr                  Show QR code for mobile access
  --reg-code NAME       Generate registration code for device
```

## 📱 Mobile Access

1. Make sure your phone is on the same WiFi network
2. Scan the QR code or enter the URL shown
3. Enter the registration code when prompted
4. View real-time decrypted sensor data!

**Untrusted devices** will only see encrypted ciphertext (random-looking characters).

## 🔐 How FHE Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    Homomorphic Encryption                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Plaintext: [25.5, 26.1, 25.8]  (Temperature readings)         │
│                     │                                            │
│                     ▼                                            │
│   ┌─────────────────────────────────────────────────────┐       │
│   │              ENCRYPT (with Public Key)               │       │
│   └─────────────────────────────────────────────────────┘       │
│                     │                                            │
│                     ▼                                            │
│   Ciphertext: QXhTRUFM... (unreadable without secret key)       │
│                     │                                            │
│                     ▼                                            │
│   ┌─────────────────────────────────────────────────────┐       │
│   │     COMPUTE MEAN (on encrypted data!)                │       │
│   │     Server NEVER sees actual values                  │       │
│   └─────────────────────────────────────────────────────┘       │
│                     │                                            │
│                     ▼                                            │
│   Encrypted Result: DkVNQU... (still encrypted)                 │
│                     │                                            │
│                     ▼                                            │
│   ┌─────────────────────────────────────────────────────┐       │
│   │              DECRYPT (with Secret Key)               │       │
│   │              Only trusted devices can do this        │       │
│   └─────────────────────────────────────────────────────┘       │
│                     │                                            │
│                     ▼                                            │
│   Plaintext Result: 25.8°C (correct mean!)                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
encryption-iit-dharwad/
├── fhe_core/               # Core FHE encryption engine
│   ├── __init__.py
│   ├── encryption_core.py  # TenSEAL CKKS implementation
│   └── key_manager.py      # Device trust & key distribution
│
├── sensors/                # Sensor simulation layer
│   ├── __init__.py
│   ├── sensors.py          # Sensor classes (temp, ultrasonic, etc.)
│   └── esp32_simulator.py  # ESP32 microcontroller simulation
│
├── server/                 # FastAPI server
│   ├── __init__.py
│   ├── server.py           # REST API & WebSocket endpoints
│   ├── homomorphic_processor.py  # Encrypted computations
│   └── device_registry.py  # Device authentication
│
├── client/                 # Web dashboard
│   ├── index.html          # Mobile-responsive UI
│   ├── styles.css          # Premium dark theme
│   └── app.js              # WebSocket & chart logic
│
├── tests/                  # Test suite
│   └── test_encryption.py  # Comprehensive FHE tests
│
├── requirements.txt        # Python dependencies
├── run_system.py          # Unified launcher
└── README.md              # This file
```

## 🧪 Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_encryption.py -v

# Run with coverage
python -m pytest tests/ --cov=fhe_core --cov=server
```

## 🔌 API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Server status |
| `/api/context/public` | GET | Get public FHE context (for encryption) |
| `/api/sensor-data` | POST | Receive encrypted sensor data |
| `/api/sensors` | GET | List tracked sensors |
| `/api/data/{sensor_id}` | GET | Get encrypted data for sensor |
| `/api/compute` | POST | Perform homomorphic computation |
| `/api/register/code` | POST | Generate registration code |
| `/api/register/device` | POST | Register device with code |
| `/api/authenticate` | POST | Authenticate existing device |

### WebSocket

Connect to `ws://host:port/ws` with query params:
- `device_id` - Your device ID
- `trust_token` - Your trust token

Message types:
- `sensor_update` - Real-time sensor data
- `compute_result` - Homomorphic computation results
- `ping/pong` - Heartbeat

## ⚙️ Configuration

### Encryption Parameters (encryption_core.py)

```python
FHEEngine(
    poly_modulus_degree=8192,       # Security level (8192 = 128-bit)
    coeff_mod_bit_sizes=[60, 40, 40, 60],  # Multiplication depth
    global_scale=2**40              # Precision scale
)
```

### Sensor Configuration (sensors.py)

```python
TemperatureSensor(
    ambient_temp=25.0,    # Base temperature
    variation_range=3.0,  # Natural variation
    noise_level=0.01      # Sensor noise
)
```

## 🛡️ Security Features

1. **128-bit Security Level** - Resistant to quantum attacks
2. **Checksum Verification** - Detect ciphertext tampering
3. **Rate Limiting** - Prevent brute-force attacks
4. **Device Fingerprinting** - Identify and track devices
5. **Token Expiration** - Time-limited access
6. **Master Key Encryption** - Encrypted key storage

## 🌟 Use Cases

- **Military/Secure Bases** - Encrypted sensor networks
- **Healthcare IoT** - Privacy-preserving patient monitoring
- **Industrial IoT** - Secure factory sensor data
- **Smart Home** - Private home automation
- **Banking/Finance** - Encrypted transaction processing

## 📄 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For questions or issues, please open a GitHub issue.

---

<p align="center">
  <strong>🔐 Protected by Fully Homomorphic Encryption</strong><br>
  <em>Your data, computed securely, never exposed</em>
</p>
