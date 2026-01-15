# 🚗 FHE Robot Car - Quick Start

## Run the System

```bash
python run_system.py
```

That's it! This single command will:
- ✅ Start the FHE server
- ✅ Open the robot car simulation
- ✅ Open the dashboard
- ✅ Show a registration code

## 🎮 Controls

| Key | Action |
|-----|--------|
| **W** / **↑** | Forward |
| **S** / **↓** | Brake/Reverse |
| **A** / **←** | Turn Left |
| **D** / **→** | Turn Right |
| **Space** | Handbrake (Drift) |
| **R** | Reset Position |

## 📱 Mobile Access

1. Scan the QR code shown in terminal
2. Enter the **6-digit registration code** on the dashboard
3. See decrypted sensor data!

## 💡 What You'll See

- **Simulation Tab**: Drive the car, see sensor beams
- **Dashboard Tab**: 
  - Encrypted ciphertext (untrusted)
  - Real sensor values (after registering)
  - ML collision risk analysis

## 🛑 Stop the Server

Press `Ctrl+C` in the terminal.
