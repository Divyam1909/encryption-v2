#!/usr/bin/env python3
"""
FHE IoT System Launcher
=======================
Unified script to run the complete FHE IoT system:
1. Start the server
2. Start ESP32 simulator(s)
3. Open client dashboard
4. Display QR code for mobile access
"""

import asyncio
import sys
import os
import signal
import socket
import webbrowser
import argparse
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
║   🔐  FHE IoT System - Fully Homomorphic Encryption          ║
║                                                               ║
║   Secure sensor data with computations on encrypted data     ║
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


async def run_esp32_simulator(server_url: str, sensor_type: str = "environment"):
    """Run ESP32 simulator"""
    from sensors.esp32_simulator import (
        create_environment_monitor_esp32,
        create_robot_car_esp32,
        create_security_esp32
    )
    from fhe_core.encryption_core import FHEEngine
    
    # Create appropriate ESP32
    if sensor_type == "robot":
        esp32 = create_robot_car_esp32(server_url)
    elif sensor_type == "security":
        esp32 = create_security_esp32(server_url)
    else:
        esp32 = create_environment_monitor_esp32(server_url)
    
    # Get FHE context from server
    print(f"📡 ESP32 Simulator starting ({sensor_type} mode)...")
    
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{server_url}/api/context/public")
            if response.status_code == 200:
                import base64
                data = response.json()
                context_bytes = base64.b64decode(data['context'])
                esp32.set_fhe_context(context_bytes)
                print(f"✓ ESP32: FHE context loaded (hash: {data['context_hash']})")
    except Exception as e:
        print(f"⚠️ ESP32: Could not get FHE context from server: {e}")
        print("   Creating local FHE context...")
        engine = FHEEngine()
        esp32.set_fhe_context(engine.get_public_context())
    
    # Start simulation
    await esp32.start()


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


async def main_async(args):
    """Async main function"""
    # Server binds to 0.0.0.0 but ESP32 should connect to localhost
    bind_host = args.host
    connect_host = "127.0.0.1" if bind_host == "0.0.0.0" else bind_host
    
    server_url = f"http://{connect_host}:{args.port}"
    local_ip = get_local_ip()
    network_url = f"http://{local_ip}:{args.port}"
    
    print_banner()
    print(f"🖥️  Server: http://{bind_host}:{args.port}")
    print(f"🌐 Network: {network_url}")
    print(f"📊 Dashboard: {network_url}/static/index.html")
    
    # Print QR code for mobile access
    if args.qr:
        print_qr_code(f"{network_url}/static/index.html")
    
    # Create tasks
    tasks = []
    
    # Server task
    server_task = asyncio.create_task(run_server(bind_host, args.port))
    tasks.append(server_task)
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    # ESP32 simulator tasks - use localhost for connection
    if args.esp32:
        for sensor_type in args.esp32:
            esp_task = asyncio.create_task(
                run_esp32_simulator(server_url, sensor_type)
            )
            tasks.append(esp_task)
    
    # Open browser if requested
    if args.open:
        webbrowser.open(f"http://{connect_host}:{args.port}/static/index.html")
    
    # Generate registration code
    if args.reg_code:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await asyncio.sleep(1)  # Wait for server
                response = await client.post(
                    f"{server_url}/api/register/code",
                    params={"device_name": args.reg_code}
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"\n📱 Registration Code for '{args.reg_code}':")
                    print(f"   ╔═══════════════╗")
                    print(f"   ║   {data['code']}    ║")
                    print(f"   ╚═══════════════╝")
                    print(f"   Enter this code on the mobile device\n")
        except Exception as e:
            print(f"⚠️ Could not generate registration code: {e}")
    
    print("\n✓ System running. Press Ctrl+C to stop.\n")
    print("=" * 60)
    
    # Wait for all tasks
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="FHE IoT System Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_system.py                    # Start server only
  python run_system.py --esp32 environment  # Start with environment sensors
  python run_system.py --esp32 robot security  # Multiple sensor types
  python run_system.py --open --qr        # Open browser and show QR
  python run_system.py --reg-code "My Phone"  # Generate registration code
        """
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind server (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for server (default: 8000)"
    )
    
    parser.add_argument(
        "--esp32",
        nargs="*",
        choices=["environment", "robot", "security"],
        help="Start ESP32 simulator(s) with specified sensor types"
    )
    
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open dashboard in browser"
    )
    
    parser.add_argument(
        "--qr",
        action="store_true",
        help="Show QR code for mobile access"
    )
    
    parser.add_argument(
        "--reg-code",
        metavar="DEVICE_NAME",
        help="Generate registration code for device"
    )
    
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (quick verification)"
    )
    
    args = parser.parse_args()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run async main
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n🛑 System stopped.")


if __name__ == "__main__":
    main()