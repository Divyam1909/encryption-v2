#!/usr/bin/env python3
"""
FHE Robot Car System
====================
Single-command launcher for the FHE Robot Car system.
Starts the server and opens both simulation and dashboard.
"""

import asyncio
import sys
import os
import signal
import socket
import webbrowser
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_local_ip():
    """Get the local IP address for network access"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_banner():
    """Print startup banner"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   🚗  FHE Robot Car System - Encrypted Sensor Simulation     ║
║                                                               ║
║   Drive with WASD/Arrow Keys • Data encrypted with FHE       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_qr_code(url):
    """Print QR code for mobile access"""
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        print("\n📱 Scan this QR code to access on mobile:\n")
        qr.print_ascii(invert=True)
        print(f"\n   URL: {url}\n")
    except ImportError:
        print(f"\n📱 Access on mobile: {url}\n")
        print("   (Install 'qrcode' package for QR code display)")


async def run_server(host: str, port: int):
    """Run the FastAPI server"""
    import uvicorn
    
    config = uvicorn.Config(
        "server.server:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main_async():
    """Async main function - starts server and opens browser"""
    host = "0.0.0.0"
    port = 8000
    
    local_ip = get_local_ip()
    network_url = f"http://{local_ip}:{port}"
    
    print_banner()
    print(f"🖥️  Server: http://localhost:{port}")
    print(f"🌐 Network: {network_url}")
    print(f"🚗 Dashboard: http://localhost:{port}/static/index.html")
    
    # Print QR code for mobile access
    print_qr_code(f"{network_url}/static/index.html")
    
    # Create server task
    server_task = asyncio.create_task(run_server(host, port))
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    # Generate registration code
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://127.0.0.1:{port}/api/register/code",
                params={"device_name": "My Device"}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"\n📱 Registration Code:")
                print(f"   ╔═══════════════╗")
                print(f"   ║   {data['code']}    ║")
                print(f"   ╚═══════════════╝")
                print(f"   Enter this code on the dashboard to see decrypted data\n")
    except Exception as e:
        print(f"⚠️ Could not generate registration code: {e}")
    
    # Open unified dashboard (single tab)
    webbrowser.open(f"http://localhost:{port}/static/index.html")
    
    print("\n✓ System running. Press Ctrl+C to stop.\n")
    print("=" * 60)
    print("🎮 Controls: WASD or Arrow Keys to drive, Space to brake, R to reset")
    print("=" * 60)
    
    # Wait for server task
    try:
        await asyncio.gather(server_task)
    except asyncio.CancelledError:
        pass


def main():
    """Main entry point"""
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run async main
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n🛑 System stopped.")


if __name__ == "__main__":
    main()