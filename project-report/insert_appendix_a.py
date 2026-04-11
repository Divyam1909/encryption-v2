"""
Insert Appendix A: Code Samples into the BACKUP docx.
This script is saved to a file to avoid bash heredoc triple-quote conflicts.
"""
import sys
import os
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from lxml import etree

BACKUP = r"c:\Users\divya\Desktop\encryption-iit-dharwad\project-report\SmartGridHE_MiniProject_Report_Final_v2_BACKUP.docx"

# ─────────────────────────────────────────────────────────────────────────────
# Code block strings  (triple-quoted strings are fine inside a saved .py file)
# ─────────────────────────────────────────────────────────────────────────────

CODE_A1 = """\
# fhe_engine.py  –  CKKS Homomorphic Encryption Engine
import tenseal as ts, hashlib, base64
from datetime import datetime

class SmartGridFHE:
    def __init__(self, poly_modulus_degree=16384,
                 coeff_mod_bit_sizes=None, global_scale=2**40):
        if coeff_mod_bit_sizes is None:
            coeff_mod_bit_sizes = [60, 40, 40, 40, 60]
        self.context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=poly_modulus_degree,
            coeff_mod_bit_sizes=coeff_mod_bit_sizes
        )
        self.context.generate_galois_keys()
        self.context.generate_relin_keys()
        self.context.global_scale = global_scale
        self.context.auto_rescale = True
        self.context.auto_relin   = True
        self.context.auto_mod_switch = True
        self._op_count = 0

    def get_public_context(self):
        ctx = self.context.copy()
        ctx.make_context_public()
        return ctx.serialize()          # Coordinator gets this (cannot decrypt)

    def encrypt_demand(self, demand_kw, agent_id):
        values = [float(demand_kw)] if isinstance(demand_kw, (int,float)) \
                 else [float(v) for v in demand_kw]
        enc = ts.ckks_vector(self.context, values)
        ct  = enc.serialize()
        return EncryptedDemand(ct, datetime.now().isoformat(), agent_id,
                               len(values), hashlib.sha256(ct).hexdigest()[:12])

    def aggregate_demands(self, enc_list):
        result = ts.ckks_vector_from(self.context, enc_list[0].ciphertext)
        for e in enc_list[1:]:
            result = result + ts.ckks_vector_from(self.context, e.ciphertext)
        ct = result.serialize()
        return EncryptedDemand(ct, datetime.now().isoformat(), "aggregated",
                               enc_list[0].vector_size,
                               hashlib.sha256(ct).hexdigest()[:12])

    def compute_average(self, enc_total, count):
        vec = ts.ckks_vector_from(self.context, enc_total.ciphertext)
        ct  = (vec * (1.0 / count)).serialize()
        return EncryptedDemand(ct, datetime.now().isoformat(), "average",
                               enc_total.vector_size,
                               hashlib.sha256(ct).hexdigest()[:12])

    def decrypt_demand(self, enc):
        if not self.context.is_private():
            raise ValueError("No secret key – only utility can decrypt")
        vec = ts.ckks_vector_from(self.context, enc.ciphertext)
        return vec.decrypt()[:enc.vector_size]\
"""

CODE_A2 = """\
# polynomial_comparator.py  –  Novel Contribution #1: ALT
# Adaptive Linear Threshold (ALT) – zero ciphertext multiplication
import tenseal as ts, hashlib
from datetime import datetime

class EncryptedThresholdDetector:
    ZONE_BELOW = 0.3
    ZONE_ABOVE = 0.7

    def __init__(self, fhe_engine, default_sensitivity=7.0):
        self.fhe = fhe_engine
        self.k   = default_sensitivity

    def detect_threshold_encrypted(self, enc_value, threshold,
                                   expected_range=(0,200), sensitivity=None):
        k = sensitivity if sensitivity is not None else self.k
        delta     = threshold / k            # soft-zone half-width
        slope     = 0.5 / delta              # = 0.5k / T
        intercept = 0.5 - threshold * slope  # = 0.5 - 0.5k

        # E(score) = E(x) * slope + intercept   [depth-0, no ct*ct mult]
        vec = ts.ckks_vector_from(self.fhe.context, enc_value.ciphertext)
        scored = vec * slope + intercept

        ct = scored.serialize()
        return EncryptedDemand(
            ct, datetime.now().isoformat(),
            f"alt_{enc_value.agent_id}", enc_value.vector_size,
            hashlib.sha256(ct).hexdigest()[:12],
            metadata={'method':'ALT','threshold':threshold,'k':k,'delta':delta}
        )

    @staticmethod
    def interpret_score(score, threshold=None):
        s = max(0.0, min(1.0, score))
        if s < 0.3:
            zone, conf = 'below',   1.0 - s/0.3
        elif s > 0.7:
            zone, conf = 'above',   (s-0.7)/0.3
        else:
            zone, conf = 'uncertain', abs(s-0.5)/0.2
        return zone, min(1.0, max(0.0, conf))\
"""

CODE_A3 = """\
# verifiable_aggregation.py  –  Novel Contribution #2: Pedersen ACV
# Additive Commitment Verification – detects malicious coordinator
import hashlib, secrets

PRIME = int("FFFFFFFF...FFFFFFFF", 16)   # RFC 3526 MODP-14 (2048-bit)
G, SCALE = 2, 1_000_000
H = pow(G, int.from_bytes(
    hashlib.sha256(b"SmartGridHE_Pedersen_Commitment_Generator_H_v1").digest(),
    'big'), PRIME)

class PedersenCommitmentScheme:
    def __init__(self, prime=PRIME, g=G, h=H, scale=SCALE):
        self.p, self.g, self.h = prime, g, h
        self.scale  = scale
        self.order  = prime - 1

    def commit(self, value, r=None):
        m = int(value * self.scale)
        r = r if r else secrets.randbelow(self.order)
        C = (pow(self.g, m % self.order, self.p) *
             pow(self.h, r % self.order, self.p)) % self.p
        return C, r          # C = g^m * h^r mod p

    def aggregate(self, commitments):
        agg = 1
        for C in commitments:
            agg = (agg * C) % self.p
        return agg           # Product = C(sum_m ; sum_r)

    def verify(self, claimed_sum, C_agg, r_total):
        m = int(claimed_sum * self.scale)
        expected = (pow(self.g, m % self.order, self.p) *
                    pow(self.h, r_total % self.order, self.p)) % self.p
        return expected == C_agg   # True  => coordinator honest
                                   # False => coordinator CHEATED\
"""

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions to build OOXML elements
# ─────────────────────────────────────────────────────────────────────────────

def make_rpr(bold=False, italic=False, font_name="Calibri", font_size_pt=11,
             color=None):
    rpr = OxmlElement('w:rPr')
    if bold:
        b = OxmlElement('w:b'); rpr.append(b)
    if italic:
        i = OxmlElement('w:i'); rpr.append(i)
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rpr.append(rFonts)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(font_size_pt * 2))
    rpr.append(sz)
    szCs = OxmlElement('w:szCs')
    szCs.set(qn('w:val'), str(font_size_pt * 2))
    rpr.append(szCs)
    if color:
        col = OxmlElement('w:color')
        col.set(qn('w:val'), color)
        rpr.append(col)
    return rpr


def make_ppr(align="left", space_before=0, space_after=0, line_rule="auto",
             line_val=240):
    ppr = OxmlElement('w:pPr')
    jc = OxmlElement('w:jc')
    jc.set(qn('w:val'), align)
    ppr.append(jc)
    spc = OxmlElement('w:spacing')
    spc.set(qn('w:before'), str(space_before))
    spc.set(qn('w:after'), str(space_after))
    spc.set(qn('w:line'), str(line_val))
    spc.set(qn('w:lineRule'), line_rule)
    ppr.append(spc)
    return ppr


def make_para(text, bold=False, italic=False, font="Calibri", size=11,
              align="left", space_before=0, space_after=80,
              color=None):
    p = OxmlElement('w:p')
    ppr = make_ppr(align, space_before, space_after)
    p.append(ppr)
    if text:
        r = OxmlElement('w:r')
        r.append(make_rpr(bold, italic, font, size, color))
        t = OxmlElement('w:t')
        t.text = text
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t)
        p.append(r)
    return p


def make_code_line(text, size=8):
    p = OxmlElement('w:p')
    ppr = make_ppr("left", space_before=0, space_after=0,
                   line_rule="exact", line_val=165)
    # Set shading (light grey background)
    pBdr = OxmlElement('w:pBdr')
    ppr.append(pBdr)
    p.append(ppr)
    r = OxmlElement('w:r')
    rpr = make_rpr(False, False, "Courier New", size, color="1F3864")
    r.append(rpr)
    t = OxmlElement('w:t')
    t.text = text if text else " "
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t)
    p.append(r)
    return p


def make_page_break():
    p = OxmlElement('w:p')
    r = OxmlElement('w:r')
    br = OxmlElement('w:br')
    br.set(qn('w:type'), 'page')
    r.append(br)
    p.append(r)
    return p


def make_blank(size=6):
    return make_para("", size=size, space_before=0, space_after=0)


# ─────────────────────────────────────────────────────────────────────────────
# Main insertion
# ─────────────────────────────────────────────────────────────────────────────

def main():
    doc = Document(BACKUP)
    body = doc.element.body

    # ---- 1.  Find the "Agnel Charities" paragraph (anchor for insertion) ----
    agnel_elem = None
    for p in body.findall(qn('w:p')):
        texts = [t.text for t in p.findall('.//' + qn('w:t')) if t.text]
        combined = ''.join(texts)
        if 'Agnel' in combined or 'agnel' in combined.lower():
            agnel_elem = p
            break

    if agnel_elem is None:
        print("ERROR: Could not find 'Agnel Charities' paragraph!")
        sys.exit(1)
    else:
        print(f"Found anchor paragraph: {''.join(t.text for t in agnel_elem.findall('.//' + qn('w:t')) if t.text)[:60]}")

    # ---- 2.  Check if Appendix A heading already exists ----
    for p in body.findall(qn('w:p')):
        texts = [t.text for t in p.findall('.//' + qn('w:t')) if t.text]
        if 'APPENDIX A' in ''.join(texts).upper():
            print("WARNING: Appendix A already seems inserted. Aborting.")
            sys.exit(0)

    # ---- 3.  Build all elements in correct insertion order ----
    elements = []

    # Page break to start Appendix A on new page
    elements.append(make_page_break())

    # Main heading
    elements.append(make_para(
        "APPENDIX A: CODE SAMPLES",
        bold=True, size=14, align="center",
        space_before=120, space_after=120
    ))

    # Intro paragraph
    elements.append(make_para(
        "This appendix presents condensed implementations of the three core modules "
        "of SmartGridHE: the CKKS-based FHE Engine, the Adaptive Linear Threshold (ALT) "
        "comparator, and the Pedersen Commitment verifiable aggregator. "
        "Full source is available at smart-grid-he/core/.",
        size=10, align="both", space_before=0, space_after=80
    ))

    # ── A.1 ──────────────────────────────────────────────────────────────────
    elements.append(make_para(
        "A.1  FHE Engine  (core/fhe_engine.py)",
        bold=True, size=11, align="left", space_before=100, space_after=60
    ))

    for line in CODE_A1.splitlines():
        elements.append(make_code_line(line))

    elements.append(make_blank())

    # ── A.2 ──────────────────────────────────────────────────────────────────
    elements.append(make_para(
        "A.2  Novel Contribution #1 – Adaptive Linear Threshold  (core/polynomial_comparator.py)",
        bold=True, size=11, align="left", space_before=100, space_after=60
    ))

    for line in CODE_A2.splitlines():
        elements.append(make_code_line(line))

    elements.append(make_blank())

    # ── A.3 ──────────────────────────────────────────────────────────────────
    elements.append(make_para(
        "A.3  Novel Contribution #2 – Pedersen Commitment ACV  (core/verifiable_aggregation.py)",
        bold=True, size=11, align="left", space_before=100, space_after=60
    ))

    for line in CODE_A3.splitlines():
        elements.append(make_code_line(line))

    elements.append(make_blank())

    print(f"Total elements to insert: {len(elements)}")

    # ---- 4.  Insert elements before agnel_elem (reversed so final order is correct) ----
    for elem in reversed(elements):
        agnel_elem.addprevious(elem)

    # ---- 5.  Save ----
    doc.save(BACKUP)
    print(f"Saved: {BACKUP}")

    # ---- 6.  Quick verification ----
    doc2 = Document(BACKUP)
    body2 = doc2.element.body
    found = False
    for p in body2.findall(qn('w:p')):
        texts = ''.join(t.text for t in p.findall('.//' + qn('w:t')) if t.text)
        if 'APPENDIX A' in texts.upper():
            found = True
            break
    print("Verification – Appendix A heading found:", found)


if __name__ == "__main__":
    main()
