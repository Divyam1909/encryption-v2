"""
Smart Grid Homomorphic Encryption - Core Module

NOVEL CONTRIBUTIONS:
1. EncryptedThresholdDetector: Encrypted threshold detection via linear approximation
2. VerifiableAggregator: Commitment-based aggregation verification
"""
from .fhe_engine import SmartGridFHE, EncryptedDemand
from .key_management import KeyManager
from .security_logger import SecurityLogger
from .polynomial_comparator import (
    EncryptedThresholdDetector, 
    ThresholdComparisonResult,
    InterpretedResult,
    AdaptivePolynomialComparator,  # Backward compatibility alias
    ComparisonResult               # Backward compatibility alias
)
from .verifiable_aggregation import (
    VerifiableAggregator,
    PedersenCommitmentScheme,
    PedersenCommitment,
    CommitmentOpening,
    AggregateCommitment,
    AggregateOpening,
    VerificationResult
)

__all__ = [
    # Core FHE
    'SmartGridFHE', 'EncryptedDemand', 'KeyManager', 'SecurityLogger',
    # Novel: Encrypted Threshold Detection
    'EncryptedThresholdDetector', 'ThresholdComparisonResult', 'InterpretedResult',
    'AdaptivePolynomialComparator', 'ComparisonResult',  # Backward compat
    # Novel: Verifiable Aggregation
    'VerifiableAggregator', 'PedersenCommitmentScheme',
    'PedersenCommitment', 'CommitmentOpening', 
    'AggregateCommitment', 'AggregateOpening', 'VerificationResult'
]

