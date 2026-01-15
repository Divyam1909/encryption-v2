"""
Agent Manager for Smart Grid
============================
Manages creation and coordination of multiple household agents.

Responsibilities:
- Spawn and manage multiple agents
- Distribute public FHE context to agents
- Collect encrypted demands from all agents
- Provide aggregate views for dashboard
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fhe_engine import SmartGridFHE, EncryptedDemand
from core.security_logger import SecurityLogger
from agents.household_agent import HouseholdAgent, AgentStatus
from agents.demand_generator import LoadProfile


class AgentManager:
    """
    Manages multiple household agents in the smart grid.
    
    This is the local orchestrator that:
    - Creates agents with proper FHE contexts
    - Triggers demand generation and encryption
    - Collects encrypted data for coordinator
    """
    
    def __init__(self, 
                 public_context: bytes,
                 security_logger: Optional[SecurityLogger] = None):
        """
        Initialize agent manager.
        
        Args:
            public_context: Public FHE context to distribute to agents
            security_logger: Shared security logger
        """
        self.public_context = public_context
        self.logger = security_logger
        self.agents: Dict[str, HouseholdAgent] = {}
    
    def create_agents(self, 
                      count: int,
                      profile_distribution: Optional[Dict[LoadProfile, float]] = None,
                      id_prefix: str = "house") -> List[str]:
        """
        Create multiple household agents.
        
        Args:
            count: Number of agents to create
            profile_distribution: Optional distribution of profiles
                e.g., {RESIDENTIAL_SMALL: 0.4, RESIDENTIAL_MEDIUM: 0.5, RESIDENTIAL_LARGE: 0.1}
            id_prefix: Prefix for agent IDs
            
        Returns:
            List of created agent IDs
        """
        if profile_distribution is None:
            # Default realistic distribution
            profile_distribution = {
                LoadProfile.RESIDENTIAL_SMALL: 0.35,
                LoadProfile.RESIDENTIAL_MEDIUM: 0.45,
                LoadProfile.RESIDENTIAL_LARGE: 0.15,
                LoadProfile.COMMERCIAL_SMALL: 0.05,
            }
        
        # Normalize distribution
        total = sum(profile_distribution.values())
        normalized = {k: v/total for k, v in profile_distribution.items()}
        
        # Create agents with assigned profiles
        created_ids = []
        profiles = list(normalized.keys())
        weights = list(normalized.values())
        
        for i in range(count):
            agent_id = f"{id_prefix}_{i+1:03d}"
            
            # Select profile based on distribution
            profile = random.choices(profiles, weights=weights)[0]
            
            # Create agent
            agent = HouseholdAgent(
                agent_id=agent_id,
                public_context=self.public_context,
                profile=profile,
                security_logger=self.logger,
                seed=i  # Reproducible variation per agent
            )
            
            self.agents[agent_id] = agent
            created_ids.append(agent_id)
        
        return created_ids
    
    def add_agent(self, 
                  agent_id: str,
                  profile: LoadProfile = LoadProfile.RESIDENTIAL_MEDIUM) -> HouseholdAgent:
        """Add a single agent"""
        agent = HouseholdAgent(
            agent_id=agent_id,
            public_context=self.public_context,
            profile=profile,
            security_logger=self.logger
        )
        self.agents[agent_id] = agent
        return agent
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            return True
        return False
    
    def collect_encrypted_demands(self, 
                                   timestamp: Optional[datetime] = None) -> List[EncryptedDemand]:
        """
        Collect encrypted demands from all active agents.
        
        Each agent generates and encrypts its current demand.
        Returns list of encrypted demands ready for coordinator.
        
        Args:
            timestamp: Time for demand calculation
            
        Returns:
            List of encrypted demands from all agents
        """
        encrypted_demands = []
        
        for agent_id, agent in self.agents.items():
            status = agent.get_status()
            if status.is_active:
                encrypted = agent.encrypt_demand(timestamp)
                encrypted_demands.append(encrypted)
        
        return encrypted_demands
    
    def get_all_statuses(self) -> List[AgentStatus]:
        """Get status of all agents"""
        return [agent.get_status() for agent in self.agents.values()]
    
    def get_agent(self, agent_id: str) -> Optional[HouseholdAgent]:
        """Get specific agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agent_count(self) -> int:
        """Get total number of agents"""
        return len(self.agents)
    
    def get_active_count(self) -> int:
        """Get number of active agents"""
        return sum(1 for a in self.agents.values() if a.get_status().is_active)
    
    def broadcast_load_balance(self, reduction_factor: float):
        """
        Broadcast load balance command to all agents.
        
        Args:
            reduction_factor: Factor to reduce demand by (0.0 to 1.0)
        """
        for agent in self.agents.values():
            agent.receive_load_balance_command(reduction_factor)
    
    def get_plaintext_demands_for_comparison(self) -> Dict[str, float]:
        """
        Get plaintext demands for evaluation/comparison.
        
        Only for benchmarking - proves encrypted computation is accurate.
        """
        return {
            agent_id: agent.get_plaintext_demand_for_comparison()
            for agent_id, agent in self.agents.items()
            if agent.get_status().is_active
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all agents"""
        statuses = self.get_all_statuses()
        
        profile_counts = {}
        total_demand = 0.0
        
        for status in statuses:
            profile = status.profile
            profile_counts[profile] = profile_counts.get(profile, 0) + 1
            total_demand += status.current_demand_kw
        
        return {
            'total_agents': len(self.agents),
            'active_agents': self.get_active_count(),
            'profile_distribution': profile_counts,
            'total_current_demand_kw': round(total_demand, 2),
            'average_demand_kw': round(total_demand / len(self.agents), 2) if self.agents else 0
        }
    
    def __len__(self):
        return len(self.agents)
    
    def __iter__(self):
        return iter(self.agents.values())


def demo():
    """Demonstrate agent manager"""
    print("=" * 60)
    print("Agent Manager Demo")
    print("=" * 60)
    
    from core.fhe_engine import SmartGridFHE
    
    # Create FHE engine
    print("\n[1] Creating FHE keys...")
    utility = SmartGridFHE()
    public_context = utility.get_public_context()
    
    # Create agent manager
    print("\n[2] Creating agent manager with 10 households...")
    manager = AgentManager(public_context)
    agent_ids = manager.create_agents(10)
    
    print(f"    Created {len(agent_ids)} agents")
    
    summary = manager.get_summary()
    print(f"    Profile distribution: {summary['profile_distribution']}")
    
    # Collect encrypted demands
    print("\n[3] Collecting encrypted demands from all agents...")
    encrypted_demands = manager.collect_encrypted_demands()
    
    print(f"    Collected {len(encrypted_demands)} encrypted demands")
    for enc in encrypted_demands[:3]:
        print(f"      {enc.agent_id}: {enc.get_display_ciphertext(30)}")
    print("      ...")
    
    # Get plaintext for comparison
    print("\n[4] Plaintext demands (for comparison only):")
    plaintext = manager.get_plaintext_demands_for_comparison()
    total_plaintext = sum(plaintext.values())
    print(f"    Total plaintext demand: {total_plaintext:.2f} kW")
    
    # Aggregate encrypted
    print("\n[5] Aggregating encrypted demands...")
    from core.fhe_engine import SmartGridFHE
    coordinator_fhe = SmartGridFHE.from_context(public_context)
    encrypted_total = coordinator_fhe.aggregate_demands(encrypted_demands)
    
    # Decrypt with utility
    decrypted_total = utility.decrypt_demand(encrypted_total)
    print(f"    Encrypted total (decrypted): {decrypted_total[0]:.2f} kW")
    print(f"    Error: {abs(decrypted_total[0] - total_plaintext):.2e} kW")


if __name__ == "__main__":
    demo()
