"""
FastAPI Server for Smart Grid HE System
========================================
Provides REST API and WebSocket for the privacy-preserving smart grid.

Endpoints:
- GET /status - System status
- GET /agents - List all agents
- POST /round - Trigger computation round
- WS /ws - Real-time updates

The server runs the coordinator logic and provides
the dashboard with real-time encrypted data flow.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from core.fhe_engine import SmartGridFHE
from core.security_logger import SecurityLogger
from agents.agent_manager import AgentManager
from agents.demand_generator import LoadProfile
from coordinator.grid_coordinator import GridCoordinator
from coordinator.load_balancer import UtilityDecisionMaker


class RoundResponse(BaseModel):
    """Response for a computation round"""
    round_number: int
    agent_count: int
    total_demand_kw: float
    average_demand_kw: float
    utilization_percent: float
    action: str
    reduction_factor: float
    computation_time_ms: float
    encrypted_total_preview: str
    plaintext_total_kw: float  # For comparison
    error_kw: float


class SystemConfig(BaseModel):
    """System configuration"""
    agent_count: int = 25
    grid_capacity_kw: float = 100.0


class SmartGridServer:
    """
    Main server for the Smart Grid HE system.
    
    Manages:
    - FHE key generation
    - Agent lifecycle
    - Coordinator operations
    - WebSocket connections for real-time updates
    """
    
    def __init__(self, 
                 agent_count: int = 25,
                 grid_capacity_kw: float = 100.0):
        """
        Initialize the server.
        
        Args:
            agent_count: Number of household agents
            grid_capacity_kw: Total grid capacity
        """
        self.agent_count = agent_count
        self.grid_capacity_kw = grid_capacity_kw
        
        # Components (initialized in start)
        self.utility_fhe: Optional[SmartGridFHE] = None
        self.logger: Optional[SecurityLogger] = None
        self.agent_manager: Optional[AgentManager] = None
        self.coordinator: Optional[GridCoordinator] = None
        self.utility: Optional[UtilityDecisionMaker] = None
        
        # State
        self.round_count = 0
        self.is_running = False
        self.auto_run = False
        self.auto_interval = 3.0  # seconds
        
        # WebSocket clients
        self.websocket_clients: List[WebSocket] = []
        
        # History for dashboard
        self.history: List[Dict] = []
    
    def initialize(self):
        """Initialize all components"""
        print("Initializing Smart Grid HE System...")
        
        # Create FHE engine (utility company)
        print("  Generating FHE keys...")
        self.utility_fhe = SmartGridFHE()
        public_context = self.utility_fhe.get_public_context()
        secret_context = self.utility_fhe.get_secret_context()
        
        # Security logger
        self.logger = SecurityLogger()
        
        # Agent manager with public context
        print(f"  Creating {self.agent_count} household agents...")
        self.agent_manager = AgentManager(public_context, self.logger)
        self.agent_manager.create_agents(self.agent_count)
        
        # Coordinator (untrusted, public context only)
        print("  Initializing coordinator...")
        self.coordinator = GridCoordinator(
            public_context,
            self.grid_capacity_kw,
            self.logger
        )
        
        # Utility decision maker (trusted, secret context)
        self.utility = UtilityDecisionMaker(
            secret_context,
            self.grid_capacity_kw,
            self.logger
        )
        
        print(f"  System ready! Context hash: {self.utility_fhe.get_context_hash()}")
        self.is_running = True
    
    def run_round(self) -> RoundResponse:
        """Run one computation round"""
        if not self.is_running:
            raise RuntimeError("System not initialized")
        
        self.round_count += 1
        
        # Collect encrypted demands from all agents
        encrypted_demands = self.agent_manager.collect_encrypted_demands()
        
        # Get plaintext for comparison (only for evaluation)
        plaintext_demands = self.agent_manager.get_plaintext_demands_for_comparison()
        plaintext_total = sum(plaintext_demands.values())
        plaintext_avg = plaintext_total / len(plaintext_demands)
        
        # Process on coordinator (encrypted)
        result = self.coordinator.process_round(encrypted_demands)
        
        # Utility makes decision by decrypting aggregates
        decision = self.utility.make_decision(
            result.encrypted_total,
            result.agent_count
        )
        self.coordinator.receive_decision(decision)
        
        # Get decrypted average
        decrypted_avg = self.utility.decrypt_average(result.encrypted_average)
        
        # Apply load balancing
        if decision.reduction_factor < 1.0:
            self.agent_manager.broadcast_load_balance(decision.reduction_factor)
        
        # Calculate error
        error = abs(decision.total_demand_kw - plaintext_total)
        
        response = RoundResponse(
            round_number=self.round_count,
            agent_count=result.agent_count,
            total_demand_kw=round(decision.total_demand_kw, 4),
            average_demand_kw=round(decrypted_avg, 4),
            utilization_percent=round(decision.utilization_percent, 2),
            action=decision.action.value,
            reduction_factor=decision.reduction_factor,
            computation_time_ms=round(result.computation_time_ms, 2),
            encrypted_total_preview=result.encrypted_total.get_display_ciphertext(50),
            plaintext_total_kw=round(plaintext_total, 4),
            error_kw=round(error, 8)
        )
        
        # Store in history
        self.history.append({
            'round': self.round_count,
            'timestamp': datetime.now().isoformat(),
            **response.model_dump()
        })
        
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            'is_running': self.is_running,
            'round_count': self.round_count,
            'agent_count': self.agent_manager.get_agent_count() if self.agent_manager else 0,
            'grid_capacity_kw': self.grid_capacity_kw,
            'auto_run': self.auto_run,
            'coordinator_stats': self.coordinator.get_stats() if self.coordinator else None,
            'security_audit': self.logger.generate_audit_report() if self.logger else None
        }
    
    def get_agents(self) -> List[Dict]:
        """Get all agent statuses"""
        if not self.agent_manager:
            return []
        return [s.to_dict() for s in self.agent_manager.get_all_statuses()]
    
    def get_security_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent security logs"""
        if not self.logger:
            return []
        return self.logger.to_display_format(limit)
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get computation history"""
        return self.history[-limit:]
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all WebSocket clients"""
        if not self.websocket_clients:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for client in self.websocket_clients:
            try:
                await client.send_text(message_json)
            except:
                disconnected.append(client)
        
        for client in disconnected:
            self.websocket_clients.remove(client)
    
    async def auto_run_loop(self):
        """Background loop for auto-running rounds"""
        while self.auto_run:
            try:
                response = self.run_round()
                await self.broadcast({
                    'type': 'round_complete',
                    'data': response.model_dump()
                })
            except Exception as e:
                print(f"Auto-run error: {e}")
            
            await asyncio.sleep(self.auto_interval)


# Create global server instance
server = SmartGridServer()


# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    server.initialize()
    yield
    server.is_running = False


app = FastAPI(
    title="Privacy-Preserving Smart Grid",
    description="Smart grid load balancing using homomorphic encryption",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/static", StaticFiles(directory=dashboard_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve dashboard"""
    html_path = os.path.join(dashboard_path, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse("<h1>Smart Grid HE System</h1><p>Dashboard not found</p>")


@app.get("/styles.css")
async def serve_css():
    """Serve CSS file"""
    css_path = os.path.join(dashboard_path, "styles.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    return HTMLResponse("/* CSS not found */", status_code=404)


@app.get("/dashboard.js")
async def serve_js():
    """Serve JavaScript file"""
    js_path = os.path.join(dashboard_path, "dashboard.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    return HTMLResponse("// JS not found", status_code=404)




@app.get("/status")
async def get_status():
    """Get system status"""
    return server.get_status()


@app.get("/agents")
async def get_agents():
    """Get all agent statuses"""
    return server.get_agents()


@app.post("/round")
async def run_round():
    """Run one computation round"""
    try:
        response = server.run_round()
        
        # Broadcast to WebSocket clients
        await server.broadcast({
            'type': 'round_complete',
            'data': response.model_dump()
        })
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auto/{action}")
async def toggle_auto(action: str):
    """Start/stop auto-run mode"""
    if action == "start":
        if not server.auto_run:
            server.auto_run = True
            asyncio.create_task(server.auto_run_loop())
        return {"auto_run": True}
    elif action == "stop":
        server.auto_run = False
        return {"auto_run": False}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")


@app.get("/security-logs")
async def get_security_logs(limit: int = 50):
    """Get security audit logs"""
    return server.get_security_logs(limit)


@app.get("/history")
async def get_history(limit: int = 20):
    """Get computation history"""
    return server.get_history(limit)


@app.post("/config")
async def update_config(config: SystemConfig):
    """Update system configuration"""
    # Reinitialize with new config
    server.agent_count = config.agent_count
    server.grid_capacity_kw = config.grid_capacity_kw
    server.round_count = 0
    server.history.clear()
    server.initialize()
    return {"status": "reconfigured", **config.model_dump()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    server.websocket_clients.append(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            'type': 'connected',
            'data': server.get_status()
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                msg = json.loads(data)
                
                if msg.get('type') == 'ping':
                    await websocket.send_json({'type': 'pong'})
                elif msg.get('type') == 'run_round':
                    response = server.run_round()
                    await server.broadcast({
                        'type': 'round_complete',
                        'data': response.model_dump()
                    })
            except WebSocketDisconnect:
                break
    finally:
        if websocket in server.websocket_clients:
            server.websocket_clients.remove(websocket)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the server"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
