"""
Secure Linear Algebra Operations
================================
Implements advanced vector operations on encrypted data.

Contributions:
1. Encrypted Cross Product (3D)
2. Encrypted Matrix-Vector Multiplication
"""

import tenseal as ts
import numpy as np
from typing import List, Union, Tuple
from core.fhe_engine import SmartGridFHE, EncryptedDemand

class SecureLinearAlgebra:
    def __init__(self, fhe_engine: SmartGridFHE):
        self.fhe = fhe_engine

    def encrypted_cross_product(self, 
                              enc_vec_a: EncryptedDemand, 
                              enc_vec_b: EncryptedDemand) -> EncryptedDemand:
        """
        Compute Cross Product of two encrypted 3D vectors.
        Ex B = (a2b3 - a3b2, a3b1 - a1b3, a1b2 - a2b1)
        
        Uses cyclic rotations (SIMD operations) to compute this efficiently 
        without extracting components.
        
        Requires vectors to be of size 3 (or padded).
        """
        # Step 1: Rotations
        a_rot1 = self.fhe.rotate_encrypted(enc_vec_a, 1)
        a_rot2 = self.fhe.rotate_encrypted(enc_vec_a, 2)
        
        b_rot1 = self.fhe.rotate_encrypted(enc_vec_b, 1)
        b_rot2 = self.fhe.rotate_encrypted(enc_vec_b, 2)
        
        # Step 2: Multiplications
        p1 = self.fhe.compute_elementwise_product(a_rot1, b_rot2)
        p2 = self.fhe.compute_elementwise_product(a_rot2, b_rot1)
        
        # Step 3: Subtraction
        # enc_a - enc_b is not directly exposed. Multiply by -1 and add.
        p2_neg = self.fhe.multiply_plain(p2, -1.0)
        result = self.fhe.add_encrypted(p1, p2_neg)
        
        return result
        
    def linear_transform_encrypted(self,
                                 plain_matrix: List[List[float]],
                                 enc_vector: EncryptedDemand) -> EncryptedDemand:
        """
        Apply plaintext linear transformation matrix to encrypted vector.
        v_out = M * v_in
        
        Since TenSEAL vectors are row vectors, we compute v * M.T
        which is equivalent to (M * v.T).T
        """
        vec = self.fhe._load_encrypted(enc_vector)
        
        # Transpose matrix for correct multiplication orientation
        # plain_matrix is list of lists
        matrix_T = np.array(plain_matrix).T.tolist()
        
        # Perform multiplication
        result = vec.matmul(matrix_T)
        
        enc_result = self.fhe._save_encrypted(result, enc_vector, "linear_transform")
        return enc_result
