# Smart Grid HE - Project Structure Guide

A comprehensive reference for understanding each file and folder in this project.

---

## Root Directory

| File | Description |
|------|-------------|
| `run_demo.py` | **Main entry point** - Run with `--cli` for terminal demo, or without args for web dashboard |
| `requirements.txt` | Python dependencies (tenseal, fastapi, uvicorn, numpy, pandas) |
| `README.md` | Project overview, quick start guide, and architecture diagram |

---

## `core/` - Cryptographic Core

The heart of the privacy-preserving system. Contains all FHE operations and security components.

| File | Description |
|------|-------------|
| `__init__.py` | Module exports: `SmartGridFHE`, `EncryptedDemand`, `KeyManager`, `SecurityLogger` |
| `fhe_engine.py` | **CKKS FHE Engine** - The main encryption module. Implements: |
| | - `SmartGridFHE`: Main class for encryption/decryption |
| | - `encrypt_demand()`: Encrypt a kW value |
| | - `aggregate_demands()`: Homomorphic sum: E(d1) + E(d2) + ... = E(sum) |
| | - `compute_average()`: E(sum) x (1/n) = E(avg) |
| | - `get_public_context()`: For distribution to untrusted parties |
| | - `get_secret_context()`: For authorized decryptor only |
| `key_management.py` | **Key Manager** - Handles FHE key generation, storage, and distribution |
| | - `generate_keys()`: Create new master + public keys |
| | - `get_public_context()`: Distribute to agents/coordinator |
| | - `get_secret_context()`: Only for utility company |
| `security_logger.py` | **Audit Trail** - Logs all operations to prove privacy preservation |
| | - `log_agent_encrypt()`: Agent encrypts local demand |
| | - `log_coordinator_receive()`: Coordinator receives ciphertext |
| | - `log_coordinator_aggregate()`: Coordinator performs HE operation |
| | - `log_utility_decrypt()`: Utility decrypts aggregate |
| | - `generate_audit_report()`: Prove no plaintext leakage |

### Cryptographic Parameters (fhe_engine.py)
```
- Scheme: CKKS (supports real numbers)
- poly_modulus_degree: 8192 (128-bit security)
- coeff_mod_bit_sizes: [60, 40, 40, 60] (3 multiplication depth)
- global_scale: 2^40 (~12 decimal digit precision)
```

---

## `agents/` - Household Agents

Multi-agent system components. Each household is an autonomous agent.

| File | Description |
|------|-------------|
| `__init__.py` | Module exports: `HouseholdAgent`, `RealisticDemandGenerator`, `AgentManager` |
| `household_agent.py` | **Household Agent** - Represents one home in the smart grid |
| | - `HouseholdAgent`: Main agent class |
| | - `get_current_demand()`: Generate demand (private to agent) |
| | - `encrypt_demand()`: Encrypt before sending to coordinator |
| | - Has PUBLIC context only - CANNOT decrypt |
| `demand_generator.py` | **Realistic Demand Generator** - Creates believable consumption patterns |
| | - `LoadProfile`: Enum (RESIDENTIAL_SMALL, MEDIUM, LARGE, COMMERCIAL) |
| | - `RealisticDemandGenerator`: Generates time-varying demand |
| | - Uses time-of-day curves (morning peak, evening peak) |
| | - Weekend adjustments, seasonal factors |
| | - Based on EIA/NREL residential consumption research |
| | - Range: 0.5 kW to 15 kW (realistic residential) |
| `agent_manager.py` | **Agent Manager** - Spawns and manages multiple agents |
| | - `create_agents()`: Create N households with profile distribution |
| | - `collect_encrypted_demands()`: Gather E(d) from all agents |
| | - `broadcast_load_balance()`: Send reduction commands |
| | - `get_plaintext_demands_for_comparison()`: For evaluation only |

---

## `coordinator/` - Grid Coordinator (Untrusted)

The central coordinator that works ONLY on encrypted data.

| File | Description |
|------|-------------|
| `__init__.py` | Module exports: `GridCoordinator`, `EncryptedAggregator`, `EncryptedLoadBalancer` |
| `grid_coordinator.py` | **Main Coordinator** - Orchestrates the smart grid |
| | - `GridCoordinator`: Main class |
| | - `process_round()`: Collect and aggregate encrypted demands |
| | - `receive_decision()`: Get load balance decision from utility |
| | - Has PUBLIC context only - CANNOT decrypt! |
| `encrypted_aggregator.py` | **Encrypted Aggregator** - HE operations on demand data |
| | - `EncryptedAggregator`: Performs ciphertext math |
| | - `aggregate()`: E(d1) + E(d2) + ... = E(total) |
| | - `PlaintextAggregator`: Baseline for comparison |
| `load_balancer.py` | **Load Balancer** - Makes load balancing decisions |
| | - `EncryptedLoadBalancer`: Computes encrypted utilization |
| | - `UtilityDecisionMaker`: **Has secret key**, decrypts and decides |
| | - `LoadBalanceAction`: NONE, REDUCE_10, REDUCE_20, CRITICAL |

---

## `server/` - FastAPI Backend

Web server for the dashboard.

| File | Description |
|------|-------------|
| `__init__.py` | Module export: `SmartGridServer` |
| `server.py` | **FastAPI Server** - REST API and WebSocket |
| | Endpoints: |
| | - `GET /` - Serve dashboard HTML |
| | - `GET /status` - System status |
| | - `GET /agents` - List all agent statuses |
| | - `POST /round` - Trigger one computation round |
| | - `POST /auto/start` - Start auto-run mode |
| | - `POST /auto/stop` - Stop auto-run mode |
| | - `GET /security-logs` - Get audit log entries |
| | - `WS /ws` - WebSocket for real-time updates |

---

## `dashboard/` - Web UI

Simple, clean web dashboard for visualization.

| File | Description |
|------|-------------|
| `index.html` | **Main HTML** - Dashboard layout with panels: |
| | - Status bar (online, agents, rounds, privacy) |
| | - Encrypted data flow visualization |
| | - Aggregate results (total, avg, utilization) |
| | - Comparison view (encrypted vs plaintext) |
| | - Security audit logs |
| `styles.css` | **CSS Styling** - Dark theme with accent colors |
| `dashboard.js` | **JavaScript** - WebSocket connection, real-time updates |
| | - Connects to `/ws` for live data |
| | - Updates UI on each computation round |
| | - Color-coded security log entries |

---

## `evaluation/` - Benchmarking Suite

Performance and correctness evaluation.

| File | Description |
|------|-------------|
| `benchmark.py` | **Benchmark Suite** - Measures system performance |
| | - `run_benchmark()`: Compare encrypted vs plaintext speed |
| | - `run_correctness_test()`: Verify encrypted = plaintext results |
| | - `run_scalability_test()`: Test with increasing agent counts |
| | Run with: `python evaluation/benchmark.py --all` |

---

## `docs/` - Documentation

Technical documentation and reports.

| File | Description |
|------|-------------|
| `technical_report.md` | **Academic Report** explaining: |
| | - Why homomorphic encryption is required |
| | - Why this is a true multi-agent system |
| | - Practical relevance to real smart grids |
| | - Cryptographic parameter justification |
| `project_flow.md` | System flow diagram and usefulness explanation |
| `folder_structure.md` | This file - explains all files and folders |

---

## `tests/` - Test Suite (Optional)

Unit tests for system components.

---

## Key Classes Quick Reference

| Class | Location | Role |
|-------|----------|------|
| `SmartGridFHE` | core/fhe_engine.py | FHE encryption engine |
| `EncryptedDemand` | core/fhe_engine.py | Encrypted value wrapper |
| `SecurityLogger` | core/security_logger.py | Audit trail |
| `HouseholdAgent` | agents/household_agent.py | Single household |
| `AgentManager` | agents/agent_manager.py | Multi-agent orchestrator |
| `GridCoordinator` | coordinator/grid_coordinator.py | Central coordinator |
| `EncryptedAggregator` | coordinator/encrypted_aggregator.py | HE computation |
| `UtilityDecisionMaker` | coordinator/load_balancer.py | Authorized decryptor |
