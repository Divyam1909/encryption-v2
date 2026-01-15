"""
Grid Coordinator for Smart Grid
================================
Main coordinator that orchestrates the privacy-preserving smart grid.

The coordinator is the UNTRUSTED party that:
- Collects encrypted demands from all agents
- Aggregates using homomorphic operations
- Performs ENCRYPTED THRESHOLD DETECTION (Novel!)
- Provides VERIFIABLE AGGREGATION (Novel!)
- Sends encrypted aggregates to utility for decisions
- Distributes load balance commands to agents

Security Model: HONEST-BUT-CURIOUS
- Follows protocol correctly
- May try to infer information from ciphertexts
- HE guarantees it learns nothing

NOVEL CONTRIBUTIONS INTEGRATED:
1. AdaptivePolynomialComparator - Encrypted peak detection
2. VerifiableAggregator - Commitment-based verification
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fhe_engine import SmartGridFHE, EncryptedDemand
from core.security_logger import SecurityLogger
from core.polynomial_comparator import (
    EncryptedThresholdDetector, 
    ThresholdComparisonResult
)
from core.verifiable_aggregation import (
    VerifiableAggregator, 
    PedersenCommitment, 
    AggregateCommitment,
    CommitmentOpening,
    AggregateOpening
)
from coordinator.encrypted_aggregator import EncryptedAggregator, AggregationResult
from coordinator.load_balancer import EncryptedLoadBalancer, UtilityDecisionMaker, LoadBalanceDecision


@dataclass
class GridState:
    """Current state of the smart grid"""
    timestamp: str
    agent_count: int
    encrypted_total: Optional[Dict]
    encrypted_average: Optional[Dict]
    last_computation_ms: float
    last_decision: Optional[Dict]
    utilization_percent: Optional[float]
    # Novel contribution fields
    encrypted_comparison_score: Optional[Dict] = None
    commitment_verification: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'agent_count': self.agent_count,
            'encrypted_total': self.encrypted_total,
            'encrypted_average': self.encrypted_average,
            'last_computation_ms': round(self.last_computation_ms, 2),
            'last_decision': self.last_decision,
            'utilization_percent': self.utilization_percent,
            'encrypted_comparison_score': self.encrypted_comparison_score,
            'commitment_verification': self.commitment_verification
        }


@dataclass
class VerifiableEncryptedDemand:
    """Encrypted demand with commitment for verification (Novel!)"""
    encrypted: EncryptedDemand
    commitment: PedersenCommitment
    agent_id: str


class GridCoordinator:
    """
    Main coordinator for the smart grid.
    
    This is the CENTRAL component that:
    1. Collects encrypted demands from all households
    2. Performs homomorphic aggregation (sum, average)
    3. NOVEL: Performs encrypted threshold comparison
    4. NOVEL: Provides verifiable computation via commitments
    5. Forwards encrypted results to utility for decryption
    6. Receives load balance decisions from utility
    7. Broadcasts commands to agents
    
    CRITICAL: The coordinator NEVER sees plaintext demand values.
    All computation happens on encrypted data.
    """
    
    def __init__(self, 
                 public_context: bytes,
                 grid_capacity_kw: float = 100.0,
                 security_logger: Optional[SecurityLogger] = None):
        """
        Initialize grid coordinator.
        
        Args:
            public_context: Public FHE context (NO secret key!)
            grid_capacity_kw: Total grid capacity in kW
            security_logger: Security audit logger
        """
        self.public_context = public_context
        self.grid_capacity_kw = grid_capacity_kw
        self.logger = security_logger
        
        # Initialize standard components
        self.aggregator = EncryptedAggregator(public_context, security_logger)
        self.load_balancer = EncryptedLoadBalancer(public_context, grid_capacity_kw, security_logger)
        
        # NOVEL: Initialize encrypted threshold detector
        self.threshold_detector = EncryptedThresholdDetector(
            self.aggregator.fhe,
            default_sensitivity=7.0  # Controls soft zone width
        )
        
        # NOVEL: Initialize verifiable aggregation
        self.verifiable_aggregator = VerifiableAggregator()
        
        # Verify we cannot decrypt
        if self.aggregator.fhe.is_private():
            raise ValueError("Coordinator has secret key - security violation!")
        
        # State
        self._last_aggregation: Optional[AggregationResult] = None
        self._last_decision: Optional[LoadBalanceDecision] = None
        self._last_detection: Optional[ThresholdComparisonResult] = None
        self._last_commitment_aggregate: Optional[AggregateCommitment] = None
        self._round_count = 0
        self._history: List[Dict] = []
    
    def process_round(self, 
                      encrypted_demands: List[EncryptedDemand],
                      commitments: Optional[List[PedersenCommitment]] = None) -> AggregationResult:
        """
        Process one round of demand collection and aggregation.
        
        NOVEL FEATURES INTEGRATED:
        1. Encrypted threshold comparison - detect overload without decryption
        2. Commitment aggregation - for later verification
        
        Args:
            encrypted_demands: Encrypted demands from all agents
            commitments: Optional list of Pedersen commitments for verification
            
        Returns:
            AggregationResult with encrypted totals and novel features
        """
        self._round_count += 1
        
        # Aggregate all encrypted demands
        result = self.aggregator.aggregate(encrypted_demands, compute_average=True)
        
        # Store result
        self._last_aggregation = result
        
        # Compute encrypted utilization for utility
        encrypted_util = self.load_balancer.compute_encrypted_utilization(
            result.encrypted_total
        )
        result.encrypted_total.metadata['encrypted_utilization'] = encrypted_util.to_dict()
        
        # NOVEL CONTRIBUTION #1: Encrypted Threshold Detection
        # Detect if total exceeds grid capacity - WITHOUT decryption!
        detection_result = self.threshold_detector.detect_threshold_encrypted(
            result.encrypted_total,
            threshold=self.grid_capacity_kw,
            expected_range=(0, self.grid_capacity_kw * 3)  # Up to 300% capacity
        )
        self._last_detection = detection_result
        
        # Store encrypted detection result for utility
        result.encrypted_total.metadata['threshold_detection'] = {
            'threshold': detection_result.threshold,
            'sensitivity': detection_result.sensitivity,
            'soft_zone_width': detection_result.soft_zone_width,
            'encrypted_score_checksum': detection_result.encrypted_score.checksum
        }
        
        # NOVEL CONTRIBUTION #2: Commitment Aggregation for Verification
        if commitments and len(commitments) == len(encrypted_demands):
            commitment_aggregate = self.verifiable_aggregator.aggregate_commitments(commitments)
            self._last_commitment_aggregate = commitment_aggregate
            
            result.encrypted_total.metadata['commitment_aggregate'] = {
                'commitment_hex': hex(commitment_aggregate.commitment)[:32] + "...",
                'individual_count': commitment_aggregate.individual_count,
                'verification_pending': True
            }
        
        # Record in history with novel features
        self._history.append({
            'round': self._round_count,
            'timestamp': result.timestamp,
            'agent_count': result.agent_count,
            'computation_time_ms': result.computation_time_ms,
            'novel_features_used': {
                'encrypted_comparison': True,
                'verifiable_aggregation': commitments is not None
            }
        })
        
        return result
    
    def get_detection_result(self) -> Optional[ThresholdComparisonResult]:
        """
        Get the last encrypted threshold detection result.
        
        This is the NOVEL encrypted threshold detection.
        The encrypted score can be sent to utility for interpretation.
        """
        return self._last_detection
    
    def get_commitment_aggregate(self) -> Optional[AggregateCommitment]:
        """
        Get the last commitment aggregate for verification.
        
        This is the NOVEL verifiable aggregation.
        Utility can verify correctness after decryption.
        """
        return self._last_commitment_aggregate
    
    def receive_decision(self, decision: LoadBalanceDecision):
        """
        Receive load balance decision from utility.
        
        The utility decrypts aggregates and makes decisions.
        We receive the decision and can broadcast to agents.
        
        Args:
            decision: Decision from utility
        """
        self._last_decision = decision
        self.load_balancer.record_decision(decision)
    
    def get_reduction_factor(self) -> float:
        """Get current reduction factor for agents"""
        if self._last_decision:
            return self._last_decision.reduction_factor
        return 1.0  # No reduction
    
    def get_state(self) -> GridState:
        """Get current grid state"""
        return GridState(
            timestamp=datetime.now().isoformat(),
            agent_count=self._last_aggregation.agent_count if self._last_aggregation else 0,
            encrypted_total=(
                self._last_aggregation.encrypted_total.to_dict() 
                if self._last_aggregation else None
            ),
            encrypted_average=(
                self._last_aggregation.encrypted_average.to_dict() 
                if self._last_aggregation and self._last_aggregation.encrypted_average 
                else None
            ),
            last_computation_ms=(
                self._last_aggregation.computation_time_ms 
                if self._last_aggregation else 0
            ),
            last_decision=(
                self._last_decision.to_dict() 
                if self._last_decision else None
            ),
            utilization_percent=(
                self._last_decision.utilization_percent 
                if self._last_decision else None
            )
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        return {
            'rounds_completed': self._round_count,
            'aggregator_stats': self.aggregator.get_stats(),
            'can_decrypt': self.aggregator.fhe.is_private(),
            'context_hash': self.aggregator.fhe.get_context_hash(),
            'grid_capacity_kw': self.grid_capacity_kw,
            'current_reduction_factor': self.get_reduction_factor()
        }
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get recent processing history"""
        return self._history[-limit:]
    
    def set_grid_capacity(self, capacity_kw: float):
        """Update grid capacity"""
        self.grid_capacity_kw = capacity_kw
        self.load_balancer.set_grid_capacity(capacity_kw)
    
    def verify_security(self) -> Dict[str, Any]:
        """
        Verify security properties of the coordinator.
        
        Returns audit information proving privacy preservation.
        """
        return {
            'coordinator_has_secret_key': self.aggregator.fhe.is_private(),
            'can_decrypt': False,  # Should always be False
            'security_audit': (
                self.logger.get_coordinator_summary() 
                if self.logger else None
            ),
            'privacy_preserved': not self.aggregator.fhe.is_private()
        }


def demo():
    """Full system demonstration"""
    print("=" * 70)
    print("Smart Grid Coordinator - Full System Demo")
    print("=" * 70)
    
    from core.fhe_engine import SmartGridFHE
    from core.security_logger import SecurityLogger
    from agents.agent_manager import AgentManager
    
    # Initialize
    print("\n[1] Initializing cryptographic keys...")
    utility_fhe = SmartGridFHE()
    public_context = utility_fhe.get_public_context()
    secret_context = utility_fhe.get_secret_context()
    
    print(f"    Context hash: {utility_fhe.get_context_hash()}")
    
    # Security logger
    logger = SecurityLogger()
    
    # Create components
    print("\n[2] Creating system components...")
    
    # Agent manager
    agent_manager = AgentManager(public_context, logger)
    agent_manager.create_agents(25)  # 25 households
    print(f"    Created {agent_manager.get_agent_count()} household agents")
    
    # Coordinator (untrusted)
    coordinator = GridCoordinator(
        public_context, 
        grid_capacity_kw=75.0,  # Set capacity to cause some load balancing
        security_logger=logger
    )
    print(f"    Coordinator initialized (can_decrypt: {coordinator.aggregator.fhe.is_private()})")
    
    # Utility (trusted)
    utility = UtilityDecisionMaker(
        secret_context, 
        grid_capacity_kw=75.0,
        security_logger=logger
    )
    print(f"    Utility initialized (can_decrypt: {utility.fhe.is_private()})")
    
    # Run simulation rounds
    print("\n[3] Running simulation rounds...")
    
    for round_num in range(3):
        print(f"\n    --- Round {round_num + 1} ---")
        
        # Collect encrypted demands
        encrypted_demands = agent_manager.collect_encrypted_demands()
        print(f"    Collected {len(encrypted_demands)} encrypted demands")
        
        # Process on coordinator
        result = coordinator.process_round(encrypted_demands)
        print(f"    Aggregated in {result.computation_time_ms:.2f} ms")
        
        # Utility makes decision
        decision = utility.make_decision(result.encrypted_total, result.agent_count)
        coordinator.receive_decision(decision)
        
        print(f"    Total demand: {decision.total_demand_kw:.2f} kW")
        print(f"    Utilization: {decision.utilization_percent:.1f}%")
        print(f"    Action: {decision.action.value}")
        
        # Apply load balancing
        if decision.reduction_factor < 1.0:
            agent_manager.broadcast_load_balance(decision.reduction_factor)
            print(f"    Broadcasted {int((1-decision.reduction_factor)*100)}% reduction")
    
    # Verify accuracy
    print("\n[4] Verifying computation accuracy...")
    plaintext_demands = agent_manager.get_plaintext_demands_for_comparison()
    actual_total = sum(plaintext_demands.values())
    computed_total = decision.total_demand_kw
    
    print(f"    Plaintext total: {actual_total:.4f} kW")
    print(f"    Encrypted total: {computed_total:.4f} kW")
    print(f"    Error: {abs(computed_total - actual_total):.2e} kW")
    
    # Security verification
    print("\n[5] Security audit...")
    security = coordinator.verify_security()
    print(f"    Coordinator has secret key: {security['coordinator_has_secret_key']}")
    print(f"    Privacy preserved: {security['privacy_preserved']}")
    
    if logger:
        audit = logger.generate_audit_report()
        print(f"    Total log entries: {audit['total_log_entries']}")
        print(f"    Violations: {len(audit['security_violations'])}")
        print(f"    Conclusion: {audit['conclusion']}")
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    demo()
