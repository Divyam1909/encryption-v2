"""
ESP32 Simulator
===============
Simulates an ESP32 microcontroller that:
1. Collects sensor data
2. Encrypts data using FHE before transmission
3. Sends encrypted data to server
4. Operates autonomously with configurable intervals
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.sensors import (
    SensorArray, 
    BaseSensor,
    create_robot_car_sensors,
    create_environment_sensors,
    create_military_base_sensors
)


@dataclass
class ESP32Config:
    """Configuration for ESP32 simulator"""
    device_id: str
    device_name: str
    server_url: str
    transmission_interval: float = 1.0  # seconds
    batch_size: int = 5  # readings per sensor per transmission
    encrypt_locally: bool = True  # Encrypt before sending
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class TransmissionPacket:
    """Data packet for server transmission"""
    device_id: str
    device_name: str
    timestamp: str
    sequence_number: int
    sensor_data: Dict[str, Any]
    encrypted: bool
    checksum: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ESP32Simulator:
    """
    Simulates ESP32 microcontroller functionality.
    
    Features:
    - Asynchronous sensor reading and transmission
    - Optional FHE encryption before transmission
    - Retry logic for connection failures
    - Configurable transmission intervals
    - Support for multiple sensor arrays
    """
    
    def __init__(self, config: ESP32Config):
        """
        Initialize ESP32 simulator
        
        Args:
            config: ESP32 configuration
        """
        self.config = config
        self.sensor_array: Optional[SensorArray] = None
        self.fhe_engine = None  # Will be set if encryption enabled
        self.fhe_context_bytes: Optional[bytes] = None
        
        self.running = False
        self.sequence_number = 0
        self.total_transmissions = 0
        self.failed_transmissions = 0
        self.last_transmission_time = None
        
        # Callbacks
        self.on_reading: Optional[Callable] = None
        self.on_transmission: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Session for HTTP requests
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def attach_sensors(self, sensor_array: SensorArray):
        """Attach a sensor array to the ESP32"""
        self.sensor_array = sensor_array
        print(f"📡 ESP32 [{self.config.device_id}]: Attached {len(sensor_array)} sensors")
    
    def set_fhe_context(self, context_bytes: bytes):
        """
        Set FHE encryption context for encrypting data before transmission
        
        Args:
            context_bytes: Serialized TenSEAL context (public context sufficient)
        """
        from fhe_core.encryption_core import FHEEngine
        
        self.fhe_context_bytes = context_bytes
        self.fhe_engine = FHEEngine.from_context(context_bytes, has_secret_key=False)
        print(f"🔐 ESP32 [{self.config.device_id}]: FHE encryption enabled")
    
    def _collect_sensor_data(self) -> Dict[str, List[float]]:
        """Collect batch readings from all sensors"""
        if self.sensor_array is None:
            return {}
        
        return self.sensor_array.read_batch_all(count=self.config.batch_size)
    
    def _encrypt_sensor_data(self, sensor_data: Dict[str, List[float]]) -> Dict[str, dict]:
        """Encrypt sensor data using FHE"""
        if self.fhe_engine is None:
            return sensor_data
        
        encrypted_data = {}
        for sensor_id, values in sensor_data.items():
            sensor = self.sensor_array.get_sensor(sensor_id)
            sensor_type = sensor.sensor_type if sensor else "unknown"
            
            encrypted_vector = self.fhe_engine.encrypt(values, sensor_type)
            encrypted_data[sensor_id] = encrypted_vector.to_dict()
        
        return encrypted_data
    
    def _create_packet(self, sensor_data: Dict[str, Any], encrypted: bool) -> TransmissionPacket:
        """Create transmission packet"""
        self.sequence_number += 1
        
        # Create checksum of data
        data_str = json.dumps(sensor_data, sort_keys=True)
        checksum = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        return TransmissionPacket(
            device_id=self.config.device_id,
            device_name=self.config.device_name,
            timestamp=datetime.now().isoformat(),
            sequence_number=self.sequence_number,
            sensor_data=sensor_data,
            encrypted=encrypted,
            checksum=checksum
        )
    
    async def _transmit_packet(self, packet: TransmissionPacket) -> bool:
        """
        Transmit packet to server with retry logic
        
        Returns:
            True if successful, False otherwise
        """
        session = await self._get_session()
        
        for attempt in range(self.config.retry_attempts):
            try:
                async with session.post(
                    f"{self.config.server_url}/api/sensor-data",
                    json=packet.to_dict(),
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.total_transmissions += 1
                        self.last_transmission_time = datetime.now()
                        
                        if self.on_transmission:
                            await self._call_callback(self.on_transmission, packet)
                        
                        return True
                    else:
                        print(f"⚠️ ESP32: Server returned {response.status}")
                        
            except aiohttp.ClientError as e:
                print(f"⚠️ ESP32: Connection error (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
            except Exception as e:
                print(f"❌ ESP32: Transmission error: {e}")
                if self.on_error:
                    await self._call_callback(self.on_error, e)
                break
        
        self.failed_transmissions += 1
        return False
    
    async def _call_callback(self, callback: Callable, *args):
        """Call callback (handles both sync and async)"""
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)
    
    async def _run_loop(self):
        """Main sensor reading and transmission loop"""
        print(f"🚀 ESP32 [{self.config.device_id}]: Starting sensor loop")
        print(f"   Interval: {self.config.transmission_interval}s")
        print(f"   Batch Size: {self.config.batch_size}")
        print(f"   Encryption: {'Enabled' if self.fhe_engine else 'Disabled'}")
        print(f"   Server: {self.config.server_url}")
        
        while self.running:
            try:
                # Collect sensor data
                sensor_data = self._collect_sensor_data()
                
                if self.on_reading:
                    await self._call_callback(self.on_reading, sensor_data)
                
                # Encrypt if FHE is enabled
                if self.config.encrypt_locally and self.fhe_engine:
                    processed_data = self._encrypt_sensor_data(sensor_data)
                    encrypted = True
                else:
                    processed_data = sensor_data
                    encrypted = False
                
                # Create and transmit packet
                packet = self._create_packet(processed_data, encrypted)
                success = await self._transmit_packet(packet)
                
                if success:
                    print(f"✓ ESP32: Transmitted packet #{packet.sequence_number} "
                          f"({'encrypted' if encrypted else 'plaintext'})")
                else:
                    print(f"✗ ESP32: Failed to transmit packet #{packet.sequence_number}")
                
                # Wait for next interval
                await asyncio.sleep(self.config.transmission_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ ESP32: Error in loop: {e}")
                if self.on_error:
                    await self._call_callback(self.on_error, e)
                await asyncio.sleep(self.config.retry_delay)
        
        print(f"🛑 ESP32 [{self.config.device_id}]: Stopped")
    
    async def start(self):
        """Start the ESP32 simulator"""
        if self.running:
            print("⚠️ ESP32: Already running")
            return
        
        if self.sensor_array is None:
            print("❌ ESP32: No sensors attached")
            return
        
        self.running = True
        await self._run_loop()
    
    async def stop(self):
        """Stop the ESP32 simulator"""
        self.running = False
        await self._close_session()
    
    def get_status(self) -> dict:
        """Get current status"""
        return {
            'device_id': self.config.device_id,
            'device_name': self.config.device_name,
            'running': self.running,
            'sensors_attached': len(self.sensor_array) if self.sensor_array else 0,
            'encryption_enabled': self.fhe_engine is not None,
            'total_transmissions': self.total_transmissions,
            'failed_transmissions': self.failed_transmissions,
            'last_transmission': self.last_transmission_time.isoformat() if self.last_transmission_time else None,
            'sequence_number': self.sequence_number
        }
    
    async def single_transmission(self) -> Optional[TransmissionPacket]:
        """Perform a single reading and transmission (for testing)"""
        if self.sensor_array is None:
            return None
        
        sensor_data = self._collect_sensor_data()
        
        if self.config.encrypt_locally and self.fhe_engine:
            processed_data = self._encrypt_sensor_data(sensor_data)
            encrypted = True
        else:
            processed_data = sensor_data
            encrypted = False
        
        packet = self._create_packet(processed_data, encrypted)
        await self._transmit_packet(packet)
        
        return packet


class ESP32Manager:
    """
    Manages multiple ESP32 simulators
    """
    
    def __init__(self):
        self.devices: Dict[str, ESP32Simulator] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
    
    def add_device(self, esp32: ESP32Simulator):
        """Add an ESP32 device to management"""
        self.devices[esp32.config.device_id] = esp32
    
    def remove_device(self, device_id: str):
        """Remove an ESP32 device"""
        if device_id in self.devices:
            del self.devices[device_id]
    
    async def start_all(self):
        """Start all ESP32 devices"""
        for device_id, esp32 in self.devices.items():
            task = asyncio.create_task(esp32.start())
            self.tasks[device_id] = task
    
    async def stop_all(self):
        """Stop all ESP32 devices"""
        for esp32 in self.devices.values():
            await esp32.stop()
        
        for task in self.tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self.tasks.clear()
    
    def get_all_status(self) -> Dict[str, dict]:
        """Get status of all devices"""
        return {
            device_id: esp32.get_status() 
            for device_id, esp32 in self.devices.items()
        }


# ==================== FACTORY FUNCTIONS ====================

def create_robot_car_esp32(server_url: str) -> ESP32Simulator:
    """Create ESP32 configured for robot car"""
    config = ESP32Config(
        device_id="esp32_robot_car_01",
        device_name="Robot Car Controller",
        server_url=server_url,
        transmission_interval=0.5,  # Fast updates for robot
        batch_size=3
    )
    
    esp32 = ESP32Simulator(config)
    esp32.attach_sensors(create_robot_car_sensors())
    
    return esp32


def create_environment_monitor_esp32(server_url: str) -> ESP32Simulator:
    """Create ESP32 configured for environment monitoring"""
    config = ESP32Config(
        device_id="esp32_env_monitor_01",
        device_name="Environment Monitor",
        server_url=server_url,
        transmission_interval=2.0,  # Slower updates for environment
        batch_size=5
    )
    
    esp32 = ESP32Simulator(config)
    esp32.attach_sensors(create_environment_sensors())
    
    return esp32


def create_security_esp32(server_url: str) -> ESP32Simulator:
    """Create ESP32 configured for security/military monitoring"""
    config = ESP32Config(
        device_id="esp32_security_01",
        device_name="Security Monitor",
        server_url=server_url,
        transmission_interval=1.0,
        batch_size=5
    )
    
    esp32 = ESP32Simulator(config)
    esp32.attach_sensors(create_military_base_sensors())
    
    return esp32


# ==================== DEMO ====================

async def demo():
    """Demonstrate ESP32 simulator"""
    print("=" * 60)
    print("ESP32 Simulator Demo")
    print("=" * 60)
    
    # Create ESP32
    config = ESP32Config(
        device_id="esp32_demo",
        device_name="Demo ESP32",
        server_url="http://localhost:8000",
        transmission_interval=1.0,
        batch_size=3
    )
    
    esp32 = ESP32Simulator(config)
    esp32.attach_sensors(create_environment_sensors())
    
    # Create FHE context for encryption
    try:
        from fhe_core.encryption_core import FHEEngine
        engine = FHEEngine()
        esp32.set_fhe_context(engine.get_public_context())
    except ImportError:
        print("⚠️ FHE not available, running without encryption")
    
    # Show status
    print(f"\n📊 ESP32 Status:")
    for key, value in esp32.get_status().items():
        print(f"   {key}: {value}")
    
    # Single transmission (will fail without server, but shows packet creation)
    print("\n📦 Creating sample packet...")
    sensor_data = esp32._collect_sensor_data()
    
    if esp32.fhe_engine:
        encrypted_data = esp32._encrypt_sensor_data(sensor_data)
        packet = esp32._create_packet(encrypted_data, encrypted=True)
    else:
        packet = esp32._create_packet(sensor_data, encrypted=False)
    
    print(f"   Device: {packet.device_name}")
    print(f"   Timestamp: {packet.timestamp}")
    print(f"   Sequence: {packet.sequence_number}")
    print(f"   Encrypted: {packet.encrypted}")
    print(f"   Checksum: {packet.checksum}")
    print(f"   Sensors: {list(packet.sensor_data.keys())}")
    
    if packet.encrypted:
        # Show sample ciphertext
        sample_sensor = list(packet.sensor_data.keys())[0]
        ciphertext = packet.sensor_data[sample_sensor].get('ciphertext', 'N/A')
        print(f"\n🔒 Sample Ciphertext ({sample_sensor}):")
        print(f"   {ciphertext[:80]}...")
    
    print("\n" + "=" * 60)
    print("ESP32 Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())