# Cryptography Guide
## Complete Reference for Encryption Used in This Project

---

## Overview

This project uses three cryptographic primitives:

| Cryptosystem | Purpose | Security Level |
|--------------|---------|----------------|
| **CKKS (FHE)** | Encrypt household demands | 128-bit |
| **Pedersen Commitments** | Verify aggregation correctness | 2048-bit DLP |
| **SHA-256** | Checksums and key derivation | 256-bit |

---

## 1. CKKS Homomorphic Encryption

### What is CKKS?

CKKS (Cheon-Kim-Kim-Song) is a Fully Homomorphic Encryption scheme designed for **approximate arithmetic on real numbers**. Unlike other FHE schemes that work only with integers, CKKS can handle floating-point values like `3.45 kW`.

### Why We Use It

Smart grid demands are real-valued (e.g., 3.456 kW). CKKS allows us to:
- Encrypt real numbers directly
- Perform addition on encrypted values
- Perform scalar multiplication on encrypted values

### Homomorphic Properties

```
E(a) + E(b) = E(a + b)     # Encrypted addition
E(a) × c = E(a × c)        # Scalar multiplication (c is plaintext)
```

### Parameters in Our Implementation

```python
# From core/fhe_engine.py
poly_modulus_degree = 16384      # Ring dimension (security vs performance)
coeff_mod_bit_sizes = [60, 40, 40, 60]  # Modulus chain
global_scale = 2**40             # Precision: ~12 decimal digits
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `poly_modulus_degree` | 8192 or 16384 | Higher = more security, slower |
| `global_scale` | 2⁴⁰ | Determines decimal precision |
| Security Level | 128-bit | Equivalent to AES-128 |

### Precision and Error

CKKS introduces small errors (~10⁻⁷ relative error):
- **Encoding error**: Converting float to polynomial
- **Rounding error**: After homomorphic operations
- **Acceptable for power grids**: 0.0000001 × 100 kW = 0.00001 kW error

### Key Structure

```
┌─────────────────────────────────────────┐
│           Key Generation                 │
└─────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │ Secret Key   │ ← Held by Utility ONLY
    │ (sk)         │   Used for decryption
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ Public Key   │ ← Distributed to all
    │ (pk)         │   Used for encryption
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ Relin Keys   │ ← For multiplication
    │ Galois Keys  │   (not used in this project)
    └──────────────┘
```

### Library Used

**TenSEAL** - Python wrapper around Microsoft SEAL
- GitHub: https://github.com/OpenMined/TenSEAL
- Install: `pip install tenseal`

---

## 2. Pedersen Commitments

### What is a Pedersen Commitment?

A cryptographic commitment scheme that allows you to:
1. **Commit** to a value without revealing it
2. **Open** the commitment later to prove the value

### Mathematical Form

```
Commitment: C = g^m × h^r mod p

Where:
- g, h = public generators (nothing-up-my-sleeve numbers)
- m = the value being committed (scaled to integer)
- r = random blinding factor (kept secret)
- p = large prime
```

### Why We Use It

To verify the coordinator computed aggregates correctly:
- Each household sends `C_i = Commit(demand_i)`
- Coordinator multiplies: `C_agg = ∏ C_i`
- Utility verifies: `C_agg == Commit(decrypted_sum)`

### Homomorphic Property

```
Commit(a) × Commit(b) = Commit(a + b)

Proof:
C(a) × C(b) = (g^a × h^r1) × (g^b × h^r2)
            = g^(a+b) × h^(r1+r2)
            = C(a+b; r1+r2)
```

### Parameters in Our Implementation

```python
# From core/verifiable_aggregation.py
PEDERSEN_PRIME = RFC 3526 MODP Group 14  # 2048-bit prime
PEDERSEN_G = 2                            # First generator
PEDERSEN_H = pow(g, hash(seed), p)        # Second generator
DEFAULT_SCALE_FACTOR = 1_000_000          # 6 decimal places
```

### Security Properties

| Property | Meaning |
|----------|---------|
| **Perfectly Hiding** | Commitment reveals nothing about value (information-theoretic) |
| **Computationally Binding** | Cannot change committed value (based on DLP hardness) |

### Verification Flow

```
1. Agent creates:
   - commitment = g^(demand × scale) × h^randomness mod p
   - opening = (demand, randomness)

2. Agent sends:
   - commitment → Coordinator
   - opening → Utility (secure channel)

3. Coordinator:
   - C_agg = ∏ C_i (multiply all commitments)

4. Utility verifies:
   - sum_openings = Σ(demand_i, randomness_i)
   - expected_C = g^(Σdemand × scale) × h^(Σrandomness) mod p
   - CHECK: C_agg == expected_C
```

---

## 3. SHA-256 Hash Function

### Usage in This Project

1. **Ciphertext checksums**: Verify data integrity
   ```python
   checksum = hashlib.sha256(ciphertext).hexdigest()[:12]
   ```

2. **Generator derivation**: Create second Pedersen generator
   ```python
   h = pow(g, int.from_bytes(sha256(seed).digest(), 'big'), p)
   ```

### Properties

| Property | Value |
|----------|-------|
| Output size | 256 bits (64 hex chars) |
| Collision resistance | 2¹²⁸ operations to find collision |
| Preimage resistance | 2²⁵⁶ operations to reverse |

---

## 4. Security Levels Summary

| Component | Security Level | Attack Complexity |
|-----------|---------------|-------------------|
| CKKS encryption | 128-bit | 2¹²⁸ operations |
| Pedersen DLP | ~112-bit (2048-bit) | 2¹¹² operations |
| SHA-256 collision | 128-bit | 2¹²⁸ operations |

**Weakest link**: Pedersen at 112-bit, but still requires billions of years to break.

---

## 5. What Each Entity Can See

### Household Agent

```python
# Has access to:
public_context  # Can encrypt
own_demand      # Plaintext demand value
own_randomness  # For commitment

# Cannot access:
secret_key      # Never leaves utility
other_demands   # Other households' data
```

### Coordinator

```python
# Receives:
E(d_1), E(d_2), ..., E(d_n)  # Encrypted demands
C_1, C_2, ..., C_n           # Commitments

# Can compute:
E(Σd_i) = Σ E(d_i)  # Homomorphic sum
C_agg = ∏ C_i       # Commitment product

# Cannot do:
decrypt(E(d_i))  # No secret key!
open(C_i)        # No randomness!
```

### Utility Company

```python
# Has access to:
secret_key           # For decryption
all_openings         # (demand, randomness) from agents
E(Σd_i)             # Encrypted aggregate from coordinator
C_agg               # Commitment aggregate from coordinator

# Can compute:
Σd = decrypt(E(Σd_i))  # Get actual total
verify(C_agg, Σd)       # Check coordinator honesty

# Cannot access:
individual_demands_from_ciphertext  # Only sees aggregate
```

---

## 6. Attack Scenarios

### Attack 1: Eavesdropper

**Threat**: Intercepts `E(d_i)` on the network

**Result**: Gets random-looking bytes. Without secret key, cannot decrypt.

**Security**: 128-bit (CKKS semantic security)

### Attack 2: Malicious Coordinator

**Threat**: Reports fake aggregate `E(fake_sum)`

**Result**: Verification fails: `C_agg ≠ Commit(fake_sum)`

**Security**: Detected with 100% probability (Pedersen binding)

### Attack 3: Corrupt Utility Employee

**Threat**: Has secret key, tries to learn individual demands

**Result**: Can only decrypt aggregate. Individual ciphertexts are added homomorphically before decryption.

**Security**: Only aggregate is ever decrypted (system design)

---

## 7. Code Examples

### Encrypting a Demand

```python
from core.fhe_engine import SmartGridFHE

# Utility generates keys
utility_fhe = SmartGridFHE()
public_context = utility_fhe.get_public_context()

# Household encrypts (only has public context)
household_fhe = SmartGridFHE.from_context(public_context)
encrypted = household_fhe.encrypt_demand(3.45, "house_001")
```

### Creating a Commitment

```python
from core.verifiable_aggregation import VerifiableAggregator

aggregator = VerifiableAggregator()
commitment, opening = aggregator.create_agent_contribution(
    demand_kw=3.45,
    agent_id="house_001"
)
# Send commitment to coordinator
# Send opening to utility via secure channel
```

### Verifying Aggregation

```python
# At utility side
result = aggregator.verify_aggregate(
    decrypted_sum=86.7,
    commitment_aggregate=c_agg,
    opening_aggregate=o_agg
)
print(result.is_valid)  # True if coordinator honest
```

---

## References

1. **CKKS Paper**: Cheon, J.H., et al. "Homomorphic Encryption for Arithmetic of Approximate Numbers" (ASIACRYPT 2017)

2. **TenSEAL**: https://github.com/OpenMined/TenSEAL

3. **Pedersen Commitments**: Pedersen, T.P. "Non-Interactive and Information-Theoretic Secure Verifiable Secret Sharing" (CRYPTO 1991)

4. **RFC 3526**: More Modular Exponential (MODP) Diffie-Hellman groups
