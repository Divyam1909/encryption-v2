"""
Encrypted Load Balancer for Smart Grid
=======================================
Makes load balancing decisions based on encrypted aggregates.

The load balancer:
1. Receives encrypted total demand from aggregator
2. Computes encrypted metrics (e.g., demand/capacity ratio)
3. Sends encrypted results to utility for decryption
4. Utility makes final decision and broadcasts to agents

Key insight: Load balancing DECISIONS can be made by utility
after decrypting ONLY the aggregate, not individual demands.

NOVEL CONTRIBUTIONS INTEGRATED:
1. Interpret encrypted comparison scores (from AdaptivePolynomialComparator)
2. Verify aggregation correctness (using VerifiableAggregator)
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fhe_engine import SmartGridFHE, EncryptedDemand
from core.security_logger import SecurityLogger
from core.polynomial_comparator import AdaptivePolynomialComparator, ComparisonResult
from core.verifiable_aggregation import VerifiableAggregator, AggregateCommitment, VerificationResult


class LoadBalanceAction(Enum):
    """Possible load balancing actions"""
    NONE = "none"                    # Demand within capacity
    REDUCE_10 = "reduce_10"          # Reduce by 10%
    REDUCE_20 = "reduce_20"          # Reduce by 20%
    REDUCE_30 = "reduce_30"          # Reduce by 30%
    CRITICAL = "critical"            # Critical reduction needed


@dataclass
class LoadBalanceDecision:
    """Load balancing decision from utility"""
    action: LoadBalanceAction
    reduction_factor: float          # 0.0 to 1.0 (1.0 = no reduction)
    total_demand_kw: float           # Decrypted total
    grid_capacity_kw: float
    utilization_percent: float
    timestamp: str
    reason: str
    # Novel contribution fields
    comparison_verified: bool = False
    commitment_verified: bool = False
    comparison_zone: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'action': self.action.value,
            'reduction_factor': self.reduction_factor,
            'total_demand_kw': round(self.total_demand_kw, 2),
            'grid_capacity_kw': self.grid_capacity_kw,
            'utilization_percent': round(self.utilization_percent, 1),
            'timestamp': self.timestamp,
            'reason': self.reason,
            'novel_contributions': {
                'comparison_verified': self.comparison_verified,
                'commitment_verified': self.commitment_verified,
                'comparison_zone': self.comparison_zone
            }
        }


class EncryptedLoadBalancer:
    """
    Encrypted load balancer that works with ciphertext.
    
    The coordinator uses this to compute encrypted metrics.
    Only the utility (with secret key) can make final decisions.
    
    Security Model:
    - Load balancer has PUBLIC context only
    - Computes ratios and metrics on encrypted data
    - Cannot see actual demand values
    - Sends encrypted results to utility for decision
    """
    
    def __init__(self, 
                 public_context: bytes,
                 grid_capacity_kw: float = 100.0,
                 security_logger: Optional[SecurityLogger] = None):
        """
        Initialize encrypted load balancer.
        
        Args:
            public_context: Public FHE context
            grid_capacity_kw: Total grid capacity in kW
            security_logger: Security audit logger
        """
        self.fhe = SmartGridFHE.from_context(public_context, has_secret_key=False)
        
        if self.fhe.is_private():
            raise ValueError("Load balancer received secret key - security violation!")
        
        self.grid_capacity_kw = grid_capacity_kw
        self.logger = security_logger
        
        # History
        self._decisions: List[LoadBalanceDecision] = []
    
    def compute_encrypted_utilization(self, 
                                       encrypted_total: EncryptedDemand) -> EncryptedDemand:
        """
        Compute encrypted utilization ratio: E(total) / capacity
        
        The utility will decrypt this to see if > 1.0 (overload).
        
        Args:
            encrypted_total: Encrypted total demand
            
        Returns:
            Encrypted utilization ratio
        """
        # E(total) × (1/capacity) = E(utilization)
        encrypted_util = self.fhe.multiply_plain(
            encrypted_total, 
            1.0 / self.grid_capacity_kw
        )
        return encrypted_util
    
    def get_grid_capacity(self) -> float:
        """Get grid capacity (public knowledge)"""
        return self.grid_capacity_kw
    
    def set_grid_capacity(self, capacity_kw: float):
        """Update grid capacity"""
        self.grid_capacity_kw = capacity_kw
    
    def get_decision_history(self, limit: int = 10) -> List[Dict]:
        """Get recent decisions"""
        return [d.to_dict() for d in self._decisions[-limit:]]
    
    def record_decision(self, decision: LoadBalanceDecision):
        """Record a decision (called by utility after decryption)"""
        self._decisions.append(decision)


class UtilityDecisionMaker:
    """
    Utility company component that makes final load balance decisions.
    
    This is the ONLY component with the secret key.
    It decrypts aggregates and makes binding decisions.
    
    NOVEL CONTRIBUTIONS INTEGRATED:
    1. Interprets encrypted comparison scores (validates coordinator's detection)
    2. Verifies aggregation correctness (using commitments)
    
    Privacy Guarantee:
    - Utility sees ONLY aggregate values (total, average)
    - CANNOT see individual household demands
    - Individual privacy preserved even from utility
    """
    
    def __init__(self, 
                 secret_context: bytes,
                 grid_capacity_kw: float = 100.0,
                 security_logger: Optional[SecurityLogger] = None):
        """
        Initialize utility decision maker.
        
        Args:
            secret_context: Full FHE context with secret key
            grid_capacity_kw: Total grid capacity in kW
            security_logger: Security audit logger
        """
        self.fhe = SmartGridFHE.from_context(secret_context, has_secret_key=True)
        
        if not self.fhe.is_private():
            raise ValueError("Utility did not receive secret key!")
        
        self.grid_capacity_kw = grid_capacity_kw
        self.logger = security_logger
        
        # NOVEL: Verifiable aggregator for commitment verification
        self.verifiable_aggregator = VerifiableAggregator()
        
        # Thresholds for load balancing
        self.thresholds = {
            0.80: LoadBalanceAction.NONE,       # Under 80% - no action
            0.90: LoadBalanceAction.REDUCE_10,  # 80-90% - reduce 10%
            0.95: LoadBalanceAction.REDUCE_20,  # 90-95% - reduce 20%
            1.00: LoadBalanceAction.REDUCE_30,  # 95-100% - reduce 30%
            float('inf'): LoadBalanceAction.CRITICAL  # Over 100% - critical
        }
    
    def make_decision(self, 
                      encrypted_total: EncryptedDemand,
                      agent_count: int) -> LoadBalanceDecision:
        """
        Make load balancing decision by decrypting aggregate.
        
        Args:
            encrypted_total: Encrypted total demand from coordinator
            agent_count: Number of agents (for context)
            
        Returns:
            LoadBalanceDecision with action to take
        """
        # Decrypt the aggregate total
        decrypted = self.fhe.decrypt_demand(encrypted_total)
        total_demand = decrypted[0]
        
        # Log the decryption (authorized)
        if self.logger:
            self.logger.log_utility_decrypt("total_demand")
        
        # Calculate utilization
        utilization = total_demand / self.grid_capacity_kw
        utilization_percent = utilization * 100
        
        # Determine action based on thresholds
        action = LoadBalanceAction.NONE
        for threshold, act in sorted(self.thresholds.items()):
            if utilization <= threshold:
                action = act
                break
        
        # Calculate reduction factor
        if action == LoadBalanceAction.NONE:
            reduction_factor = 1.0
            reason = f"Grid at {utilization_percent:.1f}% capacity - no action needed"
        elif action == LoadBalanceAction.REDUCE_10:
            reduction_factor = 0.90
            reason = f"Grid at {utilization_percent:.1f}% - requesting 10% reduction"
        elif action == LoadBalanceAction.REDUCE_20:
            reduction_factor = 0.80
            reason = f"Grid at {utilization_percent:.1f}% - requesting 20% reduction"
        elif action == LoadBalanceAction.REDUCE_30:
            reduction_factor = 0.70
            reason = f"Grid at {utilization_percent:.1f}% - requesting 30% reduction"
        else:
            reduction_factor = 0.50
            reason = f"CRITICAL: Grid at {utilization_percent:.1f}% - emergency 50% reduction"
        
        decision = LoadBalanceDecision(
            action=action,
            reduction_factor=reduction_factor,
            total_demand_kw=total_demand,
            grid_capacity_kw=self.grid_capacity_kw,
            utilization_percent=utilization_percent,
            timestamp=datetime.now().isoformat(),
            reason=reason
        )
        
        # Log the decision
        if self.logger:
            self.logger.log_load_balance_decision(reason)
        
        return decision
    
    def decrypt_average(self, encrypted_avg: EncryptedDemand) -> float:
        """Decrypt average demand for reporting"""
        decrypted = self.fhe.decrypt_demand(encrypted_avg)
        
        if self.logger:
            self.logger.log_utility_decrypt("average_demand")
        
        return decrypted[0]
    
    def interpret_encrypted_comparison(self, 
                                        comparison_result: ComparisonResult) -> Tuple[str, float]:
        """
        NOVEL: Interpret the encrypted comparison score.
        
        The coordinator computed an encrypted score without knowing the actual
        demand. We decrypt the score to validate the detection.
        
        Args:
            comparison_result: Result from coordinator's encrypted comparison
            
        Returns:
            Tuple of (zone, confidence) where zone is 'below', 'uncertain', 'above'
        """
        # Decrypt the comparison score
        decrypted_score = self.fhe.decrypt_demand(comparison_result.encrypted_score)[0]
        
        if self.logger:
            self.logger.log_utility_decrypt("encrypted_comparison_score")
        
        # Interpret using the comparator's interpretation method
        zone, confidence = AdaptivePolynomialComparator.interpret_score(decrypted_score)
        
        return zone, confidence, decrypted_score
    
    def verify_aggregation(self,
                            decrypted_sum: float,
                            commitment_aggregate: AggregateCommitment) -> VerificationResult:
        """
        NOVEL: Verify that coordinator computed aggregation correctly.
        
        Uses Pedersen commitment properties to verify:
        - Coordinator didn't inflate/deflate the total
        - All agent contributions were included
        
        Args:
            decrypted_sum: The total we decrypted from FHE
            commitment_aggregate: The aggregate commitment from coordinator
            
        Returns:
            VerificationResult indicating if verification passed
        """
        result = self.verifiable_aggregator.verify_aggregate(
            decrypted_sum, 
            commitment_aggregate
        )
        
        if self.logger:
            if result.is_valid:
                self.logger.log_agent_encrypt("commitment_verification_passed", "commitment")
            else:
                self.logger.log_coordinator_receive("SECURITY_VIOLATION: commitment_verification_failed", "commitment")
        
        return result
    
    def set_grid_capacity(self, capacity_kw: float):
        """Update grid capacity"""
        self.grid_capacity_kw = capacity_kw


def demo():
    """Demonstrate load balancing"""
    print("=" * 60)
    print("Encrypted Load Balancing Demo")
    print("=" * 60)
    
    from core.fhe_engine import SmartGridFHE
    from core.security_logger import SecurityLogger
    from agents.agent_manager import AgentManager
    from coordinator.encrypted_aggregator import EncryptedAggregator
    
    # Setup
    print("\n[1] Setting up system...")
    utility_fhe = SmartGridFHE()
    public_context = utility_fhe.get_public_context()
    secret_context = utility_fhe.get_secret_context()
    
    logger = SecurityLogger()
    
    # Create agents
    print("\n[2] Creating 20 household agents...")
    manager = AgentManager(public_context, logger)
    manager.create_agents(20)
    
    # Collect encrypted demands
    print("\n[3] Collecting encrypted demands...")
    encrypted_demands = manager.collect_encrypted_demands()
    
    # Aggregate
    print("\n[4] Aggregating on encrypted data...")
    aggregator = EncryptedAggregator(public_context, logger)
    result = aggregator.aggregate(encrypted_demands)
    
    print(f"    Computation time: {result.computation_time_ms:.2f} ms")
    
    # Load balancing
    print("\n[5] Making load balance decision...")
    
    # Utility with secret key
    utility = UtilityDecisionMaker(secret_context, grid_capacity_kw=50.0, security_logger=logger)
    decision = utility.make_decision(result.encrypted_total, result.agent_count)
    
    print(f"    Total demand: {decision.total_demand_kw:.2f} kW")
    print(f"    Grid capacity: {decision.grid_capacity_kw:.2f} kW")
    print(f"    Utilization: {decision.utilization_percent:.1f}%")
    print(f"    Action: {decision.action.value}")
    print(f"    Reason: {decision.reason}")
    
    # Verify plaintext comparison
    print("\n[6] Verifying accuracy...")
    plaintext = manager.get_plaintext_demands_for_comparison()
    actual_total = sum(plaintext.values())
    print(f"    Actual total: {actual_total:.2f} kW")
    print(f"    Error: {abs(decision.total_demand_kw - actual_total):.2e} kW")
    
    # Security audit
    print("\n[7] Security audit:")
    report = logger.generate_audit_report()
    print(f"    {report['conclusion']}")


if __name__ == "__main__":
    demo()
