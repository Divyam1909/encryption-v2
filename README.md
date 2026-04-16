# Homomorphic Encryption — IIT Dharwad Projects

This repository contains two independent projects demonstrating practical applications of **Fully Homomorphic Encryption (FHE)** using the CKKS scheme via [TenSEAL](https://github.com/OpenMined/TenSEAL).

---

## Projects

### 1. FHE Robot Car — Privacy-Preserving ML for Autonomous Vehicles

> Collision detection that runs entirely on encrypted sensor data.
> The server **never sees** plaintext values.

**Location:** [`robot-car/`](robot-car/)

**Quick start:**
```bash
cd robot-car
pip install -r requirements.txt
python run_system.py
```

Opens a browser-based robot car simulation with WASD controls. Sensor data is encrypted client-side and processed via CKKS homomorphic inference on the server.

---

### 2. Smart Grid Load Balancing — Privacy-Preserving Demand Aggregation

> Multi-agent household coordination where the coordinator computes
> total electricity demand without ever seeing individual consumption values.

**Location:** [`smart-grid-he/`](smart-grid-he/)

**Quick start:**
```bash
cd smart-grid-he
pip install -r requirements.txt
python run_demo.py              # Web dashboard
python run_demo.py --cli        # CLI demo
python run_demo.py --benchmark  # Benchmarks
```

---

## Requirements

Both projects require **Python 3.9+** and the dependencies listed in their respective `requirements.txt` files.

The primary dependency is [TenSEAL](https://github.com/OpenMined/TenSEAL) (`tenseal>=0.3.14`). Installation requires a C++ compiler. On most systems `pip install tenseal` works directly; if not, see the [TenSEAL installation guide](https://github.com/OpenMined/TenSEAL#installation).

---

## Repository Structure

```
encryption-iit-dharwad/
├── robot-car/          # FHE Robot Car (PPML encrypted inference)
│   ├── fhe_core/       # TenSEAL CKKS engine + collision risk model
│   ├── server/         # FastAPI backend
│   ├── client/         # Web simulation + dashboard
│   ├── sensors/        # ESP32 sensor simulator
│   ├── benchmarks/     # Performance benchmarks
│   ├── tests/          # Unit tests
│   ├── requirements.txt
│   └── run_system.py   # Entry point
│
├── smart-grid-he/      # Smart Grid HE (multi-agent demand aggregation)
│   ├── core/           # FHE engine, key management, novel contributions
│   ├── agents/         # Household agent implementations
│   ├── coordinator/    # Grid coordinator (honest-but-curious)
│   ├── server/         # FastAPI backend
│   ├── dashboard/      # Web UI
│   ├── evaluation/     # Benchmarks
│   ├── docs/           # Research documentation
│   ├── requirements.txt
│   └── run_demo.py     # Entry point
│
├── project-report/     # Project report (PDF + DOCX)
└── research-paper/     # LaTeX research paper and figures
```

---

## Academic Context

Both projects were developed as part of coursework at **IIT Dharwad**, demonstrating real-world applications of homomorphic encryption with original algorithmic contributions documented in [`smart-grid-he/docs/novel_contributions.md`](smart-grid-he/docs/novel_contributions.md).
