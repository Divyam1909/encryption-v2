# 📁 Project Structure Guide

A quick reference for understanding each file and folder in this project.

---

## 📂 Root Directory

| File | Description |
|------|-------------|
| `run_system.py` | **Main launcher** - Single command to start the system. Opens browser automatically. |
| `requirements.txt` | Python dependencies. Install with `pip install -r requirements.txt`. |
| `README.md` | Project overview with PPML features and benchmarking instructions. |
| `START.md` | Quick start guide (3 lines to get running). |

---

## 📂 fhe_core/ - Core FHE & PPML Engine

The heart of the system - handles encryption and **privacy-preserving ML inference**.

| File | Description |
|------|-------------|
| `encryption_core.py` | **FHE Engine** using TenSEAL CKKS. Handles all homomorphic operations: add, multiply, sum, mean, polynomial evaluation. |
| `collision_risk_model.py` | **🔒 PPML Inference** - Collision detection runs entirely on encrypted data. Server never sees plaintext. Includes `EncryptedCollisionDetector` and `PlaintextCollisionDetector` for comparison. |
| `key_manager.py` | Device trust system - registration codes, trust tokens, secret key distribution. |
| `data_signing.py` | ECDSA digital signatures for data integrity. |
| `differential_privacy.py` | Laplace/Gaussian noise for DP guarantees. |

---

## 📂 benchmarks/ - Performance Analysis

| File | Description |
|------|-------------|
| `benchmark.py` | **Benchmark Suite** - Measures encryption time, HE operations, encrypted vs plaintext ML inference. Outputs JSON + Markdown reports. Run with `python benchmarks/benchmark.py -n 50`. |

---

## 📂 sensors/ - Robot Car Sensors

| File | Description |
|------|-------------|
| `sensors.py` | Sensor classes: `UltrasonicSensor` (distance), `TemperatureSensor` (motor temp). Includes realistic noise/drift. |
| `esp32_simulator.py` | Simulates ESP32 microcontroller collecting and encrypting sensor data. |

---

## 📂 server/ - FastAPI Backend

| File | Description |
|------|-------------|
| `server.py` | **Main server** - REST API + WebSocket. Receives encrypted data, runs PPML inference, broadcasts to clients. |
| `device_registry.py` | Tracks registered devices and trust levels. |
| `homomorphic_processor.py` | Performs HE operations on incoming encrypted data. |

---

## 📂 client/ - Web Dashboard

| File | Description |
|------|-------------|
| `index.html` | **Unified Dashboard** - Robot car simulation + encrypted data display in one mobile-friendly page. |
| `unified.js` | Combined game logic + FHE dashboard. Touch controls for mobile. |
| `simulation.html` | Legacy separate simulation page (now integrated). |
| `simulation.js` | Legacy simulation JS. |
| `styles.css` | CSS styling. |

---

## 📂 tests/ - Test Suite

| File | Description |
|------|-------------|
| `test_encryption.py` | **25 test cases** covering encryption, HE operations, sensors, and end-to-end flows. |

---

## 🔄 Data Flow (PPML)

```
1. Client encrypts sensor data locally
         ↓
2. E(sensors) sent to server
         ↓
3. Server runs inference on CIPHERTEXT
   (never sees plaintext!)
         ↓
4. Server returns E(risk_score)
         ↓
5. Only trusted clients can decrypt
```

This is true **Privacy-Preserving Machine Learning** - mathematical proof that server cannot learn sensor values.
