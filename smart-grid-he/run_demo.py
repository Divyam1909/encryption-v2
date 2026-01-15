"""
Smart Grid HE - Main Demo Runner
================================
Single entry point to run the complete system.

Usage:
    python run_demo.py              # Run web server with dashboard
    python run_demo.py --cli        # Run CLI demo
    python run_demo.py --benchmark  # Run benchmarks
"""

import sys
import os
import argparse
import webbrowser
import time
from threading import Thread

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_cli_demo():
    """Run command-line demonstration"""
    from core.fhe_engine import SmartGridFHE
    from core.security_logger import SecurityLogger
    from agents.agent_manager import AgentManager
    from coordinator.grid_coordinator import GridCoordinator
    from coordinator.load_balancer import UtilityDecisionMaker
    
    print("=" * 70)
    print("Privacy-Preserving Smart Grid Load Balancing")
    print("Using Homomorphic Encryption (CKKS/TenSEAL)")
    print("=" * 70)
    
    # Step 1: Initialize
    print("\n[1] INITIALIZATION")
    print("-" * 40)
    
    print("Generating FHE keys (Utility Company)...")
    utility_fhe = SmartGridFHE()
    public_context = utility_fhe.get_public_context()
    secret_context = utility_fhe.get_secret_context()
    print(f"  ✓ Context hash: {utility_fhe.get_context_hash()}")
    print(f"  ✓ Security level: 128-bit")
    
    # Security logger
    logger = SecurityLogger()
    
    # Create agents
    print("\nCreating household agents...")
    agent_manager = AgentManager(public_context, logger)
    agent_ids = agent_manager.create_agents(25)
    print(f"  ✓ Created {len(agent_ids)} households")
    summary = agent_manager.get_summary()
    print(f"  ✓ Profile distribution: {summary['profile_distribution']}")
    
    # Create coordinator (untrusted)
    print("\nInitializing Grid Coordinator...")
    coordinator = GridCoordinator(public_context, grid_capacity_kw=75.0, security_logger=logger)
    print(f"  ✓ Coordinator has secret key: {coordinator.aggregator.fhe.is_private()}")
    print(f"  ✓ Grid capacity: 75.0 kW")
    
    # Create utility decision maker (trusted)
    utility = UtilityDecisionMaker(secret_context, grid_capacity_kw=75.0, security_logger=logger)
    print(f"  ✓ Utility has secret key: {utility.fhe.is_private()}")
    
    # Step 2: Simulation rounds
    print("\n[2] SIMULATION ROUNDS")
    print("-" * 40)
    
    for round_num in range(5):
        print(f"\n--- Round {round_num + 1} ---")
        
        # Collect encrypted demands
        encrypted_demands = agent_manager.collect_encrypted_demands()
        print(f"  Collected {len(encrypted_demands)} encrypted demands")
        
        # Get plaintext for comparison
        plaintext = agent_manager.get_plaintext_demands_for_comparison()
        plaintext_total = sum(plaintext.values())
        
        # Process on coordinator (encrypted)
        result = coordinator.process_round(encrypted_demands)
        print(f"  Aggregation time: {result.computation_time_ms:.2f} ms")
        
        # Utility decrypts and decides
        decision = utility.make_decision(result.encrypted_total, result.agent_count)
        coordinator.receive_decision(decision)
        
        # Results
        print(f"  Encrypted total (decrypted): {decision.total_demand_kw:.2f} kW")
        print(f"  Plaintext total: {plaintext_total:.2f} kW")
        print(f"  Error: {abs(decision.total_demand_kw - plaintext_total):.2e} kW")
        print(f"  Utilization: {decision.utilization_percent:.1f}%")
        print(f"  Action: {decision.action.value}")
        
        # Apply load balancing
        if decision.reduction_factor < 1.0:
            agent_manager.broadcast_load_balance(decision.reduction_factor)
            print(f"  Applied {int((1-decision.reduction_factor)*100)}% reduction")
    
    # Step 3: Security audit
    print("\n[3] SECURITY AUDIT")
    print("-" * 40)
    
    audit = logger.generate_audit_report()
    print(f"  Total operations logged: {audit['total_log_entries']}")
    print(f"  Entities: {audit['entities']}")
    print(f"  Coordinator plaintext access: {audit['coordinator_privacy_audit']['plaintext_access']}")
    print(f"  Violations: {len(audit['security_violations'])}")
    print(f"\n  CONCLUSION: {audit['conclusion']}")
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


def run_server(port: int = 8000):
    """Run the web server with dashboard"""
    print("=" * 70)
    print("Privacy-Preserving Smart Grid - Web Dashboard")
    print("=" * 70)
    
    print(f"\nStarting server on http://localhost:{port}")
    print("Opening browser...")
    
    # Open browser after short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")
    
    Thread(target=open_browser, daemon=True).start()
    
    # Start server
    from server.server import run_server as start_uvicorn
    start_uvicorn(host="0.0.0.0", port=port)


def run_benchmark():
    """Run benchmarks"""
    from evaluation.benchmark import main as benchmark_main
    benchmark_main()


def main():
    parser = argparse.ArgumentParser(
        description="Privacy-Preserving Smart Grid Load Balancing Demo"
    )
    parser.add_argument('--cli', action='store_true',
                       help='Run command-line demo (no web server)')
    parser.add_argument('--benchmark', action='store_true',
                       help='Run performance benchmarks')
    parser.add_argument('--port', type=int, default=8000,
                       help='Web server port (default: 8000)')
    
    args = parser.parse_args()
    
    if args.cli:
        run_cli_demo()
    elif args.benchmark:
        run_benchmark()
    else:
        run_server(args.port)


if __name__ == "__main__":
    main()
