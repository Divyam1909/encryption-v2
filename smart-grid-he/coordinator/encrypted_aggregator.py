"""
Encrypted Aggregator for Smart Grid
====================================
Performs homomorphic computations on encrypted demand data.

This is the computational core of the coordinator.
ALL operations happen on CIPHERTEXT - no plaintext is ever accessed.

Operations:
- Sum: E(d₁) + E(d₂) + ... + E(dₙ) = E(Σdᵢ)
- Average: E(Σdᵢ) × (1/n) = E(μ)
- Threshold check: E(total) compared to capacity
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fhe_engine import SmartGridFHE, EncryptedDemand
from core.security_logger import SecurityLogger, DataType, OperationType


@dataclass
class AggregationResult:
    """Result of encrypted aggregation"""
    encrypted_total: EncryptedDemand
    encrypted_average: Optional[EncryptedDemand]
    agent_count: int
    computation_time_ms: float
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            'encrypted_total': self.encrypted_total.to_dict(),
            'encrypted_average': self.encrypted_average.to_dict() if self.encrypted_average else None,
            'agent_count': self.agent_count,
            'computation_time_ms': round(self.computation_time_ms, 2),
            'timestamp': self.timestamp
        }


class EncryptedAggregator:
    """
    Performs homomorphic aggregation on encrypted demands.
    
    Security Model:
    - Has PUBLIC FHE context only (cannot decrypt)
    - All inputs are encrypted, all outputs are encrypted
    - Logs every operation for audit trail
    - CANNOT learn any individual demand values
    
    This is the "honest-but-curious" component - it performs
    correct computations but could try to infer information.
    The HE scheme guarantees it learns nothing.
    """
    
    def __init__(self, 
                 public_context: bytes,
                 security_logger: Optional[SecurityLogger] = None):
        """
        Initialize encrypted aggregator.
        
        Args:
            public_context: Public FHE context (no secret key!)
            security_logger: Security audit logger
        """
        # Initialize FHE with PUBLIC context only
        self.fhe = SmartGridFHE.from_context(public_context, has_secret_key=False)
        
        # Verify we cannot decrypt
        if self.fhe.is_private():
            raise ValueError("Aggregator received secret key - security violation!")
        
        self.logger = security_logger
        
        # Statistics
        self._aggregation_count = 0
        self._total_agents_processed = 0
        self._total_computation_time_ms = 0
    
    def aggregate(self, 
                  encrypted_demands: List[EncryptedDemand],
                  compute_average: bool = True) -> AggregationResult:
        """
        Aggregate encrypted demands from multiple households.
        
        Computes E(Σdᵢ) and optionally E(μ) = E(Σdᵢ)/n
        
        Args:
            encrypted_demands: List of encrypted demands from agents
            compute_average: Whether to compute encrypted average
            
        Returns:
            AggregationResult with encrypted totals
        """
        if len(encrypted_demands) == 0:
            raise ValueError("No encrypted demands to aggregate")
        
        start_time = time.time()
        
        # Log receiving encrypted data
        if self.logger:
            for enc in encrypted_demands:
                self.logger.log_coordinator_receive(
                    enc.agent_id, 
                    enc.get_size_kb()
                )
        
        # HOMOMORPHIC SUM: E(d₁) + E(d₂) + ... + E(dₙ) = E(Σdᵢ)
        encrypted_total = self.fhe.aggregate_demands(encrypted_demands)
        
        # Log the aggregation (on ciphertext only)
        if self.logger:
            self.logger.log_coordinator_aggregate(len(encrypted_demands))
        
        # HOMOMORPHIC AVERAGE: E(Σdᵢ) × (1/n) = E(μ)
        encrypted_avg = None
        if compute_average:
            encrypted_avg = self.fhe.compute_average(encrypted_total, len(encrypted_demands))
            
            if self.logger:
                self.logger.log_coordinator_average(len(encrypted_demands))
        
        end_time = time.time()
        computation_time_ms = (end_time - start_time) * 1000
        
        # Update statistics
        self._aggregation_count += 1
        self._total_agents_processed += len(encrypted_demands)
        self._total_computation_time_ms += computation_time_ms
        
        return AggregationResult(
            encrypted_total=encrypted_total,
            encrypted_average=encrypted_avg,
            agent_count=len(encrypted_demands),
            computation_time_ms=computation_time_ms,
            timestamp=datetime.now().isoformat()
        )
    
    def compute_reduction_factor(self, 
                                  encrypted_total: EncryptedDemand,
                                  grid_capacity_kw: float) -> EncryptedDemand:
        """
        Compute load reduction factor: E(total) / capacity
        
        If result > 1.0 (after decryption), load shedding needed.
        The coordinator computes this encrypted; utility decrypts to decide.
        
        Args:
            encrypted_total: Encrypted total demand
            grid_capacity_kw: Grid capacity in kW (public knowledge)
            
        Returns:
            Encrypted ratio (total/capacity)
        """
        # E(total) × (1/capacity) = E(total/capacity)
        encrypted_ratio = self.fhe.compute_reduction_factor(
            encrypted_total, 
            grid_capacity_kw
        )
        
        return encrypted_ratio
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics"""
        return {
            'aggregations_performed': self._aggregation_count,
            'total_agents_processed': self._total_agents_processed,
            'total_computation_time_ms': round(self._total_computation_time_ms, 2),
            'avg_time_per_aggregation_ms': (
                round(self._total_computation_time_ms / self._aggregation_count, 2)
                if self._aggregation_count > 0 else 0
            ),
            'can_decrypt': self.fhe.is_private(),
            'context_hash': self.fhe.get_context_hash()
        }
    
    def verify_cannot_decrypt(self, sample: EncryptedDemand) -> bool:
        """
        Verify that this aggregator cannot decrypt data.
        
        Returns True if correctly configured (cannot decrypt).
        """
        try:
            self.fhe.decrypt_demand(sample)
            return False  # Should not reach here
        except ValueError:
            return True  # Correctly rejected


class PlaintextAggregator:
    """
    Plaintext aggregator for baseline comparison.
    
    This is what a TRADITIONAL system would do - aggregate plaintext.
    Demonstrates the privacy loss in non-HE systems.
    
    In a real system, the coordinator would SEE all individual demands.
    This is what we're trying to prevent with HE.
    """
    
    def __init__(self):
        self._aggregations = 0
        self._total_time_ms = 0
    
    def aggregate(self, demands: Dict[str, float]) -> Tuple[float, float, float]:
        """
        Aggregate plaintext demands.
        
        PRIVACY VIOLATION: This sees all individual values!
        
        Args:
            demands: Dict mapping agent_id to demand in kW
            
        Returns:
            Tuple of (total, average, computation_time_ms)
        """
        start = time.time()
        
        total = sum(demands.values())
        avg = total / len(demands) if demands else 0
        
        end = time.time()
        time_ms = (end - start) * 1000
        
        self._aggregations += 1
        self._total_time_ms += time_ms
        
        return total, avg, time_ms
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'aggregations_performed': self._aggregations,
            'total_computation_time_ms': round(self._total_time_ms, 4),
            'privacy_preserved': False  # THIS IS THE POINT
        }
