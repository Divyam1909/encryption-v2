"""
Demo: Secure Similarity Search
==============================
Demonstrates finding the most similar energy profile to a reference pattern
using encrypted dot product logic.
"""

import numpy as np
from core.fhe_engine import SmartGridFHE
from core.secure_similarity import SecurePatternMatcher
import random

def demo_similarity():
    print("=== Secure Similarity Search Demo ===")
    
    # 1. Setup
    print("[1] Setting up FHE environment...")
    utility = SmartGridFHE()
    public_ctx = utility.get_public_context()
    coordinator = SmartGridFHE.from_context(public_ctx)
    matcher = SecurePatternMatcher(coordinator)
    
    # 2. Generate Data
    # Target Pattern: "Evening Peak" [Low, Low, High, High, Low]
    # Represented as normalized vector
    target_pattern = np.array([0.1, 0.1, 0.8, 0.9, 0.2])
    target_pattern = target_pattern / np.linalg.norm(target_pattern)
    
    print(f"\n[2] Target Pattern (Evening Peak): {np.round(target_pattern, 2)}")
    
    # Generate 5 households with different profiles
    profiles = {}
    
    # House A: Matches target (Evening Peak)
    profiles["House_A (Target Match)"] = np.array([0.1, 0.15, 0.75, 0.85, 0.25])
    
    # House B: Morning Peak
    profiles["House_B (Morning Peak)"] = np.array([0.8, 0.9, 0.2, 0.1, 0.1])
    
    # House C: Flat Usage
    profiles["House_C (Flat)"]         = np.array([0.4, 0.4, 0.4, 0.4, 0.4])
    
    # Normalize all
    for name in profiles:
        profiles[name] = profiles[name] / np.linalg.norm(profiles[name])
    
    # 3. Encrypt Everything
    print("\n[3] Encrypting Profiles and Pattern...")
    enc_profiles = {
        name: coordinator.encrypt_demand(p.tolist(), name) 
        for name, p in profiles.items()
    }
    enc_pattern = coordinator.encrypt_demand(target_pattern.tolist(), "pattern")
    
    # 4. Perform Secure Search
    print("\n[4] Computing Similarity Scores (Encrypted)...")
    # This runs on coordinator without decrypting profiles
    enc_scores = matcher.compute_similarity_scores(enc_profiles, enc_pattern)
    
    # 5. Decrypt Scores to find winner
    print("\n[5] Decrypting Scores (Utility Company)...")
    results = []
    print(f"{'Household':<25} | {'True Cosine':<12} | {'Decrypted Score':<15} | {'Error'}")
    print("-" * 70)
    
    for name, enc_score in enc_scores.items():
        # Decrypt
        dec_score = utility.decrypt_demand(enc_score)[0]
        
        # True value
        true_score = np.dot(profiles[name], target_pattern)
        
        error = abs(dec_score - true_score)
        results.append((name, dec_score))
        
        print(f"{name:<25} | {true_score:<12.4f} | {dec_score:<15.4f} | {error:.2e}")
        
    # Find winner
    results.sort(key=lambda x: x[1], reverse=True)
    winner = results[0][0]
    
    print(f"\nMost Similar Profile: {winner}")
    
    if "House_A" in winner:
        print("✓ SUCCESS: Correctly identified the matching profile matches!")
    else:
        print("✗ FAILURE: Identified wrong profile.")

if __name__ == "__main__":
    demo_similarity()
