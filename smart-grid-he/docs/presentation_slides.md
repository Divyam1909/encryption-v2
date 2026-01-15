# Privacy-Preserving Smart Grid Load Balancing
## Presentation Slides

---

# Slide 1: Title

## 🔒 Privacy-Preserving Smart Grid
### Load Balancing Using Fully Homomorphic Encryption

**Authors:** [Your Name]  
**Institution:** IIT Dharwad  
**Date:** January 2026

---

# Slide 2: The Problem

## 📍 Smart Grids Need Data, But Data Reveals Privacy

### What Smart Grids Do:
- Coordinate electricity demand across thousands of homes
- Detect peak loads before grid overload
- Issue load reduction commands

### The Privacy Problem:
**Electricity data reveals sensitive lifestyle information:**
- 🏠 When you're home or away
- 🩺 Medical equipment usage
- 📺 Entertainment habits
- 🕒 Work schedules

> *"A coordinator that sees your power data knows more about you than you'd share with a stranger."*

---

# Slide 3: Why Standard Encryption Fails

## 🔐 Traditional Solutions Don't Work

| Approach | Why It Fails |
|----------|-------------|
| **No Encryption** | Coordinator sees everything |
| **TLS (HTTPS)** | Protects transit, but coordinator must decrypt to compute |
| **End-to-End** | Coordinator can't compute aggregates |
| **Trusted Hardware** | Side-channel vulnerabilities, hardware trust issues |

### The Challenge:
**We need the coordinator to COMPUTE on data it cannot READ.**

---

# Slide 4: Our Solution - Homomorphic Encryption

## 💡 Compute on Encrypted Data

### Fully Homomorphic Encryption (FHE) allows:
```
E(a) + E(b) = E(a + b)    ← Addition on encrypted data
E(a) × c = E(a × c)       ← Scalar multiplication
```

### Our Architecture:
1. **Households** encrypt their demand locally
2. **Coordinator** aggregates *encrypted* values (never decrypts)
3. **Utility Company** decrypts only the final aggregate

### Result:
- ✅ Coordinator computes total grid demand
- ✅ Cannot see individual consumption
- ✅ Mathematically guaranteed privacy

---

# Slide 5: CKKS Encryption Scheme

## 🔢 Why CKKS?

### CKKS (Cheon-Kim-Kim-Song):
- Designed for **approximate arithmetic on real numbers**
- Perfect for power data (3.45 kW, not just whole numbers)

| Parameter | Value |
|-----------|-------|
| Security Level | 128-bit (military grade) |
| Polynomial Degree | 8192-16384 |
| Precision | ~10⁻⁷ relative error |
| Library | TenSEAL (Python) |

### Trade-offs:
- ⏱️ ~1000x slower than plaintext
- 📦 ~1000x larger ciphertext size
- ✅ Acceptable for 15-minute smart grid intervals

---

# Slide 6: Novel Contribution #1

## ⭐ Encrypted Threshold Detection

### The Problem:
FHE cannot compare values directly.
- ❌ Cannot compute: `if E(demand) > 80% capacity then...`
- Why? Comparison requires decryption

### Our Solution: Linear Approximation
```
score(x) = 0.5 + (x - Threshold) × (0.5 / δ)
```

| Score | Interpretation |
|-------|----------------|
| ≈ 0.0 | Definitely BELOW threshold |
| ≈ 0.5 | Near threshold (uncertain) |
| ≈ 1.0 | Definitely ABOVE threshold |

### Why Novel:
- **Zero ciphertext-ciphertext multiplication**
- Works within CKKS noise budget
- First practical comparison for encrypted smart grid data

---

# Slide 7: Novel Contribution #2

## ⭐ Verifiable Aggregation

### The Problem:
How do we know the coordinator computed correctly?
- A malicious coordinator could report fake totals
- No one would know without decrypting individual values

### Our Solution: Pedersen Commitments
Each household sends alongside encrypted data:
```
Commitment = g^value × h^randomness
```

### Verification:
- Commitments are **additively homomorphic**
- Utility can verify: decrypted sum matches aggregate commitment
- **Detects any cheating with 100% probability**

### Why Novel:
- First Pedersen + CKKS integration for smart grids
- Single-round, non-interactive verification

---

# Slide 8: System Architecture

## 🏗️ Who Knows What?

```
┌─────────────────────────────────────────────────┐
│           ⚡ UTILITY COMPANY (Trusted)            │
│  • Generates & holds SECRET KEY                 │
│  • Decrypts only aggregate results              │
│  • Verifies computation correctness             │
└─────────────────────────────────────────────────┘
                       ▲
                       │ E(Σdᵢ) + Verification
                       │
┌─────────────────────────────────────────────────┐
│         ⬡ COORDINATOR (Untrusted)               │
│  • Has only PUBLIC KEY                          │
│  • Aggregates encrypted values                  │
│  • CANNOT decrypt anything                      │
└─────────────────────────────────────────────────┘
         ▲         ▲         ▲
    E(d₁) │    E(d₂) │    E(dₙ) │
         │         │         │
      🏠 H1     🏠 H2     🏠 Hₙ
```

---

# Slide 9: Security Guarantees

## 🛡️ What Each Entity Learns

| Entity | Data Access | What They Learn |
|--------|-------------|-----------------|
| 🏠 Household | Own plaintext only | Only their own data |
| 🏘️ Other Households | Nothing | Nothing |
| ⬡ Coordinator | Only ciphertexts | **Nothing** (no secret key) |
| ⚡ Utility | Decrypted aggregates | Total & average demand |

### Cryptographic Properties:
- **Semantic Security**: Ciphertexts indistinguishable from random
- **CPA Security**: Secure against chosen-plaintext attacks
- **128-bit Security**: Would take billions of years to crack

---

# Slide 10: Live Demo

## 🖥️ Dashboard Features

### Grid Topology Tab:
- Visual representation of households around coordinator
- Animated data flow showing encrypted packets
- Per-house demand meters

### Analytics Tab:
- Encrypted vs Plaintext comparison (proves FHE accuracy)
- Grid utilization over time
- Computation time metrics

### System Info Tab:
- CKKS parameters explained
- Novel contributions with expandable details
- Security model table

**URL: http://localhost:8000**

---

# Slide 11: Performance Results

## 📊 Benchmarks

| Metric | Value | Practical? |
|--------|-------|-----------|
| Encryption (per value) | ~15 ms | ✅ Yes |
| Aggregation (25 agents) | ~100 ms | ✅ Yes |
| Aggregation (100 agents) | ~400 ms | ✅ Yes |
| Total round (25 agents) | ~200 ms | ✅ Yes |
| Smart grid interval | 15 min | ← Our target |

### Accuracy:
- Average error: 10⁻⁹ (negligible)
- Maximum error: <10⁻⁷

**Conclusion: FHE is practical for smart grid aggregation.**

---

# Slide 12: Comparison with Related Work

## 📚 How We Compare

| Approach | Privacy | Computation | Verification | Practical |
|----------|---------|-------------|--------------|-----------|
| Differential Privacy | Partial | Any | No | Yes |
| Secure MPC | Full | Limited | No | No (high overhead) |
| TEE (Intel SGX) | Partial | Any | No | Yes (but trust issues) |
| Paillier FHE | Full | Add only | No | Partial |
| **Ours (CKKS + Pedersen)** | **Full** | **Add + Scalar** | **Yes** | **Yes** |

---

# Slide 13: Limitations

## ⚠️ Honest Assessment

### What This System Cannot Do:
1. **Individual decisions** - Cannot make per-household recommendations on encrypted data
2. **Complex analytics** - Limited to aggregation (no ML on encrypted data in this version)
3. **Real-time** - Not suitable for <1 second response requirements

### Resource Requirements:
- Ciphertext size: ~256 KB per value
- 1000 houses × every 15 min = ~1 GB/hour network

---

# Slide 14: Future Work

## 🚀 Next Steps

- Scale to 10,000+ households
- Add differential privacy layer for aggregate output
- Implement hierarchical aggregation
- Encrypted machine learning for demand prediction

---

# Slide 15: Conclusion

## 🎯 Key Takeaways

1. ✅ **Practical FHE** for smart grid load balancing
2. ✅ **Novel threshold detection** without ciphertext multiplication
3. ✅ **Verifiable aggregation** detecting malicious coordinators
4. ✅ **Complete working system** with visualization dashboard

---

# Slide 16: References

1. **Gentry, C. (2009)** - "A Fully Homomorphic Encryption Scheme"
2. **Cheon et al. (2017)** - "Homomorphic Encryption for Arithmetic of Approximate Numbers" (CKKS)
3. **TenSEAL Library** - https://github.com/OpenMined/TenSEAL
4. **NIST IR 7628** - Guidelines for Smart Grid Cybersecurity
5. **IEEE 2030.5** - Smart Energy Profile Application Protocol
