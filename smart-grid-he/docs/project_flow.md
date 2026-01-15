# Smart Grid HE - System Flow & Usefulness

This document explains how data flows through the system and why each component is essential for privacy-preserving smart grid operations.

---

## High-Level System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SMART GRID SYSTEM FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

  STEP 1: KEY GENERATION (One-time setup)
  ═══════════════════════════════════════
  
  ┌─────────────────────────────┐
  │     UTILITY COMPANY         │
  │     (Trusted Entity)        │
  │                             │
  │  SmartGridFHE.generate()    │──── Creates master FHE keys
  │         │                   │
  │         ├── Secret Key ─────┼───► Kept securely by utility
  │         │                   │
  │         └── Public Key ─────┼───► Distributed to everyone
  └─────────────────────────────┘
  
  
  STEP 2: AGENT INITIALIZATION
  ════════════════════════════
  
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │  House 001   │   │  House 002   │   │  House 025   │
  │              │   │              │   │              │
  │ Receives     │   │ Receives     │   │ Receives     │
  │ PUBLIC key   │   │ PUBLIC key   │   │ PUBLIC key   │
  │ only!        │   │ only!        │   │ only!        │
  │              │   │              │   │              │
  │ CAN encrypt  │   │ CAN encrypt  │   │ CAN encrypt  │
  │ CANNOT       │   │ CANNOT       │   │ CANNOT       │
  │ decrypt      │   │ decrypt      │   │ decrypt      │
  └──────────────┘   └──────────────┘   └──────────────┘
  
  
  STEP 3: DEMAND GENERATION (Every 15 minutes)
  ════════════════════════════════════════════
  
  Each household generates demand based on:
  
  ┌───────────────────────────────────────────────────────────────┐
  │                  DEMAND FACTORS                                │
  │                                                                │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
  │  │ Time of Day │  │ Day Type    │  │ Season      │            │
  │  │             │  │             │  │             │            │
  │  │ Morning     │  │ Weekday vs  │  │ Summer AC   │            │
  │  │ peak: 7 AM  │  │ Weekend     │  │ Winter heat │            │
  │  │             │  │             │  │             │            │
  │  │ Evening     │  │ Weekend has │  │ Spring/Fall │            │
  │  │ peak: 7 PM  │  │ higher use  │  │ = lower use │            │
  │  └─────────────┘  └─────────────┘  └─────────────┘            │
  │                                                                │
  │  Typical range: 0.5 kW to 15 kW per household                 │
  └───────────────────────────────────────────────────────────────┘
  
  
  STEP 4: LOCAL ENCRYPTION
  ════════════════════════
  
  ┌──────────────────────────────────────────────────────────────┐
  │  HOUSEHOLD AGENT                                              │
  │                                                               │
  │  demand = 3.45 kW  ─────► E(3.45) = "A8fK2m9x...QrT5"       │
  │  (private)                (encrypted - 326 KB ciphertext)    │
  │                                                               │
  │  The plaintext (3.45 kW) NEVER leaves the household!         │
  └──────────────────────────────────────────────────────────────┘
  
  
  STEP 5: TRANSMISSION TO COORDINATOR
  ═══════════════════════════════════
  
  House 001: E(d₁) = "A8fK2m..."  ───┐
  House 002: E(d₂) = "B7gL3n..."  ───┤
  House 003: E(d₃) = "C6hM4o..."  ───┼───► COORDINATOR
  ...                                │     (receives ONLY ciphertext)
  House 025: E(d₂₅) = "Z1aR9x..." ───┘
  
  
  STEP 6: HOMOMORPHIC AGGREGATION (The Magic!)
  ════════════════════════════════════════════
  
  ┌────────────────────────────────────────────────────────────────┐
  │  COORDINATOR (Honest-but-Curious)                              │
  │  HAS: Public key only                                          │
  │  CANNOT: Decrypt anything                                      │
  │                                                                │
  │  ┌──────────────────────────────────────────────────────────┐ │
  │  │  HOMOMORPHIC ADDITION                                     │ │
  │  │                                                           │ │
  │  │  E(d₁) + E(d₂) + E(d₃) + ... + E(d₂₅)                   │ │
  │  │         =                                                 │ │
  │  │  E(d₁ + d₂ + d₃ + ... + d₂₅)                            │ │
  │  │         =                                                 │ │
  │  │  E(total)   ◄── Still encrypted!                         │ │
  │  └──────────────────────────────────────────────────────────┘ │
  │                                                                │
  │  ┌──────────────────────────────────────────────────────────┐ │
  │  │  HOMOMORPHIC AVERAGE                                      │ │
  │  │                                                           │ │
  │  │  E(total) × (1/25) = E(total/25) = E(average)            │ │
  │  │                                                           │ │
  │  │  Division is multiplication by reciprocal!                │ │
  │  └──────────────────────────────────────────────────────────┘ │
  │                                                                │
  │  RESULT: Coordinator has E(total) and E(average)              │
  │  BUT CANNOT SEE the actual values!                            │
  └────────────────────────────────────────────────────────────────┘
  
  
  STEP 7: UTILITY COMPANY DECRYPTION
  ══════════════════════════════════
  
  ┌────────────────────────────────────────────────────────────────┐
  │  UTILITY COMPANY (Authorized Decryptor)                        │
  │  HAS: Secret key                                               │
  │  CAN: Decrypt aggregates only                                  │
  │                                                                │
  │  Receives: E(total), E(average)                               │
  │                                                                │
  │  Decrypts:                                                     │
  │    D(E(total)) = 156.75 kW                                    │
  │    D(E(average)) = 6.27 kW                                    │
  │                                                                │
  │  IMPORTANT: Utility sees ONLY aggregates!                     │
  │  Cannot determine individual household consumption!            │
  └────────────────────────────────────────────────────────────────┘
  
  
  STEP 8: LOAD BALANCING DECISION
  ═══════════════════════════════
  
  ┌────────────────────────────────────────────────────────────────┐
  │  DECISION LOGIC                                                │
  │                                                                │
  │  Grid Capacity: 100 kW                                        │
  │  Total Demand:  156.75 kW                                     │
  │  Utilization:   156.75 / 100 = 156.75%  ⚠ OVERLOAD!          │
  │                                                                │
  │  Decision Table:                                               │
  │  ┌──────────────────┬────────────────────┐                    │
  │  │ Utilization      │ Action             │                    │
  │  ├──────────────────┼────────────────────┤                    │
  │  │ < 80%            │ None (OK)          │                    │
  │  │ 80% - 90%        │ Reduce 10%         │                    │
  │  │ 90% - 95%        │ Reduce 20%         │                    │
  │  │ 95% - 100%       │ Reduce 30%         │                    │
  │  │ > 100%           │ CRITICAL - 50%     │                    │
  │  └──────────────────┴────────────────────┘                    │
  │                                                                │
  │  Result: Request 50% reduction from all households            │
  └────────────────────────────────────────────────────────────────┘
  
  
  STEP 9: BROADCAST LOAD BALANCE COMMAND
  ══════════════════════════════════════
  
  Utility sends reduction factor (0.5) to all households:
  
  House 001 ◄── "Reduce to 50%"
  House 002 ◄── "Reduce to 50%"
  ...
  House 025 ◄── "Reduce to 50%"
  
  Households voluntarily comply in next round.
```

---

## Why Each Component Matters

### 1. FHE Engine (`core/fhe_engine.py`)

**Purpose**: Enable computation on encrypted data.

**Without it**: Coordinator would need to see plaintext to compute totals.

**Key innovation**: 
```
E(a) + E(b) = E(a + b)  ← Math works on ciphertext!
```

### 2. Security Logger (`core/security_logger.py`)

**Purpose**: Prove privacy preservation to auditors.

**Without it**: No way to verify coordinator didn't access plaintext.

**Key output**:
```
Coordinator operations: [ciphertext, ciphertext, ...]
Plaintext access: NONE ✓
```

### 3. Household Agent (`agents/household_agent.py`)

**Purpose**: Represent autonomous privacy-conscious households.

**Multi-agent properties**:
- Each agent decides independently
- No shared state between agents
- Only encrypted data leaves agent

### 4. Demand Generator (`agents/demand_generator.py`)

**Purpose**: Create realistic test data.

**Based on real data**:
- EIA (Energy Information Administration) patterns
- NREL ResStock dataset characteristics
- Time-of-day consumption curves

### 5. Grid Coordinator (`coordinator/grid_coordinator.py`)

**Purpose**: Aggregate demands for load balancing.

**Security**: Has PUBLIC key only - mathematically cannot decrypt.

### 6. Utility Decision Maker (`coordinator/load_balancer.py`)

**Purpose**: Make final decisions after decrypting aggregates.

**Privacy guarantee**: Sees only total/average, not individual demands.

---

## Why This System is Useful

### Problem: Smart Grid Privacy Dilemma

Smart grids need load balancing, which traditionally requires:
1. Collect individual consumption from all homes
2. Aggregate to find total demand
3. Make load balancing decisions

**But this reveals sensitive data**:
- When are you home?
- What appliances do you use?
- Your daily routine patterns
- Medical equipment usage

### Traditional Solutions (And Why They Fail)

| Approach | Failure Mode |
|----------|--------------|
| **Trust the utility** | Data breaches, insider threats |
| **Anonymization** | Can be re-identified with side data |
| **Differential privacy** | Adds noise, reduces accuracy |
| **Secure hardware (SGX)** | Side-channel attacks, trust issues |

### Our Solution: Homomorphic Encryption

| Property | Benefit |
|----------|---------|
| **Mathematical guarantee** | Cannot learn individual values |
| **No trusted party needed** | Coordinator is untrusted by design |
| **Exact computation** | ~10⁻⁹ error, not random noise |
| **Auditable** | Security logs prove compliance |

---

## Real-World Applications

### 1. Smart Grid Load Balancing (This Project)
- Coordinate demand without privacy loss
- Comply with GDPR, CCPA data minimization

### 2. Healthcare Analytics
- Aggregate patient statistics
- Hospital can't see individual records

### 3. Financial Reporting
- Compute totals across institutions
- No individual account exposure

### 4. Survey/Voting Systems
- Aggregate results
- Individual votes remain secret

---

## Performance Trade-offs

| Metric | Encrypted | Plaintext | Acceptable? |
|--------|-----------|-----------|-------------|
| Computation | ~20 ms | ~0.01 ms | ✓ Yes - grid runs every 15 min |
| Ciphertext size | 326 KB | 8 bytes | ✓ Yes - network can handle |
| Accuracy | 10⁻⁹ error | Exact | ✓ Yes - negligible for kW |

**Conclusion**: The overhead is acceptable for the privacy guarantee.

---

## Security Properties Summary

1. **Confidentiality**: Individual demands never exposed
2. **Integrity**: Checksums verify ciphertext not tampered
3. **Auditability**: All operations logged with data types
4. **Forward secrecy**: New keys can be generated per session
5. **No single point of trust**: Even utility only sees aggregates
