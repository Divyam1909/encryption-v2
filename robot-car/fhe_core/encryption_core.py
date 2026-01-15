"""
Fully Homomorphic Encryption Core Engine
========================================
Implements TenSEAL CKKS scheme for encrypted computations on real numbers.
Supports addition, multiplication, and statistical operations on ciphertext.
"""

import tenseal as ts
import numpy as np
from typing import List, Union, Optional, Tuple
from dataclasses import dataclass
import base64
import json
import hashlib
from datetime import datetime


@dataclass
class EncryptedVector:
    """Wrapper for encrypted vector with metadata"""
    ciphertext: bytes
    timestamp: str
    sensor_type: str
    vector_size: int
    checksum: str
    
    def to_dict(self) -> dict:
        return {
            'ciphertext': base64.b64encode(self.ciphertext).decode('utf-8'),
            'timestamp': self.timestamp,
            'sensor_type': self.sensor_type,
            'vector_size': self.vector_size,
            'checksum': self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EncryptedVector':
        return cls(
            ciphertext=base64.b64decode(data['ciphertext']),
            timestamp=data['timestamp'],
            sensor_type=data['sensor_type'],
            vector_size=data['vector_size'],
            checksum=data['checksum']
        )
    
    def get_display_ciphertext(self, max_length: int = 64) -> str:
        """Get truncated base64 ciphertext for display to untrusted devices"""
        b64 = base64.b64encode(self.ciphertext).decode('utf-8')
        if len(b64) > max_length:
            return f"{b64[:max_length]}..."
        return b64


class FHEEngine:
    """
    Fully Homomorphic Encryption Engine using TenSEAL CKKS
    
    CKKS scheme enables:
    - Encryption of real numbers (floating point)
    - Homomorphic addition and multiplication
    - Approximate results with configurable precision
    
    Security Parameters:
    - poly_modulus_degree: 8192 (128-bit security)
    - coeff_mod_bit_sizes: [60, 40, 40, 60] for deep computations
    - global_scale: 2^40 for precision
    """
    
    def __init__(self, 
                 poly_modulus_degree: int = 8192,
                 coeff_mod_bit_sizes: List[int] = None,
                 global_scale: float = 2**40):
        """
        Initialize FHE Engine with CKKS parameters
        
        Args:
            poly_modulus_degree: Polynomial ring degree (power of 2)
            coeff_mod_bit_sizes: Coefficient modulus chain
            global_scale: Encoding scale for precision
        """
        if coeff_mod_bit_sizes is None:
            # Default: supports ~3 multiplications with good precision
            coeff_mod_bit_sizes = [60, 40, 40, 60]
        
        self.poly_modulus_degree = poly_modulus_degree
        self.coeff_mod_bit_sizes = coeff_mod_bit_sizes
        self.global_scale = global_scale
        
        # Create TenSEAL context
        self.context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes
        )
        
        # Generate keys
        self.context.generate_galois_keys()
        self.context.generate_relin_keys()
        self.context.global_scale = global_scale
        
        # Store creation timestamp
        self.created_at = datetime.now().isoformat()
        
    def get_public_context(self) -> bytes:
        """
        Get public context (without secret key) for untrusted parties
        They can encrypt but NOT decrypt
        """
        # Create a copy without secret key
        public_ctx = self.context.copy()
        public_ctx.make_context_public()
        return public_ctx.serialize()
    
    def get_secret_context(self) -> bytes:
        """
        Get full context WITH secret key for trusted devices
        Required for decryption
        """
        return self.context.serialize(save_secret_key=True)
    
    def get_context_hash(self) -> str:
        """Get unique hash of this context for verification"""
        ctx_bytes = self.get_public_context()
        return hashlib.sha256(ctx_bytes).hexdigest()[:16]
    
    @classmethod
    def from_context(cls, context_bytes: bytes, has_secret_key: bool = False) -> 'FHEEngine':
        """
        Reconstruct FHE Engine from serialized context
        
        Args:
            context_bytes: Serialized TenSEAL context
            has_secret_key: Whether context contains secret key
        """
        engine = cls.__new__(cls)
        engine.context = ts.context_from(context_bytes)
        
        # Handle different TenSEAL API versions
        try:
            # Try method call first (older versions)
            engine.poly_modulus_degree = engine.context.poly_modulus_degree()
        except TypeError:
            # Try property access (newer versions)
            try:
                engine.poly_modulus_degree = engine.context.poly_modulus_degree
            except AttributeError:
                engine.poly_modulus_degree = 8192  # Default fallback
        except AttributeError:
            engine.poly_modulus_degree = 8192  # Default fallback
        
        try:
            engine.global_scale = engine.context.global_scale
        except AttributeError:
            engine.global_scale = 2**40  # Default fallback
            
        engine.coeff_mod_bit_sizes = []  # Not recoverable from context
        engine.created_at = datetime.now().isoformat()
        return engine
    
    def encrypt(self, 
                values: Union[List[float], np.ndarray], 
                sensor_type: str = "generic") -> EncryptedVector:
        """
        Encrypt a vector of real numbers
        
        Args:
            values: List or array of floating point values
            sensor_type: Type of sensor data for metadata
            
        Returns:
            EncryptedVector with ciphertext and metadata
        """
        if isinstance(values, np.ndarray):
            values = values.tolist()
        
        # Create encrypted CKKS vector
        encrypted = ts.ckks_vector(self.context, values)
        ciphertext = encrypted.serialize()
        
        # Generate checksum for integrity
        checksum = hashlib.sha256(ciphertext).hexdigest()[:12]
        
        return EncryptedVector(
            ciphertext=ciphertext,
            timestamp=datetime.now().isoformat(),
            sensor_type=sensor_type,
            vector_size=len(values),
            checksum=checksum
        )
    
    def decrypt(self, encrypted_vector: EncryptedVector) -> List[float]:
        """
        Decrypt an encrypted vector
        
        Args:
            encrypted_vector: EncryptedVector to decrypt
            
        Returns:
            List of decrypted floating point values
            
        Raises:
            ValueError: If context doesn't have secret key
        """
        if not self.context.is_private():
            raise ValueError("Cannot decrypt: context does not contain secret key")
        
        # Verify checksum
        computed_checksum = hashlib.sha256(encrypted_vector.ciphertext).hexdigest()[:12]
        if computed_checksum != encrypted_vector.checksum:
            raise ValueError("Ciphertext integrity check failed")
        
        # Deserialize and decrypt
        encrypted = ts.ckks_vector_from(self.context, encrypted_vector.ciphertext)
        decrypted = encrypted.decrypt()
        
        # Return only the original vector size (CKKS may pad)
        return decrypted[:encrypted_vector.vector_size]
    
    def _load_encrypted(self, encrypted_vector: EncryptedVector) -> ts.CKKSVector:
        """Load encrypted vector into TenSEAL CKKSVector"""
        return ts.ckks_vector_from(self.context, encrypted_vector.ciphertext)
    
    def _save_encrypted(self, 
                        ckks_vector: ts.CKKSVector, 
                        original: EncryptedVector,
                        operation: str) -> EncryptedVector:
        """Save CKKSVector back to EncryptedVector"""
        ciphertext = ckks_vector.serialize()
        checksum = hashlib.sha256(ciphertext).hexdigest()[:12]
        
        return EncryptedVector(
            ciphertext=ciphertext,
            timestamp=datetime.now().isoformat(),
            sensor_type=f"{original.sensor_type}_{operation}",
            vector_size=original.vector_size,
            checksum=checksum
        )
    
    # ==================== HOMOMORPHIC OPERATIONS ====================
    
    def add_encrypted(self, 
                      enc_a: EncryptedVector, 
                      enc_b: EncryptedVector) -> EncryptedVector:
        """
        Homomorphic addition: E(a) + E(b) = E(a + b)
        
        Both operands must be encrypted with same context
        """
        vec_a = self._load_encrypted(enc_a)
        vec_b = self._load_encrypted(enc_b)
        
        result = vec_a + vec_b
        return self._save_encrypted(result, enc_a, "add")
    
    def add_plain(self, 
                  encrypted: EncryptedVector, 
                  plaintext: Union[float, List[float]]) -> EncryptedVector:
        """
        Homomorphic addition with plaintext: E(a) + b = E(a + b)
        """
        vec = self._load_encrypted(encrypted)
        
        if isinstance(plaintext, (int, float)):
            result = vec + plaintext
        else:
            result = vec + plaintext
            
        return self._save_encrypted(result, encrypted, "add_plain")
    
    def multiply_encrypted(self, 
                           enc_a: EncryptedVector, 
                           enc_b: EncryptedVector) -> EncryptedVector:
        """
        Homomorphic multiplication: E(a) * E(b) = E(a * b)
        
        Note: Multiplication increases noise, limited depth
        """
        vec_a = self._load_encrypted(enc_a)
        vec_b = self._load_encrypted(enc_b)
        
        result = vec_a * vec_b
        return self._save_encrypted(result, enc_a, "mul")
    
    def multiply_plain(self, 
                       encrypted: EncryptedVector, 
                       plaintext: Union[float, List[float]]) -> EncryptedVector:
        """
        Homomorphic multiplication with plaintext: E(a) * b = E(a * b)
        """
        vec = self._load_encrypted(encrypted)
        
        if isinstance(plaintext, (int, float)):
            result = vec * plaintext
        else:
            result = vec * plaintext
            
        return self._save_encrypted(result, encrypted, "mul_plain")
    
    def subtract_encrypted(self, 
                           enc_a: EncryptedVector, 
                           enc_b: EncryptedVector) -> EncryptedVector:
        """
        Homomorphic subtraction: E(a) - E(b) = E(a - b)
        """
        vec_a = self._load_encrypted(enc_a)
        vec_b = self._load_encrypted(enc_b)
        
        result = vec_a - vec_b
        return self._save_encrypted(result, enc_a, "sub")
    
    def negate(self, encrypted: EncryptedVector) -> EncryptedVector:
        """
        Homomorphic negation: -E(a) = E(-a)
        """
        vec = self._load_encrypted(encrypted)
        result = -vec
        return self._save_encrypted(result, encrypted, "neg")
    
    def sum_elements(self, encrypted: EncryptedVector) -> EncryptedVector:
        """
        Homomorphic sum of all elements: E([a,b,c]) -> E([a+b+c, ...])
        
        Returns encrypted vector where first element is the sum
        """
        vec = self._load_encrypted(encrypted)
        result = vec.sum()
        
        # Result is a vector with sum replicated
        ciphertext = result.serialize()
        checksum = hashlib.sha256(ciphertext).hexdigest()[:12]
        
        return EncryptedVector(
            ciphertext=ciphertext,
            timestamp=datetime.now().isoformat(),
            sensor_type=f"{encrypted.sensor_type}_sum",
            vector_size=1,  # Sum is single value
            checksum=checksum
        )
    
    def compute_mean(self, encrypted: EncryptedVector) -> EncryptedVector:
        """
        Compute encrypted mean: E(mean) = E(sum) / n
        
        Division by constant is multiplication by reciprocal
        """
        n = encrypted.vector_size
        sum_vec = self.sum_elements(encrypted)
        
        # Multiply by 1/n (division by constant)
        return self.multiply_plain(sum_vec, 1.0 / n)
    
    def dot_product(self, 
                    enc_a: EncryptedVector, 
                    enc_b: EncryptedVector) -> EncryptedVector:
        """
        Homomorphic dot product: E(a · b) = sum(E(a) * E(b))
        """
        product = self.multiply_encrypted(enc_a, enc_b)
        return self.sum_elements(product)
    
    def polynomial_eval(self, 
                        encrypted: EncryptedVector, 
                        coefficients: List[float]) -> EncryptedVector:
        """
        Evaluate polynomial on encrypted data: E(p(x))
        
        coefficients = [a0, a1, a2, ...] for a0 + a1*x + a2*x^2 + ...
        """
        vec = self._load_encrypted(encrypted)
        result = vec.polyval(coefficients)
        return self._save_encrypted(result, encrypted, "poly")
    
    # ==================== BATCH OPERATIONS ====================
    
    def batch_encrypt(self, 
                      data_list: List[List[float]], 
                      sensor_types: List[str] = None) -> List[EncryptedVector]:
        """
        Encrypt multiple vectors efficiently
        """
        if sensor_types is None:
            sensor_types = ["generic"] * len(data_list)
        
        return [
            self.encrypt(data, sensor_type) 
            for data, sensor_type in zip(data_list, sensor_types)
        ]
    
    def batch_decrypt(self, encrypted_vectors: List[EncryptedVector]) -> List[List[float]]:
        """
        Decrypt multiple vectors
        """
        return [self.decrypt(enc) for enc in encrypted_vectors]
    
    def aggregate_encrypted(self, 
                            encrypted_list: List[EncryptedVector]) -> EncryptedVector:
        """
        Aggregate (sum) multiple encrypted vectors
        """
        if len(encrypted_list) == 0:
            raise ValueError("Cannot aggregate empty list")
        
        result = self._load_encrypted(encrypted_list[0])
        for enc in encrypted_list[1:]:
            vec = self._load_encrypted(enc)
            result = result + vec
        
        return self._save_encrypted(result, encrypted_list[0], "aggregate")
    
    # ==================== UTILITY METHODS ====================
    
    def get_info(self) -> dict:
        """Get engine configuration info"""
        return {
            'scheme': 'CKKS',
            'poly_modulus_degree': self.poly_modulus_degree,
            'coeff_mod_bit_sizes': self.coeff_mod_bit_sizes,
            'global_scale': self.global_scale,
            'security_level': '128-bit',
            'created_at': self.created_at,
            'context_hash': self.get_context_hash(),
            'has_secret_key': self.context.is_private()
        }
    
    def verify_encrypted(self, encrypted: EncryptedVector) -> bool:
        """Verify ciphertext integrity"""
        computed = hashlib.sha256(encrypted.ciphertext).hexdigest()[:12]
        return computed == encrypted.checksum
    
    # ==================== ALIAS METHODS (for API compatibility) ====================
    
    def add(self, enc_a: EncryptedVector, enc_b: EncryptedVector) -> EncryptedVector:
        """Alias for add_encrypted"""
        return self.add_encrypted(enc_a, enc_b)
    
    def multiply(self, enc_a: EncryptedVector, enc_b: EncryptedVector) -> EncryptedVector:
        """Alias for multiply_encrypted"""
        return self.multiply_encrypted(enc_a, enc_b)
    
    def encrypted_mean(self, encrypted: EncryptedVector) -> EncryptedVector:
        """Alias for compute_mean"""
        return self.compute_mean(encrypted)


# ==================== DEMO / TEST ====================

def demo():
    """Demonstrate FHE operations"""
    print("=" * 60)
    print("Fully Homomorphic Encryption Demo")
    print("=" * 60)
    
    # Create engine
    engine = FHEEngine()
    print(f"\n✓ Created FHE Engine: {engine.get_info()['context_hash']}")
    
    # Sample sensor data
    temperature = [25.5, 26.1, 25.8, 26.3, 25.9]
    distance = [150.2, 148.7, 151.3, 149.8, 150.5]
    
    print(f"\nOriginal Temperature: {temperature}")
    print(f"Original Distance:    {distance}")
    
    # Encrypt
    enc_temp = engine.encrypt(temperature, "temperature")
    enc_dist = engine.encrypt(distance, "ultrasonic")
    
    print(f"\n🔒 Encrypted Temperature: {enc_temp.get_display_ciphertext(40)}")
    print(f"🔒 Encrypted Distance:    {enc_dist.get_display_ciphertext(40)}")
    
    # Homomorphic operations
    print("\n--- Homomorphic Operations (on encrypted data) ---")
    
    # Add constant
    enc_temp_adjusted = engine.add_plain(enc_temp, 2.0)
    dec_adjusted = engine.decrypt(enc_temp_adjusted)
    print(f"Temperature + 2°C:   {[round(x, 2) for x in dec_adjusted]}")
    
    # Scale
    enc_temp_scaled = engine.multiply_plain(enc_temp, 1.8)
    enc_temp_fahrenheit = engine.add_plain(enc_temp_scaled, 32)
    dec_fahrenheit = engine.decrypt(enc_temp_fahrenheit)
    print(f"Temperature in °F:   {[round(x, 2) for x in dec_fahrenheit]}")
    
    # Mean
    enc_mean = engine.compute_mean(enc_temp)
    dec_mean = engine.decrypt(enc_mean)
    print(f"Mean Temperature:    {round(dec_mean[0], 2)}°C")
    
    # Verify accuracy
    expected_mean = sum(temperature) / len(temperature)
    error = abs(dec_mean[0] - expected_mean)
    print(f"Expected Mean:       {round(expected_mean, 2)}°C")
    print(f"Computation Error:   {error:.2e} (acceptable for CKKS)")
    
    print("\n" + "=" * 60)
    print("Demo Complete - All operations performed on encrypted data!")
    print("=" * 60)


if __name__ == "__main__":
    demo()