"""
Demo: Advanced Encrypted Vector Operations
==========================================
Demonstrates:
1. Encrypted Cross Product (Physics/Geometry)
2. Encrypted Matrix-Vector Multiplication (Linear Transformation)
"""

import numpy as np
from core.fhe_engine import SmartGridFHE
from core.secure_linear_algebra import SecureLinearAlgebra

def demo_cross_product():
    print("\n--- Demo 1: Encrypted Cross Product (Torque Calculation) ---")
    
    # 1. Setup FHE
    utility = SmartGridFHE()
    public_ctx = utility.get_public_context()
    coordinator = SmartGridFHE.from_context(public_ctx)
    algebra = SecureLinearAlgebra(coordinator)
    
    # 2. Data: Position Vector (r) and Force Vector (F)
    # Torque = r x F
    r = [2.0, 5.0, 3.0]  # e.g., meters
    F = [10.0, 0.0, -5.0] # e.g., Newtons
    
    print(f"Position (r): {r}")
    print(f"Force (F):    {F}")
    
    # Explain plaintext result
    # r x F = (5*-5 - 3*0, 3*10 - 2*-5, 2*0 - 5*10)
    #       = (-25, 30 + 10, -50)
    #       = (-25, 40, -50)
    expected = np.cross(r, F)
    print(f"Expected Torque (Plaintext): {expected}")
    
    # 3. Encrypt inputs
    print("Encrypting vectors...")
    enc_r = coordinator.encrypt_demand(r, "position")
    enc_F = coordinator.encrypt_demand(F, "force")
    
    # 4. Compute Encrypted Cross Product
    print("Computing Encrypted Cross Product...")
    enc_torque = algebra.encrypted_cross_product(enc_r, enc_F)
    
    # 5. Decrypt and Verify
    dec_torque = utility.decrypt_demand(enc_torque)
    # Result might be padded, take first 3
    dec_torque = dec_torque[:3]
    
    print(f"Decrypted Torque: {dec_torque}")
    
    # Check error
    error = np.linalg.norm(np.array(dec_torque) - expected)
    print(f"Error Norm: {error:.2e}")
    if error < 1e-3:
        print("✓ SUCCESS: Cross Product computed correctly on encrypted data!")
    else:
        print("✗ FAILURE: Large error.")

def demo_matrix_transform():
    print("\n--- Demo 2: Encrypted Linear Transformation (Matrix-Vector) ---")
    
    # 1. Setup
    utility = SmartGridFHE()
    public_ctx = utility.get_public_context()
    coordinator = SmartGridFHE.from_context(public_ctx)
    algebra = SecureLinearAlgebra(coordinator)
    
    # 2. Data: 3D Point and Rotation Matrix (90 deg around Z)
    v = [1.0, 0.0, 5.0]
    
    # Rotate 90 deg around Z: x->-y, y->x, z->z
    # [ 0 -1  0 ]
    # [ 1  0  0 ]
    # [ 0  0  1 ]
    M = [
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0]
    ]
    
    print(f"Vector v: {v}")
    print("Matrix M (90 deg Z-rotation):")
    for row in M: print(row)
    
    expected = np.dot(M, v)
    print(f"Expected Result (Plaintext): {expected}")
    
    # 3. Encrypt Vector
    print("Encrypting vector...")
    enc_v = coordinator.encrypt_demand(v, "point")
    
    # 4. Apply Plaintext Matrix to Encrypted Vector
    print("Applying Linear Transformation (Diagonal Method)...")
    enc_result = algebra.linear_transform_encrypted(M, enc_v)
    
    # 5. Decrypt
    dec_result = utility.decrypt_demand(enc_result)
    dec_result = dec_result[:3]
    
    print(f"Decrypted Result: {dec_result}")
    
    error = np.linalg.norm(np.array(dec_result) - expected)
    print(f"Error Norm: {error:.2e}")
    if error < 1e-3:
        print("✓ SUCCESS: Matrix-Vector multiplication successful!")
    else:
        print("✗ FAILURE: Large error.")

if __name__ == "__main__":
    print("=== Advanced Encrypted Vector Algebra Demo ===")
    demo_cross_product()
    demo_matrix_transform()
