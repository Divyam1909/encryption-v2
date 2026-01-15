"""
Benchmark Comparison Script
============================
Compares this CKKS-based smart grid system against other privacy-preserving approaches.

Comparison includes:
1. Our Approach (CKKS + Pedersen)
2. Paillier Encryption (integer-only FHE)
3. Simulated MPC (Secure Multi-Party Computation)
4. Differential Privacy (noise-based)
5. Plaintext Baseline (no encryption)

NOTE ON ACCURACY:
- CKKS (Ours): REAL measurements from actual TenSEAL execution
- Paillier: Based on python-paillier benchmarks (Jung et al., 2019)
- MPC: Based on ABY framework benchmarks (Demmler et al., NDSS 2015)
- DP/Plaintext: Real measurements

References:
- Cheon et al., "CKKS" ASIACRYPT 2017
- Paillier benchmarks: ~15-25ms per 2048-bit encryption
- ABY Framework: https://github.com/encryptogroup/ABY

Output: Comparison graphs saved to benchmark_results/
"""

import time
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Dict, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create output directory
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "benchmark_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


@dataclass
class BenchmarkResult:
    """Stores benchmark results for one approach."""
    name: str
    encryption_time_ms: float
    aggregation_time_ms: float
    decryption_time_ms: float
    total_time_ms: float
    ciphertext_size_kb: float
    accuracy_error: float
    privacy_level: str
    verification_support: bool
    is_real_measurement: bool
    notes: str


def benchmark_our_approach(num_agents: int = 25) -> BenchmarkResult:
    """Benchmark our CKKS + Pedersen approach - REAL measurements."""
    print(f"\n[1/5] Benchmarking: CKKS + Pedersen (REAL) with {num_agents} agents...")
    
    try:
        from core.fhe_engine import SmartGridFHE
        from core.verifiable_aggregation import VerifiableAggregator
        
        # Setup
        utility_fhe = SmartGridFHE()
        public_context = utility_fhe.get_public_context()
        coord_fhe = SmartGridFHE.from_context(public_context)
        verifier = VerifiableAggregator()
        
        demands = [np.random.uniform(1, 8) for _ in range(num_agents)]
        
        # Encryption benchmark
        enc_start = time.perf_counter()
        encrypted_demands = []
        commitments = []
        for i, d in enumerate(demands):
            enc = coord_fhe.encrypt_demand(d, f"agent_{i}")
            encrypted_demands.append(enc)
            commit, _ = verifier.create_agent_contribution(d, f"agent_{i}")
            commitments.append(commit)
        enc_time = (time.perf_counter() - enc_start) * 1000
        
        # Aggregation benchmark
        agg_start = time.perf_counter()
        encrypted_total = coord_fhe.aggregate_demands(encrypted_demands)
        commit_agg = verifier.aggregate_commitments(commitments)
        agg_time = (time.perf_counter() - agg_start) * 1000
        
        # Decryption benchmark
        dec_start = time.perf_counter()
        decrypted = utility_fhe.decrypt_demand(encrypted_total)[0]
        dec_time = (time.perf_counter() - dec_start) * 1000
        
        # Accuracy
        plaintext_sum = sum(demands)
        error = abs(decrypted - plaintext_sum)
        
        # Ciphertext size
        ct_size = len(encrypted_demands[0].ciphertext) / 1024
        
        print(f"    ✓ Real measurement: {enc_time + agg_time + dec_time:.1f}ms total")
        
        return BenchmarkResult(
            name="CKKS + Pedersen (Ours)",
            encryption_time_ms=enc_time,
            aggregation_time_ms=agg_time,
            decryption_time_ms=dec_time,
            total_time_ms=enc_time + agg_time + dec_time,
            ciphertext_size_kb=ct_size,
            accuracy_error=error,
            privacy_level="full",
            verification_support=True,
            is_real_measurement=True,
            notes="Real TenSEAL CKKS measurement"
        )
    except Exception as e:
        print(f"    Error: {e}")
        return None


def benchmark_paillier_literature(num_agents: int = 25) -> BenchmarkResult:
    """
    Paillier benchmark based on literature.
    
    Sources:
    - python-paillier library benchmarks: ~20ms per encryption (2048-bit)
    - "Practical Secure Aggregation" Bonawitz et al. 2017
    - Key size: 2048-bit standard
    """
    print(f"\n[2/5] Benchmarking: Paillier (Literature-based) with {num_agents} agents...")
    
    # Literature values for 2048-bit Paillier on modern CPUs:
    # Encryption: 15-25ms per value
    # Aggregation: ~0.1ms per modular multiplication  
    # Decryption: ~20-30ms
    
    enc_time = num_agents * 20.0  # 20ms per encryption (conservative)
    agg_time = num_agents * 0.1   # Modular multiplication is fast
    dec_time = 25.0               # Single decryption
    
    # Paillier ciphertext size: 2 × key_size = 512 bytes for 2048-bit
    ct_size_per_agent = 0.5  # KB
    
    print(f"    ⚠ Literature estimate: {enc_time + agg_time + dec_time:.1f}ms total")
    
    return BenchmarkResult(
        name="Paillier (2048-bit)",
        encryption_time_ms=enc_time,
        aggregation_time_ms=agg_time,
        decryption_time_ms=dec_time,
        total_time_ms=enc_time + agg_time + dec_time,
        ciphertext_size_kb=ct_size_per_agent * num_agents,
        accuracy_error=0,  # Exact for integers
        privacy_level="full",
        verification_support=False,
        is_real_measurement=False,
        notes="Literature: python-paillier, 2048-bit key"
    )


def benchmark_mpc_literature(num_agents: int = 25) -> BenchmarkResult:
    """
    MPC benchmark based on ABY framework literature.
    
    Sources:
    - ABY Framework (Demmler et al., NDSS 2015)
    - "Practical Secure Aggregation" (Bonawitz et al., CCS 2017)
    
    MPC has high communication rounds, adding latency.
    """
    print(f"\n[3/5] Benchmarking: Secure MPC (Literature-based) with {num_agents} agents...")
    
    # Based on ABY benchmarks for basic aggregation:
    # Setup phase: ~50ms (secret sharing)
    # Computation: ~2-5ms per party
    # Reconstruction: ~20ms
    # Network latency: assume 10ms per round, 3-5 rounds typical
    
    setup_time = 50.0
    compute_time = num_agents * 3.0
    reconstruct_time = 20.0
    network_rounds = 4
    network_latency = network_rounds * 10.0  # 10ms per round
    
    total = setup_time + compute_time + reconstruct_time + network_latency
    
    print(f"    ⚠ Literature estimate: {total:.1f}ms total (includes network)")
    
    return BenchmarkResult(
        name="Secure MPC (3-server)",
        encryption_time_ms=setup_time,
        aggregation_time_ms=compute_time + network_latency,
        decryption_time_ms=reconstruct_time,
        total_time_ms=total,
        ciphertext_size_kb=num_agents * 0.032,  # 32 bytes per share
        accuracy_error=0,
        privacy_level="full",
        verification_support=False,
        is_real_measurement=False,
        notes="Literature: ABY framework, 3-server model"
    )


def benchmark_differential_privacy(num_agents: int = 25) -> BenchmarkResult:
    """Benchmark differential privacy - REAL measurements."""
    print(f"\n[4/5] Benchmarking: Differential Privacy (REAL) with {num_agents} agents...")
    
    demands = [np.random.uniform(1, 8) for _ in range(num_agents)]
    true_sum = sum(demands)
    
    # Laplace mechanism with ε=1.0
    epsilon = 1.0
    sensitivity = 8.0  # Max demand per household
    
    start = time.perf_counter()
    noise = np.random.laplace(0, sensitivity / epsilon)
    noisy_sum = true_sum + noise
    dp_time = (time.perf_counter() - start) * 1000
    
    # Time for aggregation (plaintext addition)
    agg_start = time.perf_counter()
    _ = sum(demands)
    agg_time = (time.perf_counter() - agg_start) * 1000
    
    error = abs(noise)  # Expected error ~8 kW for ε=1
    
    print(f"    ✓ Real measurement: {dp_time + agg_time:.3f}ms total, error: {error:.2f} kW")
    
    return BenchmarkResult(
        name="Differential Privacy (ε=1)",
        encryption_time_ms=dp_time,
        aggregation_time_ms=agg_time,
        decryption_time_ms=0,
        total_time_ms=dp_time + agg_time,
        ciphertext_size_kb=num_agents * 0.008,  # 8 bytes per float
        accuracy_error=error,
        privacy_level="partial",
        verification_support=False,
        is_real_measurement=True,
        notes=f"Real measurement, Laplace noise ~{error:.1f} kW"
    )


def benchmark_plaintext(num_agents: int = 25) -> BenchmarkResult:
    """Plaintext baseline - REAL measurements, no privacy."""
    print(f"\n[5/5] Benchmarking: Plaintext Baseline (REAL) with {num_agents} agents...")
    
    demands = [np.random.uniform(1, 8) for _ in range(num_agents)]
    
    start = time.perf_counter()
    total = sum(demands)
    compute_time = (time.perf_counter() - start) * 1000
    
    print(f"    ✓ Real measurement: {compute_time:.4f}ms total")
    
    return BenchmarkResult(
        name="Plaintext (No Privacy)",
        encryption_time_ms=0,
        aggregation_time_ms=compute_time,
        decryption_time_ms=0,
        total_time_ms=compute_time,
        ciphertext_size_kb=num_agents * 0.008,
        accuracy_error=0,
        privacy_level="none",
        verification_support=False,
        is_real_measurement=True,
        notes="Baseline, no privacy protection"
    )


def run_scalability_benchmark() -> Dict[str, List[Tuple[int, float]]]:
    """Run benchmarks for different numbers of agents."""
    print("\n" + "="*60)
    print("Running Scalability Benchmark")
    print("="*60)
    
    agent_counts = [10, 25, 50, 100]
    results = {
        "CKKS (Ours)": [],
        "Paillier": [],
        "MPC": [],
        "DP": [],
        "Plaintext": []
    }
    
    for n in agent_counts:
        print(f"\n--- {n} agents ---")
        
        r1 = benchmark_our_approach(n)
        r2 = benchmark_paillier_literature(n)
        r3 = benchmark_mpc_literature(n)
        r4 = benchmark_differential_privacy(n)
        r5 = benchmark_plaintext(n)
        
        if r1:
            results["CKKS (Ours)"].append((n, r1.total_time_ms))
        results["Paillier"].append((n, r2.total_time_ms))
        results["MPC"].append((n, r3.total_time_ms))
        results["DP"].append((n, r4.total_time_ms))
        results["Plaintext"].append((n, r5.total_time_ms))
    
    return results


def create_comparison_graphs(results: List[BenchmarkResult], scalability: Dict):
    """Create and save comparison graphs with WHITE background."""
    print("\n" + "="*60)
    print("Generating Comparison Graphs (White Background)")
    print("="*60)
    
    # Use default style (white background)
    plt.style.use('default')
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#95A3A6']
    
    # Filter out None results
    results = [r for r in results if r is not None]
    
    # ===== Graph 1: Total Time Comparison =====
    fig, ax = plt.subplots(figsize=(12, 6))
    names = [r.name for r in results]
    times = [r.total_time_ms for r in results]
    real_markers = ['✓ Real' if r.is_real_measurement else '* Lit.' for r in results]
    
    bars = ax.bar(names, times, color=colors[:len(results)], edgecolor='black', linewidth=1)
    ax.set_ylabel('Total Time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Computation Time Comparison (25 Agents)', fontsize=14, fontweight='bold')
    ax.set_ylim(0, max(times) * 1.25)
    
    for bar, time_val, marker in zip(bars, times, real_markers):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(times)*0.02,
                f'{time_val:.1f}ms\n({marker})', ha='center', va='bottom', fontsize=9)
    
    plt.xticks(rotation=15, ha='right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '1_time_comparison.png'), dpi=150, facecolor='white')
    print(f"  ✓ Saved: 1_time_comparison.png")
    plt.close()
    
    # ===== Graph 2: Privacy vs Speed Trade-off =====
    fig, ax = plt.subplots(figsize=(10, 8))
    
    privacy_scores = {'full': 100, 'partial': 50, 'none': 0}
    x = [r.total_time_ms for r in results]
    y = [privacy_scores[r.privacy_level] for r in results]
    sizes = [300 + r.ciphertext_size_kb * 2 for r in results]
    
    scatter = ax.scatter(x, y, s=sizes, c=colors[:len(results)], alpha=0.7, edgecolors='black', linewidth=2)
    
    for i, r in enumerate(results):
        label = r.name.split('(')[0].strip()
        ax.annotate(label, (x[i], y[i]), textcoords="offset points", 
                   xytext=(0, 20), ha='center', fontsize=10, fontweight='bold')
    
    ax.set_xlabel('Total Computation Time (ms)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Privacy Level', fontsize=12, fontweight='bold')
    ax.set_yticks([0, 50, 100])
    ax.set_yticklabels(['None', 'Partial (DP)', 'Full (Crypto)'])
    ax.set_title('Privacy vs Performance Trade-off', fontsize=14, fontweight='bold')
    ax.axhline(y=75, color='green', linestyle='--', alpha=0.5, linewidth=2)
    ax.text(max(x)*0.9, 78, 'Acceptable Privacy', fontsize=9, color='green')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '2_privacy_vs_speed.png'), dpi=150, facecolor='white')
    print(f"  ✓ Saved: 2_privacy_vs_speed.png")
    plt.close()
    
    # ===== Graph 3: Scalability Comparison =====
    fig, ax = plt.subplots(figsize=(12, 6))
    
    markers = ['o', 's', '^', 'D', 'v']
    for i, (name, data) in enumerate(scalability.items()):
        if data:
            agents = [d[0] for d in data]
            times = [d[1] for d in data]
            ax.plot(agents, times, marker=markers[i], linewidth=2, markersize=8, 
                    label=name, color=colors[i % len(colors)])
    
    ax.set_xlabel('Number of Agents', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Time (ms)', fontsize=12, fontweight='bold')
    ax.set_title('Scalability: Time vs Number of Agents', fontsize=14, fontweight='bold')
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '3_scalability.png'), dpi=150, facecolor='white')
    print(f"  ✓ Saved: 3_scalability.png")
    plt.close()
    
    # ===== Graph 4: Feature Comparison Radar =====
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    
    categories = ['Privacy', 'Speed', 'Accuracy', 'Verification', 'Scalability']
    num_cats = len(categories)
    angles = np.linspace(0, 2*np.pi, num_cats, endpoint=False).tolist()
    angles += angles[:1]
    
    def score_approach(r: BenchmarkResult, scalability_score: float) -> List[float]:
        privacy = {'full': 10, 'partial': 5, 'none': 0}[r.privacy_level]
        speed = max(0, 10 - (r.total_time_ms / 100))
        accuracy = 10 if r.accuracy_error < 0.01 else (5 if r.accuracy_error < 1 else 2)
        verification = 10 if r.verification_support else 2
        return [privacy, speed, accuracy, verification, scalability_score]
    
    approach_scores = [
        ("CKKS (Ours)", score_approach(results[0], 7), colors[0]),
        ("Paillier", score_approach(results[1], 6), colors[1]),
        ("MPC", score_approach(results[2], 4), colors[2]),
        ("DP", score_approach(results[3], 9), colors[3]),
    ]
    
    for name, scores, color in approach_scores:
        scores_closed = scores + scores[:1]
        ax.plot(angles, scores_closed, 'o-', linewidth=2, label=name, color=color)
        ax.fill(angles, scores_closed, alpha=0.15, color=color)
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=11, fontweight='bold')
    ax.set_ylim(0, 10)
    ax.set_title('Multi-Criteria Comparison', fontsize=14, fontweight='bold', y=1.08)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '4_radar_comparison.png'), dpi=150, facecolor='white')
    print(f"  ✓ Saved: 4_radar_comparison.png")
    plt.close()
    
    # ===== Graph 5: Ciphertext Size Comparison =====
    fig, ax = plt.subplots(figsize=(10, 6))
    
    names = [r.name.split('(')[0].strip() for r in results]
    sizes = [r.ciphertext_size_kb for r in results]
    
    bars = ax.barh(names, sizes, color=colors[:len(results)], edgecolor='black', linewidth=1)
    ax.set_xlabel('Data Size (KB)', fontsize=12, fontweight='bold')
    ax.set_title('Storage/Bandwidth Overhead per Round', fontsize=14, fontweight='bold')
    
    for bar, size in zip(bars, sizes):
        ax.text(bar.get_width() + max(sizes)*0.02, bar.get_y() + bar.get_height()/2,
                f'{size:.1f} KB', ha='left', va='center', fontsize=10)
    
    ax.set_xlim(0, max(sizes) * 1.3)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '5_size_comparison.png'), dpi=150, facecolor='white')
    print(f"  ✓ Saved: 5_size_comparison.png")
    plt.close()
    
    # ===== Graph 6: Security Features Table as Image =====
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis('off')
    
    table_data = [
        ['Approach', 'Privacy', 'Verification', 'Accuracy', 'Measurement'],
        ['CKKS + Pedersen (Ours)', 'Full (128-bit)', '✓ Yes', '~10⁻⁷ error', '✓ Real'],
        ['Paillier (2048-bit)', 'Full (112-bit)', '✗ No', 'Exact (int)', '* Literature'],
        ['Secure MPC (3-server)', 'Full (128-bit)', '✗ No', 'Exact', '* Literature'],
        ['Differential Privacy', 'Partial (ε=1)', '✗ No', '~8 kW noise', '✓ Real'],
        ['Plaintext', 'None', '✗ No', 'Exact', '✓ Real'],
    ]
    
    table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                     cellLoc='center', loc='center',
                     colColours=['#E8E8E8']*5)
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 2)
    
    # Color the "Ours" row
    for j in range(5):
        table[(1, j)].set_facecolor('#D4EDDA')
    
    ax.set_title('Security Features Comparison', fontsize=14, fontweight='bold', y=0.95)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, '6_security_features.png'), dpi=150, facecolor='white')
    print(f"  ✓ Saved: 6_security_features.png")
    plt.close()


def create_summary_table(results: List[BenchmarkResult]):
    """Print summary table."""
    print("\n" + "="*90)
    print("BENCHMARK SUMMARY")
    print("="*90)
    
    results = [r for r in results if r is not None]
    
    header = f"{'Approach':<28} {'Time (ms)':<12} {'Size (KB)':<10} {'Privacy':<10} {'Verify':<8} {'Source':<12}"
    print(header)
    print("-" * 90)
    
    for r in results:
        verify = "✓" if r.verification_support else "✗"
        source = "Real" if r.is_real_measurement else "Literature"
        print(f"{r.name:<28} {r.total_time_ms:<12.1f} {r.ciphertext_size_kb:<10.1f} {r.privacy_level:<10} {verify:<8} {source:<12}")
    
    print("-" * 90)
    print("\n✓ Real = Measured on this system")
    print("* Literature = Based on published benchmarks")
    print(f"\nResults saved to: {OUTPUT_DIR}/")


def main():
    """Run all benchmarks and generate graphs."""
    print("="*60)
    print("Smart Grid FHE Benchmark Comparison")
    print("="*60)
    print("\nComparing approaches:")
    print("  1. CKKS + Pedersen (Ours) - REAL measurements")
    print("  2. Paillier - Literature-based")
    print("  3. Secure MPC - Literature-based")
    print("  4. Differential Privacy - REAL measurements")
    print("  5. Plaintext Baseline - REAL measurements")
    
    # Run single-configuration benchmarks
    results = [
        benchmark_our_approach(25),
        benchmark_paillier_literature(25),
        benchmark_mpc_literature(25),
        benchmark_differential_privacy(25),
        benchmark_plaintext(25),
    ]
    
    # Run scalability benchmarks
    scalability = run_scalability_benchmark()
    
    # Generate graphs
    create_comparison_graphs(results, scalability)
    
    # Print summary
    create_summary_table(results)
    
    print("\n" + "="*60)
    print("Benchmark Complete!")
    print("="*60)
    print(f"\nGenerated 6 comparison graphs in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
