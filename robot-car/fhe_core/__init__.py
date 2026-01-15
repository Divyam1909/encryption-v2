"""
FHE Core Module - Privacy-Preserving Machine Learning Engine
=============================================================
Powered by TenSEAL with CKKS scheme for real-number operations
"""

from .encryption_core import FHEEngine, EncryptedVector
from .key_manager import KeyManager, DeviceKeys
from .data_signing import DataSigner, SignatureVerifier, SignedData
from .differential_privacy import DifferentialPrivacy, SensorDataPrivatizer, NoiseType
from .collision_risk_model import (
    EncryptedCollisionDetector,
    PlaintextCollisionDetector, 
    EncryptedInferenceResult,
    DecryptedResult,
    RiskLevel
)

__all__ = [
    # Core FHE
    'FHEEngine', 'EncryptedVector',
    
    # Key Management
    'KeyManager', 'DeviceKeys',
    
    # Data Signing
    'DataSigner', 'SignatureVerifier', 'SignedData',
    
    # Differential Privacy
    'DifferentialPrivacy', 'SensorDataPrivatizer', 'NoiseType',
    
    # PPML Collision Detection
    'EncryptedCollisionDetector', 'PlaintextCollisionDetector',
    'EncryptedInferenceResult', 'DecryptedResult', 'RiskLevel'
]

__version__ = '2.0.0'  # Major version bump for PPML