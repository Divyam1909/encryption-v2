import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(18, 8))
ax.set_xlim(0, 18)
ax.set_ylim(0, 8)
ax.axis('off')
fig.patch.set_facecolor('white')

BH = 0.58


def box(x, y, w, h, text, fc, ec='#555', fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle='round,pad=0.1', facecolor=fc, edgecolor=ec, lw=1.3, zorder=2))
    ax.text(x+w/2, y+h/2, text, ha='center', va='center',
        fontsize=fs, fontweight='bold' if bold else 'normal',
        multialignment='center', zorder=3)


def harrow(x1, y, x2, col, lw=1.4):
    """Horizontal arrow from (x1,y) to (x2,y)"""
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
        arrowprops=dict(arrowstyle='-|>', color=col, lw=lw,
            mutation_scale=13, shrinkA=0, shrinkB=0), zorder=5)


def varrow(x, y1, y2, col, lw=1.4):
    """Vertical arrow from (x,y1) to (x,y2)"""
    ax.annotate('', xy=(x, y2), xytext=(x, y1),
        arrowprops=dict(arrowstyle='-|>', color=col, lw=lw,
            mutation_scale=13, shrinkA=0, shrinkB=0), zorder=5)


def darrow(x1, y1, x2, y2, col, lw=1.4):
    """Diagonal arrow from (x1,y1) to (x2,y2)"""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle='-|>', color=col, lw=lw,
            mutation_scale=13, shrinkA=0, shrinkB=0), zorder=5)


def mul_node(x, y, r=0.21):
    ax.add_patch(plt.Circle((x, y), r, color='#f5f5f5', ec='#444', lw=1.4, zorder=4))
    ax.text(x, y, 'x', ha='center', va='center', fontsize=11, fontweight='bold', zorder=5)


# ═══════════════════════════════════════════════════════════════
# LEFT PANEL — Encrypted Matrix-Vector Multiplication
# ═══════════════════════════════════════════════════════════════
ax.text(3.6, 7.7, 'Encrypted Matrix-Vector Multiplication',
        ha='center', fontsize=10, fontweight='bold')
ax.text(3.6, 7.38,
        '[core/secure_linear_algebra.py: fully_homomorphic_matrix_vector_multiply()]',
        ha='center', fontsize=7, color='#555')

# --- Geometry (tweak these to fix layout) ---
MAT_X  = 0.2    # left edge of matrix row boxes
MAT_W  = 2.55   # width of matrix row boxes
MUL_X  = 3.7    # x-center of multiply (×) nodes
MUL_R  = 0.21   # radius of multiply nodes
RES_X  = 4.1    # left edge of result boxes
RES_W  = 2.1    # width of result boxes
EV_W   = 0.85   # width of E(v) box
EV_X   = 2.6    # left edge of E(v) box  ← adjust to move E(v) left/right
ROW_CY = [6.3, 4.55, 2.8]   # y-centers of the 3 rows  ← adjust spacing

EV_CY  = ROW_CY[1]           # E(v) vertically centered on middle row
EV_CX  = EV_X + EV_W / 2

# Matrix row boxes
row_labels = [
    'E(M[1,:]) = E([m\u2081\u2081, m\u2081\u2082, m\u2081\u2083])',
    'E(M[2,:]) = E([m\u2082\u2081, m\u2082\u2082, m\u2082\u2083])',
    'E(M[3,:]) = E([m\u2083\u2081, m\u2083\u2082, m\u2083\u2083])',
]
for cy, lbl in zip(ROW_CY, row_labels):
    box(MAT_X, cy - BH/2, MAT_W, BH, lbl, '#bbdefb', fs=8)

# E(v) box
box(EV_X, EV_CY - BH/2, EV_W, BH, 'E(v)', '#ffe0b2', fs=10, bold=True)

# Multiply nodes
for cy in ROW_CY:
    mul_node(MUL_X, cy)

# Result boxes
res_labels = [
    'E(r\u2081) = E(M[1,:]\u00b7v)',
    'E(r\u2082) = E(M[2,:]\u00b7v)',
    'E(r\u2083) = E(M[3,:]\u00b7v)',
]
for cy, lbl in zip(ROW_CY, res_labels):
    box(RES_X, cy - BH/2, RES_W, BH, lbl, '#bbdefb', fs=8)

# --- Arrows (LEFT PANEL) ---

# 1. Matrix row right edge → multiply node left
for cy in ROW_CY:
    harrow(MAT_X + MAT_W, cy, MUL_X - MUL_R, '#1565c0')

# 2. Multiply node right → result box left
for cy in ROW_CY:
    harrow(MUL_X + MUL_R, cy, RES_X, '#1565c0')

# 3. E(v) → multiply nodes
# Currently uses a vertical bus line approach:
#   - horizontal stub from E(v) right edge to BUS_X
#   - vertical bus from top row to bottom row at BUS_X
#   - horizontal arrows from BUS_X to each × node
BUS_X = EV_X + EV_W + 0.12   # ← adjust to move bus left/right
ax.plot([EV_X + EV_W, BUS_X], [EV_CY, EV_CY],
        color='#e65100', lw=1.6, zorder=3)                            # stub
ax.plot([BUS_X, BUS_X], [ROW_CY[2], ROW_CY[0]],
        color='#e65100', lw=1.6, zorder=3)                            # vertical bus
for cy in ROW_CY:
    harrow(BUS_X, cy, MUL_X - MUL_R, '#e65100')                      # branches

# Note box
box(MAT_X, 1.7, 4.0, 0.65,
    'Fully Homomorphic: BOTH matrix rows\nand vector are encrypted (CKKS ciphertexts)',
    '#f9f9f9', ec='#bbb', fs=7.8)


# ═══════════════════════════════════════════════════════════════
# Divider
# ═══════════════════════════════════════════════════════════════
ax.plot([6.8, 6.8], [0.5, 7.8], color='#ccc', lw=1.2, linestyle='--')


# ═══════════════════════════════════════════════════════════════
# RIGHT PANEL — Encrypted 3D Cross Product
# ═══════════════════════════════════════════════════════════════
ax.text(10.0, 7.7, 'Encrypted 3D Cross Product',
        ha='center', fontsize=10, fontweight='bold')
ax.text(10.0, 7.38,
        '[core/secure_linear_algebra.py: encrypted_cross_product()]',
        ha='center', fontsize=7, color='#555')

CP_W  = 2.7
EA_X  = 7.0;  EA_CY = 6.5
EB_X  = 10.0; EB_CY = 6.5
ROT_X = 8.0;  ROT_Y = 5.0; ROT_W = 3.0; ROT_H = 0.75
OUT_X = 7.8;  OUT_Y = 3.3; OUT_W = 3.4; OUT_H = 1.2

box(EA_X, EA_CY - BH/2, CP_W, BH, 'E(a) = E([a\u2081, a\u2082, a\u2083])', '#bbdefb', fs=8.5)
box(EB_X, EB_CY - BH/2, CP_W, BH, 'E(b) = E([b\u2081, b\u2082, b\u2083])', '#bbdefb', fs=8.5)
box(ROT_X, ROT_Y - ROT_H/2, ROT_W, ROT_H,
    'Rotate E(b) by 1, 2\n(via matmul permutation)', '#ffe0b2', fs=8.5)
box(OUT_X, OUT_Y - OUT_H/2, OUT_W, OUT_H,
    'E(a\u00d7b) = E([a\u2082b\u2083\u2212a\u2083b\u2082,\n   a\u2083b\u2081\u2212a\u2081b\u2083,\n   a\u2081b\u2082\u2212a\u2082b\u2081])',
    '#c8e6c9', fs=8.5)

# E(a) bottom-center → Rotate top (left portion)
darrow(EA_X + CP_W/2, EA_CY - BH/2,  ROT_X + ROT_W*0.3, ROT_Y + ROT_H/2, '#1565c0')
# E(b) bottom-center → Rotate top (right portion)
darrow(EB_X + CP_W/2, EB_CY - BH/2,  ROT_X + ROT_W*0.7, ROT_Y + ROT_H/2, '#1565c0')
# Rotate bottom-center → Output top-center
varrow(ROT_X + ROT_W/2, ROT_Y - ROT_H/2, OUT_Y + OUT_H/2, '#e65100')


# ═══════════════════════════════════════════════════════════════
# Steps text (right of cross product)
# ═══════════════════════════════════════════════════════════════
steps = [
    ('Steps:', True),
    ('1. Rotate E(a) cyclically by 1 and 2 positions', False),
    ('2. Rotate E(b) cyclically by 1 and 2 positions', False),
    ('3. Element-wise multiply rotated vectors', False),
    ('4. Subtract to get cross product components', False),
    ('', False),
    ('Key: Rotation uses permutation matrix M', False),
    ('   (r\u00b7f(\u00b7) = s((s(x) mod r) + i))', False),
    ('   Implemented via vec_matmul(M)', False),
    ('', False),
    ('Operation depth: 1 multiplication', False),
    ('No plaintext extraction required', False),
]
sx, sy = 13.2, 7.1
for i, (s, bold) in enumerate(steps):
    ax.text(sx, sy - i*0.46, s, ha='left', va='center', fontsize=8.2,
        fontweight='bold' if bold else 'normal',
        family='monospace' if s.startswith('   ') else 'sans-serif')


plt.savefig('fig_vector_ops_new.png', dpi=150, bbox_inches='tight', facecolor='white')
print('Saved fig_vector_ops_new.png')
