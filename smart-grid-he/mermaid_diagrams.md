# Mermaid Diagram Codes for Research Paper Figures

Render these at https://mermaid.live or using mermaid-cli.

## Figure 1: System Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor': '#e3f2fd', 'primaryBorderColor': '#1565c0', 'secondaryColor': '#fff3e0', 'tertiaryColor': '#e8f5e9'}}}%%
graph TD
    subgraph Households["Household Agents (Untrusted)"]
        H1["House 1<br/>d₁ = 3.45 kW"]
        H2["House 2<br/>d₂ = 2.18 kW"]
        H3["House 3<br/>d₃ = 5.72 kW"]
        HN["House N<br/>dₙ = ? kW"]
    end

    subgraph Encryption["CKKS Encryption (Public Key Only)"]
        E1["E(d₁)"]
        E2["E(d₂)"]
        E3["E(d₃)"]
        EN["E(dₙ)"]
    end

    subgraph Coordinator["Grid Coordinator (Semi-Honest, NO Secret Key)"]
        AGG["Homomorphic Aggregation<br/>E(Σdᵢ) = Σ E(dᵢ)"]
        AVG["Homomorphic Average<br/>E(avg) = E(Σ) × (1/n)"]
        MV["Encrypted Mat-Vec Multiply<br/>E(M) @ E(v) → E(Mv)"]
        ALT["ALT Threshold Detection<br/>E(score) = E(x) × slope + intercept"]
        COMM["Commitment Aggregation<br/>C_agg = Π Cᵢ"]
    end

    subgraph Utility["Utility Company (Trusted, HAS Secret Key)"]
        DEC["Decrypt(E(Σdᵢ)) → Σdᵢ"]
        VER["Verify: C_agg =? g^(Σdᵢ·s) × h^(Σrᵢ)"]
        DEC2["Load Balance Decision"]
    end

    H1 --> E1
    H2 --> E2
    H3 --> E3
    HN --> EN

    E1 --> AGG
    E2 --> AGG
    E3 --> AGG
    EN --> AGG

    AGG --> AVG
    AGG --> MV
    AGG --> ALT
    AGG --> COMM

    AVG --> DEC
    MV --> DEC
    COMM --> VER
    DEC --> DEC2
    VER --> DEC2

    style Households fill:#e3f2fd,stroke:#1565c0
    style Coordinator fill:#fff3e0,stroke:#e65100
    style Utility fill:#e8f5e9,stroke:#2e7d32
    style Encryption fill:#f3e5f5,stroke:#7b1fa2
```

## Supplementary: FHE Matrix-Vector Multiply Sequence

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    participant A as Agent/Data Owner
    participant C as Coordinator (No Secret Key)
    participant U as Utility (Has Secret Key)

    Note over A: Matrix M ∈ ℝ^(m×n), Vector v ∈ ℝ^n

    A->>A: E(row₁), E(row₂), ..., E(rowₘ) ← Encrypt matrix rows
    A->>A: E(v) ← Encrypt vector
    A->>C: Send E(row₁)...E(rowₘ), E(v)

    loop For each row i = 1 to m
        C->>C: E(pᵢ) ← E(rowᵢ) ⊗ E(v)  [ciph×ciph multiply]
        C->>C: E(rᵢ) ← Sum(E(pᵢ))  [SIMD rotation-and-add]
    end

    C->>U: Send E(r₁), E(r₂), ..., E(rₘ)
    U->>U: rᵢ ← Decrypt(E(rᵢ)) for each i
    Note over U: Result: Mv = [r₁, r₂, ..., rₘ]
```

## Supplementary: Verifiable Aggregation Protocol

```mermaid
%%{init: {'theme': 'base'}}%%
sequenceDiagram
    participant H as Household Agent i
    participant C as Coordinator
    participant U as Utility Company

    H->>H: Compute demand dᵢ
    H->>H: Cᵢ = g^(dᵢ·s) × h^(rᵢ) mod p
    H->>H: E(dᵢ) = CKKS.Encrypt(dᵢ)

    H->>C: Send (E(dᵢ), Cᵢ)
    H->>U: Send Opening Oᵢ = (dᵢ, rᵢ) [secure channel]

    Note over C: Aggregate E(Σdᵢ) = Σ E(dᵢ)
    Note over C: Aggregate C_agg = Π Cᵢ

    C->>U: Send (E(Σdᵢ), C_agg)

    U->>U: Decrypt: D̂ = Decrypt(E(Σdᵢ))
    U->>U: Compute: Σrᵢ from all openings
    U->>U: Verify: C_agg =? g^(D̂·s) × h^(Σrᵢ) mod p

    alt Verification Passes
        Note over U: ✓ Coordinator computed correctly
    else Verification Fails
        Note over U: ✗ MALICIOUS COORDINATOR DETECTED
    end
```
