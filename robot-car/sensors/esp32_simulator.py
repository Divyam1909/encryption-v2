"""
ESP32 Robot Car Simulator
=========================
Simulates the ESP32 microcontroller for the robot car:
1. Collects ultrasonic sensor data
2. Encrypts data using FHE before transmission
3. Sends encrypted data to server
"""

import asyncio
import json
import hashlib
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensors.sensors import SensorArray, create_robot_car_sensors


@dataclass
class ESP32Config:
    """Configuration for ESP32 simulator"""
    device_id: str = "esp32_robot_car_01"
    device_name: str = "Robot Car Controller"
    server_url: str = "http://localhost:8000"
    transmission_interval: float = 0.5  # seconds (fast for robot car)
    batch_size: int = 3  # readings per sensor
    encrypt_locally: bool = True
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
    Simulates ESP32 Robot Car Controller.
    
    Features:
    - Asynchronous sensor reading and transmission
    - FHE encryption before transmission
    - Retry logic for connection failures
    """
    
    def __init__(self, config: ESP32Config = None):
        self.config = config or ESP32Config()
        self.sensor_array: Optional[SensorArray] = None
        self.fhe_engine = None
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
        
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def _close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def attach_sensors(self, sensor_array: SensorArray):
        """Attach a sensor array to the ESP32"""
        self.sensor_array = sensor_array
        print(f"📡 ESP32: Attached {len(sensor_array)} sensors")
    
    def set_fhe_context(self, context_bytes: bytes):
        """Set FHE encryption context"""
        from fhe_core.encryption_core import FHEEngine
        
        self.fhe_context_bytes = context_bytes
        self.fhe_engine = FHEEngine.from_context(context_bytes, has_secret_key=False)
        print(f"🔐 ESP32: FHE encryption enabled")
    
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
        """Transmit packet to server with retry logic"""
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
        if asyncio.iscoroutinefunction(callback):
            await callback(*args)
        else:
            callback(*args)
    
    async def _run_loop(self):
        """Main sensor reading and transmission loop"""
        print(f"🚀 ESP32 Robot Car: Starting sensor loop")
        print(f"   Interval: {self.config.transmission_interval}s")
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
                    print(f"✓ ESP32: Packet #{packet.sequence_number} transmitted")
                else:
                    print(f"✗ ESP32: Failed packet #{packet.sequence_number}")
                
                await asyncio.sleep(self.config.transmission_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ ESP32: Error in loop: {e}")
                if self.on_error:
                    await self._call_callback(self.on_error, e)
                await asyncio.sleep(self.config.retry_delay)
        
        print(f"🛑 ESP32 Robot Car: Stopped")
    
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


def create_robot_car_esp32(server_url: str = "http://localhost:8000") -> ESP32Simulator:
    """Create ESP32 configured for robot car"""
    config = ESP32Config(
        device_id="esp32_robot_car_01",
        device_name="Robot Car Controller",
        server_url=server_url,
        transmission_interval=0.5,
        batch_size=3
    )
    
    esp32 = ESP32Simulator(config)
    esp32.attach_sensors(create_robot_car_sensors())
    
    return esp32


# ==================== DEMO ====================

async def demo():
    """Demonstrate ESP32 simulator"""
    print("=" * 60)
    print("ESP32 Robot Car Simulator Demo")
    print("=" * 60)
    
    esp32 = create_robot_car_esp32()
    
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
    
    # Sample packet
    print("\n📦 Creating sample packet...")
    sensor_data = esp32._collect_sensor_data()
    
    if esp32.fhe_engine:
        encrypted_data = esp32._encrypt_sensor_data(sensor_data)
        packet = esp32._create_packet(encrypted_data, encrypted=True)
    else:
        packet = esp32._create_packet(sensor_data, encrypted=False)
    
    print(f"   Device: {packet.device_name}")
    print(f"   Timestamp: {packet.timestamp}")
    print(f"   Encrypted: {packet.encrypted}")
    print(f"   Sensors: {list(packet.sensor_data.keys())}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())