"""
FHE Benchmarking Suite
======================
Comprehensive benchmarks for the FHE Robot Car system.
Measures encryption, decryption, homomorphic operations, and ML inference times.
"""

import time
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class BenchmarkResult:
    """Single benchmark measurement"""
    name: str
    iterations: int
    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    total_ms: float
    
    def to_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v for k, v in asdict(self).items()}


@dataclass
class BenchmarkReport:
    """Complete benchmark report"""
    timestamp: str
    system_info: Dict[str, Any]
    results: List[BenchmarkResult]
    summary: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "system_info": self.system_info,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary
        }
    
    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_markdown(self) -> str:
        """Generate markdown report"""
        md = []
        md.append("# FHE Benchmark Report")
        md.append(f"\n**Generated**: {self.timestamp}")
        md.append(f"**Platform**: {self.system_info.get('platform', 'Unknown')}")
        md.append(f"**Python**: {self.system_info.get('python_version', 'Unknown')}")
        
        md.append("\n## Results\n")
        md.append("| Benchmark | Mean (ms) | Std Dev | Min | Max |")
        md.append("|-----------|-----------|---------|-----|-----|")
        
        for r in self.results:
            md.append(f"| {r.name} | {r.mean_ms:.3f} | {r.std_ms:.3f} | {r.min_ms:.3f} | {r.max_ms:.3f} |")
        
        md.append("\n## Summary\n")
        for key, value in self.summary.items():
            if isinstance(value, float):
                md.append(f"- **{key}**: {value:.3f}")
            else:
                md.append(f"- **{key}**: {value}")
        
        return "\n".join(md)


class FHEBenchmark:
    """
    Comprehensive FHE benchmarking suite.
    
    Benchmarks:
    1. Key generation
    2. Encryption (single value, batch)
    3. Decryption (single value, batch)
    4. Homomorphic addition (cipher + cipher)
    5. Homomorphic multiplication (cipher * cipher)
    6. Homomorphic scalar multiplication
    7. ML inference (encrypted vs plaintext)
    """
    
    def __init__(self, iterations: int = 50, warmup: int = 5):
        self.iterations = iterations
        self.warmup = warmup
        self.results: List[BenchmarkResult] = []
        
        # Sample data for benchmarks
        self.sample_data = [25.5, 30.2, 45.8, 100.3, 75.6]
        self.sample_sensor_data = {
            "ultrasonic_front": 80,
            "ultrasonic_left": 120,
            "ultrasonic_right": 100,
            "ultrasonic_rear": 200,
            "speed": 25
        }
    
    def _benchmark(self, name: str, func, *args) -> BenchmarkResult:
        """Run a benchmark and return results"""
        times = []
        
        # Warmup
        for _ in range(self.warmup):
            func(*args)
        
        # Actual benchmark
        for _ in range(self.iterations):
            start = time.perf_counter()
            func(*args)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        result = BenchmarkResult(
            name=name,
            iterations=self.iterations,
            mean_ms=statistics.mean(times),
            std_ms=statistics.stdev(times) if len(times) > 1 else 0,
            min_ms=min(times),
            max_ms=max(times),
            total_ms=sum(times)
        )
        
        self.results.append(result)
        print(f"  ✓ {name}: {result.mean_ms:.3f}ms (±{result.std_ms:.3f})")
        
        return result
    
    def run_all(self) -> BenchmarkReport:
        """Run all benchmarks and generate report"""
        print("=" * 60)
        print("🔬 FHE Benchmark Suite")
        print("=" * 60)
        print(f"\nIterations: {self.iterations} | Warmup: {self.warmup}")
        print("-" * 60)
        
        # Import FHE components
        from fhe_core.encryption_core import FHEEngine
        from fhe_core.collision_risk_model import (
            EncryptedCollisionDetector, 
            PlaintextCollisionDetector
        )
        
        # =============== Key Generation ===============
        print("\n📦 Key Generation")
        self._benchmark("Context Creation (Full)", FHEEngine)
        
        # Create engine for remaining tests
        engine = FHEEngine()
        
        # =============== Encryption ===============
        print("\n🔐 Encryption")
        self._benchmark("Encrypt Single Value", 
                       lambda: engine.encrypt([42.0], "test"))
        self._benchmark("Encrypt Batch (5 values)", 
                       lambda: engine.encrypt(self.sample_data, "test"))
        self._benchmark("Encrypt Batch (50 values)", 
                       lambda: engine.encrypt([i * 1.1 for i in range(50)], "test"))
        
        # =============== Decryption ===============
        print("\n🔓 Decryption")
        encrypted = engine.encrypt(self.sample_data, "test")
        self._benchmark("Decrypt Batch (5 values)", 
                       lambda: engine.decrypt(encrypted))
        
        # =============== Homomorphic Operations ===============
        print("\n➕ Homomorphic Operations")
        enc1 = engine.encrypt([10.0, 20.0, 30.0], "test")
        enc2 = engine.encrypt([1.0, 2.0, 3.0], "test")
        
        self._benchmark("HE Addition (cipher + cipher)", 
                       lambda: engine.add(enc1, enc2))
        self._benchmark("HE Multiplication (cipher * cipher)", 
                       lambda: engine.multiply(enc1, enc2))
        self._benchmark("HE Scalar Mult (cipher * plain)", 
                       lambda: engine.multiply_plain(enc1, [2.0, 2.0, 2.0]))
        self._benchmark("HE Mean (encrypted)", 
                       lambda: engine.encrypted_mean(enc1))
        
        # =============== ML Inference ===============
        print("\n🤖 ML Inference Comparison")
        
        enc_detector = EncryptedCollisionDetector(engine)
        plain_detector = PlaintextCollisionDetector()
        
        # Encrypted pipeline
        self._benchmark("ML: Encrypt Sensors", 
                       lambda: enc_detector.encrypt_sensor_data(self.sample_sensor_data))
        
        enc_features = enc_detector.encrypt_sensor_data(self.sample_sensor_data)
        self._benchmark("ML: Encrypted Inference (PPML)", 
                       lambda: enc_detector.infer_encrypted(enc_features))
        
        enc_result = enc_detector.infer_encrypted(enc_features)
        self._benchmark("ML: Decrypt Result", 
                       lambda: enc_detector.decrypt_result(enc_result, speed=25))
        
        self._benchmark("ML: Full Pipeline (E2E)", 
                       lambda: enc_detector.full_inference_pipeline(self.sample_sensor_data))
        
        # Plaintext baseline
        self._benchmark("ML: Plaintext Inference (baseline)", 
                       lambda: plain_detector.infer(self.sample_sensor_data))
        
        # =============== Generate Report ===============
        print("\n" + "-" * 60)
        
        # System info
        import platform
        system_info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "fhe_library": "TenSEAL (CKKS)",
            "security_level": "128-bit"
        }
        
        # Summary calculations
        enc_inference = next((r for r in self.results if "Encrypted Inference" in r.name), None)
        plain_inference = next((r for r in self.results if "Plaintext Inference" in r.name), None)
        
        overhead = (enc_inference.mean_ms / plain_inference.mean_ms) if enc_inference and plain_inference else 0
        
        full_pipeline = next((r for r in self.results if "Full Pipeline" in r.name), None)
        encryption = next((r for r in self.results if r.name == "Encrypt Batch (5 values)"), None)
        
        summary = {
            "total_benchmarks": len(self.results),
            "encryption_overhead_factor": round(overhead, 1),
            "avg_encryption_time_ms": round(encryption.mean_ms, 2) if encryption else 0,
            "avg_full_pipeline_ms": round(full_pipeline.mean_ms, 2) if full_pipeline else 0,
            "suitable_for_realtime": full_pipeline.mean_ms < 100 if full_pipeline else False
        }
        
        report = BenchmarkReport(
            timestamp=datetime.now().isoformat(),
            system_info=system_info,
            results=self.results,
            summary=summary
        )
        
        print("\n📊 Summary:")
        print(f"   Encryption Overhead: {summary['encryption_overhead_factor']}x slower than plaintext")
        print(f"   Full Pipeline: {summary['avg_full_pipeline_ms']}ms/inference")
        print(f"   Real-time Capable: {'✓ Yes' if summary['suitable_for_realtime'] else '✗ No'} (<100ms)")
        
        return report
    
    def save_report(self, report: BenchmarkReport, output_dir: str = "."):
        """Save report to files"""
        # JSON report
        json_path = os.path.join(output_dir, "benchmark_results.json")
        with open(json_path, "w") as f:
            f.write(report.to_json())
        print(f"\n📁 JSON saved: {json_path}")
        
        # Markdown report
        md_path = os.path.join(output_dir, "benchmark_report.md")
        with open(md_path, "w") as f:
            f.write(report.to_markdown())
        print(f"📁 Markdown saved: {md_path}")


def main():
    """Run benchmarks from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FHE Benchmark Suite")
    parser.add_argument("--iterations", "-n", type=int, default=50,
                       help="Number of iterations per benchmark")
    parser.add_argument("--warmup", "-w", type=int, default=5,
                       help="Warmup iterations")
    parser.add_argument("--output", "-o", type=str, default="benchmarks",
                       help="Output directory for reports")
    args = parser.parse_args()
    
    # Run benchmarks
    benchmark = FHEBenchmark(iterations=args.iterations, warmup=args.warmup)
    report = benchmark.run_all()
    
    # Save reports
    os.makedirs(args.output, exist_ok=True)
    benchmark.save_report(report, args.output)
    
    print("\n" + "=" * 60)
    print("✅ Benchmark Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
