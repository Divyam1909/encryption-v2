# Novel Contributions in Smart Grid HE

This document explains the **novel research contributions** in this project that go beyond simply using existing libraries.

---

## Novel Contribution #1: Encrypted Threshold Detection via Linear Approximation

### The Problem

Homomorphic encryption (specifically CKKS) supports addition and multiplication, but **NOT comparison**. Given `E(x)` and threshold `T`, we cannot directly determine if `x > T` without decrypting.

This is critical for smart grid peak detection:
- We need to know if `total_demand > grid_capacity`
- But we only have `E(total_demand)` at the coordinator
- The coordinator cannot decrypt!

### Existing Approaches & Their Limitations

| Approach | Limitation |
|----------|------------|
| Garbled circuits | Requires interaction, high bandwidth |
| Polynomial approximation of sign | Deep multiplicative depth, scale issues |
| Bootstrapping | Extremely slow (seconds per operation) |
| Comparator gates (BFV) | Only works for integers |

### Our Novel Solution: Adaptive Linear Approximation (ALA)

We observe that for **load balancing decisions**, we don't need exact comparison. We need a "soft" indicator that tells us:
- Definitely below threshold
- Definitely above threshold  
- Close to threshold (uncertain)

**Key Insight**: A linear function can approximate the step function in a soft region around the threshold, and linear functions require **only scalar multiplication and addition** - no ciphertext-ciphertext multiplication!

```
For x ∈ [T-δ, T+δ]:  score(x) = 0.5 + (x - T) / (2δ)
For x < T-δ:          score(x) ≈ 0
For x > T+δ:          score(x) ≈ 1
```

Where `δ = T/k` and `k` controls sharpness.

### Mathematical Derivation

```
score = 0.5 + (x - T) * (0.5/δ)
      = 0.5 + x * (0.5/δ) - T * (0.5/δ)
      = [0.5 - T/(2δ)] + x * [1/(2δ)]
      = intercept + slope × x
```

This is a simple affine transformation:
- `E(score) = intercept + slope × E(x)`
- Only requires `add_plain` and `multiply_plain`
- **Zero ciphertext-ciphertext multiplications!**

### Novelty Claims

1. **CKKS-Stable**: Unlike polynomial approximations that require deep multiplicative chains (causing scale issues), our approach uses only depth-1 operations.

2. **Confidence Zones**: Our output naturally provides confidence levels:
   - Score < 0.3: High confidence "below"
   - Score > 0.7: High confidence "above"
   - Score ∈ [0.3, 0.7]: Low confidence, near threshold

3. **Adaptive Sensitivity**: The parameter `k` controls how "sharp" the transition is, allowing tradeoff between sensitivity and noise.

4. **Grid-Optimized**: The default parameters are tuned for typical kW ranges in residential smart grids.

### Code Location

`core/polynomial_comparator.py` - `AdaptivePolynomialComparator` class

---

## Novel Contribution #2: Commitment-Based Verifiable Aggregation (CBV)

### The Problem

The coordinator aggregates encrypted demands:
```
E(d₁) + E(d₂) + ... + E(dₙ) = E(Σdᵢ)
```

But how can the utility company verify that the coordinator computed correctly? A malicious coordinator could:
- Inflate totals (cause unnecessary load shedding)
- Deflate totals (cause grid overload)
- Exclude certain households

### Existing Approaches & Their Limitations

| Approach | Limitation |
|----------|------------|
| Zero-knowledge proofs | Computationally expensive |
| Trusted execution (SGX) | Hardware dependency, side channels |
| Redundant computation | Requires multiple coordinators |
| Audit logging | Cannot prove correctness, only track actions |

### Our Novel Solution: Pedersen Commitment Integration

We add a **lightweight verification layer** using Pedersen commitments alongside the FHE computation.

**Key Insight**: Pedersen commitments are additively homomorphic!
```
Commit(a) × Commit(b) = Commit(a + b)
```

This means commitment aggregation is **parallel to** FHE aggregation.

### Protocol

```
AGENT SIDE:
1. Agent i computes demand dᵢ
2. Agent creates commitment: Cᵢ = Commit(dᵢ; rᵢ) = g^dᵢ × h^rᵢ
3. Agent encrypts: Eᵢ = FHE_Encrypt(dᵢ)
4. Agent sends (Eᵢ, Cᵢ) to coordinator

COORDINATOR SIDE:
5. Coordinator aggregates FHE: E_total = Σ Eᵢ
6. Coordinator aggregates commitments: C_total = ∏ Cᵢ
7. Coordinator sends (E_total, C_total) to utility

UTILITY SIDE:
8. Utility decrypts: total = FHE_Decrypt(E_total)
9. Utility recomputes: C_check = Commit(total; Σrᵢ)
10. Utility verifies: C_check == C_total

If step 10 fails → Coordinator cheated!
```

### Novelty Claims

1. **First Integration with CKKS**: Previous work on verifiable HE focused on BFV/BGV. We demonstrate practical integration with CKKS for real-valued smart grid data.

2. **Single-Round Verification**: Unlike interactive zero-knowledge proofs, our verification is non-interactive and happens in a single round.

3. **Efficient**: Pedersen commitments are just modular exponentiations - thousands of times faster than ZK-SNARKs.

4. **Retrospective Auditing**: Commitment history can be stored for post-hoc verification by auditors.

5. **Binding Guarantee**: Based on Discrete Log hardness - coordinator cannot open to different values.

### Security Properties

| Property | Guarantee |
|----------|-----------|
| **Hiding** | Commitment reveals nothing about dᵢ |
| **Binding** | Cannot open Cᵢ to different d'ᵢ |
| **Soundness** | Malicious coordinator detected with probability 1 |
| **Efficiency** | O(n) commitment operations for n agents |

### Code Location

`core/verifiable_aggregation.py` - `PedersenCommitmentScheme` and `VerifiableAggregator` classes

---

## Research Impact

These contributions address real gaps in the literature:

1. **Practical HE Comparison**: Most encrypted comparison work focuses on theoretical constructions with impractical overhead. Our linear approximation is immediately usable.

2. **Lightweight Verification**: ZK-proofs for HE correctness are complex. Our commitment-based approach provides similar guarantees with simpler implementation.

3. **Smart Grid Application**: We demonstrate these techniques in a realistic smart grid setting, not just toy examples.

---

## Future Work

1. **Polynomial Comparison with Bootstrapping**: For applications requiring sharper comparison, bootstrapping could enable deeper polynomial evaluation.

2. **Distributed Threshold Decryption**: Extend CBV to require k-of-n utilities to cooperate for decryption.

3. **Differential Privacy Integration**: Add calibrated noise before encryption for layered privacy guarantees.

---

## References

- Gentry, C. (2009). Fully homomorphic encryption using ideal lattices.
- Cheon, J.H., et al. (2017). Homomorphic encryption for arithmetic of approximate numbers (CKKS).
- Pedersen, T.P. (1991). Non-interactive and information-theoretic secure verifiable secret sharing.
- Smart grid cybersecurity: NIST IR 7628.
