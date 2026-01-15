# FHE Benchmark Report

**Generated**: 2026-01-10T19:05:56.176515
**Platform**: Windows-11-10.0.26200-SP0
**Python**: 3.13.2

## Results

| Benchmark | Mean (ms) | Std Dev | Min | Max |
|-----------|-----------|---------|-----|-----|
| Context Creation (Full) | 229.927 | 2.356 | 227.151 | 235.119 |
| Encrypt Single Value | 5.464 | 0.276 | 4.925 | 5.913 |
| Encrypt Batch (5 values) | 6.075 | 0.691 | 5.224 | 7.485 |
| Encrypt Batch (50 values) | 5.721 | 0.255 | 5.184 | 6.175 |
| Decrypt Batch (5 values) | 2.260 | 0.197 | 2.011 | 2.643 |
| HE Addition (cipher + cipher) | 4.482 | 0.501 | 3.955 | 5.324 |
| HE Multiplication (cipher * cipher) | 5.141 | 0.345 | 4.756 | 5.855 |
| HE Scalar Mult (cipher * plain) | 2.822 | 0.143 | 2.675 | 3.068 |
| HE Mean (encrypted) | 9.957 | 0.578 | 9.354 | 11.276 |
| ML: Encrypt Sensors | 5.424 | 0.376 | 4.880 | 6.119 |
| ML: Encrypted Inference (PPML) | 10.694 | 0.501 | 10.011 | 11.527 |
| ML: Decrypt Result | 1.525 | 0.075 | 1.453 | 1.695 |
| ML: Full Pipeline (E2E) | 16.616 | 1.086 | 15.611 | 19.398 |
| ML: Plaintext Inference (baseline) | 0.002 | 0.000 | 0.002 | 0.003 |

## Summary

- **total_benchmarks**: 14
- **encryption_overhead_factor**: 5658.300
- **avg_encryption_time_ms**: 6.080
- **avg_full_pipeline_ms**: 16.620
- **suitable_for_realtime**: True