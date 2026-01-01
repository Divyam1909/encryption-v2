"""
Device Registry
===============
Manages device authentication, trust status, and access control.
Provides real-time tracking of connected devices.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import asyncio


class AccessLevel(str, Enum):
    """Device access levels"""
    FULL = "full"                 # Can decrypt all data
    READ_ONLY = "read_only"       # Can decrypt but not control
    ENCRYPTED_ONLY = "encrypted"  # Can only see encrypted data
    BLOCKED = "blocked"           # No access


class DeviceStatus(str, Enum):
    """Device connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    PENDING = "pending"
    REVOKED = "revoked"


@dataclass
class DeviceInfo:
    """Information about a connected device"""
    device_id: str
    device_name: str
    fingerprint: str
    trust_token: Optional[str] = None
    access_level: AccessLevel = AccessLevel.ENCRYPTED_ONLY
    status: DeviceStatus = DeviceStatus.PENDING
    
    # Registration info
    registered_at: Optional[str] = None
    registered_via: str = "unknown"
    
    # Connection tracking
    last_seen: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    connection_count: int = 0
    
    # Activity tracking
    data_requests: int = 0
    decrypt_requests: int = 0
    failed_auth_attempts: int = 0
    
    def to_dict(self, include_token: bool = False) -> dict:
        """Convert to dictionary, optionally excluding trust token"""
        d = asdict(self)
        d['access_level'] = self.access_level.value
        d['status'] = self.status.value
        if not include_token:
            d.pop('trust_token', None)
        return d
    
    def is_trusted(self) -> bool:
        """Check if device is trusted"""
        return (
            self.access_level in [AccessLevel.FULL, AccessLevel.READ_ONLY] and
            self.status == DeviceStatus.ONLINE and
            self.trust_token is not None
        )


@dataclass
class RegistrationRequest:
    """Pending device registration"""
    code: str
    device_name: str
    access_level: AccessLevel
    created_at: str
    expires_at: str
    max_uses: int = 1
    current_uses: int = 0
    used_by: List[str] = field(default_factory=list)


class DeviceRegistry:
    """
    Manages device registration, authentication, and trust.
    
    Features:
    - One-time registration codes
    - Trust token verification
    - Real-time connection tracking
    - Rate limiting for failed attempts
    - Device revocation
    """
    
    def __init__(self, max_failed_attempts: int = 5, lockout_minutes: int = 15):
        """
        Initialize device registry
        
        Args:
            max_failed_attempts: Max failed auth before lockout
            lockout_minutes: Lockout duration
        """
        self.devices: Dict[str, DeviceInfo] = {}
        self.registration_codes: Dict[str, RegistrationRequest] = {}
        self.fingerprint_to_device: Dict[str, str] = {}
        
        # WebSocket connections
        self.websocket_connections: Dict[str, Set] = {}  # device_id -> set of websockets
        
        # Rate limiting
        self.max_failed_attempts = max_failed_attempts
        self.lockout_minutes = lockout_minutes
        self.lockout_until: Dict[str, datetime] = {}
        
        # Event callbacks
        self.on_device_registered = None
        self.on_device_connected = None
        self.on_device_disconnected = None
        self.on_auth_failed = None
    
    def generate_fingerprint(self, user_agent: str, ip_address: str, extra: str = "") -> str:
        """Generate unique device fingerprint"""
        data = f"{user_agent}|{ip_address}|{extra}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    def create_registration_code(self, 
                                  device_name: str,
                                  access_level: AccessLevel = AccessLevel.FULL,
                                  valid_hours: int = 24,
                                  max_uses: int = 100) -> str:  # Allow 100 uses by default
        """
        Create a registration code for device enrollment
        
        Args:
            device_name: Name for the device
            access_level: Access level to grant
            valid_hours: Hours until expiration
            max_uses: Maximum number of uses
            
        Returns:
            6-character registration code
        """
        code = secrets.token_hex(3).upper()
        
        # Ensure uniqueness
        while code in self.registration_codes:
            code = secrets.token_hex(3).upper()
        
        now = datetime.now()
        expires = now + timedelta(hours=valid_hours)
        
        self.registration_codes[code] = RegistrationRequest(
            code=code,
            device_name=device_name,
            access_level=access_level,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
            max_uses=max_uses
        )
        
        return code
    
    def validate_registration_code(self, code: str) -> tuple[bool, str, Optional[RegistrationRequest]]:
        """
        Validate a registration code
        
        Returns:
            (valid, message, registration_request)
        """
        code = code.upper().strip()
        
        if code not in self.registration_codes:
            return False, "Invalid registration code", None
        
        reg = self.registration_codes[code]
        
        if reg.current_uses >= reg.max_uses:
            return False, "Registration code already used", None
        
        expires = datetime.fromisoformat(reg.expires_at)
        if datetime.now() > expires:
            return False, "Registration code expired", None
        
        return True, "Valid", reg
    
    def register_device(self,
                        registration_code: str,
                        fingerprint: str,
                        ip_address: str = None,
                        user_agent: str = None) -> Optional[DeviceInfo]:
        """
        Register a new device using registration code
        
        Returns:
            DeviceInfo if successful, None otherwise
        """
        valid, message, reg = self.validate_registration_code(registration_code)
        if not valid:
            print(f"Registration failed: {message}")
            return None
        
        # Check if fingerprint already registered
        if fingerprint in self.fingerprint_to_device:
            existing_id = self.fingerprint_to_device[fingerprint]
            existing = self.devices.get(existing_id)
            if existing and existing.status != DeviceStatus.REVOKED:
                print(f"Device already registered: {existing.device_name}")
                # Update and return existing
                existing.last_seen = datetime.now().isoformat()
                existing.status = DeviceStatus.ONLINE
                return existing
        
        # Create new device
        device_id = secrets.token_hex(8)
        trust_token = secrets.token_urlsafe(32)
        
        device = DeviceInfo(
            device_id=device_id,
            device_name=reg.device_name,
            fingerprint=fingerprint,
            trust_token=trust_token,
            access_level=reg.access_level,
            status=DeviceStatus.ONLINE,
            registered_at=datetime.now().isoformat(),
            registered_via="registration_code",
            last_seen=datetime.now().isoformat(),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store device
        self.devices[device_id] = device
        self.fingerprint_to_device[fingerprint] = device_id
        
        # Update registration code usage
        reg.current_uses += 1
        reg.used_by.append(device_id)
        
        if self.on_device_registered:
            self.on_device_registered(device)
        
        return device
    
    def _is_locked_out(self, fingerprint: str) -> bool:
        """Check if fingerprint is locked out due to failed attempts"""
        if fingerprint in self.lockout_until:
            if datetime.now() < self.lockout_until[fingerprint]:
                return True
            else:
                del self.lockout_until[fingerprint]
        return False
    
    def _record_failed_attempt(self, fingerprint: str) -> bool:
        """
        Record failed authentication attempt
        
        Returns:
            True if now locked out
        """
        device_id = self.fingerprint_to_device.get(fingerprint)
        if device_id and device_id in self.devices:
            device = self.devices[device_id]
            device.failed_auth_attempts += 1
            
            if device.failed_auth_attempts >= self.max_failed_attempts:
                self.lockout_until[fingerprint] = datetime.now() + timedelta(minutes=self.lockout_minutes)
                device.status = DeviceStatus.REVOKED
                return True
        return False
    
    def authenticate(self,
                     device_id: str,
                     trust_token: str,
                     fingerprint: str = None) -> tuple[bool, Optional[DeviceInfo]]:
        """
        Authenticate a device request
        
        Returns:
            (authenticated, device_info)
        """
        # Check lockout
        if fingerprint and self._is_locked_out(fingerprint):
            return False, None
        
        if device_id not in self.devices:
            if fingerprint:
                self._record_failed_attempt(fingerprint)
            if self.on_auth_failed:
                self.on_auth_failed(device_id, fingerprint)
            return False, None
        
        device = self.devices[device_id]
        
        if device.status == DeviceStatus.REVOKED:
            return False, None
        
        if device.trust_token != trust_token:
            device.failed_auth_attempts += 1
            if fingerprint:
                self._record_failed_attempt(fingerprint)
            if self.on_auth_failed:
                self.on_auth_failed(device_id, fingerprint)
            return False, None
        
        # Successful auth - update device
        device.last_seen = datetime.now().isoformat()
        device.status = DeviceStatus.ONLINE
        device.connection_count += 1
        device.failed_auth_attempts = 0  # Reset on successful auth
        
        if self.on_device_connected:
            self.on_device_connected(device)
        
        return True, device
    
    def authenticate_by_fingerprint(self, fingerprint: str) -> tuple[bool, Optional[DeviceInfo]]:
        """
        Try to authenticate by fingerprint alone (for returning devices)
        
        Returns:
            (authenticated, device_info)
        """
        if self._is_locked_out(fingerprint):
            return False, None
        
        if fingerprint not in self.fingerprint_to_device:
            return False, None
        
        device_id = self.fingerprint_to_device[fingerprint]
        device = self.devices.get(device_id)
        
        if not device or device.status == DeviceStatus.REVOKED:
            return False, None
        
        # Update device
        device.last_seen = datetime.now().isoformat()
        device.status = DeviceStatus.ONLINE
        device.connection_count += 1
        
        return True, device
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def get_device_by_fingerprint(self, fingerprint: str) -> Optional[DeviceInfo]:
        """Get device by fingerprint"""
        device_id = self.fingerprint_to_device.get(fingerprint)
        if device_id:
            return self.devices.get(device_id)
        return None
    
    def revoke_device(self, device_id: str) -> bool:
        """Revoke a device's access"""
        if device_id in self.devices:
            self.devices[device_id].status = DeviceStatus.REVOKED
            self.devices[device_id].trust_token = None
            return True
        return False
    
    def update_access_level(self, device_id: str, access_level: AccessLevel) -> bool:
        """Update device access level"""
        if device_id in self.devices:
            self.devices[device_id].access_level = access_level
            return True
        return False
    
    def mark_offline(self, device_id: str):
        """Mark device as offline"""
        if device_id in self.devices:
            self.devices[device_id].status = DeviceStatus.OFFLINE
            if self.on_device_disconnected:
                self.on_device_disconnected(self.devices[device_id])
    
    def record_data_request(self, device_id: str):
        """Record a data request from device"""
        if device_id in self.devices:
            self.devices[device_id].data_requests += 1
    
    def record_decrypt_request(self, device_id: str):
        """Record a decrypt request from device"""
        if device_id in self.devices:
            self.devices[device_id].decrypt_requests += 1
    
    def list_devices(self, status: DeviceStatus = None) -> List[dict]:
        """List all devices, optionally filtered by status"""
        devices = self.devices.values()
        if status:
            devices = [d for d in devices if d.status == status]
        return [d.to_dict(include_token=False) for d in devices]
    
    def list_trusted_devices(self) -> List[dict]:
        """List all trusted devices"""
        return [d.to_dict() for d in self.devices.values() if d.is_trusted()]
    
    def cleanup_expired_codes(self) -> int:
        """Remove expired registration codes"""
        now = datetime.now()
        expired = [
            code for code, reg in self.registration_codes.items()
            if datetime.fromisoformat(reg.expires_at) < now
        ]
        for code in expired:
            del self.registration_codes[code]
        return len(expired)
    
    def get_stats(self) -> dict:
        """Get registry statistics"""
        now = datetime.now()
        online = sum(1 for d in self.devices.values() if d.status == DeviceStatus.ONLINE)
        trusted = sum(1 for d in self.devices.values() if d.is_trusted())
        pending_codes = sum(
            1 for r in self.registration_codes.values()
            if r.current_uses < r.max_uses and datetime.fromisoformat(r.expires_at) > now
        )
        
        return {
            'total_devices': len(self.devices),
            'online_devices': online,
            'trusted_devices': trusted,
            'pending_registration_codes': pending_codes,
            'locked_out_fingerprints': len(self.lockout_until)
        }
    
    # WebSocket connection management
    def add_websocket(self, device_id: str, websocket):
        """Register websocket connection for device"""
        if device_id not in self.websocket_connections:
            self.websocket_connections[device_id] = set()
        self.websocket_connections[device_id].add(websocket)
    
    def remove_websocket(self, device_id: str, websocket):
        """Remove websocket connection"""
        if device_id in self.websocket_connections:
            self.websocket_connections[device_id].discard(websocket)
            if not self.websocket_connections[device_id]:
                del self.websocket_connections[device_id]
                self.mark_offline(device_id)
    
    async def broadcast_to_trusted(self, message: dict, exclude: str = None):
        """Broadcast message to all trusted connected devices"""
        for device_id, connections in self.websocket_connections.items():
            if device_id == exclude:
                continue
            
            device = self.devices.get(device_id)
            if device and device.is_trusted():
                for ws in list(connections):
                    try:
                        await ws.send_json(message)
                    except Exception:
                        connections.discard(ws)
    
    async def broadcast_to_all(self, message: dict, encrypted_only_message: dict = None):
        """
        Broadcast to all connected devices.
        Trusted devices get full message, untrusted get encrypted_only_message
        """
        for device_id, connections in self.websocket_connections.items():
            device = self.devices.get(device_id)
            
            if device and device.is_trusted():
                msg = message
            else:
                msg = encrypted_only_message or message
            
            for ws in list(connections):
                try:
                    await ws.send_json(msg)
                except Exception:
                    connections.discard(ws)