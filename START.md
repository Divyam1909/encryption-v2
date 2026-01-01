# 🚀 FHE IoT System - Quick Start Guide

## Option 1: Single Command (Recommended)

Run everything at once - server, ESP32 simulator, browser, QR code, AND generate a registration code:

```bash
python run_system.py --esp32 environment --open --qr --reg-code "My Phone"
```

## 🚗 Robot Car Simulation (NEW!)

Open the interactive car simulation in a separate tab:
```
http://localhost:8000/static/simulation.html
```

Drive with **WASD** or **Arrow Keys**, and see real sensor distances to obstacles!

This will:
- ✅ Start the FHE server on port 8000
- ✅ Start ESP32 simulator with environment sensors
- ✅ Open dashboard in your browser
- ✅ Show QR code for mobile access
- ✅ Generate and display a 6-digit registration code

---

## Option 2: Step by Step

### Step 1: Start the Server with Sensors
```bash
python run_system.py --esp32 environment --open --qr
```

### Step 2: Generate Registration Code (while server is running)
Open a **new terminal** and run:
```bash
python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/api/register/code', params={'device_name': 'MyPhone'}); print(r.json()['code'])"
```

Or open this URL in your browser:
```
http://localhost:8000/docs#/default/create_registration_code_api_register_code_post
```

---

## 📱 How to Register Your Device

1. When the dashboard opens, you'll see a **"Device Registration"** popup
2. Enter the **6-character code** that was displayed in the terminal
3. Click **"Register Device"**
4. You're now a **trusted device** and can see decrypted sensor data!

---

## 🔧 Useful Commands

| Command | Description |
|---------|-------------|
| `python run_system.py` | Start server only (no sensors) |
| `python run_system.py --esp32 environment` | Server + environment sensors |
| `python run_system.py --esp32 robot` | Server + robot car sensors |
| `python run_system.py --esp32 security` | Server + security sensors |
| `python run_system.py --open` | Also open browser |
| `python run_system.py --qr` | Also show QR code |
| `python run_system.py --reg-code "Name"` | Also generate registration code |

### Combine any options:
```bash
python run_system.py --esp32 environment robot --open --qr --reg-code "My Phone"
```

---

## 🔑 Get Registration Code While Server is Running

### Method 1: Python command (in new terminal)
```bash
python -c "import httpx; r = httpx.post('http://127.0.0.1:8000/api/register/code', params={'device_name': 'MyDevice'}); print('Registration Code:', r.json()['code'])"
```

### Method 2: PowerShell/curl
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/register/code?device_name=MyDevice"
```

### Method 3: Browser API Docs
Open: http://localhost:8000/docs

Click on `/api/register/code` → "Try it out" → Enter device name → Execute

---

## 📊 Access the Dashboard

| From | URL |
|------|-----|
| Laptop | http://localhost:8000/static/index.html |
| Mobile (same WiFi) | http://YOUR_IP:8000/static/index.html |

Your IP is shown when you start the server (e.g., `http://192.168.1.212:8000`)

---

## 🛑 Stop the Server

Press `Ctrl+C` in the terminal where the server is running.

---

## ✅ Quick Test Checklist

1. [ ] Run: `python run_system.py --esp32 environment --open --qr --reg-code "Test"`
2. [ ] Note the 6-digit code displayed in terminal
3. [ ] Enter the code in the browser popup
4. [ ] See real sensor values and graphs (trusted device)
5. [ ] Open in incognito/different browser WITHOUT registering
6. [ ] See only encrypted ciphertext (untrusted device)
7. [ ] Scan QR code on mobile and register to see data there too!
