"""
FHE Engine for Smart Grid Load Balancing
=========================================
Implements TenSEAL CKKS scheme optimized for electricity demand data.
Supports encrypted aggregation, averaging, and threshold detection.

Cryptographic Justification:
- CKKS chosen over Paillier for real-valued demand data (kW values like 2.45, 3.71)
- Supports both addition AND multiplication on ciphertexts
- Enables computing averages: E(avg) = E(sum) × (1/n)
- Approximate results with ~10^-7 relative error (negligible for kW range)

Security Parameters:
- poly_modulus_degree: 8192 → 128-bit security (NIST standard)
- coeff_mod_bit_sizes: [60, 40, 40, 60] → Supports 3 multiplicative depths
- global_scale: 2^40 → 12 decimal digits of precision
"""

import tenseal as ts
import numpy as np
from typing import List, Union, Optional, Dict, Any
from dataclasses import dataclass, field
import base64
import hashlib
from datetime import datetime
import json


@dataclass
class EncryptedDemand:
    """
    Wrapper for encrypted electricity demand with metadata.
    
    The ciphertext contains the CKKS encryption of the demand value.
    No plaintext information is stored or derivable from this object.
    """
    ciphertext: bytes
    timestamp: str
    agent_id: str
    vector_size: int
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for transmission"""
        return {
            'ciphertext': base64.b64encode(self.ciphertext).decode('utf-8'),
            'timestamp': self.timestamp,
            'agent_id': self.agent_id,
            'vector_size': self.vector_size,
            'checksum': self.checksum,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedDemand':
        """Deserialize from dictionary"""
        return cls(
            ciphertext=base64.b64decode(data['ciphertext']),
            timestamp=data['timestamp'],
            agent_id=data['agent_id'],
            vector_size=data['vector_size'],
            checksum=data['checksum'],
            metadata=data.get('metadata', {})
        )
    
    def get_display_ciphertext(self, max_length: int = 64) -> str:
        """Get truncated base64 ciphertext for display (proves it's encrypted)"""
        b64 = base64.b64encode(self.ciphertext).decode('utf-8')
        if len(b64) > max_length:
            return f"{b64[:max_length//2]}...{b64[-max_length//2:]}"
        return b64
    
    def get_size_kb(self) -> float:
        """Get ciphertext size in KB"""
        return len(self.ciphertext) / 1024


class SmartGridFHE:
    """
    Fully Homomorphic Encryption Engine for Smart Grid Operations.
    
    This engine provides:
    - Encryption of demand values (real numbers in kW)
    - Homomorphic aggregation (sum of encrypted demands)
    - Homomorphic averaging (encrypted mean computation)
    - Threshold comparison support
    
    The coordinator uses this with PUBLIC context only (cannot decrypt).
    Only the authorized utility company has the SECRET context.
    """
    
    def __init__(self, 
                 poly_modulus_degree: int = 16384,
                 coeff_mod_bit_sizes: List[int] = None,
                 global_scale: float = 2**40):
        """
        Initialize FHE Engine with CKKS parameters.
        
        Args:
            poly_modulus_degree: Polynomial ring degree (power of 2)
                - 8192 provides 128-bit security
                - Higher values allow more operations but slower
            coeff_mod_bit_sizes: Coefficient modulus chain
                - Determines multiplicative depth
            global_scale: Encoding scale for precision
                - 2^40 gives ~12 decimal digits
        """
        if coeff_mod_bit_sizes is None:
            # Standard CKKS chain for ~3-4 multiplications
            coeff_mod_bit_sizes = [60, 40, 40, 40, 60]
        
        self.poly_modulus_degree = poly_modulus_degree
        self.coeff_mod_bit_sizes = coeff_mod_bit_sizes
        self.global_scale = global_scale
        
        # Create TenSEAL context with CKKS scheme
        self.context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes
        )
        
        # Generate required keys
        self.context.generate_galois_keys()  # For rotation operations
        self.context.generate_relin_keys()   # For relinearization after multiplication
        self.context.global_scale = global_scale
        
        # Enable automatic rescaling for multiplication chains
        self.context.auto_rescale = True
        self.context.auto_relin = True
        self.context.auto_mod_switch = True
        
        self.created_at = datetime.now().isoformat()
        self._operation_count = 0
    
    def get_public_context(self) -> bytes:
        """
        Get public context (without secret key) for untrusted parties.
        
        The coordinator and agents receive this context.
        They can ENCRYPT data but CANNOT DECRYPT.
        """
        public_ctx = self.context.copy()
        public_ctx.make_context_public()
        return public_ctx.serialize()
    
    def get_secret_context(self) -> bytes:
        """
        Get full context WITH secret key for authorized decryptor.
        
        Only the utility company (final authorized entity) receives this.
        Required for decryption of final aggregates.
        """
        return self.context.serialize(save_secret_key=True)
    
    def get_context_hash(self) -> str:
        """Get unique hash of this context for verification"""
        ctx_bytes = self.get_public_context()
        return hashlib.sha256(ctx_bytes).hexdigest()[:16]
    
    def is_private(self) -> bool:
        """Check if this engine can decrypt (has secret key)"""
        return self.context.is_private()
    
    @classmethod
    def from_context(cls, context_bytes: bytes, has_secret_key: bool = False) -> 'SmartGridFHE':
        """
        Reconstruct FHE Engine from serialized context.
        
        Used by coordinator (public context) and utility (secret context).
        """
        engine = cls.__new__(cls)
        engine.context = ts.context_from(context_bytes)
        
        # Handle different TenSEAL API versions
        try:
            engine.poly_modulus_degree = engine.context.poly_modulus_degree()
        except TypeError:
            try:
                engine.poly_modulus_degree = engine.context.poly_modulus_degree
            except AttributeError:
                engine.poly_modulus_degree = 8192
        except AttributeError:
            engine.poly_modulus_degree = 8192
        
        try:
            engine.global_scale = engine.context.global_scale
        except AttributeError:
            engine.global_scale = 2**40
            
        engine.coeff_mod_bit_sizes = []
        engine.created_at = datetime.now().isoformat()
        engine._operation_count = 0
        return engine
    
    # ==================== ENCRYPTION / DECRYPTION ====================
    
    def encrypt_demand(self, 
                       demand_kw: Union[float, List[float]], 
                       agent_id: str) -> EncryptedDemand:
        """
        Encrypt electricity demand value(s).
        
        Args:
            demand_kw: Demand in kilowatts (single value or time series)
            agent_id: Identifier of the household agent
            
        Returns:
            EncryptedDemand containing the ciphertext
            
        Example:
            enc = engine.encrypt_demand(3.45, "household_001")
        """
        if isinstance(demand_kw, (int, float)):
            values = [float(demand_kw)]
        elif isinstance(demand_kw, np.ndarray):
            values = demand_kw.tolist()
        else:
            values = [float(v) for v in demand_kw]
        
        # Create encrypted CKKS vector
        encrypted = ts.ckks_vector(self.context, values)
        ciphertext = encrypted.serialize()
        
        # Generate checksum for integrity verification
        checksum = hashlib.sha256(ciphertext).hexdigest()[:12]
        
        self._operation_count += 1
        
        return EncryptedDemand(
            ciphertext=ciphertext,
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            vector_size=len(values),
            checksum=checksum,
            metadata={'operation_id': self._operation_count}
        )
    
    def decrypt_demand(self, encrypted: EncryptedDemand) -> List[float]:
        """
        Decrypt an encrypted demand value.
        
        ONLY the utility company (with secret key) can call this.
        The coordinator CANNOT decrypt - it only has public context.
        
        Args:
            encrypted: EncryptedDemand to decrypt
            
        Returns:
            List of decrypted demand values in kW
            
        Raises:
            ValueError: If context doesn't have secret key
        """
        if not self.context.is_private():
            raise ValueError("Cannot decrypt: context does not contain secret key. "
                           "Only the authorized utility company can decrypt.")
        
        # Verify integrity
        computed_checksum = hashlib.sha256(encrypted.ciphertext).hexdigest()[:12]
        if computed_checksum != encrypted.checksum:
            raise ValueError("Ciphertext integrity check failed - data may be corrupted")
        
        # Deserialize and decrypt
        enc_vector = ts.ckks_vector_from(self.context, encrypted.ciphertext)
        decrypted = enc_vector.decrypt()
        
        # Return only original vector size (CKKS may pad internally)
        return decrypted[:encrypted.vector_size]
    
    # ==================== HOMOMORPHIC OPERATIONS ====================
    
    def _load_encrypted(self, encrypted: EncryptedDemand) -> ts.CKKSVector:
        """Load encrypted demand into TenSEAL vector"""
        return ts.ckks_vector_from(self.context, encrypted.ciphertext)
    
    def _save_encrypted(self, 
                        ckks_vector: ts.CKKSVector, 
                        original: EncryptedDemand,
                        operation: str) -> EncryptedDemand:
        """Save computed result back to EncryptedDemand"""
        ciphertext = ckks_vector.serialize()
        checksum = hashlib.sha256(ciphertext).hexdigest()[:12]
        
        self._operation_count += 1
        
        return EncryptedDemand(
            ciphertext=ciphertext,
            timestamp=datetime.now().isoformat(),
            agent_id=f"aggregated_{operation}",
            vector_size=original.vector_size,
            checksum=checksum,
            metadata={
                'operation': operation,
                'operation_id': self._operation_count,
                'source_agents': original.metadata.get('source_agents', [original.agent_id])
            }
        )
    
    def add_encrypted(self, 
                      enc_a: EncryptedDemand, 
                      enc_b: EncryptedDemand) -> EncryptedDemand:
        """
        Homomorphic addition: E(a) + E(b) = E(a + b)
        
        Used to aggregate demands from two households.
        The result is still encrypted - coordinator never sees values.
        """
        vec_a = self._load_encrypted(enc_a)
        vec_b = self._load_encrypted(enc_b)
        
        result = vec_a + vec_b
        
        # Track source agents
        sources_a = enc_a.metadata.get('source_agents', [enc_a.agent_id])
        sources_b = enc_b.metadata.get('source_agents', [enc_b.agent_id])
        
        enc_result = self._save_encrypted(result, enc_a, "sum")
        enc_result.metadata['source_agents'] = sources_a + sources_b
        return enc_result
    
    def aggregate_demands(self, encrypted_list: List[EncryptedDemand]) -> EncryptedDemand:
        """
        Aggregate (sum) multiple encrypted demands.
        
        E(d₁) + E(d₂) + ... + E(dₙ) = E(Σdᵢ)
        
        This is the primary operation for the coordinator.
        The result is encrypted total demand - no individual values exposed.
        
        Args:
            encrypted_list: List of encrypted demands from households
            
        Returns:
            Single EncryptedDemand containing encrypted total
        """
        if len(encrypted_list) == 0:
            raise ValueError("Cannot aggregate empty list")
        
        if len(encrypted_list) == 1:
            return encrypted_list[0]
        
        # Sum all encrypted vectors
        result = self._load_encrypted(encrypted_list[0])
        all_sources = encrypted_list[0].metadata.get('source_agents', [encrypted_list[0].agent_id])
        
        for enc in encrypted_list[1:]:
            vec = self._load_encrypted(enc)
            result = result + vec
            sources = enc.metadata.get('source_agents', [enc.agent_id])
            all_sources.extend(sources)
        
        enc_result = self._save_encrypted(result, encrypted_list[0], "aggregate")
        enc_result.metadata['source_agents'] = all_sources
        enc_result.metadata['agent_count'] = len(encrypted_list)
        return enc_result
    
    def compute_average(self, encrypted_total: EncryptedDemand, count: int) -> EncryptedDemand:
        """
        Compute encrypted average: E(avg) = E(sum) × (1/n)
        
        Division by constant is multiplication by reciprocal.
        Result is still encrypted.
        
        Args:
            encrypted_total: Encrypted sum of demands
            count: Number of values in the sum
            
        Returns:
            EncryptedDemand containing encrypted average
        """
        vec = self._load_encrypted(encrypted_total)
        result = vec * (1.0 / count)
        
        enc_result = self._save_encrypted(result, encrypted_total, "average")
        enc_result.metadata['divisor'] = count
        return enc_result
    
    def multiply_plain(self, 
                       encrypted: EncryptedDemand, 
                       scalar: float) -> EncryptedDemand:
        """
        Multiply encrypted value by plaintext scalar: E(a) × b = E(a × b)
        
        Useful for scaling operations (e.g., unit conversion, reduction factors).
        """
        vec = self._load_encrypted(encrypted)
        result = vec * scalar
        
        enc_result = self._save_encrypted(result, encrypted, "scaled")
        enc_result.metadata['scale_factor'] = scalar
        return enc_result
    
    def add_plain(self, 
                  encrypted: EncryptedDemand, 
                  offset: float) -> EncryptedDemand:
        """
        Add plaintext offset to encrypted value: E(a) + b = E(a + b)
        
        Useful for adjustments (e.g., adding base load).
        """
        vec = self._load_encrypted(encrypted)
        result = vec + offset
        
        enc_result = self._save_encrypted(result, encrypted, "offset")
        enc_result.metadata['offset'] = offset
        return enc_result
    
    def multiply_encrypted(self,
                           enc_a: EncryptedDemand,
                           enc_b: EncryptedDemand) -> EncryptedDemand:
        """
        Homomorphic multiplication: E(a) × E(b) = E(a × b)
        
        CRITICAL for polynomial evaluation in encrypted comparison.
        This is what enables our novel encrypted peak detection.
        
        Note: Multiplication consumes more noise budget than addition.
        CKKS typically supports ~3-5 multiplications before noise issues.
        
        Args:
            enc_a: First encrypted value
            enc_b: Second encrypted value
            
        Returns:
            Encrypted product
        """
        vec_a = self._load_encrypted(enc_a)
        vec_b = self._load_encrypted(enc_b)
        
        result = vec_a * vec_b
        
        enc_result = self._save_encrypted(result, enc_a, "multiply")
        enc_result.metadata['operation'] = 'ciphertext_multiplication'
        return enc_result
    
    def compute_elementwise_product(self,
                                  enc_a: EncryptedDemand,
                                  enc_b: EncryptedDemand) -> EncryptedDemand:
        """
        Compute element-wise product of two encrypted vectors.
        E(a) * E(b) = E([a1*b1, a2*b2, ...])
        """
        return self.multiply_encrypted(enc_a, enc_b)

    def compute_dot_product(self,
                          enc_a: EncryptedDemand,
                          enc_b: EncryptedDemand) -> EncryptedDemand:
        """
        Compute dot product of two encrypted vectors.
        E(a) . E(b) = E(sum(ai * bi))
        
        Note: This consumes one multiplication depth.
        """
        vec_a = self._load_encrypted(enc_a)
        vec_b = self._load_encrypted(enc_b)
        
        # Element-wise multiply
        product = vec_a * vec_b
        
        # Sum all elements
        result = product.sum()
        
        enc_result = self._save_encrypted(result, enc_a, "dot_product")
        enc_result.metadata['operation'] = 'dot_product'
        enc_result.metadata['operand_b'] = enc_b.agent_id
        return enc_result

    def rotate_encrypted(self, 
                        encrypted: EncryptedDemand, 
                        steps: int) -> EncryptedDemand:
        """
        Rotate the encrypted vector cyclically using Matrix Multiplication.
        
        Args:
            encrypted: Vector to rotate
            steps: Number of steps to rotate left (positive)
            
        Returns:
            EncryptedDemand with rotated vector
        """
        vec = self._load_encrypted(encrypted)
        n = encrypted.vector_size
        
        if n > 100:
            raise NotImplementedError("Rotation via matmul only supported for small vectors (n<=100)")
            
        # Create permutation matrix for v * M rotation
        # We want out[j] = in[(j + steps) % n]
        # (v * M)[j] = sum(v[i] * M[i,j])
        # So M[i,j] = 1 where i == (j + steps) % n
        
        M = np.zeros((n, n))
        for j in range(n):
            i = (j + steps) % n
            M[i, j] = 1.0
            
        # Perform matrix multiplication
        # Note: TenSEAL matmul expects list of lists
        result = vec.matmul(M.tolist())
        
        enc_result = self._save_encrypted(result, encrypted, f"rotate_{steps}")
        enc_result.metadata['rotation'] = steps
        return enc_result
    
    def compute_reduction_factor(self, 
                                  encrypted_total: EncryptedDemand,
                                  capacity_limit: float) -> EncryptedDemand:
        """
        Compute load reduction factor based on capacity.
        
        If total > capacity, agents need to reduce proportionally.
        Returns E(total / capacity) which gives the reduction needed.
        
        Note: The coordinator computes this but cannot see the actual values.
        The utility company decrypts and broadcasts reduction commands.
        """
        vec = self._load_encrypted(encrypted_total)
        result = vec * (1.0 / capacity_limit)
        
        enc_result = self._save_encrypted(result, encrypted_total, "reduction_factor")
        enc_result.metadata['capacity_limit'] = capacity_limit
        return enc_result
    
    # ==================== UTILITY METHODS ====================
    
    def get_info(self) -> dict:
        """Get engine configuration information"""
        return {
            'scheme': 'CKKS',
            'poly_modulus_degree': self.poly_modulus_degree,
            'coeff_mod_bit_sizes': self.coeff_mod_bit_sizes,
            'global_scale': self.global_scale,
            'security_level': '128-bit',
            'created_at': self.created_at,
            'context_hash': self.get_context_hash(),
            'has_secret_key': self.context.is_private(),
            'operations_performed': self._operation_count
        }
    
    def verify_integrity(self, encrypted: EncryptedDemand) -> bool:
        """Verify ciphertext integrity using checksum"""
        computed = hashlib.sha256(encrypted.ciphertext).hexdigest()[:12]
        return computed == encrypted.checksum
    
    def estimate_noise_budget(self) -> str:
        """
        Estimate remaining noise budget.
        
        CKKS accumulates noise with operations. After too many operations,
        decryption may fail. This helps monitor capacity.
        """
        # Simplified estimation based on operation count
        if self._operation_count < 10:
            return "High (fresh)"
        elif self._operation_count < 50:
            return "Medium"
        elif self._operation_count < 100:
            return "Low - consider refreshing"
        else:
            return "Critical - refresh recommended"


# ==================== DEMO / VERIFICATION ====================

def demo():
    """Demonstrate FHE operations for smart grid"""
    print("=" * 70)
    print("Smart Grid Homomorphic Encryption Demo")
    print("=" * 70)
    
    # Create engine (utility company - has secret key)
    print("\n[1] Utility Company generates FHE keys...")
    utility_engine = SmartGridFHE()
    print(f"    Context Hash: {utility_engine.get_context_hash()}")
    print(f"    Has Secret Key: {utility_engine.is_private()}")
    
    # Distribute public context to coordinator
    print("\n[2] Coordinator receives PUBLIC context (cannot decrypt)...")
    public_context = utility_engine.get_public_context()
    coordinator_engine = SmartGridFHE.from_context(public_context, has_secret_key=False)
    print(f"    Coordinator Has Secret Key: {coordinator_engine.is_private()}")
    
    # Simulate household demands (in kW)
    print("\n[3] Households encrypt their demand locally...")
    household_demands = {
        'house_001': 3.45,  # kW
        'house_002': 2.18,
        'house_003': 5.72,
        'house_004': 1.89,
        'house_005': 4.33,
    }
    
    # Each household encrypts with coordinator's public context
    encrypted_demands = []
    for house_id, demand in household_demands.items():
        enc = coordinator_engine.encrypt_demand(demand, house_id)
        print(f"    {house_id}: {demand} kW -> {enc.get_display_ciphertext(40)}")
        encrypted_demands.append(enc)
    
    # Coordinator aggregates (on encrypted data)
    print("\n[4] Coordinator aggregates demands (ON ENCRYPTED DATA)...")
    encrypted_total = coordinator_engine.aggregate_demands(encrypted_demands)
    print(f"    Encrypted Total: {encrypted_total.get_display_ciphertext(40)}")
    print(f"    Ciphertext Size: {encrypted_total.get_size_kb():.1f} KB")
    
    # Coordinator computes average (on encrypted data)
    encrypted_avg = coordinator_engine.compute_average(encrypted_total, len(household_demands))
    print(f"    Encrypted Average: {encrypted_avg.get_display_ciphertext(40)}")
    
    # Utility company decrypts final aggregates
    print("\n[5] Utility Company decrypts final aggregates...")
    decrypted_total = utility_engine.decrypt_demand(encrypted_total)
    decrypted_avg = utility_engine.decrypt_demand(encrypted_avg)
    
    actual_total = sum(household_demands.values())
    actual_avg = actual_total / len(household_demands)
    
    print(f"    Decrypted Total: {decrypted_total[0]:.4f} kW")
    print(f"    Expected Total:  {actual_total:.4f} kW")
    print(f"    Error: {abs(decrypted_total[0] - actual_total):.2e} kW")
    print()
    print(f"    Decrypted Average: {decrypted_avg[0]:.4f} kW")
    print(f"    Expected Average:  {actual_avg:.4f} kW")
    print(f"    Error: {abs(decrypted_avg[0] - actual_avg):.2e} kW")
    
    # Prove coordinator cannot decrypt
    print("\n[6] PROOF: Coordinator CANNOT decrypt...")
    try:
        coordinator_engine.decrypt_demand(encrypted_total)
        print("    ERROR: Coordinator should not be able to decrypt!")
    except ValueError as e:
        print(f"    ✓ Correctly rejected: {str(e)[:50]}...")
    
    print("\n" + "=" * 70)
    print("Demo Complete - Privacy preserved, computation performed!")
    print("=" * 70)


if __name__ == "__main__":
    demo()
