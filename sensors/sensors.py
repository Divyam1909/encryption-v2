"""
Simulated IoT Sensors
======================
High-fidelity sensor simulations with realistic noise patterns,
drift, and environmental modeling for testing the FHE system.
"""

import numpy as np
from typing import List, Optional, Dict, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from abc import ABC, abstractmethod
import random
import math


@dataclass
class SensorReading:
    """Single sensor reading with metadata"""
    value: float
    unit: str
    timestamp: str
    sensor_id: str
    sensor_type: str
    quality: float = 1.0  # 0-1 signal quality
    
    def to_dict(self) -> dict:
        return {
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp,
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'quality': self.quality
        }


class BaseSensor(ABC):
    """Abstract base class for all sensors"""
    
    def __init__(self,
                 sensor_id: str,
                 name: str,
                 unit: str,
                 min_value: float,
                 max_value: float,
                 noise_level: float = 0.02,
                 drift_rate: float = 0.001):
        """
        Initialize sensor
        
        Args:
            sensor_id: Unique identifier
            name: Human-readable name
            unit: Measurement unit
            min_value: Minimum possible reading
            max_value: Maximum possible reading
            noise_level: Standard deviation of gaussian noise (fraction of range)
            drift_rate: Rate of sensor drift over time
        """
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.noise_level = noise_level
        self.drift_rate = drift_rate
        
        self.range = max_value - min_value
        self.created_at = datetime.now()
        self.readings_count = 0
        self.drift_offset = 0.0
        self.last_value = (min_value + max_value) / 2
        
    @property
    @abstractmethod
    def sensor_type(self) -> str:
        """Return sensor type identifier"""
        pass
    
    @abstractmethod
    def _generate_base_value(self) -> float:
        """Generate base sensor value (to be overridden)"""
        pass
    
    def _apply_noise(self, value: float) -> float:
        """Apply gaussian noise to reading"""
        noise = np.random.normal(0, self.noise_level * self.range)
        return value + noise
    
    def _apply_drift(self, value: float) -> float:
        """Apply long-term drift"""
        # Slow random walk for drift
        self.drift_offset += np.random.normal(0, self.drift_rate * self.range)
        # Clamp drift
        self.drift_offset = np.clip(self.drift_offset, -0.1 * self.range, 0.1 * self.range)
        return value + self.drift_offset
    
    def _clamp(self, value: float) -> float:
        """Ensure value is within valid range"""
        return np.clip(value, self.min_value, self.max_value)
    
    def read(self) -> SensorReading:
        """Take a single sensor reading"""
        base_value = self._generate_base_value()
        noisy_value = self._apply_noise(base_value)
        drifted_value = self._apply_drift(noisy_value)
        final_value = self._clamp(drifted_value)
        
        # Smooth with previous reading
        smoothing = 0.3
        final_value = smoothing * self.last_value + (1 - smoothing) * final_value
        self.last_value = final_value
        
        self.readings_count += 1
        
        # Calculate signal quality based on stability
        quality = 1.0 - min(abs(self.drift_offset) / (0.1 * self.range), 0.2)
        
        return SensorReading(
            value=round(final_value, 3),
            unit=self.unit,
            timestamp=datetime.now().isoformat(),
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type,
            quality=round(quality, 3)
        )
    
    def read_batch(self, count: int = 10) -> List[SensorReading]:
        """Take multiple readings"""
        return [self.read() for _ in range(count)]
    
    def get_values(self, count: int = 10) -> List[float]:
        """Get just the numeric values"""
        return [self.read().value for _ in range(count)]
    
    def reset(self):
        """Reset sensor state"""
        self.drift_offset = 0.0
        self.readings_count = 0
        self.last_value = (self.min_value + self.max_value) / 2
    
    def get_info(self) -> dict:
        """Get sensor information"""
        return {
            'sensor_id': self.sensor_id,
            'name': self.name,
            'type': self.sensor_type,
            'unit': self.unit,
            'range': [self.min_value, self.max_value],
            'readings_count': self.readings_count,
            'current_drift': round(self.drift_offset, 4)
        }


class UltrasonicSensor(BaseSensor):
    """
    Ultrasonic Distance Sensor (HC-SR04 simulation)
    
    Measures distance using sound waves.
    Range: 2cm - 400cm
    Accuracy: ±3mm
    """
    
    def __init__(self,
                 sensor_id: str = "ultrasonic_01",
                 name: str = "HC-SR04 Ultrasonic",
                 target_distance: float = 100.0,
                 movement_speed: float = 0.0):
        """
        Args:
            target_distance: Base distance to object (cm)
            movement_speed: Speed of object movement (cm/s), 0 for stationary
        """
        super().__init__(
            sensor_id=sensor_id,
            name=name,
            unit="cm",
            min_value=2.0,
            max_value=400.0,
            noise_level=0.005,  # Very low noise for ultrasonic
            drift_rate=0.0005
        )
        
        self.target_distance = target_distance
        self.movement_speed = movement_speed
        self.movement_phase = random.uniform(0, 2 * math.pi)
        
    @property
    def sensor_type(self) -> str:
        return "ultrasonic"
    
    def _generate_base_value(self) -> float:
        """Generate distance reading with optional movement pattern"""
        if self.movement_speed > 0:
            # Simulate sinusoidal movement
            time_factor = self.readings_count * 0.1
            movement = self.movement_speed * math.sin(time_factor + self.movement_phase)
            return self.target_distance + movement
        else:
            # Small random variations for stationary object
            variation = np.random.normal(0, 0.5)
            return self.target_distance + variation
    
    def set_target_distance(self, distance: float):
        """Update target distance"""
        self.target_distance = np.clip(distance, self.min_value, self.max_value)


class TemperatureSensor(BaseSensor):
    """
    Temperature Sensor (DHT22/DS18B20 simulation)
    
    Range: -40°C to 80°C
    Accuracy: ±0.5°C
    """
    
    def __init__(self,
                 sensor_id: str = "temp_01",
                 name: str = "DHT22 Temperature",
                 ambient_temp: float = 25.0,
                 variation_range: float = 3.0):
        """
        Args:
            ambient_temp: Base ambient temperature (°C)
            variation_range: Range of natural variation (°C)
        """
        super().__init__(
            sensor_id=sensor_id,
            name=name,
            unit="°C",
            min_value=-40.0,
            max_value=80.0,
            noise_level=0.01,
            drift_rate=0.002
        )
        
        self.ambient_temp = ambient_temp
        self.variation_range = variation_range
        self.time_of_day_factor = 0.0
        
    @property
    def sensor_type(self) -> str:
        return "temperature"
    
    def _generate_base_value(self) -> float:
        """Generate temperature with time-based variation"""
        # Simulate daily temperature cycle
        self.time_of_day_factor += 0.01
        daily_variation = self.variation_range * 0.5 * math.sin(self.time_of_day_factor)
        
        # Random short-term fluctuations
        random_variation = np.random.normal(0, self.variation_range * 0.1)
        
        return self.ambient_temp + daily_variation + random_variation
    
    def set_ambient_temp(self, temp: float):
        """Update ambient temperature"""
        self.ambient_temp = temp


class HumiditySensor(BaseSensor):
    """
    Humidity Sensor (DHT22 simulation)
    
    Range: 0% - 100% RH
    Accuracy: ±2%
    """
    
    def __init__(self,
                 sensor_id: str = "humidity_01",
                 name: str = "DHT22 Humidity",
                 base_humidity: float = 55.0):
        super().__init__(
            sensor_id=sensor_id,
            name=name,
            unit="%RH",
            min_value=0.0,
            max_value=100.0,
            noise_level=0.02,
            drift_rate=0.003
        )
        
        self.base_humidity = base_humidity
        
    @property
    def sensor_type(self) -> str:
        return "humidity"
    
    def _generate_base_value(self) -> float:
        """Generate humidity reading"""
        # Humidity varies inversely with temperature patterns somewhat
        variation = np.random.normal(0, 5)
        return self.base_humidity + variation


class MotionSensor(BaseSensor):
    """
    PIR Motion Sensor simulation
    
    Returns: 0 (no motion) or 1 (motion detected)
    With configurable activity probability
    """
    
    def __init__(self,
                 sensor_id: str = "motion_01",
                 name: str = "PIR Motion Sensor",
                 activity_probability: float = 0.3):
        super().__init__(
            sensor_id=sensor_id,
            name=name,
            unit="binary",
            min_value=0.0,
            max_value=1.0,
            noise_level=0.0,
            drift_rate=0.0
        )
        
        self.activity_probability = activity_probability
        self.motion_duration = 0
        
    @property
    def sensor_type(self) -> str:
        return "motion"
    
    def _generate_base_value(self) -> float:
        """Generate motion detection value"""
        if self.motion_duration > 0:
            self.motion_duration -= 1
            return 1.0
        
        if random.random() < self.activity_probability:
            # Motion detected, stays for a few readings
            self.motion_duration = random.randint(2, 5)
            return 1.0
        
        return 0.0
    
    def _apply_noise(self, value: float) -> float:
        """Binary sensor, no noise"""
        return value
    
    def _apply_drift(self, value: float) -> float:
        """Binary sensor, no drift"""
        return value


class LightSensor(BaseSensor):
    """
    Light Sensor (LDR/BH1750 simulation)
    
    Range: 0 - 65535 lux
    """
    
    def __init__(self,
                 sensor_id: str = "light_01",
                 name: str = "BH1750 Light Sensor",
                 base_light: float = 500.0,
                 indoor: bool = True):
        super().__init__(
            sensor_id=sensor_id,
            name=name,
            unit="lux",
            min_value=0.0,
            max_value=65535.0,
            noise_level=0.03,
            drift_rate=0.001
        )
        
        self.base_light = base_light
        self.indoor = indoor
        self.time_factor = 0.0
        
    @property
    def sensor_type(self) -> str:
        return "light"
    
    def _generate_base_value(self) -> float:
        """Generate light reading with daily cycle"""
        self.time_factor += 0.005
        
        if self.indoor:
            # Indoor lighting is more stable
            variation = np.random.normal(0, self.base_light * 0.1)
            return self.base_light + variation
        else:
            # Outdoor follows sun cycle
            sun_factor = max(0, math.sin(self.time_factor))
            outdoor_light = self.base_light * sun_factor * 2
            variation = np.random.normal(0, outdoor_light * 0.05)
            return outdoor_light + variation


class SensorArray:
    """
    Collection of multiple sensors with synchronized reading
    """
    
    def __init__(self, name: str = "Sensor Array"):
        self.name = name
        self.sensors: Dict[str, BaseSensor] = {}
        self.created_at = datetime.now()
        
    def add_sensor(self, sensor: BaseSensor) -> 'SensorArray':
        """Add a sensor to the array"""
        self.sensors[sensor.sensor_id] = sensor
        return self
    
    def remove_sensor(self, sensor_id: str) -> bool:
        """Remove a sensor from the array"""
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]
            return True
        return False
    
    def read_all(self) -> Dict[str, SensorReading]:
        """Read all sensors simultaneously"""
        return {
            sensor_id: sensor.read() 
            for sensor_id, sensor in self.sensors.items()
        }
    
    def read_all_values(self) -> Dict[str, float]:
        """Get just the numeric values from all sensors"""
        return {
            sensor_id: sensor.read().value 
            for sensor_id, sensor in self.sensors.items()
        }
    
    def read_batch_all(self, count: int = 10) -> Dict[str, List[float]]:
        """Get batch readings from all sensors"""
        return {
            sensor_id: sensor.get_values(count) 
            for sensor_id, sensor in self.sensors.items()
        }
    
    def get_sensor(self, sensor_id: str) -> Optional[BaseSensor]:
        """Get a specific sensor"""
        return self.sensors.get(sensor_id)
    
    def list_sensors(self) -> List[dict]:
        """List all sensors with their info"""
        return [sensor.get_info() for sensor in self.sensors.values()]
    
    def reset_all(self):
        """Reset all sensors"""
        for sensor in self.sensors.values():
            sensor.reset()
    
    def __len__(self) -> int:
        return len(self.sensors)
    
    def __iter__(self):
        return iter(self.sensors.values())


# ==================== FACTORY FUNCTIONS ====================

def create_robot_car_sensors() -> SensorArray:
    """Create sensor array for a robot car"""
    array = SensorArray("Robot Car Sensors")
    
    # Front ultrasonic for obstacle detection
    array.add_sensor(UltrasonicSensor(
        sensor_id="ultrasonic_front",
        name="Front Distance Sensor",
        target_distance=150.0,
        movement_speed=20.0
    ))
    
    # Side ultrasonics
    array.add_sensor(UltrasonicSensor(
        sensor_id="ultrasonic_left",
        name="Left Distance Sensor",
        target_distance=80.0,
        movement_speed=5.0
    ))
    
    array.add_sensor(UltrasonicSensor(
        sensor_id="ultrasonic_right",
        name="Right Distance Sensor",
        target_distance=80.0,
        movement_speed=5.0
    ))
    
    # Temperature (motor/battery monitoring)
    array.add_sensor(TemperatureSensor(
        sensor_id="temp_motor",
        name="Motor Temperature",
        ambient_temp=35.0,
        variation_range=5.0
    ))
    
    return array


def create_environment_sensors() -> SensorArray:
    """Create sensor array for environmental monitoring"""
    array = SensorArray("Environment Sensors")
    
    array.add_sensor(TemperatureSensor(
        sensor_id="temp_room",
        name="Room Temperature",
        ambient_temp=25.0,
        variation_range=2.0
    ))
    
    array.add_sensor(HumiditySensor(
        sensor_id="humidity_room",
        name="Room Humidity",
        base_humidity=50.0
    ))
    
    array.add_sensor(LightSensor(
        sensor_id="light_room",
        name="Room Light",
        base_light=400.0,
        indoor=True
    ))
    
    array.add_sensor(MotionSensor(
        sensor_id="motion_room",
        name="Room Motion",
        activity_probability=0.2
    ))
    
    return array


def create_military_base_sensors() -> SensorArray:
    """Create sensor array for military/secure base monitoring"""
    array = SensorArray("Military Base Sensors")
    
    # Perimeter sensors
    array.add_sensor(UltrasonicSensor(
        sensor_id="perimeter_north",
        name="North Perimeter",
        target_distance=500.0,
        movement_speed=0.0
    ))
    
    array.add_sensor(UltrasonicSensor(
        sensor_id="perimeter_south",
        name="South Perimeter",
        target_distance=500.0,
        movement_speed=0.0
    ))
    
    # Motion detection
    array.add_sensor(MotionSensor(
        sensor_id="motion_gate",
        name="Gate Motion",
        activity_probability=0.1
    ))
    
    # Environmental
    array.add_sensor(TemperatureSensor(
        sensor_id="temp_outdoor",
        name="Outdoor Temperature",
        ambient_temp=28.0,
        variation_range=10.0
    ))
    
    array.add_sensor(LightSensor(
        sensor_id="light_outdoor",
        name="Outdoor Light",
        base_light=10000.0,
        indoor=False
    ))
    
    return array


# ==================== DEMO ====================

def demo():
    """Demonstrate sensor simulations"""
    print("=" * 60)
    print("Sensor Simulation Demo")
    print("=" * 60)
    
    # Create environment sensors
    sensors = create_environment_sensors()
    print(f"\n📊 Created: {sensors.name}")
    print(f"   Sensors: {len(sensors)}")
    
    # List sensors
    print("\n   Sensor List:")
    for sensor in sensors:
        print(f"   - {sensor.name} ({sensor.sensor_type})")
    
    # Take readings
    print("\n📈 Sample Readings:")
    for _ in range(3):
        readings = sensors.read_all()
        for sensor_id, reading in readings.items():
            print(f"   {reading.sensor_type}: {reading.value} {reading.unit}")
        print("   ---")
    
    # Batch readings for encryption
    print("\n📦 Batch Readings (for encryption):")
    batch = sensors.read_batch_all(count=5)
    for sensor_id, values in batch.items():
        values_str = ", ".join([f"{v:.1f}" for v in values])
        print(f"   {sensor_id}: [{values_str}]")
    
    print("\n" + "=" * 60)
    print("Sensor Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo()