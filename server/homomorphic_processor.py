"""
Homomorphic Processor
=====================
Performs computations on encrypted data without decryption.
Implements statistical operations, anomaly detection, and data aggregation
entirely on ciphertext using FHE operations.
"""

import sys
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import deque
import json

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ProcessedResult:
    """Result of homomorphic computation"""
    operation: str
    sensor_id: str
    result_ciphertext: dict  # Encrypted result
    input_count: int
    computed_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass  
class SensorBuffer:
    """Buffer for accumulating encrypted sensor data"""
    sensor_id: str
    sensor_type: str
    encrypted_readings: deque  # Queue of EncryptedVector dicts
    max_size: int = 100
    
    def add(self, encrypted_data: dict):
        """Add encrypted reading to buffer"""
        if len(self.encrypted_readings) >= self.max_size:
            self.encrypted_readings.popleft()
        self.encrypted_readings.append(encrypted_data)
    
    def get_latest(self, count: int = 10) -> List[dict]:
        """Get most recent readings"""
        readings = list(self.encrypted_readings)
        return readings[-count:] if len(readings) >= count else readings
    
    def clear(self):
        """Clear buffer"""
        self.encrypted_readings.clear()


class HomomorphicProcessor:
    """
    Processes encrypted sensor data using homomorphic operations.
    
    All computations are performed on ciphertext - the server never
    sees the actual sensor values, only the encrypted form.
    
    Supported Operations:
    - Encrypted sum/mean of sensor readings
    - Encrypted scaling and offset adjustments
    - Aggregation of multiple encrypted vectors
    - Rolling statistics on encrypted time series
    """
    
    def __init__(self, buffer_size: int = 100):
        """
        Initialize processor
        
        Args:
            buffer_size: Max readings to keep per sensor
        """
        self.fhe_engine = None
        self.buffers: Dict[str, SensorBuffer] = {}
        self.buffer_size = buffer_size
        self.operations_count = 0
        self.last_operation_time = None
        
        # Results cache
        self.cached_results: Dict[str, ProcessedResult] = {}
        
    def set_fhe_engine(self, fhe_engine):
        """
        Set the FHE engine for computations
        
        Args:
            fhe_engine: FHEEngine instance with public context
        """
        self.fhe_engine = fhe_engine
        print("🔢 HomomorphicProcessor: FHE engine configured")
    
    def set_fhe_context(self, context_bytes: bytes):
        """
        Set FHE context from serialized bytes
        
        Args:
            context_bytes: Serialized TenSEAL context
        """
        from fhe_core.encryption_core import FHEEngine
        self.fhe_engine = FHEEngine.from_context(context_bytes, has_secret_key=False)
        print("🔢 HomomorphicProcessor: FHE context loaded")
    
    def _ensure_buffer(self, sensor_id: str, sensor_type: str = "unknown") -> SensorBuffer:
        """Get or create buffer for sensor"""
        if sensor_id not in self.buffers:
            self.buffers[sensor_id] = SensorBuffer(
                sensor_id=sensor_id,
                sensor_type=sensor_type,
                encrypted_readings=deque(maxlen=self.buffer_size)
            )
        return self.buffers[sensor_id]
    
    def ingest_encrypted_data(self, device_id: str, sensor_data: Dict[str, dict]):
        """
        Ingest encrypted sensor data from ESP32
        
        Args:
            device_id: Source device ID
            sensor_data: Dict mapping sensor_id to encrypted vector dict
        """
        for sensor_id, encrypted_dict in sensor_data.items():
            # Determine sensor type from metadata
            sensor_type = encrypted_dict.get('sensor_type', 'unknown')
            buffer = self._ensure_buffer(sensor_id, sensor_type)
            
            # Add with device metadata
            data_with_meta = {
                **encrypted_dict,
                'device_id': device_id,
                'ingested_at': datetime.now().isoformat()
            }
            buffer.add(data_with_meta)
    
    def _load_encrypted_vector(self, encrypted_dict: dict):
        """Load encrypted vector from dict"""
        from fhe_core.encryption_core import EncryptedVector
        return EncryptedVector.from_dict(encrypted_dict)
    
    # ==================== HOMOMORPHIC OPERATIONS ====================
    
    def compute_encrypted_sum(self, sensor_id: str, last_n: int = 10) -> Optional[ProcessedResult]:
        """
        Compute sum of last N readings (encrypted)
        
        This adds encrypted vectors together without decryption.
        Result is still encrypted.
        """
        if self.fhe_engine is None:
            raise ValueError("FHE engine not configured")
        
        buffer = self.buffers.get(sensor_id)
        if not buffer or len(buffer.encrypted_readings) == 0:
            return None
        
        readings = buffer.get_latest(last_n)
        if len(readings) < 2:
            return None
        
        try:
            # Load first vector
            result = self._load_encrypted_vector(readings[0])
            
            # Add remaining vectors
            for i, reading in enumerate(readings[1:], 1):
                vec = self._load_encrypted_vector(reading)
                result = self.fhe_engine.add_encrypted(result, vec)
            
            self.operations_count += 1
            self.last_operation_time = datetime.now()
            
            processed = ProcessedResult(
                operation="encrypted_sum",
                sensor_id=sensor_id,
                result_ciphertext=result.to_dict(),
                input_count=len(readings),
                computed_at=datetime.now().isoformat(),
                metadata={
                    'readings_used': len(readings),
                    'buffer_type': buffer.sensor_type
                }
            )
            
            self.cached_results[f"sum_{sensor_id}"] = processed
            return processed
            
        except Exception as e:
            print(f"❌ Error computing encrypted sum: {e}")
            return None
    
    def compute_encrypted_mean(self, sensor_id: str, last_n: int = 10) -> Optional[ProcessedResult]:
        """
        Compute mean of last N readings (encrypted)
        
        Computes sum then divides by n (multiplies by 1/n).
        Result is still encrypted.
        """
        if self.fhe_engine is None:
            raise ValueError("FHE engine not configured")
        
        buffer = self.buffers.get(sensor_id)
        if not buffer or len(buffer.encrypted_readings) == 0:
            return None
        
        readings = buffer.get_latest(last_n)
        if len(readings) < 2:
            return None
        
        try:
            # First compute sum
            result = self._load_encrypted_vector(readings[0])
            for reading in readings[1:]:
                vec = self._load_encrypted_vector(reading)
                result = self.fhe_engine.add_encrypted(result, vec)
            
            # Divide by n (multiply by 1/n)
            n = len(readings)
            result = self.fhe_engine.multiply_plain(result, 1.0 / n)
            
            self.operations_count += 1
            self.last_operation_time = datetime.now()
            
            processed = ProcessedResult(
                operation="encrypted_mean",
                sensor_id=sensor_id,
                result_ciphertext=result.to_dict(),
                input_count=len(readings),
                computed_at=datetime.now().isoformat(),
                metadata={
                    'readings_used': len(readings),
                    'buffer_type': buffer.sensor_type,
                    'divisor': n
                }
            )
            
            self.cached_results[f"mean_{sensor_id}"] = processed
            return processed
            
        except Exception as e:
            print(f"❌ Error computing encrypted mean: {e}")
            return None
    
    def compute_encrypted_scaled(self, 
                                  sensor_id: str, 
                                  scale: float, 
                                  offset: float = 0.0) -> Optional[ProcessedResult]:
        """
        Scale and offset latest reading: (value * scale) + offset
        
        Useful for unit conversions on encrypted data.
        E.g., Celsius to Fahrenheit: scale=1.8, offset=32
        """
        if self.fhe_engine is None:
            raise ValueError("FHE engine not configured")
        
        buffer = self.buffers.get(sensor_id)
        if not buffer or len(buffer.encrypted_readings) == 0:
            return None
        
        try:
            latest = buffer.get_latest(1)[0]
            vec = self._load_encrypted_vector(latest)
            
            # Apply scale
            if scale != 1.0:
                vec = self.fhe_engine.multiply_plain(vec, scale)
            
            # Apply offset
            if offset != 0.0:
                vec = self.fhe_engine.add_plain(vec, offset)
            
            self.operations_count += 1
            self.last_operation_time = datetime.now()
            
            return ProcessedResult(
                operation="encrypted_scale_offset",
                sensor_id=sensor_id,
                result_ciphertext=vec.to_dict(),
                input_count=1,
                computed_at=datetime.now().isoformat(),
                metadata={
                    'scale': scale,
                    'offset': offset,
                    'buffer_type': buffer.sensor_type
                }
            )
            
        except Exception as e:
            print(f"❌ Error computing scaled value: {e}")
            return None
    
    def compute_encrypted_difference(self, 
                                      sensor_id: str) -> Optional[ProcessedResult]:
        """
        Compute difference between latest and previous reading (encrypted)
        
        Useful for detecting changes/anomalies.
        """
        if self.fhe_engine is None:
            raise ValueError("FHE engine not configured")
        
        buffer = self.buffers.get(sensor_id)
        if not buffer or len(buffer.encrypted_readings) < 2:
            return None
        
        try:
            readings = buffer.get_latest(2)
            prev = self._load_encrypted_vector(readings[0])
            curr = self._load_encrypted_vector(readings[1])
            
            # Compute difference
            diff = self.fhe_engine.subtract_encrypted(curr, prev)
            
            self.operations_count += 1
            self.last_operation_time = datetime.now()
            
            return ProcessedResult(
                operation="encrypted_difference",
                sensor_id=sensor_id,
                result_ciphertext=diff.to_dict(),
                input_count=2,
                computed_at=datetime.now().isoformat(),
                metadata={
                    'buffer_type': buffer.sensor_type,
                    'description': 'current - previous'
                }
            )
            
        except Exception as e:
            print(f"❌ Error computing difference: {e}")
            return None
    
    def aggregate_sensors(self, 
                          sensor_ids: List[str],
                          operation: str = "sum") -> Optional[ProcessedResult]:
        """
        Aggregate data from multiple sensors (encrypted)
        
        Args:
            sensor_ids: List of sensor IDs to aggregate
            operation: "sum" or "mean"
        """
        if self.fhe_engine is None:
            raise ValueError("FHE engine not configured")
        
        vectors = []
        for sensor_id in sensor_ids:
            buffer = self.buffers.get(sensor_id)
            if buffer and len(buffer.encrypted_readings) > 0:
                latest = buffer.get_latest(1)[0]
                vectors.append(self._load_encrypted_vector(latest))
        
        if len(vectors) < 2:
            return None
        
        try:
            # Sum all vectors
            result = vectors[0]
            for vec in vectors[1:]:
                result = self.fhe_engine.add_encrypted(result, vec)
            
            if operation == "mean":
                result = self.fhe_engine.multiply_plain(result, 1.0 / len(vectors))
            
            self.operations_count += 1
            self.last_operation_time = datetime.now()
            
            return ProcessedResult(
                operation=f"aggregate_{operation}",
                sensor_id=",".join(sensor_ids),
                result_ciphertext=result.to_dict(),
                input_count=len(vectors),
                computed_at=datetime.now().isoformat(),
                metadata={
                    'sensors_aggregated': sensor_ids,
                    'aggregation_type': operation
                }
            )
            
        except Exception as e:
            print(f"❌ Error aggregating sensors: {e}")
            return None
    
    # ==================== DATA ACCESS ====================
    
    def get_latest_encrypted(self, sensor_id: str) -> Optional[dict]:
        """Get latest encrypted reading for sensor"""
        buffer = self.buffers.get(sensor_id)
        if buffer and len(buffer.encrypted_readings) > 0:
            return buffer.get_latest(1)[0]
        return None
    
    def get_latest_all(self) -> Dict[str, dict]:
        """Get latest encrypted readings from all sensors"""
        result = {}
        for sensor_id, buffer in self.buffers.items():
            if len(buffer.encrypted_readings) > 0:
                result[sensor_id] = buffer.get_latest(1)[0]
        return result
    
    def get_history_encrypted(self, sensor_id: str, count: int = 10) -> List[dict]:
        """Get encrypted history for sensor"""
        buffer = self.buffers.get(sensor_id)
        if buffer:
            return buffer.get_latest(count)
        return []
    
    def get_cached_result(self, key: str) -> Optional[ProcessedResult]:
        """Get cached computation result"""
        return self.cached_results.get(key)
    
    def get_all_cached_results(self) -> Dict[str, dict]:
        """Get all cached results"""
        return {k: v.to_dict() for k, v in self.cached_results.items()}
    
    # ==================== UTILITIES ====================
    
    def list_sensors(self) -> List[dict]:
        """List all sensors with buffer info"""
        return [
            {
                'sensor_id': sensor_id,
                'sensor_type': buffer.sensor_type,
                'reading_count': len(buffer.encrypted_readings),
                'max_size': buffer.max_size
            }
            for sensor_id, buffer in self.buffers.items()
        ]
    
    def get_stats(self) -> dict:
        """Get processor statistics"""
        total_readings = sum(
            len(b.encrypted_readings) for b in self.buffers.values()
        )
        
        return {
            'sensors_tracked': len(self.buffers),
            'total_readings_buffered': total_readings,
            'total_operations': self.operations_count,
            'cached_results': len(self.cached_results),
            'last_operation': self.last_operation_time.isoformat() if self.last_operation_time else None,
            'fhe_configured': self.fhe_engine is not None
        }
    
    def clear_sensor(self, sensor_id: str):
        """Clear buffer for specific sensor"""
        if sensor_id in self.buffers:
            self.buffers[sensor_id].clear()
    
    def clear_all(self):
        """Clear all buffers and caches"""
        for buffer in self.buffers.values():
            buffer.clear()
        self.cached_results.clear()


# ==================== DEMO ====================

def demo():
    """Demonstrate homomorphic processing"""
    print("=" * 60)
    print("Homomorphic Processor Demo")
    print("=" * 60)
    
    # Create processor and FHE engine
    from fhe_core.encryption_core import FHEEngine
    
    engine = FHEEngine()
    processor = HomomorphicProcessor()
    processor.set_fhe_engine(engine)
    
    print(f"\n✓ Processor initialized")
    
    # Simulate encrypted sensor data
    print("\n📊 Simulating encrypted sensor data...")
    
    for i in range(5):
        # Encrypt some fake temperature readings
        temps = [25.0 + i * 0.5 + j * 0.1 for j in range(5)]
        encrypted = engine.encrypt(temps, "temperature")
        
        processor.ingest_encrypted_data(
            device_id="esp32_test",
            sensor_data={
                "temp_sensor_1": encrypted.to_dict()
            }
        )
    
    print(f"   Ingested 5 encrypted readings")
    print(f"   Stats: {processor.get_stats()}")
    
    # Compute encrypted mean
    print("\n🔢 Computing encrypted mean (no decryption on server)...")
    result = processor.compute_encrypted_mean("temp_sensor_1", last_n=5)
    
    if result:
        print(f"   Operation: {result.operation}")
        print(f"   Input count: {result.input_count}")
        print(f"   Result is encrypted: True")
        
        # Decrypt on trusted side
        encrypted_result = engine._load_encrypted_vector(
            processor._load_encrypted_vector(result.result_ciphertext)
        )
        # Re-create from dict
        from fhe_core.encryption_core import EncryptedVector
        enc_vec = EncryptedVector.from_dict(result.result_ciphertext)
        decrypted = engine.decrypt(enc_vec)
        print(f"\n   [Trusted client decrypts]: Mean ≈ {decrypted[0]:.2f}°C")
    
    print("\n" + "=" * 60)
    print("Homomorphic Processor Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()