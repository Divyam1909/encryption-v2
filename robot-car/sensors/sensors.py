"""
Robot Car Sensors
=================
Sensor simulations for the FHE Robot Car system.
Ultrasonic distance sensors and motor temperature.
"""

import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass
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
    quality: float = 1.0
    
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
    """Abstract base class for sensors"""
    
    def __init__(self,
                 sensor_id: str,
                 name: str,
                 unit: str,
                 min_value: float,
                 max_value: float,
                 noise_level: float = 0.02,
                 drift_rate: float = 0.001):
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
        pass
    
    @abstractmethod
    def _generate_base_value(self) -> float:
        pass
    
    def _apply_noise(self, value: float) -> float:
        noise = np.random.normal(0, self.noise_level * self.range)
        return value + noise
    
    def _apply_drift(self, value: float) -> float:
        self.drift_offset += np.random.normal(0, self.drift_rate * self.range)
        self.drift_offset = np.clip(self.drift_offset, -0.1 * self.range, 0.1 * self.range)
        return value + self.drift_offset
    
    def _clamp(self, value: float) -> float:
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
        quality = 1.0 - min(abs(self.drift_offset) / (0.1 * self.range), 0.2)
        
        return SensorReading(
            value=round(final_value, 3),
            unit=self.unit,
            timestamp=datetime.now().isoformat(),
            sensor_id=self.sensor_id,
            sensor_type=self.sensor_type,
            quality=round(quality, 3)
        )
    
    def get_values(self, count: int = 10) -> List[float]:
        """Get just the numeric values"""
        return [self.read().value for _ in range(count)]
    
    def get_info(self) -> dict:
        return {
            'sensor_id': self.sensor_id,
            'name': self.name,
            'type': self.sensor_type,
            'unit': self.unit,
            'range': [self.min_value, self.max_value],
            'readings_count': self.readings_count
        }


class UltrasonicSensor(BaseSensor):
    """
    Ultrasonic Distance Sensor (HC-SR04 simulation)
    Range: 2cm - 400cm
    """
    
    def __init__(self,
                 sensor_id: str = "ultrasonic_01",
                 name: str = "HC-SR04 Ultrasonic",
                 target_distance: float = 100.0,
                 movement_speed: float = 0.0):
        super().__init__(
            sensor_id=sensor_id,
            name=name,
            unit="cm",
            min_value=2.0,
            max_value=400.0,
            noise_level=0.005,
            drift_rate=0.0005
        )
        
        self.target_distance = target_distance
        self.movement_speed = movement_speed
        self.movement_phase = random.uniform(0, 2 * math.pi)
        
    @property
    def sensor_type(self) -> str:
        return "ultrasonic"
    
    def _generate_base_value(self) -> float:
        if self.movement_speed > 0:
            time_factor = self.readings_count * 0.1
            movement = self.movement_speed * math.sin(time_factor + self.movement_phase)
            return self.target_distance + movement
        else:
            variation = np.random.normal(0, 0.5)
            return self.target_distance + variation
    
    def set_target_distance(self, distance: float):
        self.target_distance = np.clip(distance, self.min_value, self.max_value)


class TemperatureSensor(BaseSensor):
    """
    Temperature Sensor for motor monitoring
    Range: -40°C to 80°C
    """
    
    def __init__(self,
                 sensor_id: str = "temp_01",
                 name: str = "Motor Temperature",
                 ambient_temp: float = 25.0,
                 variation_range: float = 3.0):
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
        self.time_of_day_factor += 0.01
        daily_variation = self.variation_range * 0.5 * math.sin(self.time_of_day_factor)
        random_variation = np.random.normal(0, self.variation_range * 0.1)
        return self.ambient_temp + daily_variation + random_variation
    
    def set_ambient_temp(self, temp: float):
        self.ambient_temp = temp


class SensorArray:
    """Collection of sensors for the robot car"""
    
    def __init__(self, name: str = "Robot Car Sensors"):
        self.name = name
        self.sensors: Dict[str, BaseSensor] = {}
        self.created_at = datetime.now()
        
    def add_sensor(self, sensor: BaseSensor) -> 'SensorArray':
        self.sensors[sensor.sensor_id] = sensor
        return self
    
    def read_all_values(self) -> Dict[str, float]:
        return {
            sensor_id: sensor.read().value 
            for sensor_id, sensor in self.sensors.items()
        }
    
    def read_batch_all(self, count: int = 10) -> Dict[str, List[float]]:
        return {
            sensor_id: sensor.get_values(count) 
            for sensor_id, sensor in self.sensors.items()
        }
    
    def get_sensor(self, sensor_id: str) -> Optional[BaseSensor]:
        return self.sensors.get(sensor_id)
    
    def list_sensors(self) -> List[dict]:
        return [sensor.get_info() for sensor in self.sensors.values()]
    
    def __len__(self) -> int:
        return len(self.sensors)
    
    def __iter__(self):
        return iter(self.sensors.values())


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
    
    # Rear ultrasonic
    array.add_sensor(UltrasonicSensor(
        sensor_id="ultrasonic_rear",
        name="Rear Distance Sensor",
        target_distance=200.0,
        movement_speed=0.0
    ))
    
    # Motor temperature
    array.add_sensor(TemperatureSensor(
        sensor_id="temp_motor",
        name="Motor Temperature",
        ambient_temp=35.0,
        variation_range=5.0
    ))
    
    return array


# ==================== DEMO ====================

def demo():
    """Demonstrate sensor simulations"""
    print("=" * 60)
    print("Robot Car Sensor Demo")
    print("=" * 60)
    
    sensors = create_robot_car_sensors()
    print(f"\n📊 Created: {sensors.name}")
    print(f"   Sensors: {len(sensors)}")
    
    print("\n   Sensor List:")
    for sensor in sensors:
        print(f"   - {sensor.name} ({sensor.sensor_type})")
    
    print("\n📈 Sample Readings:")
    for _ in range(3):
        readings = sensors.read_all_values()
        for sensor_id, value in readings.items():
            sensor = sensors.get_sensor(sensor_id)
            print(f"   {sensor.name}: {value:.1f} {sensor.unit}")
        print("   ---")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()