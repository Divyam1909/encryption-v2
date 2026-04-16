# Novel Research Contributions

## Overview

This project makes two original contributions on top of existing FHE libraries.

---

## 1. Encrypted Threshold Detection via Linear Approximation

### Problem

The CKKS scheme supports addition and multiplication of ciphertexts, but **cannot directly compare values**. There is no native `E(x) > threshold` operation — comparison requires polynomial approximation, which is expensive and numerically unstable at the boundary.

### Our Solution

We approximate the Heaviside step function with a **piecewise linear function** that only requires scalar (ciphertext × plaintext constant) operations — no ciphertext-ciphertext multiplication:

```
score(x) = 0.5 + (x − T) × (0.5 / δ)
```

Where:
- `T` is the decision threshold (e.g. grid capacity)
- `δ` is the soft-zone half-width (configurable sensitivity)
- `score ≤ 0` → clearly below threshold
- `0 < score < 1` → uncertain zone
- `score ≥ 1` → clearly above threshold

**Key properties:**
- Requires only one homomorphic scalar multiplication and one scalar addition
- Works within CKKS numerical precision constraints
- Provides three-class output: `BELOW_THRESHOLD`, `UNCERTAIN`, `ABOVE_THRESHOLD`
- Sensitivity parameter `δ` provides a configurable confidence zone

**Implementation:** [`core/polynomial_comparator.py`](../core/polynomial_comparator.py)

---

## 2. Commitment-Based Verifiable Aggregation

### Problem

In the honest-but-curious threat model, the coordinator performs aggregation without seeing plaintext data. But how can the utility company (who holds the secret key) verify that the coordinator computed the sum **correctly** rather than substituting fabricated ciphertexts?

### Our Solution

Each household agent sends a **Pedersen commitment** alongside its FHE ciphertext:

```
Commit(x, r) = g^x · h^r   (mod p)
```

Pedersen commitments are **additively homomorphic** over multiplication:

```
Commit(a, r_a) × Commit(b, r_b) = Commit(a + b, r_a + r_b)
```

The coordinator aggregates both commitments and ciphertexts. The utility then:
1. Decrypts the FHE aggregate to get `Σxᵢ`
2. Multiplies all received commitments to get `Commit(Σxᵢ, Σrᵢ)`
3. Verifies the decrypted value matches the commitment

A malicious coordinator that substitutes a different ciphertext would need to forge a commitment, which is computationally infeasible under the discrete logarithm assumption.

**Detection probability:** 1 — any deviation is detected with certainty.

**Implementation:** [`core/verifiable_aggregation.py`](../core/verifiable_aggregation.py)

---

## Summary Table

| Contribution | Problem Solved | Implementation |
|---|---|---|
| Linear threshold approximation | CKKS has no comparison operator | `core/polynomial_comparator.py` |
| Pedersen commitment verification | Coordinator correctness cannot be verified | `core/verifiable_aggregation.py` |

---

## References

- Cheon, J. H., et al. "Homomorphic encryption for arithmetic of approximate numbers." *ASIACRYPT 2017*.
- Pedersen, T. P. "Non-interactive and information-theoretic secure verifiable secret sharing." *CRYPTO 1991*.
- TenSEAL Library: https://github.com/OpenMined/TenSEAL
