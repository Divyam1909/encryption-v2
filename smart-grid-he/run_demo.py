#!/usr/bin/env python3
"""
Smart Grid HE - Demo Launcher
==============================
Entry point for the Privacy-Preserving Smart Grid system.

Usage:
    python run_demo.py              # Start web dashboard (default)
    python run_demo.py --cli        # Run CLI demo (no browser needed)
    python run_demo.py --benchmark  # Run performance benchmarks
"""

import sys
import os
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def run_web_dashboard():
    """Start the FastAPI server and open the dashboard in a browser."""
    import webbrowser
    import threading
    import time
    import uvicorn

    host = "127.0.0.1"
    port = 8001

    print("=" * 60)
    print("  Privacy-Preserving Smart Grid - Web Dashboard")
    print("=" * 60)
    print(f"\n  Initializing FHE keys (this takes ~5 seconds)...")
    print(f"  Dashboard will open at: http://{host}:{port}\n")

    # Open browser after a short delay so the server has time to start
    def open_browser():
        time.sleep(3)
        webbrowser.open(f"http://{host}:{port}")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "server.server:app",
        host=host,
        port=port,
        log_level="info",
    )


def run_cli_demo():
    """Run the system in CLI mode — no browser or server needed."""
    from coordinator.grid_coordinator import demo
    demo()


def run_benchmark():
    """Run the full evaluation benchmark suite."""
    import subprocess
    benchmark_script = os.path.join(PROJECT_ROOT, "evaluation", "benchmark.py")
    result = subprocess.run(
        [sys.executable, benchmark_script, "--all"],
        cwd=PROJECT_ROOT,
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Privacy-Preserving Smart Grid Load Balancing (Homomorphic Encryption)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_demo.py              Start web dashboard at http://127.0.0.1:8001
  python run_demo.py --cli        CLI demo — runs 3 rounds and prints results
  python run_demo.py --benchmark  Full evaluation benchmark suite
        """,
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run CLI demo instead of web dashboard",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarks",
    )
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
    elif args.cli:
        run_cli_demo()
    else:
        run_web_dashboard()


if __name__ == "__main__":
    main()
