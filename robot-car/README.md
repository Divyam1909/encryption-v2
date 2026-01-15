# FHE Robot Car - Privacy-Preserving ML for Autonomous Vehicles

<p align="center">
  <img src="https://img.shields.io/badge/FHE-CKKS%20128--bit-blue" alt="CKKS 128-bit">
  <img src="https://img.shields.io/badge/PPML-Encrypted%20Inference-green" alt="PPML">
  <img src="https://img.shields.io/badge/Python-3.9+-yellow" alt="Python 3.9+">
</p>

A **Privacy-Preserving Machine Learning (PPML)** system for autonomous vehicle sensor data. Features true encrypted inference where the **server never sees your sensor data**.

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **Encrypted ML Inference** | Collision detection runs entirely on encrypted data |
| **True PPML** | Server never sees plaintext sensor values |
| **Real-time Simulation** | Interactive robot car with WASD controls |
| **Benchmarking Suite** | Compare encrypted vs plaintext performance |
| **Multi-layer Security** | FHE + ECDSA + Differential Privacy |

## 🔬 Research Novelty

This project implements **true Privacy-Preserving Machine Learning**:

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   Client    │────▶│   Server (Computes   │────▶│   Client    │
│ E(sensors)  │     │   on Ciphertext)     │     │ D(E(risk))  │
└─────────────┘     │                      │     └─────────────┘
                    │  Never sees sensors! │
                    └──────────────────────┘
```

The server performs collision risk analysis **entirely on encrypted data** using homomorphic polynomial evaluation.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the system
python run_system.py
```

## 📊 Run Benchmarks

```bash
# Run full benchmark suite
python benchmarks/benchmark.py -n 50

# Output: benchmark_results.json, benchmark_report.md
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| W / ↑ | Forward |
| S / ↓ | Brake/Reverse |
| A / ← | Turn Left |
| D / → | Turn Right |
| Space | Handbrake |
| R | Reset Position |

## 📁 Project Structure

```
encryption-iit-dharwad/
├── fhe_core/                 # Core FHE & PPML engine
│   ├── encryption_core.py    # TenSEAL CKKS implementation
│   ├── collision_risk_model.py  # 🔒 Encrypted ML Inference
│   ├── key_manager.py        # Device trust system
│   └── ...
├── benchmarks/               # Performance benchmarks
│   └── benchmark.py          # FHE benchmark suite
├── sensors/                  # Sensor simulation
├── server/                   # FastAPI backend
├── client/                   # Web dashboard
├── tests/                    # Unit tests
└── run_system.py            # Single-command launcher
```

## 🔐 Security Architecture

| Layer | Implementation |
|-------|----------------|
| **Encryption** | TenSEAL CKKS (128-bit security) |
| **ML Inference** | Polynomial evaluation on ciphertext |
| **Integrity** | SHA-256 checksums |
| **Signing** | ECDSA (SECP256R1) |
| **Privacy** | Differential Privacy (Laplace/Gaussian) |
| **Trust** | Device registration tokens |

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run PPML demo
python fhe_core/collision_risk_model.py
```

## 📈 Benchmark Results

Typical results (Intel i7, 16GB RAM):

| Operation | Time (ms) |
|-----------|-----------|
| Encryption (5 values) | 2-5 |
| Encrypted Inference | 10-30 |
| Decryption | 1-3 |
| **Overhead Factor** | ~100x |

*Note: Encrypted inference is ~100x slower than plaintext, but provides mathematical privacy guarantees.*

## 📚 References

- [TenSEAL Library](https://github.com/OpenMined/TenSEAL)
- [CKKS Scheme Paper](https://eprint.iacr.org/2016/421)
- [Privacy-Preserving ML Survey](https://arxiv.org/abs/2106.06593)

## 📄 License

MIT License
