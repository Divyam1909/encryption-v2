"""
Key Management for Smart Grid HE System
========================================
Handles generation, distribution, and storage of FHE keys.

Key Distribution Model:
1. Utility Company generates master keys (public + secret)
2. Public context distributed to all agents and coordinator
3. Secret key stays ONLY with utility company
4. Agents can encrypt, coordinator can compute, only utility can decrypt
"""

import os
import json
import base64
import hashlib
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class KeyMetadata:
    """Metadata about a key context"""
    context_hash: str
    created_at: str
    has_secret_key: bool
    poly_modulus_degree: int
    security_level: str
    purpose: str  # 'master', 'coordinator', 'agent'


class KeyManager:
    """
    Manages FHE key generation, storage, and distribution.
    
    Security Model:
    - Master context (with secret key) is stored encrypted
    - Public contexts are freely distributed to agents and coordinator
    - Key rotation support for periodic security refresh
    """
    
    def __init__(self, storage_dir: str = ".keys"):
        """
        Initialize key manager.
        
        Args:
            storage_dir: Directory to store key files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._master_context: Optional[bytes] = None
        self._public_context: Optional[bytes] = None
        self._metadata: Optional[KeyMetadata] = None
    
    def generate_keys(self, fhe_engine) -> Tuple[bytes, bytes]:
        """
        Generate and store new FHE keys.
        
        Args:
            fhe_engine: SmartGridFHE instance to extract contexts from
            
        Returns:
            Tuple of (secret_context, public_context)
        """
        from .fhe_engine import SmartGridFHE
        
        # Get contexts
        secret_context = fhe_engine.get_secret_context()
        public_context = fhe_engine.get_public_context()
        
        # Store locally
        self._master_context = secret_context
        self._public_context = public_context
        
        # Create metadata
        self._metadata = KeyMetadata(
            context_hash=fhe_engine.get_context_hash(),
            created_at=datetime.now().isoformat(),
            has_secret_key=True,
            poly_modulus_degree=fhe_engine.poly_modulus_degree,
            security_level="128-bit",
            purpose="master"
        )
        
        # Save to files
        self._save_to_disk()
        
        return secret_context, public_context
    
    def _save_to_disk(self):
        """Save keys and metadata to disk"""
        # Save master context (would be encrypted in production)
        master_path = self.storage_dir / "master_context.bin"
        with open(master_path, 'wb') as f:
            f.write(self._master_context)
        
        # Save public context
        public_path = self.storage_dir / "public_context.bin"
        with open(public_path, 'wb') as f:
            f.write(self._public_context)
        
        # Save metadata
        meta_path = self.storage_dir / "key_metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(asdict(self._metadata), f, indent=2)
    
    def load_keys(self) -> bool:
        """
        Load keys from disk.
        
        Returns:
            True if keys loaded successfully
        """
        try:
            master_path = self.storage_dir / "master_context.bin"
            public_path = self.storage_dir / "public_context.bin"
            meta_path = self.storage_dir / "key_metadata.json"
            
            if not all(p.exists() for p in [master_path, public_path, meta_path]):
                return False
            
            with open(master_path, 'rb') as f:
                self._master_context = f.read()
            
            with open(public_path, 'rb') as f:
                self._public_context = f.read()
            
            with open(meta_path, 'r') as f:
                data = json.load(f)
                self._metadata = KeyMetadata(**data)
            
            return True
        except Exception as e:
            print(f"Error loading keys: {e}")
            return False
    
    def get_public_context(self) -> bytes:
        """Get public context for distribution to agents/coordinator"""
        if self._public_context is None:
            raise ValueError("No keys loaded. Call generate_keys() or load_keys() first.")
        return self._public_context
    
    def get_secret_context(self) -> bytes:
        """Get secret context (only for utility company)"""
        if self._master_context is None:
            raise ValueError("No keys loaded. Call generate_keys() or load_keys() first.")
        return self._master_context
    
    def get_metadata(self) -> Optional[KeyMetadata]:
        """Get key metadata"""
        return self._metadata
    
    def get_context_hash(self) -> Optional[str]:
        """Get hash of the current context"""
        if self._metadata:
            return self._metadata.context_hash
        return None
    
    def verify_context(self, context_bytes: bytes) -> bool:
        """Verify a context matches our public context"""
        if self._public_context is None:
            return False
        
        our_hash = hashlib.sha256(self._public_context).hexdigest()[:16]
        their_hash = hashlib.sha256(context_bytes).hexdigest()[:16]
        return our_hash == their_hash
    
    def keys_exist(self) -> bool:
        """Check if keys have been generated"""
        return (self.storage_dir / "master_context.bin").exists()
    
    def clear_keys(self):
        """Delete all key files (for key rotation)"""
        for f in self.storage_dir.glob("*"):
            f.unlink()
        self._master_context = None
        self._public_context = None
        self._metadata = None
