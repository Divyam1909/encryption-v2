"""
Remove reversed Appendix A and re-insert in correct order.
Key fix: addprevious() WITHOUT reversed() gives correct order.
"""
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BACKUP = r"c:\Users\divya\Desktop\encryption-iit-dharwad\project-report\SmartGridHE_MiniProject_Report_Final_v2_BACKUP.docx"

CODE_A1 = [
"# core/fhe_engine.py  -  CKKS Homomorphic Encryption Engine",
"import tenseal as ts, hashlib",
"from datetime import datetime",
"",
"class SmartGridFHE:",
"    def __init__(self, poly_modulus_degree=16384,",
"                 coeff_mod_bit_sizes=None, global_scale=2**40):",
"        if coeff_mod_bit_sizes is None:",
"            coeff_mod_bit_sizes = [60, 40, 40, 40, 60]",
"        self.context = ts.context(",
"            ts.SCHEME_TYPE.CKKS,",
"            poly_modulus_degree=poly_modulus_degree,",
"            coeff_mod_bit_sizes=coeff_mod_bit_sizes",
"        )",
"        self.context.generate_galois_keys()   # rotation support",
"        self.context.generate_relin_keys()    # relinearisation after mult",
"        self.context.global_scale    = global_scale",
"        self.context.auto_rescale    = True",
"        self.context.auto_relin      = True",
"        self.context.auto_mod_switch = True",
"        self._op_count = 0",
"",
"    def get_public_context(self) -> bytes:",
"        ctx = self.context.copy()",
"        ctx.make_context_public()        # strips secret key",
"        return ctx.serialize()           # coordinator gets this; cannot decrypt",
"",
"    def encrypt_demand(self, demand_kw, agent_id):",
"        values = [float(demand_kw)] if isinstance(demand_kw, (int, float)) \\",
"                 else [float(v) for v in demand_kw]",
"        enc = ts.ckks_vector(self.context, values)",
"        ct  = enc.serialize()",
"        return EncryptedDemand(ct, datetime.now().isoformat(),",
"                               agent_id, len(values),",
"                               hashlib.sha256(ct).hexdigest()[:12])",
"",
"    def aggregate_demands(self, enc_list):",
"        result = ts.ckks_vector_from(self.context, enc_list[0].ciphertext)",
"        for e in enc_list[1:]:",
"            result = result + ts.ckks_vector_from(self.context, e.ciphertext)",
"        ct = result.serialize()",
"        return EncryptedDemand(ct, datetime.now().isoformat(), 'aggregated',",
"                               enc_list[0].vector_size,",
"                               hashlib.sha256(ct).hexdigest()[:12])",
"",
"    def compute_average(self, enc_total, count):",
"        vec = ts.ckks_vector_from(self.context, enc_total.ciphertext)",
"        ct  = (vec * (1.0 / count)).serialize()",
"        return EncryptedDemand(ct, datetime.now().isoformat(), 'average',",
"                               enc_total.vector_size,",
"                               hashlib.sha256(ct).hexdigest()[:12])",
"",
"    def decrypt_demand(self, enc) -> list:",
"        if not self.context.is_private():",
"            raise ValueError('No secret key - only Utility Company can decrypt')",
"        vec = ts.ckks_vector_from(self.context, enc.ciphertext)",
"        return vec.decrypt()[:enc.vector_size]",
]

CODE_A2 = [
"# core/polynomial_comparator.py  -  Novel Contribution #1: ALT",
"# Adaptive Linear Threshold: approximate comparison, zero ct*ct multiplications",
"import tenseal as ts, hashlib",
"from datetime import datetime",
"",
"class EncryptedThresholdDetector:",
"    ZONE_BELOW, ZONE_ABOVE = 0.3, 0.7",
"",
"    def __init__(self, fhe_engine, default_sensitivity=7.0):",
"        self.fhe = fhe_engine",
"        self.k   = default_sensitivity",
"",
"    def detect_threshold_encrypted(self, enc_value, threshold,",
"                                   sensitivity=None):",
"        k         = sensitivity if sensitivity is not None else self.k",
"        delta     = threshold / k            # soft-zone half-width",
"        slope     = 0.5 / delta              # = 0.5k / T",
"        intercept = 0.5 - threshold * slope  # = 0.5 - 0.5k",
"",
"        # Only multiply_plain + add_plain needed (multiplicative depth = 0)",
"        # E(score) = E(x) * slope + intercept",
"        vec    = ts.ckks_vector_from(self.fhe.context, enc_value.ciphertext)",
"        scored = vec * slope + intercept",
"        ct     = scored.serialize()",
"",
"        return EncryptedDemand(",
"            ct, datetime.now().isoformat(),",
"            f'alt_{enc_value.agent_id}', enc_value.vector_size,",
"            hashlib.sha256(ct).hexdigest()[:12],",
"            metadata={'method':'ALT','threshold':threshold,'k':k,'delta':delta}",
"        )",
"",
"    @staticmethod",
"    def interpret_score(score, threshold=None):",
"        s = max(0.0, min(1.0, score))",
"        if   s < 0.3: return 'below',     1.0 - s / 0.3",
"        elif s > 0.7: return 'above',     (s - 0.7) / 0.3",
"        else:         return 'uncertain', abs(s - 0.5) / 0.2",
]

CODE_A3 = [
"# core/verifiable_aggregation.py  -  Novel Contribution #2: Pedersen ACV",
"# Additive Commitment Verification: detects malicious coordinator",
"import hashlib, secrets",
"",
"# RFC 3526 MODP Group 14 (2048-bit prime) - truncated for readability",
"PRIME = int('FFFFFFFF...FFFFFFFF', 16)   # full constant in source file",
"G     = 2",
"SCALE = 1_000_000   # float -> integer (6 decimal places)",
"H     = pow(G, int.from_bytes(",
"            hashlib.sha256(",
"            b'SmartGridHE_Pedersen_Commitment_Generator_H_v1'",
"            ).digest(), 'big'), PRIME)",
"",
"class PedersenCommitmentScheme:",
"    def __init__(self, prime=PRIME, g=G, h=H, scale=SCALE):",
"        self.p, self.g, self.h = prime, g, h",
"        self.scale = scale",
"        self.order = prime - 1",
"",
"    def commit(self, value: float) -> tuple:",
"        # Returns (C_public -> coordinator,  r_secret -> utility via secure ch)",
"        # C = g^m * h^r mod p  (perfectly hiding, computationally binding)",
"        m = int(value * self.scale)",
"        r = secrets.randbelow(self.order)",
"        C = (pow(self.g, m % self.order, self.p) *",
"             pow(self.h, r % self.order, self.p)) % self.p",
"        return C, r",
"",
"    def aggregate(self, commitments: list) -> int:",
"        # C_agg = prod(C_i) mod p = g^(sum_m) * h^(sum_r) mod p",
"        agg = 1",
"        for C in commitments:",
"            agg = (agg * C) % self.p",
"        return agg",
"",
"    def verify(self, claimed_sum: float, C_agg: int, r_total: int) -> bool:",
"        # Utility checks: C_agg == g^(sum*scale) * h^(sum_r) mod p",
"        m        = int(claimed_sum * self.scale)",
"        expected = (pow(self.g, m % self.order, self.p) *",
"                    pow(self.h, r_total % self.order, self.p)) % self.p",
"        return expected == C_agg   # True: honest | False: coordinator CHEATED",
]

# ── XML helpers ───────────────────────────────────────────────────────────────

def rpr(bold=False, font="Calibri", size=11, color=None):
    el = OxmlElement('w:rPr')
    if bold:
        el.append(OxmlElement('w:b'))
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), font); rf.set(qn('w:hAnsi'), font)
    el.append(rf)
    for tag in ('w:sz', 'w:szCs'):
        s = OxmlElement(tag); s.set(qn('w:val'), str(size*2)); el.append(s)
    if color:
        c = OxmlElement('w:color'); c.set(qn('w:val'), color); el.append(c)
    return el

def ppr_el(align="left", before=0, after=80, line=240, rule="auto"):
    el = OxmlElement('w:pPr')
    jc = OxmlElement('w:jc'); jc.set(qn('w:val'), align); el.append(jc)
    sp = OxmlElement('w:spacing')
    sp.set(qn('w:before'), str(before)); sp.set(qn('w:after'), str(after))
    sp.set(qn('w:line'), str(line)); sp.set(qn('w:lineRule'), rule)
    el.append(sp)
    return el

def para(text, bold=False, font="Calibri", size=11, align="left",
         before=0, after=80, color=None):
    p = OxmlElement('w:p')
    p.append(ppr_el(align, before, after))
    if text:
        r = OxmlElement('w:r')
        r.append(rpr(bold, font, size, color))
        t = OxmlElement('w:t')
        t.text = text
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t); p.append(r)
    return p

def code_line(text):
    p = OxmlElement('w:p')
    p.append(ppr_el("left", before=0, after=0, line=160, rule="exact"))
    r = OxmlElement('w:r')
    r.append(rpr(False, "Courier New", 8, color="1F3864"))
    t = OxmlElement('w:t')
    t.text = text if text.strip() else " "
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t); p.append(r)
    return p

def page_break():
    p = OxmlElement('w:p')
    r = OxmlElement('w:r')
    br = OxmlElement('w:br'); br.set(qn('w:type'), 'page')
    r.append(br); p.append(r)
    return p

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    doc = Document(BACKUP)
    body = doc.element.body

    # 1. Find Agnel paragraph
    agnel_elem = None
    for p in body.findall(qn('w:p')):
        if 'Agnel' in ''.join(t.text for t in p.findall('.//' + qn('w:t')) if t.text):
            agnel_elem = p; break

    if agnel_elem is None:
        print("ERROR: Agnel not found"); return

    # 2. Remove existing bad Appendix A (walk backwards from agnel to References)
    removed = 0
    cursor = agnel_elem.getprevious()
    while cursor is not None:
        txt = ''.join(t.text for t in cursor.findall('.//' + qn('w:t')) if t.text)
        if '[22]' in txt or '[21]' in txt or '[20]' in txt:
            break
        prev = cursor.getprevious()
        cursor.getparent().remove(cursor)
        removed += 1
        cursor = prev
    print(f"Removed {removed} paragraphs")

    # 3. Build elements list in correct display order
    elements = []
    elements.append(page_break())
    elements.append(para("APPENDIX A: CODE SAMPLES",
                         bold=True, size=14, align="center",
                         before=120, after=120))
    elements.append(para(
        "This appendix presents condensed implementations of the three core "
        "modules of SmartGridHE. Full source is available in smart-grid-he/core/.",
        size=10, align="both", before=0, after=80))

    elements.append(para("A.1  FHE Engine  (core/fhe_engine.py)",
                         bold=True, size=11, before=100, after=60))
    for line in CODE_A1:
        elements.append(code_line(line))
    elements.append(para("", size=6, before=0, after=0))

    elements.append(para(
        "A.2  Novel Contribution #1 - Adaptive Linear Threshold  "
        "(core/polynomial_comparator.py)",
        bold=True, size=11, before=100, after=60))
    for line in CODE_A2:
        elements.append(code_line(line))
    elements.append(para("", size=6, before=0, after=0))

    elements.append(para(
        "A.3  Novel Contribution #2 - Pedersen Commitment ACV  "
        "(core/verifiable_aggregation.py)",
        bold=True, size=11, before=100, after=60))
    for line in CODE_A3:
        elements.append(code_line(line))
    elements.append(para("", size=6, before=0, after=0))

    print(f"Elements to insert: {len(elements)}")

    # 4. Insert WITHOUT reversed() — addprevious() in forward order gives correct order
    #    Proof: addprevious(e0) -> [..., e0, agnel]
    #           addprevious(e1) -> [..., e0, e1, agnel]
    #           ...
    #    Result: e0, e1, ..., eN, agnel  ✓
    for elem in elements:
        agnel_elem.addprevious(elem)

    doc.save(BACKUP)
    print("Saved.")

    # 5. Verify
    doc2 = Document(BACKUP)
    body2 = doc2.element.body
    paras = body2.findall(qn('w:p'))
    hits = {}
    for i, p in enumerate(paras):
        txt = ''.join(t.text for t in p.findall('.//' + qn('w:t')) if t.text)
        for key in ['APPENDIX A: CODE SAMPLES', 'A.1  FHE Engine',
                    'A.2  Novel Contribution', 'A.3  Novel Contribution',
                    'Agnel']:
            if key in txt and key not in hits:
                hits[key] = i
    for k, v in sorted(hits.items(), key=lambda x: x[1]):
        print(f"  [{v:3d}] {k[:60]}")
    print(f"Total paragraphs: {len(paras)}")

if __name__ == "__main__":
    main()
