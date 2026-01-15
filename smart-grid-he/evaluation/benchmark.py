"""
Evaluation Suite for Smart Grid HE System
==========================================
Measures performance and correctness of homomorphic encryption operations.

Evaluates:
1. Computation overhead vs plaintext baseline
2. Correctness equivalence (encrypted vs plaintext results)
3. Scalability with varying agent counts
4. Ciphertext size overhead
"""

import time
import sys
import os
from typing import Dict, List, Tuple
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fhe_engine import SmartGridFHE
from core.security_logger import SecurityLogger
from agents.agent_manager import AgentManager
from coordinator.encrypted_aggregator import EncryptedAggregator, PlaintextAggregator
from coordinator.load_balancer import UtilityDecisionMaker


class BenchmarkResult:
    """Container for benchmark results"""
    
    def __init__(self, name: str):
        self.name = name
        self.encrypted_times: List[float] = []
        self.plaintext_times: List[float] = []
        self.errors: List[float] = []
        self.ciphertext_sizes: List[float] = []
        self.agent_counts: List[int] = []
    
    def add_run(self, agent_count: int, enc_time: float, plain_time: float, 
                error: float, ct_size: float):
        self.agent_counts.append(agent_count)
        self.encrypted_times.append(enc_time)
        self.plaintext_times.append(plain_time)
        self.errors.append(error)
        self.ciphertext_sizes.append(ct_size)
    
    def get_summary(self) -> Dict:
        if not self.encrypted_times:
            return {}
        
        avg_enc = sum(self.encrypted_times) / len(self.encrypted_times)
        avg_plain = sum(self.plaintext_times) / len(self.plaintext_times)
        avg_error = sum(self.errors) / len(self.errors)
        avg_ct_size = sum(self.ciphertext_sizes) / len(self.ciphertext_sizes)
        
        return {
            'name': self.name,
            'runs': len(self.encrypted_times),
            'avg_encrypted_time_ms': round(avg_enc, 2),
            'avg_plaintext_time_ms': round(avg_plain, 4),
            'overhead_ratio': round(avg_enc / avg_plain, 1) if avg_plain > 0 else 0,
            'avg_error_kw': avg_error,
            'max_error_kw': max(self.errors),
            'avg_ciphertext_size_kb': round(avg_ct_size, 1)
        }
    
    def to_table_row(self, agent_count: int = None) -> str:
        if agent_count:
            idx = self.agent_counts.index(agent_count) if agent_count in self.agent_counts else -1
            if idx >= 0:
                return (f"| {agent_count} | {self.encrypted_times[idx]:.2f} | "
                       f"{self.plaintext_times[idx]:.4f} | "
                       f"{self.encrypted_times[idx]/max(self.plaintext_times[idx], 0.0001):.0f}x | "
                       f"{self.errors[idx]:.2e} |")
        return ""


def run_benchmark(agent_counts: List[int] = None, runs_per_count: int = 3) -> Dict:
    """
    Run comprehensive benchmark suite.
    
    Args:
        agent_counts: List of agent counts to test
        runs_per_count: Number of runs per agent count
        
    Returns:
        Benchmark results dictionary
    """
    if agent_counts is None:
        agent_counts = [10, 25, 50, 100]
    
    print("=" * 70)
    print("Smart Grid HE Benchmark Suite")
    print("=" * 70)
    
    # Initialize FHE
    print("\n[1] Initializing FHE engine...")
    setup_start = time.time()
    utility_fhe = SmartGridFHE()
    public_context = utility_fhe.get_public_context()
    secret_context = utility_fhe.get_secret_context()
    setup_time = (time.time() - setup_start) * 1000
    print(f"    FHE setup time: {setup_time:.0f} ms")
    
    results = BenchmarkResult("aggregation")
    
    print("\n[2] Running benchmarks...")
    print(f"    Agent counts: {agent_counts}")
    print(f"    Runs per count: {runs_per_count}")
    
    all_results = []
    
    for agent_count in agent_counts:
        print(f"\n    Testing with {agent_count} agents...")
        
        for run in range(runs_per_count):
            # Create fresh components
            agent_manager = AgentManager(public_context)
            agent_manager.create_agents(agent_count)
            
            encrypted_agg = EncryptedAggregator(public_context)
            plaintext_agg = PlaintextAggregator()
            utility = UtilityDecisionMaker(secret_context)
            
            # Collect encrypted demands
            encrypted_demands = agent_manager.collect_encrypted_demands()
            plaintext_demands = agent_manager.get_plaintext_demands_for_comparison()
            
            # Benchmark encrypted aggregation
            enc_start = time.time()
            enc_result = encrypted_agg.aggregate(encrypted_demands)
            decrypted_total = utility.fhe.decrypt_demand(enc_result.encrypted_total)[0]
            enc_time = (time.time() - enc_start) * 1000
            
            # Benchmark plaintext aggregation
            plain_start = time.time()
            plain_total, plain_avg, _ = plaintext_agg.aggregate(plaintext_demands)
            plain_time = (time.time() - plain_start) * 1000
            
            # Calculate error
            error = abs(decrypted_total - plain_total)
            
            # Ciphertext size
            ct_size = enc_result.encrypted_total.get_size_kb()
            
            results.add_run(agent_count, enc_time, plain_time, error, ct_size)
            
            all_results.append({
                'agent_count': agent_count,
                'run': run + 1,
                'encrypted_time_ms': round(enc_time, 2),
                'plaintext_time_ms': round(plain_time, 4),
                'encrypted_total_kw': round(decrypted_total, 4),
                'plaintext_total_kw': round(plain_total, 4),
                'error_kw': error,
                'ciphertext_size_kb': round(ct_size, 1)
            })
        
        print(f"      Completed {runs_per_count} runs")
    
    # Generate summary
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)
    
    print("\n| Agents | Encrypted (ms) | Plaintext (ms) | Overhead | Error (kW) |")
    print("|--------|----------------|----------------|----------|------------|")
    
    for ac in agent_counts:
        print(results.to_table_row(ac))
    
    summary = results.get_summary()
    
    print(f"\nSummary:")
    print(f"  Average overhead: {summary['overhead_ratio']}x")
    print(f"  Average error: {summary['avg_error_kw']:.2e} kW")
    print(f"  Average ciphertext size: {summary['avg_ciphertext_size_kb']} KB")
    
    return {
        'setup_time_ms': setup_time,
        'summary': summary,
        'detailed_results': all_results,
        'timestamp': datetime.now().isoformat()
    }


def run_correctness_test(agent_count: int = 50, rounds: int = 10) -> Dict:
    """
    Test correctness equivalence over multiple rounds.
    
    Args:
        agent_count: Number of agents
        rounds: Number of rounds to test
        
    Returns:
        Correctness test results
    """
    print("=" * 70)
    print("Correctness Equivalence Test")
    print("=" * 70)
    
    # Setup
    utility_fhe = SmartGridFHE()
    public_context = utility_fhe.get_public_context()
    
    agent_manager = AgentManager(public_context)
    agent_manager.create_agents(agent_count)
    
    encrypted_agg = EncryptedAggregator(public_context)
    
    errors = []
    relative_errors = []
    
    print(f"\nRunning {rounds} rounds with {agent_count} agents...")
    
    for i in range(rounds):
        # Get demands
        encrypted_demands = agent_manager.collect_encrypted_demands()
        plaintext_demands = agent_manager.get_plaintext_demands_for_comparison()
        
        # Compute
        enc_result = encrypted_agg.aggregate(encrypted_demands)
        decrypted = utility_fhe.decrypt_demand(enc_result.encrypted_total)[0]
        plaintext = sum(plaintext_demands.values())
        
        error = abs(decrypted - plaintext)
        rel_error = error / plaintext if plaintext > 0 else 0
        
        errors.append(error)
        relative_errors.append(rel_error)
        
        print(f"  Round {i+1}: Error = {error:.2e} kW, Relative = {rel_error:.2e}")
    
    avg_error = sum(errors) / len(errors)
    max_error = max(errors)
    avg_rel_error = sum(relative_errors) / len(relative_errors)
    
    print(f"\nResults:")
    print(f"  Average absolute error: {avg_error:.2e} kW")
    print(f"  Maximum absolute error: {max_error:.2e} kW")
    print(f"  Average relative error: {avg_rel_error:.2e}")
    print(f"  All errors < 1e-5: {all(e < 1e-5 for e in errors)}")
    
    return {
        'agent_count': agent_count,
        'rounds': rounds,
        'avg_error_kw': avg_error,
        'max_error_kw': max_error,
        'avg_relative_error': avg_rel_error,
        'all_passed': all(e < 1e-5 for e in errors)
    }


def run_scalability_test(max_agents: int = 200, step: int = 25) -> Dict:
    """
    Test scalability with increasing agent counts.
    
    Args:
        max_agents: Maximum number of agents to test
        step: Step size for agent count
        
    Returns:
        Scalability test results
    """
    print("=" * 70)
    print("Scalability Test")
    print("=" * 70)
    
    # Setup
    utility_fhe = SmartGridFHE()
    public_context = utility_fhe.get_public_context()
    
    results = []
    agent_counts = list(range(step, max_agents + 1, step))
    
    print(f"\nTesting agent counts: {agent_counts}")
    
    for count in agent_counts:
        print(f"\n  Testing {count} agents...")
        
        agent_manager = AgentManager(public_context)
        agent_manager.create_agents(count)
        
        encrypted_agg = EncryptedAggregator(public_context)
        
        # Time encryption
        enc_start = time.time()
        encrypted_demands = agent_manager.collect_encrypted_demands()
        enc_time = (time.time() - enc_start) * 1000
        
        # Time aggregation
        agg_start = time.time()
        enc_result = encrypted_agg.aggregate(encrypted_demands)
        agg_time = (time.time() - agg_start) * 1000
        
        total_time = enc_time + agg_time
        
        results.append({
            'agent_count': count,
            'encryption_time_ms': round(enc_time, 2),
            'aggregation_time_ms': round(agg_time, 2),
            'total_time_ms': round(total_time, 2),
            'time_per_agent_ms': round(total_time / count, 2)
        })
        
        print(f"    Encryption: {enc_time:.0f} ms, Aggregation: {agg_time:.0f} ms")
    
    print("\n| Agents | Encryption | Aggregation | Total | Per Agent |")
    print("|--------|------------|-------------|-------|-----------|")
    for r in results:
        print(f"| {r['agent_count']:6} | {r['encryption_time_ms']:>10} | "
              f"{r['aggregation_time_ms']:>11} | {r['total_time_ms']:>5} | "
              f"{r['time_per_agent_ms']:>9} |")
    
    return {
        'max_agents': max_agents,
        'results': results
    }


def main():
    """Run all benchmarks"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart Grid HE Benchmarks')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmark')
    parser.add_argument('--correctness', action='store_true', help='Run correctness test')
    parser.add_argument('--scalability', action='store_true', help='Run scalability test')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--agents', type=str, default='10,25,50,100', 
                       help='Comma-separated agent counts')
    parser.add_argument('--runs', type=int, default=3, help='Runs per agent count')
    parser.add_argument('--output', type=str, help='Output JSON file')
    
    args = parser.parse_args()
    
    if not any([args.benchmark, args.correctness, args.scalability, args.all]):
        args.all = True
    
    results = {}
    
    if args.all or args.benchmark:
        agent_counts = [int(x) for x in args.agents.split(',')]
        results['benchmark'] = run_benchmark(agent_counts, args.runs)
    
    if args.all or args.correctness:
        results['correctness'] = run_correctness_test()
    
    if args.all or args.scalability:
        results['scalability'] = run_scalability_test()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")
    
    return results


if __name__ == "__main__":
    main()
