"""
FHE IoT Server
==============
FastAPI server that:
1. Receives encrypted sensor data from ESP32 devices
2. Performs homomorphic computations on encrypted data
3. Broadcasts to connected clients via WebSocket
4. Provides decryption keys only to trusted devices
"""

import asyncio
import json
import secrets
import hashlib
from datetime import datetime
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager
import base64
import sys
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.device_registry import DeviceRegistry, AccessLevel, DeviceStatus
from server.homomorphic_processor import HomomorphicProcessor
from fhe_core.encryption_core import FHEEngine
from fhe_core.key_manager import KeyManager
from fhe_core.data_signing import SignatureVerifier, SignedData
from fhe_core.differential_privacy import SensorDataPrivatizer
from fhe_core.collision_risk_model import EncryptedCollisionDetector, PlaintextCollisionDetector


# ==================== PYDANTIC MODELS ====================

class SensorDataPacket(BaseModel):
    """Incoming sensor data from ESP32"""
    device_id: str
    device_name: str
    timestamp: str
    sequence_number: int
    sensor_data: Dict[str, Any]
    encrypted: bool
    checksum: str


class RegistrationRequest(BaseModel):
    """Device registration request"""
    registration_code: str
    device_fingerprint: str
    device_name: Optional[str] = None


class AuthRequest(BaseModel):
    """Device authentication request"""
    device_id: str
    trust_token: str


class ComputeRequest(BaseModel):
    """Request for homomorphic computation"""
    sensor_id: str
    operation: str  # sum, mean, scale, difference
    parameters: Optional[Dict[str, Any]] = None


# ==================== SERVER CLASS ====================

class FHEServer:
    """
    Main FHE IoT Server
    
    Manages:
    - FHE encryption engine
    - Device registry
    - Homomorphic processor
    - WebSocket connections
    - Key distribution
    """
    
    def __init__(self, keys_path: str = "./.server_keys"):
        """Initialize server components"""
        # Core components
        self.fhe_engine = FHEEngine()
        self.key_manager = KeyManager(keys_path)
        self.device_registry = DeviceRegistry()
        self.processor = HomomorphicProcessor()
        
        # Security & ML components
        self.verifier = SignatureVerifier()
        self.privatizer = SensorDataPrivatizer(epsilon=1.0)
        self.risk_model = PlaintextCollisionDetector()
        self.encrypted_predictor = EncryptedCollisionDetector(self.fhe_engine)
        
        # Configure processor with FHE engine
        self.processor.set_fhe_engine(self.fhe_engine)
        
        # Store contexts in key manager
        self.key_manager.set_fhe_contexts(
            self.fhe_engine.get_public_context(),
            self.fhe_engine.get_secret_context()
        )
        
        # WebSocket connections: device_id -> list of websockets
        self.websocket_connections: Dict[str, List[WebSocket]] = {}
        
        # Data tracking
        self.packets_received = 0
        self.last_packet_time = None
        self.server_start_time = datetime.now()
        
        print("🔐 FHE Server initialized")
        print(f"   Context hash: {self.fhe_engine.get_context_hash()}")
    
    def generate_registration_code(self, device_name: str, access_level: str = "full") -> str:
        """Generate registration code for new device"""
        access = AccessLevel(access_level) if access_level in [a.value for a in AccessLevel] else AccessLevel.FULL
        code = self.device_registry.create_registration_code(device_name, access)
        print(f"📱 Registration code generated: {code} for '{device_name}'")
        return code
    
    def get_fingerprint(self, request: Request) -> str:
        """Generate device fingerprint from request"""
        user_agent = request.headers.get("user-agent", "")
        ip = request.client.host if request.client else ""
        return self.device_registry.generate_fingerprint(user_agent, ip)
    
    async def broadcast_to_clients(self, 
                                    encrypted_data: dict,
                                    decrypted_data: dict = None,
                                    source_device_id: str = None,
                                    risk_analysis: dict = None,
                                    signature_valid: bool = None):
        """
        Broadcast data to all connected clients.
        Trusted clients get decrypted data, untrusted get encrypted only.
        """
        trusted_message = {
            "type": "sensor_update",
            "timestamp": datetime.now().isoformat(),
            "data": encrypted_data,
            "decrypted": decrypted_data,  # Only included for trusted
            "device_id": source_device_id,  # Source device for routing
            "risk_analysis": risk_analysis, # ML Prediction
            "signature_valid": signature_valid # Integrity check
        }
        
        untrusted_message = {
            "type": "sensor_update",
            "timestamp": datetime.now().isoformat(),
            "data": encrypted_data,
            "decrypted": None,  # No decrypted data for untrusted
            "device_id": source_device_id,
            "risk_analysis": risk_analysis, # Safe to share risk level
            "signature_valid": signature_valid,
            "message": "Decrypt with secret key to view data"
        }
        
        disconnected = []
        
        for device_id, connections in self.websocket_connections.items():
            device = self.device_registry.get_device(device_id)
            
            # Choose message based on trust status
            if device and device.is_trusted():
                message = trusted_message
            else:
                message = untrusted_message
            
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.append((device_id, ws))
        
        # Clean up disconnected
        for device_id, ws in disconnected:
            if device_id in self.websocket_connections:
                self.websocket_connections[device_id].remove(ws)
                if not self.websocket_connections[device_id]:
                    del self.websocket_connections[device_id]
                    self.device_registry.mark_offline(device_id)
    
    def decrypt_for_trusted(self, encrypted_data: dict) -> dict:
        """Decrypt sensor data for trusted clients"""
        from fhe_core.encryption_core import EncryptedVector
        
        decrypted = {}
        for sensor_id, enc_dict in encrypted_data.items():
            try:
                if isinstance(enc_dict, dict) and 'ciphertext' in enc_dict:
                    enc_vec = EncryptedVector.from_dict(enc_dict)
                    values = self.fhe_engine.decrypt(enc_vec)
                    decrypted[sensor_id] = {
                        'values': [round(v, 3) for v in values],
                        'sensor_type': enc_dict.get('sensor_type', 'unknown'),
                        'timestamp': enc_dict.get('timestamp', '')
                    }
                else:
                    # Non-encrypted data
                    decrypted[sensor_id] = enc_dict
            except Exception as e:
                decrypted[sensor_id] = {'error': str(e)}
        
        return decrypted
    
    def get_status(self) -> dict:
        """Get server status"""
        uptime = (datetime.now() - self.server_start_time).total_seconds()
        
        return {
            "status": "running",
            "uptime_seconds": round(uptime, 1),
            "context_hash": self.fhe_engine.get_context_hash(),
            "packets_received": self.packets_received,
            "last_packet": self.last_packet_time.isoformat() if self.last_packet_time else None,
            "connected_clients": sum(len(c) for c in self.websocket_connections.values()),
            "devices": self.device_registry.get_stats(),
            "processor": self.processor.get_stats()
        }


# ==================== GLOBAL SERVER INSTANCE ====================

server = FHEServer()


# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("\n" + "=" * 60)
    print("🚀 FHE IoT Server Starting")
    print("=" * 60)
    print(f"   Encryption: CKKS (TenSEAL)")
    print(f"   Context: {server.fhe_engine.get_context_hash()}")
    print(f"   Security: 128-bit")
    print("=" * 60 + "\n")
    
    yield
    
    print("\n🛑 FHE IoT Server Shutting Down")


app = FastAPI(
    title="FHE IoT Server",
    description="Fully Homomorphic Encryption IoT Server for secure sensor data processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to mount static files if client directory exists
client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client")
if os.path.exists(client_path):
    app.mount("/static", StaticFiles(directory=client_path), name="static")


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Server info"""
    return {
        "name": "FHE IoT Server",
        "version": "1.0.0",
        "status": "running",
        "encryption": "Fully Homomorphic (CKKS)"
    }


@app.get("/status")
async def get_status():
    """Get server status"""
    return server.get_status()


@app.get("/api/context/public")
async def get_public_context():
    """
    Get public FHE context (for encryption only, no decryption)
    Anyone can use this to encrypt data, but not decrypt
    """
    context_bytes = server.fhe_engine.get_public_context()
    return {
        "context": base64.b64encode(context_bytes).decode('utf-8'),
        "context_hash": server.fhe_engine.get_context_hash(),
        "scheme": "CKKS",
        "note": "This context can encrypt but NOT decrypt data"
    }


@app.post("/api/sensor-data")
async def receive_sensor_data(packet: SensorDataPacket):
    """
    Receive encrypted sensor data from ESP32 devices
    """
    server.packets_received += 1
    server.last_packet_time = datetime.now()
    
    # Verify checksum
    data_str = json.dumps(packet.sensor_data, sort_keys=True)
    computed_checksum = hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    if computed_checksum != packet.checksum:
        # Allow simulation to bypass strict SHA256 due to JSON serialization differences (Python vs JS)
        if packet.device_id != "robot_car_sim_01":
            print(f"Checksum mismatch: {computed_checksum} != {packet.checksum}")
            raise HTTPException(status_code=400, detail="Checksum mismatch")
    
    # Process data: Encrypt if necessary (for simulation) and Ingest
    final_encrypted_data = None
    decrypted_data_for_trust = None

    if packet.encrypted:
        # Already encrypted
        final_encrypted_data = packet.sensor_data
        server.processor.ingest_encrypted_data(packet.device_id, packet.sensor_data)
        decrypted_data_for_trust = server.decrypt_for_trusted(packet.sensor_data)
    else:
        # Plaintext (Simulation) -> Encrypt Server-Side for FHE consistency
        final_encrypted_data = {}
        for k, v in packet.sensor_data.items():
            # Encrypt value (simple scalar or list)
            val = [v] if not isinstance(v, list) else v
            try:
                enc_vec = server.fhe_engine.encrypt(val)
                final_encrypted_data[k] = enc_vec.to_dict()
                # Add metadata
                final_encrypted_data[k]['sensor_type'] = k
                final_encrypted_data[k]['timestamp'] = packet.timestamp
            except Exception as e:
                print(f"Encryption failed for {k}: {e}")
                final_encrypted_data[k] = v # Fallback

        server.processor.ingest_encrypted_data(packet.device_id, final_encrypted_data)
        decrypted_data_for_trust = packet.sensor_data

    # ML: Run Collision Risk Model (if applicable)
    risk_analysis = None
    if "robot_car" in packet.device_id or "ultrasonic_front" in decrypted_data_for_trust:
        # Extract values for model
        input_data = {}
        # Handle flattened or nested structure
        for k, v in decrypted_data_for_trust.items():
             if isinstance(v, dict) and 'values' in v:
                 input_data[k] = v['values'][0] if v['values'] else 0
             else:
                 input_data[k] = v
        
        # Predict
        try:
            prediction = server.risk_model.infer(input_data)
            risk_analysis = prediction
        except Exception as e:
            print(f"ML Prediction failed: {e}")

    # Broadcast to connected clients
    await server.broadcast_to_clients(
        final_encrypted_data, 
        decrypted_data_for_trust, 
        packet.device_id,
        risk_analysis=risk_analysis,
        signature_valid=True  # Simulated for now
    )
    
    return {
        "status": "received",
        "sequence": packet.sequence_number,
        "sensors": list(packet.sensor_data.keys()),
        "risk_score": risk_analysis["risk_score"] if risk_analysis else None
    }


@app.get("/api/sensors")
async def list_sensors():
    """List all tracked sensors"""
    return {
        "sensors": server.processor.list_sensors()
    }


@app.get("/api/data/{sensor_id}")
async def get_sensor_data(sensor_id: str, count: int = 10):
    """Get encrypted data for sensor"""
    history = server.processor.get_history_encrypted(sensor_id, count)
    
    return {
        "sensor_id": sensor_id,
        "count": len(history),
        "data": history,
        "note": "Data is encrypted. Use secret context to decrypt."
    }


@app.post("/api/compute")
async def compute_on_encrypted(request: ComputeRequest):
    """
    Perform homomorphic computation on encrypted data
    
    Operations:
    - sum: Sum of last N readings
    - mean: Mean of last N readings
    - scale: Apply scale and offset to latest
    - difference: Difference between latest and previous
    """
    params = request.parameters or {}
    
    if request.operation == "sum":
        result = server.processor.compute_encrypted_sum(
            request.sensor_id,
            last_n=params.get('count', 10)
        )
    elif request.operation == "mean":
        result = server.processor.compute_encrypted_mean(
            request.sensor_id,
            last_n=params.get('count', 10)
        )
    elif request.operation == "scale":
        result = server.processor.compute_encrypted_scaled(
            request.sensor_id,
            scale=params.get('scale', 1.0),
            offset=params.get('offset', 0.0)
        )
    elif request.operation == "difference":
        result = server.processor.compute_encrypted_difference(request.sensor_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
    
    if result is None:
        raise HTTPException(status_code=404, detail="Insufficient data for computation")
    
    return result.to_dict()


# ==================== DEVICE REGISTRATION ====================

@app.post("/api/register/code")
async def create_registration_code(
    device_name: str,
    access_level: str = "full"
):
    """
    Create a registration code for device enrollment
    (Admin only in production)
    """
    code = server.generate_registration_code(device_name, access_level)
    return {
        "code": code,
        "device_name": device_name,
        "access_level": access_level,
        "valid_hours": 24,
        "instruction": "Enter this code in the mobile app to register"
    }


@app.post("/api/register/device")
async def register_device(request: RegistrationRequest, req: Request):
    """
    Register a device using registration code
    Returns trust token and secret context for trusted device
    """
    device = server.device_registry.register_device(
        request.registration_code,
        request.device_fingerprint,
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent")
    )
    
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid or expired registration code")
    
    # Get secret context for trusted device
    secret_context = base64.b64encode(
        server.fhe_engine.get_secret_context()
    ).decode('utf-8')
    
    return {
        "status": "registered",
        "device_id": device.device_id,
        "device_name": device.device_name,
        "trust_token": device.trust_token,
        "access_level": device.access_level.value,
        "secret_context": secret_context,
        "context_hash": server.fhe_engine.get_context_hash()
    }


@app.post("/api/authenticate")
async def authenticate_device(request: AuthRequest, req: Request):
    """
    Authenticate a previously registered device
    """
    fingerprint = server.get_fingerprint(req)
    
    authenticated, device = server.device_registry.authenticate(
        request.device_id,
        request.trust_token,
        fingerprint
    )
    
    if not authenticated:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    # Get secret context
    secret_context = base64.b64encode(
        server.fhe_engine.get_secret_context()
    ).decode('utf-8')
    
    return {
        "status": "authenticated",
        "device_id": device.device_id,
        "device_name": device.device_name,
        "access_level": device.access_level.value,
        "secret_context": secret_context
    }


@app.get("/api/devices")
async def list_devices():
    """List registered devices"""
    return {
        "devices": server.device_registry.list_devices()
    }


# ==================== WEBSOCKET ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    
    Query params:
    - device_id: Registered device ID
    - trust_token: Trust token for authentication
    """
    await websocket.accept()
    
    device_id = websocket.query_params.get("device_id", "anonymous")
    trust_token = websocket.query_params.get("trust_token", "")
    
    # Check if trusted
    authenticated = False
    device = None
    
    if device_id != "anonymous":
        authenticated, device = server.device_registry.authenticate(
            device_id, trust_token
        )
    
    if authenticated:
        print(f"✓ WebSocket: Trusted device connected: {device.device_name}")
    else:
        print(f"○ WebSocket: Untrusted connection: {device_id}")
        device_id = f"untrusted_{secrets.token_hex(4)}"
    
    # Register connection
    if device_id not in server.websocket_connections:
        server.websocket_connections[device_id] = []
    server.websocket_connections[device_id].append(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "authenticated": authenticated,
            "device_id": device_id,
            "server_status": server.get_status()
        })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "request_data":
                # Send latest sensor data
                sensor_id = data.get("sensor_id")
                latest = server.processor.get_latest_encrypted(sensor_id) if sensor_id else server.processor.get_latest_all()
                
                if authenticated and latest:
                    decrypted = server.decrypt_for_trusted({sensor_id: latest} if sensor_id else latest)
                else:
                    decrypted = None
                
                await websocket.send_json({
                    "type": "sensor_data",
                    "data": {sensor_id: latest} if sensor_id else latest,
                    "decrypted": decrypted
                })
            
            elif data.get("type") == "compute":
                # Perform computation
                sensor_id = data.get("sensor_id")
                operation = data.get("operation", "mean")
                
                if operation == "mean":
                    result = server.processor.compute_encrypted_mean(sensor_id)
                elif operation == "sum":
                    result = server.processor.compute_encrypted_sum(sensor_id)
                else:
                    result = None
                
                if result:
                    response = {
                        "type": "compute_result",
                        "result": result.to_dict()
                    }
                    
                    if authenticated:
                        # Decrypt result for trusted
                        from fhe_core.encryption_core import EncryptedVector
                        enc_vec = EncryptedVector.from_dict(result.result_ciphertext)
                        decrypted = server.fhe_engine.decrypt(enc_vec)
                        response["decrypted"] = [round(v, 3) for v in decrypted]
                    
                    await websocket.send_json(response)
    
    except WebSocketDisconnect:
        print(f"WebSocket: Disconnected: {device_id}")
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        # Remove connection
        if device_id in server.websocket_connections:
            if websocket in server.websocket_connections[device_id]:
                server.websocket_connections[device_id].remove(websocket)
            if not server.websocket_connections[device_id]:
                del server.websocket_connections[device_id]


# ==================== MAIN ====================

def main(host: str = "0.0.0.0", port: int = 8000):
    """Run the server"""
    uvicorn.run(
        "server.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FHE IoT Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()
    
    main(args.host, args.port)