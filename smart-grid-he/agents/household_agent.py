"""
Household Agent for Smart Grid
==============================
Represents a single household in the multi-agent smart grid system.

Multi-Agent Properties:
- Autonomous: Each agent generates and encrypts its own data
- Decentralized: No shared state with other agents
- Privacy-preserving: Only encrypted data leaves the agent
- Non-trusting: Does not trust coordinator or other agents

Security Model:
- Agent has PUBLIC FHE context only
- Can encrypt its own demand
- CANNOT decrypt any data (including its own after encryption)
- CANNOT infer other agents' demands
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fhe_engine import SmartGridFHE, EncryptedDemand
from core.security_logger import SecurityLogger, DataType, OperationType
from agents.demand_generator import RealisticDemandGenerator, LoadProfile


@dataclass
class AgentStatus:
    """Current status of a household agent"""
    agent_id: str
    profile: str
    current_demand_kw: float
    last_update: str
    is_active: bool
    load_balance_factor: float = 1.0  # Reduction factor from coordinator
    
    def to_dict(self) -> dict:
        return {
            'agent_id': self.agent_id,
            'profile': self.profile,
            'current_demand_kw': round(self.current_demand_kw, 3),
            'last_update': self.last_update,
            'is_active': self.is_active,
            'load_balance_factor': self.load_balance_factor
        }


class HouseholdAgent:
    """
    Represents a household in the smart grid multi-agent system.
    
    This is a TRUE multi-agent implementation:
    - Each agent operates independently
    - Has its own demand generator (private state)
    - Encrypts data locally before transmission
    - Does not share any state with other agents
    - Only communicates through encrypted messages to coordinator
    
    Trust Model:
    - Agent trusts only itself
    - Coordinator is honest-but-curious (will compute but may try to infer)
    - Other agents are untrusted
    """
    
    def __init__(self, 
                 agent_id: str,
                 public_context: bytes,
                 profile: LoadProfile = LoadProfile.RESIDENTIAL_MEDIUM,
                 security_logger: Optional[SecurityLogger] = None,
                 seed: Optional[int] = None):
        """
        Initialize a household agent.
        
        Args:
            agent_id: Unique identifier for this household
            public_context: Serialized public FHE context (cannot decrypt)
            profile: Load profile type for demand generation
            security_logger: Optional shared security logger
            seed: Random seed for reproducibility
        """
        self.agent_id = agent_id
        self.profile = profile
        
        # Initialize FHE engine with PUBLIC context only
        self.fhe = SmartGridFHE.from_context(public_context, has_secret_key=False)
        
        # Verify we cannot decrypt
        if self.fhe.is_private():
            raise ValueError("Agent received secret context - security violation!")
        
        # Initialize demand generator (private to this agent)
        self.demand_generator = RealisticDemandGenerator(profile, seed=seed)
        
        # State
        self._current_demand: float = 0.0
        self._last_encrypted: Optional[EncryptedDemand] = None
        self._is_active: bool = True
        self._load_balance_factor: float = 1.0
        self._history: List[Dict] = []
        
        # Security logging
        self.logger = security_logger
    
    def get_current_demand(self, timestamp: Optional[datetime] = None) -> float:
        """
        Get current electricity demand.
        
        This is the PRIVATE value known only to this agent.
        It will be encrypted before transmission.
        
        Args:
            timestamp: Time for demand calculation
            
        Returns:
            Demand in kilowatts
        """
        demand = self.demand_generator.get_demand(timestamp)
        
        # Apply load balance factor if coordinator requested reduction
        adjusted_demand = demand * self._load_balance_factor
        
        self._current_demand = adjusted_demand
        return adjusted_demand
    
    def encrypt_demand(self, timestamp: Optional[datetime] = None) -> EncryptedDemand:
        """
        Encrypt current demand for transmission to coordinator.
        
        This is the ONLY way data leaves the agent - always encrypted.
        The coordinator will receive this and aggregate with other agents.
        
        Args:
            timestamp: Time for demand calculation
            
        Returns:
            EncryptedDemand ready for transmission
        """
        # Get current demand (private)
        demand = self.get_current_demand(timestamp)
        
        # Encrypt locally
        encrypted = self.fhe.encrypt_demand(demand, self.agent_id)
        
        # Log the encryption (agent sees own plaintext, produces ciphertext)
        if self.logger:
            self.logger.log_agent_encrypt(
                self.agent_id, 
                f"{demand:.2f}kW"
            )
        
        # Store for reference
        self._last_encrypted = encrypted
        self._history.append({
            'timestamp': datetime.now().isoformat(),
            'demand_kw': demand,
            'ciphertext_hash': encrypted.checksum
        })
        
        return encrypted
    
    def receive_load_balance_command(self, reduction_factor: float):
        """
        Receive load balancing command from utility company.
        
        The utility company (not coordinator) sends reduction factors
        after decrypting aggregate demands.
        
        Args:
            reduction_factor: Factor to multiply demand by (0.0 to 1.0)
        """
        self._load_balance_factor = max(0.0, min(1.0, reduction_factor))
    
    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        return AgentStatus(
            agent_id=self.agent_id,
            profile=self.profile.value,
            current_demand_kw=self._current_demand,
            last_update=datetime.now().isoformat(),
            is_active=self._is_active,
            load_balance_factor=self._load_balance_factor
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get detailed agent information"""
        profile_info = self.demand_generator.get_profile_info()
        
        return {
            'agent_id': self.agent_id,
            'profile': profile_info,
            'fhe_context_hash': self.fhe.get_context_hash(),
            'can_decrypt': self.fhe.is_private(),
            'is_active': self._is_active,
            'load_balance_factor': self._load_balance_factor,
            'history_length': len(self._history)
        }
    
    def get_last_encrypted(self) -> Optional[EncryptedDemand]:
        """Get the last encrypted demand (for transmission)"""
        return self._last_encrypted
    
    def set_active(self, active: bool):
        """Set agent active/inactive status"""
        self._is_active = active
    
    def get_plaintext_demand_for_comparison(self) -> float:
        """
        Get plaintext demand for accuracy comparison ONLY.
        
        This method exists ONLY for evaluation purposes to compare
        encrypted computation results with plaintext baseline.
        In a real deployment, this would not be exposed.
        
        Returns:
            Current plaintext demand in kW
        """
        return self._current_demand
    
    def __repr__(self):
        return f"HouseholdAgent(id={self.agent_id}, profile={self.profile.value})"


def demo():
    """Demonstrate household agent functionality"""
    print("=" * 60)
    print("Household Agent Demo")
    print("=" * 60)
    
    from core.fhe_engine import SmartGridFHE
    from core.security_logger import SecurityLogger
    
    # Create FHE engine (utility company)
    print("\n[1] Utility company creates FHE keys...")
    utility = SmartGridFHE()
    public_context = utility.get_public_context()
    
    # Create security logger
    logger = SecurityLogger()
    
    # Create household agent
    print("\n[2] Creating household agent...")
    agent = HouseholdAgent(
        agent_id="house_001",
        public_context=public_context,
        profile=LoadProfile.RESIDENTIAL_MEDIUM,
        security_logger=logger
    )
    
    info = agent.get_info()
    print(f"    Agent ID: {info['agent_id']}")
    print(f"    Profile: {info['profile']['profile_name']}")
    print(f"    Can Decrypt: {info['can_decrypt']}")
    
    # Get and encrypt demand
    print("\n[3] Agent generates and encrypts demand...")
    demand = agent.get_current_demand()
    encrypted = agent.encrypt_demand()
    
    print(f"    Plaintext demand: {demand:.2f} kW (private to agent)")
    print(f"    Encrypted: {encrypted.get_display_ciphertext(40)}")
    print(f"    Ciphertext size: {encrypted.get_size_kb():.1f} KB")
    
    # Prove agent cannot decrypt
    print("\n[4] Proving agent cannot decrypt...")
    try:
        agent.fhe.decrypt_demand(encrypted)
        print("    ERROR: Agent should not be able to decrypt!")
    except ValueError as e:
        print(f"    ✓ Correctly rejected: {str(e)[:50]}...")
    
    # Utility company can decrypt
    print("\n[5] Utility company decrypts...")
    decrypted = utility.decrypt_demand(encrypted)
    print(f"    Decrypted: {decrypted[0]:.4f} kW")
    print(f"    Error: {abs(decrypted[0] - demand):.2e} kW")
    
    # Security log
    print("\n[6] Security audit:")
    report = logger.generate_audit_report()
    print(f"    {report['conclusion']}")


if __name__ == "__main__":
    demo()
