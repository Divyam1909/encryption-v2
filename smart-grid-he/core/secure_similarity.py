"""
Secure Similarity Search
========================
Find most similar encrypted vector to a target pattern.

Demonstrates:
- Encrypted Dot Product
- Pattern Matching on Encrypted Data
"""

import tenseal as ts
import numpy as np
from typing import List, Tuple, Dict
from core.fhe_engine import SmartGridFHE, EncryptedDemand

class SecurePatternMatcher:
    def __init__(self, fhe_engine: SmartGridFHE):
        self.fhe = fhe_engine

    def compute_similarity_scores(self, 
                                encrypted_profiles: Dict[str, EncryptedDemand], 
                                encrypted_pattern: EncryptedDemand) -> Dict[str, EncryptedDemand]:
        """
        Compute similarity scores (dot products) between many profiles and a pattern.
        """
        scores = {}
        for agent_id, enc_profile in encrypted_profiles.items():
            # Compute dot product: E(profile) . E(pattern)
            score = self.fhe.compute_dot_product(enc_profile, encrypted_pattern)
            scores[agent_id] = score
            
        return scores
        
    def find_top_matches(self, 
                       encrypted_profiles: Dict[str, EncryptedDemand],
                       encrypted_pattern: EncryptedDemand,
                       utility_engine: SmartGridFHE,
                       top_k: int = 1) -> List[Tuple[str, float]]:
        """
        Find top k matches.
        
        Note: Sorting requires decryption of the scores.
        The profiles themselves remain encrypted. 
        Only the similarity score is revealed.
        """
        # 1. Compute encrypted scores
        enc_scores = self.compute_similarity_scores(encrypted_profiles, encrypted_pattern)
        
        # 2. Decrypt scores (simulating utility company action)
        decrypted_scores = []
        for agent_id, enc_score in enc_scores.items():
            # Decrypt returns list, dot product is scalar (size 1 relevant)
            score_val = utility_engine.decrypt_demand(enc_score)[0]
            decrypted_scores.append((agent_id, score_val))
            
        # 3. Sort and pick top k
        # Sort descending (higher dot product = more similar, assuming normalized vectors)
        decrypted_scores.sort(key=lambda x: x[1], reverse=True)
        
        return decrypted_scores[:top_k]
