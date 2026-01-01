"""
Data Signing Module
===================
Provides digital signatures for data integrity and authenticity.
Uses ECDSA (Elliptic Curve Digital Signature Algorithm) for compact, fast signatures.
"""

import hashlib
import json
import base64
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature


@dataclass
class SignedData:
    """Container for signed data"""
    data: Dict[str, Any]
    signature: str
    public_key_id: str
    timestamp: str
    algorithm: str = "ECDSA-SHA256"
    
    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "signature": self.signature,
            "public_key_id": self.public_key_id,
            "timestamp": self.timestamp,
            "algorithm": self.algorithm
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'SignedData':
        return cls(
            data=d["data"],
            signature=d["signature"],
            public_key_id=d["public_key_id"],
            timestamp=d["timestamp"],
            algorithm=d.get("algorithm", "ECDSA-SHA256")
        )


class DataSigner:
    """
    Handles data signing for ESP32/sensor devices.
    
    Each device has a unique ECDSA key pair:
    - Private key: stays on device, used to sign
    - Public key: registered with server, used to verify
    """
    
    def __init__(self, device_id: str, private_key: ec.EllipticCurvePrivateKey = None):
        """
        Initialize signer for a device.
        
        Args:
            device_id: Unique device identifier
            private_key: Optional existing key, generates new if None
        """
        self.device_id = device_id
        
        if private_key:
            self.private_key = private_key
        else:
            # Generate new ECDSA key pair
            self.private_key = ec.generate_private_key(
                ec.SECP256R1(),  # P-256 curve, widely supported
                default_backend()
            )
        
        self.public_key = self.private_key.public_key()
        self.public_key_id = self._compute_key_id()
    
    def _compute_key_id(self) -> str:
        """Compute short ID from public key (first 8 chars of hash)"""
        pub_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(pub_bytes).hexdigest()[:8]
    
    def get_public_key_pem(self) -> str:
        """Export public key as PEM string for registration"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def sign_data(self, data: Dict[str, Any]) -> SignedData:
        """
        Sign data with device's private key.
        
        Args:
            data: Dictionary of data to sign
            
        Returns:
            SignedData with signature
        """
        timestamp = datetime.now().isoformat()
        
        # Create canonical representation for signing
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        message = f"{canonical}|{timestamp}|{self.device_id}"
        message_bytes = message.encode('utf-8')
        
        # Sign with ECDSA
        signature = self.private_key.sign(
            message_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        
        # Encode signature as base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return SignedData(
            data=data,
            signature=signature_b64,
            public_key_id=self.public_key_id,
            timestamp=timestamp
        )
    
    def export_private_key(self, password: bytes = None) -> bytes:
        """Export private key (for secure storage)"""
        if password:
            encryption = serialization.BestAvailableEncryption(password)
        else:
            encryption = serialization.NoEncryption()
        
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )


class SignatureVerifier:
    """
    Server-side signature verification.
    Maintains registry of device public keys.
    """
    
    def __init__(self):
        self.public_keys: Dict[str, ec.EllipticCurvePublicKey] = {}
        self.device_key_map: Dict[str, str] = {}  # device_id -> public_key_id
    
    def register_device_key(self, device_id: str, public_key_pem: str) -> str:
        """
        Register a device's public key.
        
        Args:
            device_id: Device identifier
            public_key_pem: PEM-encoded public key
            
        Returns:
            Public key ID
        """
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
        
        # Compute key ID
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        key_id = hashlib.sha256(pub_bytes).hexdigest()[:8]
        
        # Store
        self.public_keys[key_id] = public_key
        self.device_key_map[device_id] = key_id
        
        print(f"✓ Registered signing key for device '{device_id}': {key_id}")
        return key_id
    
    def verify_signature(self, signed_data: SignedData, device_id: str = None) -> Tuple[bool, str]:
        """
        Verify a signed data packet.
        
        Args:
            signed_data: The signed data to verify
            device_id: Optional device ID to verify against
            
        Returns:
            (is_valid, message)
        """
        key_id = signed_data.public_key_id
        
        # Check if key is registered
        if key_id not in self.public_keys:
            return False, f"Unknown public key: {key_id}"
        
        # If device_id provided, verify it matches
        if device_id and self.device_key_map.get(device_id) != key_id:
            return False, f"Key mismatch: device '{device_id}' not associated with key '{key_id}'"
        
        # Reconstruct message
        canonical = json.dumps(signed_data.data, sort_keys=True, separators=(',', ':'))
        
        # Get device_id from key map (reverse lookup)
        signing_device = None
        for dev_id, k_id in self.device_key_map.items():
            if k_id == key_id:
                signing_device = dev_id
                break
        
        if not signing_device:
            return False, "Cannot determine signing device"
        
        message = f"{canonical}|{signed_data.timestamp}|{signing_device}"
        message_bytes = message.encode('utf-8')
        
        # Decode signature
        try:
            signature = base64.b64decode(signed_data.signature)
        except Exception as e:
            return False, f"Invalid signature encoding: {e}"
        
        # Verify
        public_key = self.public_keys[key_id]
        try:
            public_key.verify(
                signature,
                message_bytes,
                ec.ECDSA(hashes.SHA256())
            )
            return True, "Signature valid"
        except InvalidSignature:
            return False, "Invalid signature"
        except Exception as e:
            return False, f"Verification error: {e}"
    
    def get_registered_devices(self) -> Dict[str, str]:
        """Get map of device_id -> public_key_id"""
        return dict(self.device_key_map)


# ==================== DEMO ====================

def demo():
    """Demonstrate data signing flow"""
    print("=" * 60)
    print("Data Signing Demo")
    print("=" * 60)
    
    # Device side: create signer
    device_id = "esp32_robot_car_01"
    signer = DataSigner(device_id)
    print(f"\n1. Device created signing key")
    print(f"   Device ID: {device_id}")
    print(f"   Public Key ID: {signer.public_key_id}")
    
    # Server side: create verifier and register device
    verifier = SignatureVerifier()
    verifier.register_device_key(device_id, signer.get_public_key_pem())
    print(f"\n2. Server registered device's public key")
    
    # Device signs sensor data
    sensor_data = {
        "ultrasonic_front": 85.3,
        "ultrasonic_left": 120.5,
        "ultrasonic_right": 95.2,
        "motor_temp": 42.1,
        "speed": 5.5
    }
    
    signed = signer.sign_data(sensor_data)
    print(f"\n3. Device signed sensor data")
    print(f"   Timestamp: {signed.timestamp}")
    print(f"   Signature: {signed.signature[:40]}...")
    
    # Server verifies
    valid, message = verifier.verify_signature(signed, device_id)
    print(f"\n4. Server verified signature")
    print(f"   Valid: {valid}")
    print(f"   Message: {message}")
    
    # Try tampering
    print(f"\n5. Testing tamper detection...")
    signed.data["ultrasonic_front"] = 999.9  # Tamper!
    valid, message = verifier.verify_signature(signed, device_id)
    print(f"   Tampered data valid: {valid}")
    print(f"   Message: {message}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
