# Privacy-Preserving Smart Grid Load Balancing
## Using Homomorphic Encryption (CKKS)

A multi-agent smart grid system where households coordinate electricity demand without revealing private consumption data. The coordinator performs computations entirely on encrypted data.

![Architecture](docs/architecture.png)

## ⭐ Novel Research Contributions

This project goes **beyond using existing libraries** with two original contributions:

### 1. Encrypted Threshold Detection via Linear Approximation

**Problem**: CKKS cannot compare values (is `E(x) > threshold`?)

**Our Solution**: Approximate the step function with a linear function that requires **only scalar operations** - no ciphertext-ciphertext multiplication!

```
score(x) = 0.5 + (x - T) × (0.5/δ)
```

- Works within CKKS numerical constraints
- Provides confidence zones (below/uncertain/above)
- See `core/polynomial_comparator.py`

### 2. Commitment-Based Verifiable Aggregation

**Problem**: How to verify the coordinator computed correctly?

**Our Solution**: Pedersen commitments alongside FHE encryption. Commitments are additively homomorphic:

```
Commit(a) × Commit(b) = Commit(a + b)
```

- Utility verifies aggregate matches commitment
- Detects malicious coordinator with probability 1
- See `core/verifiable_aggregation.py`

📖 **Full details**: [docs/novel_contributions.md](docs/novel_contributions.md)

---

## Key Features

- **True Privacy Preservation**: Coordinator never sees plaintext demand values
- **Homomorphic Computation**: Total and average demand computed on encrypted data
- **Multi-Agent Architecture**: Each household is an autonomous agent
- **Real-Time Dashboard**: Visual proof of encrypted data flow
- **Audit Trail**: Security logs prove no plaintext leakage

## Why Homomorphic Encryption?

Traditional solutions have a critical flaw:

| Approach | Privacy Issue |
|----------|---------------|
| **No encryption** | Coordinator sees all data |
| **TLS/HTTPS** | Coordinator must decrypt to compute |
| **Standard encryption** | Computation requires decryption |
| **Homomorphic Encryption** | ✓ Computation on ciphertext only |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run web dashboard
python run_demo.py

# Or run CLI demo
python run_demo.py --cli

# Run benchmarks
python run_demo.py --benchmark
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SMART GRID SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐       ┌─────────┐       │
│  │ House 1 │  │ House 2 │  │ House 3 │  ...  │ House N │       │
│  │  E(d₁)  │  │  E(d₂)  │  │  E(d₃)  │       │  E(dₙ)  │       │
│  └────┬────┘  └────┬────┘  └────┬────┘       └────┬────┘       │
│       │            │            │                 │             │
│       └────────────┴────────────┴─────────────────┘             │
│                           │                                      │
│                           ▼                                      │
│              ┌────────────────────────┐                         │
│              │    COORDINATOR         │                         │
│              │  (Honest-but-Curious)  │                         │
│              │                        │                         │
│              │  E(Σdᵢ) = Σ E(dᵢ)     │  ← Homomorphic Sum      │
│              │  E(avg) = E(Σ)/n      │  ← Homomorphic Avg      │
│              │                        │                         │
│              │  ⚠ NO SECRET KEY      │                         │
│              └───────────┬────────────┘                         │
│                          │                                      │
│                          ▼                                      │
│              ┌────────────────────────┐                         │
│              │    UTILITY COMPANY     │                         │
│              │   (Authorized Only)    │                         │
│              │                        │                         │
│              │  Decrypt(E(Σdᵢ))       │  ← Only aggregates     │
│              │  Make LB decision      │                         │
│              │  ✓ HAS SECRET KEY     │                         │
│              └────────────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Security Model

| Entity | Trust Level | Sees | Learns |
|--------|-------------|------|--------|
| Household | Self | Own plaintext | Only own data |
| Other Houses | Untrusted | Nothing | Nothing |
| Coordinator | Honest-but-curious | Ciphertext only | Nothing |
| Utility | Trusted | Aggregates only | Total/avg only |

## Cryptographic Parameters

- **Scheme**: CKKS (TenSEAL)
- **Security**: 128-bit (NIST standard)
- **Polynomial Degree**: 8192
- **Precision**: ~12 decimal digits

## Performance

| Agents | Encrypted | Plaintext | Overhead |
|--------|-----------|-----------|----------|
| 10 | ~50 ms | ~0.01 ms | ~5000x |
| 50 | ~200 ms | ~0.05 ms | ~4000x |
| 100 | ~400 ms | ~0.1 ms | ~4000x |

The overhead is acceptable for privacy guarantees in power grid applications where decisions are made every 15 minutes.

## Project Structure

```
smart-grid-he/
├── core/               # FHE engine and security
│   ├── fhe_engine.py      # CKKS encryption core
│   ├── key_management.py  # Key generation/distribution
│   └── security_logger.py # Audit trail
├── agents/             # Household agents
│   ├── household_agent.py    # Individual agent
│   ├── demand_generator.py   # Realistic demand patterns
│   └── agent_manager.py      # Multi-agent orchestration
├── coordinator/        # Grid coordinator
│   ├── grid_coordinator.py    # Main coordinator
│   ├── encrypted_aggregator.py # HE operations
│   └── load_balancer.py       # Decision making
├── server/             # FastAPI backend
├── dashboard/          # Web UI
├── evaluation/         # Benchmarks
└── run_demo.py         # Entry point
```

## Academic Context

This project demonstrates:
1. Practical application of FHE to smart grid privacy
2. Multi-agent system design with cryptographic security
3. Trade-offs between privacy and performance
4. Real-world relevant system (IEEE/NIST smart grid standards)

## License

MIT License - For academic and research use.
