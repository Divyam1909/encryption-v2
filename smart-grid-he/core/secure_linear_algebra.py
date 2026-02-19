"""
Secure Linear Algebra Operations
================================
Implements advanced vector operations on encrypted data.

Contributions:
1. Encrypted Cross Product (3D)
2. Encrypted Matrix-Vector Multiplication (plaintext matrix × encrypted vector)
3. Fully Homomorphic Matrix-Vector Multiplication (encrypted matrix × encrypted vector)
"""

import tenseal as ts
import numpy as np
from typing import List, Union, Tuple, Callable, Optional
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
        
        NOTE: This only works for square matrices due to TenSEAL's matmul constraints.
        For non-square matrices, use fully_homomorphic_matrix_vector_multiply.
        """
        vec = self.fhe._load_encrypted(enc_vector)
        
        # Transpose matrix for correct multiplication orientation
        # plain_matrix is list of lists
        matrix_T = np.array(plain_matrix).T.tolist()
        
        # Perform multiplication
        result = vec.matmul(matrix_T)
        
        enc_result = self.fhe._save_encrypted(result, enc_vector, "linear_transform")
        return enc_result
    
    def fully_homomorphic_matrix_vector_multiply(self,
                                                  enc_matrix_rows: List[EncryptedDemand],
                                                  enc_vector: EncryptedDemand,
                                                  rows: int,
                                                  cols: int,
                                                  log_callback: Optional[Callable] = None) -> List[EncryptedDemand]:
        """
        FULLY HOMOMORPHIC Matrix-Vector Multiplication.
        
        Both the matrix AND the vector are encrypted!
        
        Computes: result[i] = sum(M[i][j] * v[j]) for each row i
        
        This is TRUE fully homomorphic encryption where:
        - Matrix rows are encrypted as separate ciphertexts
        - Vector is encrypted as a single ciphertext
        - All computation happens on encrypted data
        - Only the final result is decrypted
        
        Args:
            enc_matrix_rows: List of EncryptedDemand, one per row of the matrix
            enc_vector: Encrypted input vector
            rows: Number of rows in matrix
            cols: Number of columns in matrix (must match vector size)
            log_callback: Optional callback for logging steps
            
        Returns:
            List of EncryptedDemand, one per output element (encrypted dot products)
        """
        result_encrypted = []
        step = 1
        
        for i in range(rows):
            if log_callback:
                log_callback(f"Step {step}: Computing E(row_{i+1}) · E(v) [encrypted dot product]")
            
            # Get encrypted row
            enc_row = enc_matrix_rows[i]
            
            # Compute encrypted dot product: E(row) * E(vector) element-wise, then sum
            # This is E(row[0]*v[0], row[1]*v[1], ...) then sum to get E(row · v)
            enc_product = self.fhe.compute_dot_product(enc_row, enc_vector)
            
            result_encrypted.append(enc_product)
            
            if log_callback:
                log_callback(f"        E(M[{i+1},:]) × E(v) → E(result[{i+1}])")
            
            step += 1
        
        if log_callback:
            log_callback(f"Step {step}: All {rows} encrypted dot products computed")
        
        return result_encrypted
    
    def plaintext_matrix_encrypted_vector_multiply(self,
                                                    plain_matrix: List[List[float]],
                                                    enc_vector: EncryptedDemand,
                                                    rows: int,
                                                    cols: int,
                                                    log_callback: Optional[Callable] = None) -> List[EncryptedDemand]:
        """
        Matrix-Vector multiplication with plaintext matrix and encrypted vector.
        
        Computes: result[i] = sum(M[i][j] * v[j]) for each row i
        
        This works for ANY matrix shape (not just square).
        
        Args:
            plain_matrix: Plaintext matrix as list of lists
            enc_vector: Encrypted input vector
            rows: Number of rows
            cols: Number of columns
            log_callback: Optional logging callback
            
        Returns:
            List of EncryptedDemand, one per output element
        """
        result_encrypted = []
        step = 1
        
        # Load encrypted vector once
        vec = self.fhe._load_encrypted(enc_vector)
        
        for i in range(rows):
            if log_callback:
                log_callback(f"Step {step}: Computing row_{i+1} · E(v)")
            
            row = plain_matrix[i]
            
            # Element-wise multiply: E(v) * row (plaintext)
            # This gives E([v[0]*row[0], v[1]*row[1], ...])
            row_product = vec * row
            
            if log_callback:
                log_callback(f"        E(v) × {[f'{x:.2f}' for x in row]} = E(element-wise product)")
            
            # Sum all elements to get dot product: E(sum(v[j] * row[j]))
            dot_product = row_product.sum()
            
            if log_callback:
                log_callback(f"        sum(E(v × row)) = E(row_{i+1} · v)")
            
            # Wrap in EncryptedDemand
            enc_result = self.fhe._save_encrypted(dot_product, enc_vector, f"dot_product_row_{i}")
            result_encrypted.append(enc_result)
            
            step += 1
        
        if log_callback:
            log_callback(f"Step {step}: All {rows} dot products computed homomorphically")
        
        return result_encrypted
