"""
FHE Core Module - Fully Homomorphic Encryption Engine
Powered by TenSEAL with CKKS scheme for real-number operations
"""

from .encryption_core import FHEEngine, EncryptedVector
from .key_manager import KeyManager, DeviceKeys

__all__ = ['FHEEngine', 'EncryptedVector', 'KeyManager', 'DeviceKeys']
__version__ = '1.0.0'