
import tenseal as ts
import numpy as np

def inspect():
    ctx = ts.context(ts.SCHEME_TYPE.CKKS, poly_modulus_degree=8192, coeff_mod_bit_sizes=[60, 40, 40, 60])
    ctx.generate_galois_keys()
    ctx.global_scale = 2**40
    
    vec = ts.ckks_vector(ctx, [1, 2, 3])
    methods = [d for d in dir(vec) if not d.startswith('_')]
    print("Methods with 'rot' or 'roll':")
    print([m for m in methods if 'rot' in m or 'roll' in m])
    print("All methods:")
    print(methods)

if __name__ == "__main__":
    inspect()
