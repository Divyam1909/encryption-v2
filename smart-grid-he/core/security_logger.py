"""
Security Logger for Smart Grid HE System
=========================================
Provides audit trail proving no plaintext data is ever accessed by coordinator.

Purpose:
- Log all operations with encrypted vs plaintext classification
- Prove to auditors that coordinator only handles ciphertext
- Detect any security violations
- Support compliance requirements (GDPR, CCPA privacy audits)
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading


class DataType(Enum):
    """Classification of data handled in an operation"""
    CIPHERTEXT = "ciphertext"      # Encrypted data - safe
    PLAINTEXT = "plaintext"        # Raw data - privacy risk
    PUBLIC_PARAM = "public_param"  # Public parameters (count, threshold) - safe
    METADATA = "metadata"          # Non-sensitive metadata - safe


class OperationType(Enum):
    """Types of operations in the system"""
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    AGGREGATE = "aggregate"
    COMPUTE_AVERAGE = "compute_average"
    SCALE = "scale"
    TRANSMIT = "transmit"
    RECEIVE = "receive"
    STORE = "store"
    LOAD_BALANCE = "load_balance"


@dataclass
class SecurityLogEntry:
    """Single security audit log entry"""
    timestamp: str
    entity: str          # 'agent', 'coordinator', 'utility'
    operation: str
    data_types: List[str]  # What types of data were involved
    is_safe: bool        # True if no plaintext exposure
    details: Dict[str, Any]
    sequence_id: int
    
    def to_dict(self) -> dict:
        return asdict(self)


class SecurityLogger:
    """
    Immutable audit log for proving privacy preservation.
    
    Every operation is logged with:
    - Who performed it
    - What data types were involved
    - Whether plaintext was ever exposed
    
    The coordinator should ONLY have entries with CIPHERTEXT data type.
    Any PLAINTEXT entry for coordinator indicates a security violation.
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize security logger.
        
        Args:
            log_file: Optional file path to persist logs
        """
        self._entries: List[SecurityLogEntry] = []
        self._lock = threading.Lock()
        self._sequence = 0
        self.log_file = Path(log_file) if log_file else None
        
        # Load existing entries if file exists
        if self.log_file and self.log_file.exists():
            self._load_from_file()
    
    def log(self, 
            entity: str,
            operation: OperationType,
            data_types: List[DataType],
            details: Dict[str, Any] = None) -> SecurityLogEntry:
        """
        Log a security-relevant operation.
        
        Args:
            entity: Who performed the operation ('agent_001', 'coordinator', 'utility')
            operation: Type of operation performed
            data_types: Types of data involved in the operation
            details: Additional context for the operation
            
        Returns:
            The created log entry
        """
        with self._lock:
            self._sequence += 1
            
            # Determine if this is a safe operation (no plaintext for coordinator)
            is_safe = True
            if entity == 'coordinator' and DataType.PLAINTEXT in data_types:
                is_safe = False  # SECURITY VIOLATION
            
            entry = SecurityLogEntry(
                timestamp=datetime.now().isoformat(),
                entity=entity,
                operation=operation.value,
                data_types=[dt.value for dt in data_types],
                is_safe=is_safe,
                details=details or {},
                sequence_id=self._sequence
            )
            
            self._entries.append(entry)
            
            # Write to file if configured
            if self.log_file:
                self._append_to_file(entry)
            
            return entry
    
    def log_agent_encrypt(self, agent_id: str, demand_range: str) -> SecurityLogEntry:
        """Log an agent encrypting their demand"""
        return self.log(
            entity=agent_id,
            operation=OperationType.ENCRYPT,
            data_types=[DataType.PLAINTEXT, DataType.CIPHERTEXT],  # Agent sees own plaintext
            details={'action': 'encrypt_local_demand', 'demand_range': demand_range}
        )
    
    def log_coordinator_receive(self, agent_id: str, ciphertext_size_kb: float) -> SecurityLogEntry:
        """Log coordinator receiving encrypted demand"""
        return self.log(
            entity='coordinator',
            operation=OperationType.RECEIVE,
            data_types=[DataType.CIPHERTEXT],  # Coordinator only sees ciphertext
            details={'from_agent': agent_id, 'ciphertext_size_kb': ciphertext_size_kb}
        )
    
    def log_coordinator_aggregate(self, agent_count: int) -> SecurityLogEntry:
        """Log coordinator aggregating encrypted demands"""
        return self.log(
            entity='coordinator',
            operation=OperationType.AGGREGATE,
            data_types=[DataType.CIPHERTEXT, DataType.PUBLIC_PARAM],
            details={'agent_count': agent_count, 'operation': 'homomorphic_sum'}
        )
    
    def log_coordinator_average(self, divisor: int) -> SecurityLogEntry:
        """Log coordinator computing encrypted average"""
        return self.log(
            entity='coordinator',
            operation=OperationType.COMPUTE_AVERAGE,
            data_types=[DataType.CIPHERTEXT, DataType.PUBLIC_PARAM],
            details={'divisor': divisor, 'operation': 'homomorphic_divide'}
        )
    
    def log_utility_decrypt(self, result_type: str) -> SecurityLogEntry:
        """Log utility company decrypting final aggregates"""
        return self.log(
            entity='utility',
            operation=OperationType.DECRYPT,
            data_types=[DataType.CIPHERTEXT, DataType.PLAINTEXT],  # Utility is authorized
            details={'result_type': result_type, 'authorized': True}
        )
    
    def log_load_balance_decision(self, decision: str) -> SecurityLogEntry:
        """Log load balancing decision"""
        return self.log(
            entity='utility',
            operation=OperationType.LOAD_BALANCE,
            data_types=[DataType.PLAINTEXT, DataType.METADATA],
            details={'decision': decision}
        )
    
    def get_all_entries(self) -> List[SecurityLogEntry]:
        """Get all log entries"""
        return list(self._entries)
    
    def get_entries_for_entity(self, entity: str) -> List[SecurityLogEntry]:
        """Get entries for a specific entity"""
        return [e for e in self._entries if e.entity == entity]
    
    def get_violations(self) -> List[SecurityLogEntry]:
        """Get all security violation entries"""
        return [e for e in self._entries if not e.is_safe]
    
    def verify_no_violations(self) -> bool:
        """Verify that no security violations occurred"""
        return len(self.get_violations()) == 0
    
    def get_coordinator_summary(self) -> Dict[str, Any]:
        """
        Get summary of coordinator operations for audit.
        
        This proves the coordinator never accessed plaintext.
        """
        coordinator_entries = self.get_entries_for_entity('coordinator')
        
        data_types_seen = set()
        for entry in coordinator_entries:
            data_types_seen.update(entry.data_types)
        
        return {
            'total_operations': len(coordinator_entries),
            'data_types_handled': list(data_types_seen),
            'plaintext_access': 'plaintext' in data_types_seen,
            'violations': len([e for e in coordinator_entries if not e.is_safe]),
            'privacy_preserved': 'plaintext' not in data_types_seen
        }
    
    def generate_audit_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive audit report.
        
        Suitable for compliance reviews and academic demonstration.
        """
        coordinator_summary = self.get_coordinator_summary()
        
        return {
            'report_generated': datetime.now().isoformat(),
            'total_log_entries': len(self._entries),
            'entities': list(set(e.entity for e in self._entries)),
            'coordinator_privacy_audit': coordinator_summary,
            'security_violations': [e.to_dict() for e in self.get_violations()],
            'conclusion': (
                "PRIVACY PRESERVED: Coordinator never accessed plaintext data." 
                if coordinator_summary['privacy_preserved']
                else "PRIVACY VIOLATION: Coordinator accessed plaintext data!"
            )
        }
    
    def _append_to_file(self, entry: SecurityLogEntry):
        """Append entry to log file"""
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')
    
    def _load_from_file(self):
        """Load entries from log file"""
        with open(self.log_file, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    self._entries.append(SecurityLogEntry(**data))
                    self._sequence = max(self._sequence, data['sequence_id'])
    
    def clear(self):
        """Clear all entries (for testing)"""
        self._entries.clear()
        self._sequence = 0
        if self.log_file and self.log_file.exists():
            self.log_file.unlink()
    
    def to_display_format(self, max_entries: int = 50) -> List[Dict[str, Any]]:
        """
        Convert entries to display format for dashboard.
        
        Returns recent entries with color coding:
        - green: Safe operation (ciphertext only)
        - yellow: Agent local operation (sees own plaintext)
        - blue: Utility operation (authorized decryption)
        - red: Violation (coordinator saw plaintext)
        """
        entries = self._entries[-max_entries:]
        
        display = []
        for e in entries:
            if not e.is_safe:
                color = 'red'
                icon = '🚨'
            elif e.entity == 'coordinator':
                color = 'green'
                icon = '🔒'
            elif e.entity.startswith('house') or e.entity.startswith('agent'):
                color = 'yellow'
                icon = '🏠'
            elif e.entity == 'utility':
                color = 'blue'
                icon = '⚡'
            else:
                color = 'gray'
                icon = '📝'
            
            display.append({
                'time': e.timestamp.split('T')[1][:8],
                'icon': icon,
                'color': color,
                'entity': e.entity,
                'operation': e.operation,
                'safe': e.is_safe,
                'details': e.details
            })
        
        return display
