"""
Realistic Electricity Demand Generator
======================================
Generates realistic household electricity demand patterns based on:
- Time of day (morning peak, evening peak)
- Day type (weekday vs weekend)
- Season (summer AC, winter heating)
- Household profile (small, medium, large, commercial)
- Random variations for realism

Data is based on real residential consumption patterns from:
- US Energy Information Administration (EIA)
- NREL ResStock dataset characteristics
- European energy grid research

Typical ranges:
- Small household: 0.5 - 5 kW
- Medium household: 1 - 8 kW
- Large household: 2 - 15 kW
- Small commercial: 5 - 50 kW
"""

import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import random


class LoadProfile(Enum):
    """Household load profile types"""
    RESIDENTIAL_SMALL = "residential_small"      # Apartment, 1-2 people
    RESIDENTIAL_MEDIUM = "residential_medium"    # House, 3-4 people
    RESIDENTIAL_LARGE = "residential_large"      # Large house, 5+ people
    COMMERCIAL_SMALL = "commercial_small"        # Small shop/office


@dataclass
class DemandProfile:
    """Configuration for a load profile"""
    name: str
    base_load_kw: float       # Minimum constant load (fridge, standby)
    peak_load_kw: float       # Maximum possible load
    morning_peak_hour: int    # Hour of morning peak (6-9)
    evening_peak_hour: int    # Hour of evening peak (18-21)
    weekend_factor: float     # Multiplier for weekend (typically higher)
    noise_std: float          # Standard deviation of random noise


# Realistic profiles based on research data
PROFILES: Dict[LoadProfile, DemandProfile] = {
    LoadProfile.RESIDENTIAL_SMALL: DemandProfile(
        name="Small Residential",
        base_load_kw=0.3,
        peak_load_kw=4.0,
        morning_peak_hour=7,
        evening_peak_hour=19,
        weekend_factor=1.1,
        noise_std=0.15
    ),
    LoadProfile.RESIDENTIAL_MEDIUM: DemandProfile(
        name="Medium Residential",
        base_load_kw=0.5,
        peak_load_kw=8.0,
        morning_peak_hour=7,
        evening_peak_hour=19,
        weekend_factor=1.15,
        noise_std=0.2
    ),
    LoadProfile.RESIDENTIAL_LARGE: DemandProfile(
        name="Large Residential",
        base_load_kw=0.8,
        peak_load_kw=15.0,
        morning_peak_hour=7,
        evening_peak_hour=20,
        weekend_factor=1.2,
        noise_std=0.25
    ),
    LoadProfile.COMMERCIAL_SMALL: DemandProfile(
        name="Small Commercial",
        base_load_kw=2.0,
        peak_load_kw=30.0,
        morning_peak_hour=9,
        evening_peak_hour=17,
        weekend_factor=0.3,  # Much lower on weekends
        noise_std=0.1
    ),
}


class RealisticDemandGenerator:
    """
    Generates realistic electricity demand patterns.
    
    Uses real-world consumption characteristics to create believable
    time-series data for smart grid simulation.
    """
    
    def __init__(self, 
                 profile: LoadProfile = LoadProfile.RESIDENTIAL_MEDIUM,
                 seed: Optional[int] = None):
        """
        Initialize demand generator.
        
        Args:
            profile: Type of household/building
            seed: Random seed for reproducibility
        """
        self.profile = profile
        self.config = PROFILES[profile]
        
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        # Generate unique household characteristics
        self._base_load_variation = np.random.uniform(0.8, 1.2)
        self._peak_variation = np.random.uniform(0.7, 1.3)
        self._peak_hour_offset = np.random.randint(-1, 2)
    
    def get_demand(self, timestamp: Optional[datetime] = None) -> float:
        """
        Get electricity demand for a specific timestamp.
        
        Args:
            timestamp: Time to calculate demand for (defaults to now)
            
        Returns:
            Demand in kilowatts (kW)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        hour = timestamp.hour
        is_weekend = timestamp.weekday() >= 5
        month = timestamp.month
        
        # Calculate base demand (always-on appliances)
        base = self.config.base_load_kw * self._base_load_variation
        
        # Time-of-day factor (normalized consumption curve)
        tod_factor = self._get_time_of_day_factor(hour)
        
        # Calculate variable demand
        variable_range = self.config.peak_load_kw - self.config.base_load_kw
        variable = variable_range * tod_factor * self._peak_variation
        
        # Weekend adjustment
        if is_weekend:
            variable *= self.config.weekend_factor
            # Shift pattern later on weekends
            if hour < 10:
                variable *= 0.7
        
        # Seasonal adjustment (heating/cooling)
        seasonal = self._get_seasonal_factor(month)
        variable *= seasonal
        
        # Total demand
        demand = base + variable
        
        # Add realistic noise
        noise = np.random.normal(0, self.config.noise_std * demand)
        demand += noise
        
        # Ensure non-negative and within bounds
        demand = max(0.1, min(demand, self.config.peak_load_kw * 1.2))
        
        return round(demand, 3)
    
    def _get_time_of_day_factor(self, hour: int) -> float:
        """
        Get normalized demand factor based on time of day.
        
        Uses a double-peak pattern typical of residential consumption:
        - Low overnight (0-5)
        - Morning peak (6-9)
        - Moderate midday (10-16)
        - Evening peak (17-22)
        - Declining late night (23)
        """
        morning_peak = self.config.morning_peak_hour + self._peak_hour_offset
        evening_peak = self.config.evening_peak_hour + self._peak_hour_offset
        
        # Overnight low (0-5)
        if 0 <= hour < 5:
            return 0.15 + 0.05 * (hour / 5)
        
        # Morning ramp (5-morning_peak)
        elif 5 <= hour < morning_peak:
            progress = (hour - 5) / (morning_peak - 5)
            return 0.2 + 0.6 * progress
        
        # Morning peak
        elif hour == morning_peak:
            return 0.8
        
        # Post-morning decline (morning_peak+1 to 12)
        elif morning_peak < hour < 12:
            progress = (hour - morning_peak) / (12 - morning_peak)
            return 0.8 - 0.3 * progress
        
        # Midday plateau (12-16)
        elif 12 <= hour < 16:
            return 0.5 + 0.1 * np.sin((hour - 12) * np.pi / 4)
        
        # Evening ramp (16-evening_peak)
        elif 16 <= hour < evening_peak:
            progress = (hour - 16) / (evening_peak - 16)
            return 0.5 + 0.5 * progress
        
        # Evening peak
        elif hour == evening_peak:
            return 1.0
        
        # Evening decline (evening_peak+1 to 23)
        elif evening_peak < hour < 24:
            progress = (hour - evening_peak) / (24 - evening_peak)
            return 1.0 - 0.7 * progress
        
        return 0.3
    
    def _get_seasonal_factor(self, month: int) -> float:
        """
        Get seasonal adjustment factor.
        
        Higher in summer (AC) and winter (heating).
        Lower in spring and fall.
        """
        # Simple seasonal curve
        seasonal_factors = {
            1: 1.3,   # January - heating
            2: 1.25,
            3: 1.0,   # March - mild
            4: 0.9,
            5: 1.0,
            6: 1.2,   # June - AC starts
            7: 1.4,   # July - peak AC
            8: 1.35,
            9: 1.1,
            10: 0.95,
            11: 1.1,
            12: 1.3   # December - heating
        }
        return seasonal_factors.get(month, 1.0)
    
    def generate_time_series(self, 
                             start_time: Optional[datetime] = None,
                             duration_hours: int = 24,
                             interval_minutes: int = 15) -> List[Tuple[datetime, float]]:
        """
        Generate time series of demand values.
        
        Args:
            start_time: Starting timestamp (defaults to now)
            duration_hours: Duration to generate
            interval_minutes: Time between readings
            
        Returns:
            List of (timestamp, demand_kw) tuples
        """
        if start_time is None:
            start_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        series = []
        current = start_time
        end_time = start_time + timedelta(hours=duration_hours)
        
        while current < end_time:
            demand = self.get_demand(current)
            series.append((current, demand))
            current += timedelta(minutes=interval_minutes)
        
        return series
    
    def get_profile_info(self) -> Dict:
        """Get information about this generator's profile"""
        return {
            'profile_type': self.profile.value,
            'profile_name': self.config.name,
            'base_load_kw': self.config.base_load_kw * self._base_load_variation,
            'peak_load_kw': self.config.peak_load_kw * self._peak_variation,
            'typical_range': f"{self.config.base_load_kw:.1f} - {self.config.peak_load_kw:.1f} kW"
        }


def demo():
    """Demonstrate demand generation"""
    print("=" * 60)
    print("Realistic Demand Generation Demo")
    print("=" * 60)
    
    # Create generators for different profiles
    profiles = [
        LoadProfile.RESIDENTIAL_SMALL,
        LoadProfile.RESIDENTIAL_MEDIUM,
        LoadProfile.RESIDENTIAL_LARGE,
    ]
    
    for profile in profiles:
        gen = RealisticDemandGenerator(profile)
        info = gen.get_profile_info()
        
        print(f"\n{info['profile_name']}:")
        print(f"  Range: {info['typical_range']}")
        
        # Generate 24 hours of data
        series = gen.generate_time_series(duration_hours=24)
        
        demands = [d for _, d in series]
        print(f"  24h Min: {min(demands):.2f} kW")
        print(f"  24h Max: {max(demands):.2f} kW")
        print(f"  24h Avg: {np.mean(demands):.2f} kW")
        
        # Show a few samples
        print(f"  Sample readings:")
        for ts, demand in series[::8][:6]:  # Every 2 hours
            print(f"    {ts.strftime('%H:%M')}: {demand:.2f} kW")


if __name__ == "__main__":
    demo()
