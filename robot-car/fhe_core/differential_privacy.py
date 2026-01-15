"""
Differential Privacy Module
===========================
Adds privacy-preserving noise to data and query results.
Implements Laplace mechanism for differential privacy.
"""

import math
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class NoiseType(str, Enum):
    """Types of noise mechanisms"""
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"


@dataclass
class PrivacyBudget:
    """
    Differential Privacy budget tracker.
    
    epsilon: Privacy loss parameter (lower = more privacy)
    delta: Probability of privacy breach (for Gaussian mechanism)
    """
    epsilon: float = 1.0
    delta: float = 1e-5
    spent_epsilon: float = 0.0
    
    def can_spend(self, epsilon_cost: float) -> bool:
        """Check if budget available"""
        return self.spent_epsilon + epsilon_cost <= self.epsilon
    
    def spend(self, epsilon_cost: float) -> bool:
        """Spend budget, returns success"""
        if self.can_spend(epsilon_cost):
            self.spent_epsilon += epsilon_cost
            return True
        return False
    
    def remaining(self) -> float:
        """Remaining epsilon budget"""
        return max(0, self.epsilon - self.spent_epsilon)
    
    def reset(self):
        """Reset spent budget"""
        self.spent_epsilon = 0.0


class DifferentialPrivacy:
    """
    Differential Privacy implementation for sensor data.
    
    Provides:
    - Laplace mechanism for numeric queries
    - Gaussian mechanism for higher accuracy
    - Budget tracking to prevent privacy exhaustion
    - Sensitivity calibration for different data types
    """
    
    # Sensitivity values for common sensor types (max change one record can cause)
    DEFAULT_SENSITIVITIES = {
        "temperature": 5.0,      # 5°C max single reading impact
        "humidity": 10.0,        # 10% max
        "distance": 50.0,        # 50cm max
        "speed": 10.0,           # 10 km/h max
        "light": 100.0,          # 100 lux max
        "default": 1.0
    }
    
    def __init__(self, 
                 epsilon: float = 1.0, 
                 delta: float = 1e-5,
                 noise_type: NoiseType = NoiseType.LAPLACE):
        """
        Initialize DP mechanism.
        
        Args:
            epsilon: Privacy budget (1.0 = moderate privacy, 0.1 = strong privacy)
            delta: Probability bound for Gaussian mechanism
            noise_type: Type of noise to use
        """
        self.budget = PrivacyBudget(epsilon=epsilon, delta=delta)
        self.noise_type = noise_type
        self.sensitivities = dict(self.DEFAULT_SENSITIVITIES)
        self.query_count = 0
    
    def set_sensitivity(self, data_type: str, sensitivity: float):
        """Set custom sensitivity for a data type"""
        self.sensitivities[data_type] = sensitivity
    
    def get_sensitivity(self, data_type: str) -> float:
        """Get sensitivity for a data type"""
        return self.sensitivities.get(data_type, self.sensitivities["default"])
    
    def _laplace_noise(self, scale: float) -> float:
        """Generate Laplace noise with given scale"""
        u = random.random() - 0.5
        return scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))
    
    def _gaussian_noise(self, sigma: float) -> float:
        """Generate Gaussian noise with given standard deviation"""
        return random.gauss(0, sigma)
    
    def add_noise(self, 
                  value: float, 
                  sensitivity: float = None,
                  data_type: str = "default",
                  epsilon_cost: float = None) -> Tuple[float, bool]:
        """
        Add DP noise to a single value.
        
        Args:
            value: Original value
            sensitivity: Query sensitivity (max impact of one record)
            data_type: Type of data for automatic sensitivity lookup
            epsilon_cost: Epsilon to spend (default: auto-calculated)
            
        Returns:
            (noisy_value, budget_ok)
        """
        if sensitivity is None:
            sensitivity = self.get_sensitivity(data_type)
        
        if epsilon_cost is None:
            epsilon_cost = 0.1  # Default per-query cost
        
        # Check budget
        if not self.budget.can_spend(epsilon_cost):
            # Return original value if budget exhausted (log warning)
            return value, False
        
        self.budget.spend(epsilon_cost)
        self.query_count += 1
        
        if self.noise_type == NoiseType.LAPLACE:
            # Laplace mechanism: scale = sensitivity / epsilon
            scale = sensitivity / epsilon_cost
            noise = self._laplace_noise(scale)
        else:
            # Gaussian mechanism: sigma = sensitivity * sqrt(2 * ln(1.25/delta)) / epsilon
            sigma = sensitivity * math.sqrt(2 * math.log(1.25 / self.budget.delta)) / epsilon_cost
            noise = self._gaussian_noise(sigma)
        
        return value + noise, True
    
    def add_noise_to_dict(self, 
                          data: Dict[str, float],
                          epsilon_per_field: float = 0.05) -> Tuple[Dict[str, float], bool]:
        """
        Add DP noise to all numeric fields in a dictionary.
        
        Args:
            data: Dictionary of sensor values
            epsilon_per_field: Epsilon budget per field
            
        Returns:
            (noisy_data, all_ok)
        """
        noisy_data = {}
        all_ok = True
        
        for key, value in data.items():
            if isinstance(value, (int, float)):
                # Determine data type from key
                data_type = "default"
                for dt in self.sensitivities.keys():
                    if dt in key.lower():
                        data_type = dt
                        break
                
                noisy_val, ok = self.add_noise(
                    float(value), 
                    data_type=data_type,
                    epsilon_cost=epsilon_per_field
                )
                noisy_data[key] = noisy_val
                if not ok:
                    all_ok = False
            else:
                noisy_data[key] = value
        
        return noisy_data, all_ok
    
    def privatize_aggregate(self,
                           values: List[float],
                           operation: str = "mean",
                           data_type: str = "default",
                           epsilon_cost: float = 0.2) -> Tuple[float, bool]:
        """
        Compute privatized aggregate.
        
        Args:
            values: List of values to aggregate
            operation: "mean", "sum", "count", "min", "max"
            data_type: Type of data
            epsilon_cost: Privacy budget for this query
            
        Returns:
            (private_result, budget_ok)
        """
        if not values:
            return 0.0, True
        
        sensitivity = self.get_sensitivity(data_type)
        n = len(values)
        
        # Compute true aggregate
        if operation == "mean":
            true_result = sum(values) / n
            # Sensitivity of mean = sensitivity / n
            query_sensitivity = sensitivity / n
        elif operation == "sum":
            true_result = sum(values)
            query_sensitivity = sensitivity
        elif operation == "count":
            true_result = float(n)
            query_sensitivity = 1.0
        elif operation == "min":
            true_result = min(values)
            query_sensitivity = sensitivity
        elif operation == "max":
            true_result = max(values)
            query_sensitivity = sensitivity
        else:
            true_result = sum(values) / n
            query_sensitivity = sensitivity / n
        
        # Add noise
        return self.add_noise(
            true_result, 
            sensitivity=query_sensitivity,
            epsilon_cost=epsilon_cost
        )
    
    def get_privacy_guarantee(self) -> Dict[str, Any]:
        """Get current privacy guarantees"""
        return {
            "mechanism": self.noise_type.value,
            "epsilon_total": self.budget.epsilon,
            "epsilon_spent": self.budget.spent_epsilon,
            "epsilon_remaining": self.budget.remaining(),
            "delta": self.budget.delta,
            "queries_answered": self.query_count,
            "privacy_level": self._describe_privacy_level()
        }
    
    def _describe_privacy_level(self) -> str:
        """Human-readable privacy level"""
        remaining = self.budget.remaining()
        if remaining <= 0:
            return "exhausted"
        elif remaining < 0.1:
            return "critical"
        elif remaining < 0.5:
            return "low"
        elif remaining < 1.0:
            return "moderate"
        else:
            return "high"
    
    def reset_budget(self):
        """Reset privacy budget (e.g., for new time window)"""
        self.budget.reset()
        self.query_count = 0


class SensorDataPrivatizer:
    """
    High-level privacy manager for IoT sensor data.
    Combines multiple privacy mechanisms.
    """
    
    def __init__(self, epsilon: float = 1.0):
        self.dp = DifferentialPrivacy(epsilon=epsilon)
        self.enabled = True
    
    def privatize_sensor_reading(self, 
                                  sensor_type: str, 
                                  value: float) -> float:
        """Add DP noise to a single sensor reading"""
        if not self.enabled:
            return value
        
        noisy, _ = self.dp.add_noise(value, data_type=sensor_type)
        return round(noisy, 2)
    
    def privatize_sensor_batch(self, 
                                sensor_data: Dict[str, float]) -> Dict[str, float]:
        """Add DP noise to a batch of sensor readings"""
        if not self.enabled:
            return sensor_data
        
        noisy_data, _ = self.dp.add_noise_to_dict(sensor_data)
        return {k: round(v, 2) if isinstance(v, float) else v 
                for k, v in noisy_data.items()}
    
    def get_private_average(self, 
                            values: List[float], 
                            sensor_type: str) -> float:
        """Get differentially private average"""
        if not self.enabled or not values:
            return sum(values) / len(values) if values else 0.0
        
        result, _ = self.dp.privatize_aggregate(
            values, 
            operation="mean", 
            data_type=sensor_type
        )
        return round(result, 2)
    
    def get_status(self) -> Dict[str, Any]:
        """Get privacy status"""
        status = self.dp.get_privacy_guarantee()
        status["enabled"] = self.enabled
        return status


# ==================== DEMO ====================

def demo():
    """Demonstrate differential privacy"""
    print("=" * 60)
    print("Differential Privacy Demo")
    print("=" * 60)
    
    # Create privatizer
    privatizer = SensorDataPrivatizer(epsilon=1.0)
    
    # Original sensor data
    original_data = {
        "temperature": 25.5,
        "humidity": 65.3,
        "distance": 120.8,
        "speed": 5.2
    }
    
    print(f"\n1. Original sensor data:")
    for k, v in original_data.items():
        print(f"   {k}: {v}")
    
    # Privatize
    private_data = privatizer.privatize_sensor_batch(original_data)
    
    print(f"\n2. Privatized sensor data (with DP noise):")
    for k, v in private_data.items():
        orig = original_data[k]
        diff = v - orig
        print(f"   {k}: {v} (noise: {diff:+.2f})")
    
    # Aggregate with privacy
    temperatures = [23.1, 24.5, 25.2, 25.8, 26.1, 25.5, 24.9, 25.3]
    true_avg = sum(temperatures) / len(temperatures)
    private_avg = privatizer.get_private_average(temperatures, "temperature")
    
    print(f"\n3. Temperature averaging:")
    print(f"   True average: {true_avg:.2f}°C")
    print(f"   Private average: {private_avg}°C")
    print(f"   Difference: {abs(private_avg - true_avg):.2f}°C")
    
    # Show privacy status
    status = privatizer.get_status()
    print(f"\n4. Privacy budget status:")
    print(f"   Epsilon remaining: {status['epsilon_remaining']:.3f}")
    print(f"   Privacy level: {status['privacy_level']}")
    print(f"   Queries answered: {status['queries_answered']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    demo()
