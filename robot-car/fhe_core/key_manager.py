"""
Key Manager - Secure Key Generation and Distribution
=====================================================
Handles device registration, trust verification, and secure key distribution.
Implements a hierarchical key system for multi-agent FHE operations.
"""

import os
import json
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@dataclass
class DeviceKeys:
    """Keys and metadata for a registered device"""
    device_id: str
    device_name: str
    trust_token: str
    secret_context: bytes
    public_context: bytes
    created_at: str
    expires_at: str
    fingerprint: str
    is_trusted: bool = True
    access_level: str = "full"  # full, read_only, encrypted_only
    
    def to_dict(self, include_secrets: bool = False) -> dict:
        """Convert to dictionary, optionally excluding secrets"""
        d = {
            'device_id': self.device_id,
            'device_name': self.device_name,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'fingerprint': self.fingerprint,
            'is_trusted': self.is_trusted,
            'access_level': self.access_level
        }
        if include_secrets:
            d['trust_token'] = self.trust_token
            d['secret_context'] = base64.b64encode(self.secret_context).decode('utf-8')
            d['public_context'] = base64.b64encode(self.public_context).decode('utf-8')
        return d


@dataclass
class RegistrationCode:
    """One-time registration code for device enrollment"""
    code: str
    device_name: str
    created_at: str
    expires_at: str
    used: bool = False
    used_by: Optional[str] = None


class KeyManager:
    """
    Manages cryptographic keys and device trust for the FHE system.
    
    Features:
    - Generate and store FHE contexts
    - Device registration with one-time codes
    - Trust token generation and verification
    - Secure key distribution to trusted devices
    - Key rotation and expiration management
    """
    
    def __init__(self, storage_path: str = "./.keys"):
        """
        Initialize Key Manager
        
        Args:
            storage_path: Directory to store encrypted keys
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Master key for encrypting stored data
        self.master_key = self._load_or_create_master_key()
        self.fernet = Fernet(self.master_key)
        
        # In-memory caches
        self.devices: Dict[str, DeviceKeys] = {}
        self.registration_codes: Dict[str, RegistrationCode] = {}
        self.public_context: Optional[bytes] = None
        self.secret_context: Optional[bytes] = None
        
        # Load existing data
        self._load_data()
        
    def _load_or_create_master_key(self) -> bytes:
        """Load or create master encryption key"""
        key_file = self.storage_path / ".master_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data with master key"""
        return self.fernet.encrypt(data)
    
    def _decrypt_data(self, encrypted: bytes) -> bytes:
        """Decrypt data with master key"""
        return self.fernet.decrypt(encrypted)
    
    def _load_data(self):
        """Load saved devices and registration codes"""
        devices_file = self.storage_path / "devices.enc"
        codes_file = self.storage_path / "codes.enc"
        
        if devices_file.exists():
            try:
                with open(devices_file, 'rb') as f:
                    decrypted = self._decrypt_data(f.read())
                    data = json.loads(decrypted.decode('utf-8'))
                    for device_data in data:
                        device_data['secret_context'] = base64.b64decode(device_data['secret_context'])
                        device_data['public_context'] = base64.b64decode(device_data['public_context'])
                        device = DeviceKeys(**device_data)
                        self.devices[device.device_id] = device
            except Exception as e:
                print(f"Warning: Could not load devices: {e}")
        
        if codes_file.exists():
            try:
                with open(codes_file, 'rb') as f:
                    decrypted = self._decrypt_data(f.read())
                    data = json.loads(decrypted.decode('utf-8'))
                    for code_data in data:
                        code = RegistrationCode(**code_data)
                        self.registration_codes[code.code] = code
            except Exception as e:
                print(f"Warning: Could not load registration codes: {e}")
    
    def _save_data(self):
        """Persist devices and codes to encrypted storage"""
        devices_file = self.storage_path / "devices.enc"
        codes_file = self.storage_path / "codes.enc"
        
        # Save devices
        devices_data = []
        for device in self.devices.values():
            d = asdict(device)
            d['secret_context'] = base64.b64encode(d['secret_context']).decode('utf-8')
            d['public_context'] = base64.b64encode(d['public_context']).decode('utf-8')
            devices_data.append(d)
        
        encrypted = self._encrypt_data(json.dumps(devices_data).encode('utf-8'))
        with open(devices_file, 'wb') as f:
            f.write(encrypted)
        
        # Save registration codes
        codes_data = [asdict(code) for code in self.registration_codes.values()]
        encrypted = self._encrypt_data(json.dumps(codes_data).encode('utf-8'))
        with open(codes_file, 'wb') as f:
            f.write(encrypted)
    
    def set_fhe_contexts(self, public_context: bytes, secret_context: bytes):
        """
        Store the FHE contexts from the encryption engine
        
        Args:
            public_context: Context without secret key
            secret_context: Context with secret key (for trusted devices)
        """
        self.public_context = public_context
        self.secret_context = secret_context
        
        # Save to encrypted storage
        ctx_file = self.storage_path / "contexts.enc"
        data = {
            'public': base64.b64encode(public_context).decode('utf-8'),
            'secret': base64.b64encode(secret_context).decode('utf-8')
        }
        encrypted = self._encrypt_data(json.dumps(data).encode('utf-8'))
        with open(ctx_file, 'wb') as f:
            f.write(encrypted)
    
    def load_fhe_contexts(self) -> bool:
        """Load saved FHE contexts"""
        ctx_file = self.storage_path / "contexts.enc"
        
        if not ctx_file.exists():
            return False
        
        try:
            with open(ctx_file, 'rb') as f:
                decrypted = self._decrypt_data(f.read())
                data = json.loads(decrypted.decode('utf-8'))
                self.public_context = base64.b64decode(data['public'])
                self.secret_context = base64.b64decode(data['secret'])
            return True
        except Exception as e:
            print(f"Warning: Could not load contexts: {e}")
            return False
    
    def generate_registration_code(self, 
                                   device_name: str,
                                   valid_hours: int = 24) -> str:
        """
        Generate a one-time registration code for device enrollment
        
        Args:
            device_name: Name for the device being registered
            valid_hours: Hours until code expires
            
        Returns:
            6-character registration code
        """
        # Generate unique code
        code = secrets.token_hex(3).upper()  # 6 hex characters
        
        # Ensure uniqueness
        while code in self.registration_codes:
            code = secrets.token_hex(3).upper()
        
        now = datetime.now()
        expires = now + timedelta(hours=valid_hours)
        
        reg_code = RegistrationCode(
            code=code,
            device_name=device_name,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            used=False
        )
        
        self.registration_codes[code] = reg_code
        self._save_data()
        
        return code
    
    def validate_registration_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate a registration code
        
        Returns:
            (valid, message) tuple
        """
        code = code.upper()
        
        if code not in self.registration_codes:
            return False, "Invalid registration code"
        
        reg_code = self.registration_codes[code]
        
        if reg_code.used:
            return False, "Registration code already used"
        
        expires = datetime.fromisoformat(reg_code.expires_at)
        if datetime.now() > expires:
            return False, "Registration code expired"
        
        return True, reg_code.device_name
    
    def register_device(self, 
                        registration_code: str,
                        device_fingerprint: str) -> Optional[DeviceKeys]:
        """
        Register a new trusted device
        
        Args:
            registration_code: Valid registration code
            device_fingerprint: Unique device identifier
            
        Returns:
            DeviceKeys if successful, None otherwise
        """
        valid, result = self.validate_registration_code(registration_code)
        if not valid:
            print(f"Registration failed: {result}")
            return None
        
        reg_code = self.registration_codes[registration_code.upper()]
        
        # Check contexts are available
        if self.secret_context is None or self.public_context is None:
            print("Error: FHE contexts not initialized")
            return None
        
        # Generate device credentials
        device_id = secrets.token_hex(8)
        trust_token = secrets.token_urlsafe(32)
        
        now = datetime.now()
        expires = now + timedelta(days=365)  # 1 year validity
        
        device = DeviceKeys(
            device_id=device_id,
            device_name=reg_code.device_name,
            trust_token=trust_token,
            secret_context=self.secret_context,
            public_context=self.public_context,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            fingerprint=device_fingerprint,
            is_trusted=True,
            access_level="full"
        )
        
        # Mark registration code as used
        reg_code.used = True
        reg_code.used_by = device_id
        
        # Store device
        self.devices[device_id] = device
        self._save_data()
        
        return device
    
    def verify_trust_token(self, device_id: str, trust_token: str) -> bool:
        """
        Verify a device's trust token
        
        Args:
            device_id: Device identifier
            trust_token: Token to verify
            
        Returns:
            True if valid and trusted
        """
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        
        if not device.is_trusted:
            return False
        
        if device.trust_token != trust_token:
            return False
        
        # Check expiration
        expires = datetime.fromisoformat(device.expires_at)
        if datetime.now() > expires:
            return False
        
        return True
    
    def get_device(self, device_id: str) -> Optional[DeviceKeys]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def get_device_by_fingerprint(self, fingerprint: str) -> Optional[DeviceKeys]:
        """Find device by fingerprint"""
        for device in self.devices.values():
            if device.fingerprint == fingerprint:
                return device
        return None
    
    def list_devices(self) -> List[dict]:
        """List all registered devices (without secrets)"""
        return [d.to_dict(include_secrets=False) for d in self.devices.values()]
    
    def revoke_device(self, device_id: str) -> bool:
        """Revoke trust from a device"""
        if device_id in self.devices:
            self.devices[device_id].is_trusted = False
            self._save_data()
            return True
        return False
    
    def delete_device(self, device_id: str) -> bool:
        """Permanently delete a device"""
        if device_id in self.devices:
            del self.devices[device_id]
            self._save_data()
            return True
        return False
    
    def rotate_trust_token(self, device_id: str) -> Optional[str]:
        """Generate new trust token for device"""
        if device_id not in self.devices:
            return None
        
        new_token = secrets.token_urlsafe(32)
        self.devices[device_id].trust_token = new_token
        self._save_data()
        return new_token
    
    def get_public_context_for_untrusted(self) -> bytes:
        """
        Get public context for untrusted devices
        They can see encrypted data but not decrypt
        """
        if self.public_context is None:
            raise ValueError("FHE contexts not initialized")
        return self.public_context
    
    def get_secret_context_for_device(self, device_id: str, trust_token: str) -> Optional[bytes]:
        """
        Get secret context for verified trusted device
        
        Args:
            device_id: Device requesting context
            trust_token: Trust token for verification
            
        Returns:
            Secret context bytes if verified, None otherwise
        """
        if not self.verify_trust_token(device_id, trust_token):
            return None
        
        device = self.devices[device_id]
        return device.secret_context
    
    def cleanup_expired_codes(self):
        """Remove expired registration codes"""
        now = datetime.now()
        expired = []
        
        for code, reg_code in self.registration_codes.items():
            expires = datetime.fromisoformat(reg_code.expires_at)
            if now > expires:
                expired.append(code)
        
        for code in expired:
            del self.registration_codes[code]
        
        if expired:
            self._save_data()
        
        return len(expired)
    
    def get_stats(self) -> dict:
        """Get key manager statistics"""
        now = datetime.now()
        active_devices = sum(
            1 for d in self.devices.values() 
            if d.is_trusted and datetime.fromisoformat(d.expires_at) > now
        )
        pending_codes = sum(
            1 for c in self.registration_codes.values()
            if not c.used and datetime.fromisoformat(c.expires_at) > now
        )
        
        return {
            'total_devices': len(self.devices),
            'active_devices': active_devices,
            'pending_registration_codes': pending_codes,
            'contexts_loaded': self.public_context is not None
        }


# ==================== DEMO ====================

def demo():
    """Demonstrate key management"""
    print("=" * 60)
    print("Key Manager Demo")
    print("=" * 60)
    
    # Initialize
    km = KeyManager("./.demo_keys")
    
    # Simulate FHE context creation
    from encryption_core import FHEEngine
    engine = FHEEngine()
    
    km.set_fhe_contexts(
        engine.get_public_context(),
        engine.get_secret_context()
    )
    print(f"\n✓ FHE Contexts stored")
    
    # Generate registration code
    code = km.generate_registration_code("Mobile-iPhone-Divya")
    print(f"\n📱 Registration Code: {code}")
    print("   (Share this with the trusted device)")
    
    # Simulate device registration
    fingerprint = hashlib.sha256(b"device-unique-id").hexdigest()[:16]
    device = km.register_device(code, fingerprint)
    
    if device:
        print(f"\n✓ Device Registered:")
        print(f"   Device ID: {device.device_id}")
        print(f"   Name: {device.device_name}")
        print(f"   Access Level: {device.access_level}")
    
    # Verify trust
    is_trusted = km.verify_trust_token(device.device_id, device.trust_token)
    print(f"\n🔐 Trust Verification: {'TRUSTED' if is_trusted else 'NOT TRUSTED'}")
    
    # Stats
    print(f"\n📊 Stats: {km.get_stats()}")
    
    # Cleanup demo
    import shutil
    shutil.rmtree("./.demo_keys", ignore_errors=True)
    
    print("\n" + "=" * 60)
    print("Key Manager Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()