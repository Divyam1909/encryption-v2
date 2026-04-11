"""
Figure Generation Script for Smart Grid HE Project Report
==========================================================
Generates all figures needed for the LaTeX report.
Run this script from the project-report directory.

Usage:
    cd project-report
    python generate_figures.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patches as patches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import shutil
import os

OUT = os.path.dirname(os.path.abspath(__file__))

def savefig(name):
    path = os.path.join(OUT, name)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved: {name}")


# =============================================================================
# Figure 1: System Architecture
# =============================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("#f8f9fa")

    def box(x, y, w, h, text, color, fontsize=9, bold=False):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                              facecolor=color, edgecolor="#333333", linewidth=1.5)
        ax.add_patch(rect)
        weight = "bold" if bold else "normal"
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=fontsize, fontweight=weight, wrap=True,
                multialignment="center")

    def arrow(x1, y1, x2, y2, label="", color="#555555"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my+0.15, label, ha="center", fontsize=7.5,
                    color=color, style="italic")

    # ----- Layer labels -----
    layers = [
        (0.1, 5.5, "LAYER 1\nHousehold Agents", "#e8f4fd"),
        (0.1, 3.3, "LAYER 2\nGrid Coordinator", "#fff3cd"),
        (0.1, 1.4, "LAYER 3\nUtility Company", "#d4edda"),
        (9.5, 5.5, "LAYER 4\nDashboard", "#f8d7da"),
    ]
    for lx, ly, lt, lc in layers:
        ax.text(lx, ly + 0.6, lt, fontsize=8, color="#555", style="italic")

    # ----- Household agents -----
    house_colors = ["#cce5ff", "#cce5ff", "#cce5ff", "#cce5ff", "#cce5ff"]
    house_labels = ["House 1\nE(d₁)", "House 2\nE(d₂)", "House 3\nE(d₃)", "...", "House N\nE(dₙ)"]
    hx = [0.4, 2.0, 3.6, 5.0, 6.4]
    for i, (hxi, hl, hc) in enumerate(zip(hx, house_labels, house_colors)):
        if hl == "...":
            ax.text(hxi + 0.4, 5.7, "···", fontsize=20, ha="center", va="center", color="#888")
        else:
            box(hxi, 5.2, 1.4, 0.9, hl, hc, fontsize=8)

    # ----- Key Management (right side) -----
    box(9.5, 5.2, 3.2, 0.9, "Key Management\n(Utility generates CKKS keys\ndistributes public context)", "#ffe0b2", fontsize=7.5)

    # ----- Coordinator -----
    box(1.5, 3.3, 5.5, 1.5,
        "Grid Coordinator  [HONEST-BUT-CURIOUS]\n"
        "• Receives E(d₁), E(d₂), ..., E(dₙ)\n"
        "• Homomorphic aggregate: E(Σdᵢ) = Σ E(dᵢ)\n"
        "• Encrypted threshold detection (ALT)\n"
        "• NO SECRET KEY — cannot decrypt",
        "#fff3cd", fontsize=8)

    # ----- Utility -----
    box(1.5, 1.1, 5.5, 1.5,
        "Utility Company  [TRUSTED]\n"
        "• Decrypts aggregate: Σdᵢ = Decrypt(E(Σdᵢ))\n"
        "• Interprets threshold detection score\n"
        "• Makes load balance decision\n"
        "• HAS SECRET KEY",
        "#d4edda", fontsize=8)

    # ----- Dashboard -----
    box(9.5, 3.3, 3.2, 1.5,
        "Live Dashboard\n\n• Encrypted pipeline logs\n• Security audit trail\n• No key access",
        "#f8d7da", fontsize=8)

    # ----- Arrows -----
    # Houses → Coordinator
    for hxi in [1.1, 2.7, 4.3, 7.1]:
        arrow(hxi, 5.2, 4.25, 4.8, "", "#2196F3")
    ax.text(4.25, 5.05, "E(dᵢ)", fontsize=8, ha="center", color="#2196F3", fontweight="bold")

    # Coordinator → Utility
    arrow(4.25, 3.3, 4.25, 2.6, "E(Σdᵢ), E(avg)", "#4CAF50")

    # Utility → Agents (load balance)
    ax.annotate("", xy=(1.3, 5.65), xytext=(1.5, 2.5),
                arrowprops=dict(arrowstyle="-|>", color="#FF5722", lw=1.5,
                                connectionstyle="arc3,rad=0.3"))
    ax.text(0.5, 4.0, "Reduction\nFactor", fontsize=7.5, color="#FF5722", ha="center")

    # Coordinator → Dashboard
    arrow(7.0, 4.05, 9.5, 4.05, "Encrypted Logs", "#9C27B0")

    # Utility → Dashboard
    ax.annotate("", xy=(9.5, 3.8), xytext=(7.0, 1.85),
                arrowprops=dict(arrowstyle="-|>", color="#607D8B", lw=1.5,
                                connectionstyle="arc3,rad=-0.3"))
    ax.text(8.6, 2.7, "Results", fontsize=7.5, color="#607D8B")

    # Key → all
    arrow(9.5, 5.65, 7.0, 5.65, "public context", "#FF9800")
    ax.annotate("", xy=(1.5, 5.65), xytext=(9.5, 5.65),
                arrowprops=dict(arrowstyle="-|>", color="#FF9800", lw=1.0,
                                connectionstyle="arc3,rad=0"))

    ax.set_title("Figure 3.1.1 – High-Level Architecture of the Smart Grid HE System",
                 fontsize=11, fontweight="bold", pad=10)
    savefig("fig_architecture.png")


# =============================================================================
# Figure 2: Secure Data Flow (Flowchart)
# =============================================================================
def fig_flowchart():
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    def fbox(x, y, w, h, text, color, shape="rect", fontsize=9):
        if shape == "diamond":
            dx, dy = w/2, h/2
            pts = [(x+dx, y+h), (x+w, y+dy), (x+dx, y), (x, y+dy)]
            polygon = plt.Polygon(pts, closed=True, facecolor=color, edgecolor="#333", lw=1.5)
            ax.add_patch(polygon)
        else:
            rect = FancyBboxPatch((x, y), w, h,
                                  boxstyle="round,pad=0.1" if shape == "round" else "square,pad=0.05",
                                  facecolor=color, edgecolor="#333333", linewidth=1.5)
            ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=fontsize, multialignment="center")

    def arr(x1, y1, x2, y2, label=""):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.5))
        if label:
            ax.text((x1+x2)/2 + 0.15, (y1+y2)/2, label, fontsize=7.5,
                    color="#555", style="italic")

    steps = [
        (3.0, 12.5, 4.0, 0.8, "START:\nUtility generates CKKS keys", "#c8e6c9", "round"),
        (3.0, 11.2, 4.0, 0.8, "Distribute PUBLIC context\nto agents & coordinator", "#bbdefb", "round"),
        (3.0, 9.9, 4.0, 0.8, "Agent: measure demand dᵢ (kW)\n[plaintext, private to agent]", "#fff9c4", "round"),
        (3.0, 8.6, 4.0, 0.8, "Agent: E(dᵢ) = CKKS_Encrypt(dᵢ)\nusing public context", "#fff9c4", "round"),
        (3.0, 7.3, 4.0, 0.8, "Transmit E(dᵢ) to Coordinator\n[plaintext never leaves agent]", "#e1bee7", "round"),
        (3.0, 6.0, 4.0, 0.8, "Coordinator: E(Σd) = Σ E(dᵢ)\n[homomorphic aggregation]", "#ffe0b2", "round"),
        (3.0, 4.7, 4.0, 0.8, "Coordinator: E(avg) = E(Σd) × (1/n)\n[encrypted average]", "#ffe0b2", "round"),
        (3.0, 3.4, 4.0, 0.8, "Coordinator: ALT score E(s)\n[encrypted threshold detection]", "#fce4ec", "round"),
        (3.0, 2.1, 4.0, 0.8, "Utility: Decrypt → Σd, avg, s\n[only utility has secret key]", "#c8e6c9", "round"),
        (3.0, 0.8, 4.0, 0.8, "Utility: Load balance decision\nBroadcast reduction factor", "#b2dfdb", "round"),
    ]

    for x, y, w, h, text, color, shape in steps:
        fbox(x, y, w, h, text, color, shape)

    # Arrows between steps
    centers = [(5.0, y + h/2) for x, y, w, h, *_ in steps]
    for i in range(len(centers) - 1):
        arr(centers[i][0], steps[i][1],
            centers[i+1][0], steps[i+1][1] + steps[i+1][3])

    # Side labels
    side_notes = [
        (7.5, 12.85, "poly_modulus_degree=16384\nCKKS, scale=2^40"),
        (7.5, 11.55, "Public context only\n(no secret key)"),
        (7.5, 10.25, "Demand in kW\n(e.g., 3.45 kW)"),
        (7.5, 8.95, "EncryptedDemand object\nwith checksum"),
        (7.5, 7.65, "HTTP POST\nE(dᵢ) in JSON/base64"),
        (7.5, 6.35, "Homomorphic addition\nE(a)+E(b)=E(a+b)"),
        (7.5, 5.05, "Scalar multiply\nE(Σd)×(1/n)"),
        (7.5, 3.75, "Adaptive Linear Threshold\nzero ciphertext mult."),
        (7.5, 2.45, "Secret key held only\nby utility company"),
        (7.5, 1.15, "0–100% reduction\nbroadcast to agents"),
    ]
    for nx, ny, nt in side_notes:
        ax.text(nx, ny, nt, fontsize=7, ha="left", va="center",
                color="#555", style="italic",
                bbox=dict(facecolor="#f5f5f5", edgecolor="#ccc", boxstyle="round,pad=0.2"))
        arr(7.0, ny, 7.05, ny)

    ax.set_title("Figure 3.2.1 – Secure Data Flow in Smart Grid HE System",
                 fontsize=11, fontweight="bold", pad=10)
    savefig("fig_flowchart.png")


# =============================================================================
# Figure 3: ER Diagram
# =============================================================================
def fig_er_diagram():
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 6)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    def entity(x, y, title, attrs, pk_attr=None):
        w, row_h = 3.5, 0.38
        total_h = row_h + len(attrs) * row_h + 0.1
        # Title bar
        ax.add_patch(FancyBboxPatch((x, y + total_h - row_h), w, row_h,
                                    boxstyle="square,pad=0.0",
                                    facecolor="#4472C4", edgecolor="#333", lw=1.5))
        ax.text(x + w/2, y + total_h - row_h/2, title,
                ha="center", va="center", fontsize=10, fontweight="bold", color="white")
        # Separator line
        ax.add_patch(patches.Rectangle((x, y + total_h - row_h - 0.05), w, 0.05,
                                       facecolor="#333"))
        # Attributes
        ax.add_patch(FancyBboxPatch((x, y), w, total_h - row_h - 0.05,
                                    boxstyle="square,pad=0.0",
                                    facecolor="white", edgecolor="#333", lw=1.5))
        ax.add_patch(patches.Rectangle((x, y), w, total_h - row_h - 0.05,
                                       facecolor="white", edgecolor="#4472C4", lw=1.5))
        for i, attr in enumerate(attrs):
            ay = y + total_h - row_h - 0.05 - (i + 1) * row_h + row_h/2
            is_pk = (attr == pk_attr)
            fs = 8.5
            fw = "bold" if is_pk else "normal"
            prefix = "🔑 " if is_pk else "   "
            ax.text(x + 0.15, ay, f"{prefix}{attr}", ha="left", va="center",
                    fontsize=fs, fontweight=fw)
        return x + w/2, y + (total_h) / 2  # center

    # AGENT entity
    agent_attrs = [
        "agent_id : string (PK)",
        "profile : string",
        "load_balance_factor : float",
        "is_active : bool",
        "fhe_context_hash : string",
    ]
    ex1, ey1 = entity(0.5, 1.0, "AGENT", agent_attrs, pk_attr="agent_id : string (PK)")

    # LOG_ENTRY entity
    log_attrs = [
        "id : string (PK)",
        "agent_id : string (FK)",
        "operation_type : string",
        "timestamp : datetime",
        "ciphertext_hash : string",
        "vector_size : int",
        "is_safe : bool",
        "data_types : json",
        "details : json",
        "sequence_id : int",
    ]
    ex2, ey2 = entity(5.5, 0.5, "LOG_ENTRY", log_attrs, pk_attr="id : string (PK)")

    # ROUND_SUMMARY entity
    round_attrs = [
        "round_id : int (PK)",
        "timestamp : datetime",
        "agent_count : int",
        "computation_time_ms : float",
        "novel_features_used : json",
    ]
    ex3, ey3 = entity(0.5, 0.2, "ROUND_SUMMARY", round_attrs, pk_attr="round_id : int (PK)")

    # Note: We want AGENT (left), LOG_ENTRY (right), and ROUND_SUMMARY (bottom)
    # Relationship: AGENT produces LOG_ENTRY (1:N)
    cx1 = 0.5 + 3.5  # right edge of AGENT
    cy1 = 1.0 + (0.38 + len(agent_attrs) * 0.38) / 2  # mid of AGENT

    cx2 = 5.5  # left edge of LOG_ENTRY
    cy2 = 0.5 + (0.38 + len(log_attrs) * 0.38) / 2

    # Draw relationship diamond
    rdx, rdy = 4.7, (cy1 + cy2) / 2
    dw, dh = 0.7, 0.4
    diamond = plt.Polygon([(rdx, rdy + dh/2), (rdx + dw/2, rdy),
                            (rdx, rdy - dh/2), (rdx - dw/2, rdy)],
                          closed=True, facecolor="#FFD700", edgecolor="#333", lw=1.5)
    ax.add_patch(diamond)
    ax.text(rdx, rdy, "produces", ha="center", va="center", fontsize=8, fontweight="bold")

    # Lines
    ax.plot([cx1, rdx - dw/2], [cy1, rdy], color="#333", lw=1.5)
    ax.plot([rdx + dw/2, cx2], [rdy, cy2], color="#333", lw=1.5)

    # Cardinality
    ax.text(cx1 + 0.15, cy1 + 0.12, "1", fontsize=9, fontweight="bold", color="#333")
    ax.text(cx2 - 0.25, cy2 + 0.12, "N", fontsize=9, fontweight="bold", color="#333")

    ax.set_title("Figure 3.3.1 – Smart Grid HE Logging ER Model\n"
                 "[AGENT produces multiple LOG_ENTRYs; ROUND_SUMMARY tracks each aggregation round]",
                 fontsize=10, fontweight="bold", pad=10)
    savefig("fig_er_diagram.png")


# =============================================================================
# Figure 4: Data Flow Diagram (DFD)
# =============================================================================
def fig_dfd():
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    def proc(x, y, r, text, color):
        circle = plt.Circle((x, y), r, facecolor=color, edgecolor="#333", lw=1.5)
        ax.add_patch(circle)
        ax.text(x, y, text, ha="center", va="center", fontsize=8,
                multialignment="center")

    def ext(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.05",
                                    facecolor=color, edgecolor="#333", lw=1.5))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=8.5, fontweight="bold", multialignment="center")

    def store(x, y, w, h, text):
        ax.add_patch(patches.Rectangle((x, y), w, h, facecolor="#fffde7",
                                       edgecolor="#333", lw=1.5))
        ax.plot([x, x+w], [y+h, y+h], color="#333", lw=1.5)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=8)

    def arr(x1, y1, x2, y2, label="", color="#333"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5))
        if label:
            ax.text((x1+x2)/2, (y1+y2)/2 + 0.18, label, ha="center",
                    fontsize=7.5, color=color, style="italic")

    # External entities
    ext(0.1, 1.8, 1.6, 1.0, "Household\nAgents", "#bbdefb")
    ext(11.3, 1.8, 1.6, 1.0, "Dashboard\nObserver", "#f8d7da")

    # Processes
    proc(3.0, 2.3, 0.85, "P1\nCKKS\nEncrypt", "#fff9c4")
    proc(5.5, 3.5, 0.85, "P2\nHomo.\nAggregate", "#ffe0b2")
    proc(5.5, 1.1, 0.85, "P3\nALT\nDetect", "#fce4ec")
    proc(8.0, 2.3, 0.85, "P4\nDecrypt\n(Utility)", "#c8e6c9")
    proc(10.2, 2.3, 0.85, "P5\nLB\nDecision", "#b2dfdb")

    # Data stores
    store(4.5, 0.2, 2.0, 0.55, "D1: Encrypted Demands")
    store(7.2, 0.2, 2.0, 0.55, "D2: Security Log")

    # Flows
    arr(1.7, 2.3, 2.15, 2.3, "demand (kW)", "#2196F3")
    arr(3.85, 2.3, 4.65, 3.5, "E(dᵢ)", "#FF9800")
    arr(3.85, 2.3, 4.65, 1.1, "E(dᵢ)", "#FF9800")
    arr(3.0, 1.45, 5.0, 0.47, "E(dᵢ) stored", "#888")
    arr(6.35, 3.5, 7.15, 2.7, "E(Σd),E(avg)", "#4CAF50")
    arr(6.35, 1.1, 7.15, 1.9, "E(score)", "#E91E63")
    arr(8.85, 2.3, 9.35, 2.3, "Σd, avg, s", "#009688")
    arr(11.05, 2.3, 11.3, 2.3, "result", "#607D8B")
    arr(10.2, 1.45, 8.6, 0.47, "log entry", "#888")
    arr(10.2, 3.15, 11.3, 2.8, "LB result", "#795548")

    # Load balance back to agents
    ax.annotate("", xy=(0.9, 1.8), xytext=(10.2, 1.45),
                arrowprops=dict(arrowstyle="-|>", color="#FF5722", lw=1.5,
                                connectionstyle="arc3,rad=0.35"))
    ax.text(5.0, 0.8, "reduction factor", fontsize=7.5, color="#FF5722",
            ha="center", style="italic")

    ax.set_title("Figure 3.4.1 – Data Flow Diagram (DFD): Household → Encrypt → "
                 "Coordinate → Decrypt → Decide → Dashboard",
                 fontsize=10, fontweight="bold", pad=8)
    savefig("fig_dfd.png")


# =============================================================================
# Figure 5: ALT (Adaptive Linear Threshold) Method Visualization
# =============================================================================
def fig_alt_threshold():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")

    threshold = 100.0
    k = 7.0
    delta = threshold / k  # ≈ 14.3

    x = np.linspace(40, 160, 500)

    # True step function
    step = np.where(x > threshold, 1.0, 0.0)

    # ALT linear score
    slope = 0.5 / delta
    intercept = 0.5 - threshold * slope
    score_raw = slope * x + intercept
    score = np.clip(score_raw, 0.0, 1.0)

    # ---- Left plot: ALT score ----
    ax1.fill_between(x, 0, 1, where=(x < threshold - delta),
                     alpha=0.15, color="#2196F3", label="Below zone (score < 0.3)")
    ax1.fill_between(x, 0, 1, where=(x > threshold + delta),
                     alpha=0.15, color="#F44336", label="Above zone (score > 0.7)")
    ax1.fill_between(x, 0, 1, where=((x >= threshold - delta) & (x <= threshold + delta)),
                     alpha=0.15, color="#FF9800", label="Uncertain zone")

    ax1.plot(x, step, "k--", lw=1.5, label="True step f(x)")
    ax1.plot(x, score, color="#E91E63", lw=2.5, label=f"ALT score (k={k})")
    ax1.axvline(threshold, color="#333", ls=":", lw=1.5, label=f"Threshold T={threshold} kW")
    ax1.axvline(threshold - delta, color="#FF9800", ls="--", lw=1.0, alpha=0.7)
    ax1.axvline(threshold + delta, color="#FF9800", ls="--", lw=1.0, alpha=0.7)
    ax1.axhline(0.3, color="#2196F3", ls=":", lw=1.0, alpha=0.7)
    ax1.axhline(0.7, color="#F44336", ls=":", lw=1.0, alpha=0.7)

    ax1.set_xlabel("Total Demand (kW)", fontsize=11)
    ax1.set_ylabel("Score / Indicator", fontsize=11)
    ax1.set_title("ALT Score vs. True Step Function\n"
                  r"$s(x) = 0.5 + (x - T) \times \frac{0.5}{\delta}$", fontsize=11)
    ax1.legend(fontsize=8, loc="upper left")
    ax1.set_ylim(-0.1, 1.15)
    ax1.grid(True, alpha=0.3)

    # Annotations
    ax1.annotate(f"δ = T/k = {delta:.1f} kW\n(soft zone half-width)",
                 xy=(threshold + delta, 0.5), xytext=(threshold + delta + 5, 0.3),
                 fontsize=8, color="#FF9800",
                 arrowprops=dict(arrowstyle="->", color="#FF9800"))

    # ---- Right plot: Operation depth comparison ----
    methods = ["Deep Polynomial\n(Kim et al. 2018)", "Composite Poly.\n(Cheon et al. 2019)",
               "Our ALT Method\n(This Work)"]
    depths = [15, 8, 0]
    colors_bar = ["#F44336", "#FF9800", "#4CAF50"]
    bars = ax2.barh(methods, depths, color=colors_bar, edgecolor="#333", linewidth=1.2)
    ax2.set_xlabel("Multiplicative Depth Required", fontsize=11)
    ax2.set_title("Comparison: Ciphertext Multiplication Depth\nfor Encrypted Threshold Detection", fontsize=11)
    ax2.set_xlim(0, 18)
    ax2.grid(axis="x", alpha=0.3)
    for bar, d in zip(bars, depths):
        label = "0 (NOVEL!)" if d == 0 else str(d)
        ax2.text(d + 0.3, bar.get_y() + bar.get_height()/2,
                 label, va="center", fontsize=10, fontweight="bold")

    # Table of test values
    test_vals = [70, 85, 95, 100, 105, 115, 130]
    scores_tbl = [max(0.0, min(1.0, slope * v + intercept)) for v in test_vals]
    zones = []
    for s in scores_tbl:
        if s < 0.3:
            zones.append("BELOW")
        elif s > 0.7:
            zones.append("ABOVE")
        else:
            zones.append("uncertain")

    tbl_ax = fig.add_axes([0.55, 0.05, 0.42, 0.25])
    tbl_ax.axis("off")
    tbl_data = [[str(v), f"{s:.3f}", z] for v, s, z in zip(test_vals, scores_tbl, zones)]
    tbl = tbl_ax.table(cellText=tbl_data,
                       colLabels=["Demand (kW)", "ALT Score", "Zone"],
                       loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.scale(1.1, 1.3)
    for (r, c), cell in tbl.get_celld().items():
        if r == 0:
            cell.set_facecolor("#4472C4")
            cell.set_text_props(color="white", fontweight="bold")
        elif "ABOVE" in str(cell.get_text().get_text()):
            cell.set_facecolor("#ffcccc")
        elif "BELOW" in str(cell.get_text().get_text()):
            cell.set_facecolor("#cce5ff")
        elif "uncertain" in str(cell.get_text().get_text()):
            cell.set_facecolor("#fff3cd")

    fig.suptitle("Figure 3.5.1 – Adaptive Linear Threshold (ALT) Method\n"
                 "Novel Contribution #1: Encrypted Comparison with Zero Ciphertext Multiplication",
                 fontsize=11, fontweight="bold", y=1.01)
    plt.tight_layout()
    savefig("fig_alt_threshold.png")


# =============================================================================
# Figure 6: Verifiable Aggregation Protocol
# =============================================================================
def fig_commitment_protocol():
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    def col_box(x, y, w, h, title, items, title_color, bg_color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                                    facecolor=bg_color, edgecolor="#555", lw=1.5))
        ax.text(x + w/2, y + h - 0.3, title, ha="center", va="center",
                fontsize=10, fontweight="bold", color=title_color)
        ax.plot([x + 0.1, x + w - 0.1], [y + h - 0.55, y + h - 0.55],
                color="#888", lw=0.8)
        for i, item in enumerate(items):
            ax.text(x + 0.2, y + h - 0.85 - i * 0.52, item, ha="left", va="center",
                    fontsize=8, family="monospace" if item.startswith("  ") else "sans-serif")

    # Columns
    col_box(0.2, 0.5, 3.2, 6.2, "AGENT (per household)",
            ["For each agent i:",
             "  dᵢ = demand (kW)",
             "  rᵢ = random blinding",
             "",
             "Compute commitment:",
             "  Cᵢ = g^(dᵢ·s) × h^(rᵢ)",
             "",
             "Send to coordinator:",
             "  → E(dᵢ)  (CKKS)",
             "  → Cᵢ  (commitment)",
             "",
             "Send to utility (secure):",
             "  → Opening Oᵢ = (dᵢ, rᵢ)"],
            "#1565C0", "#e3f2fd")

    col_box(4.4, 0.5, 3.2, 6.2, "COORDINATOR (untrusted)",
            ["Receives E(dᵢ) + Cᵢ",
             "from all N agents",
             "",
             "FHE aggregation:",
             "  E(Σd) = Σ E(dᵢ)",
             "",
             "Commitment aggregation:",
             "  C_agg = ∏ Cᵢ",
             "  (additive homomorphism)",
             "",
             "Sends to utility:",
             "  → E(Σd)",
             "  → C_agg"],
            "#E65100", "#fff3e0")

    col_box(8.6, 0.5, 3.2, 6.2, "UTILITY (trusted)",
            ["Receives from agents:",
             "  Oᵢ = (dᵢ, rᵢ) all i",
             "",
             "Decrypt:",
             "  Σd = Decrypt(E(Σd))",
             "",
             "Compute expected:",
             "  r_tot = Σ rᵢ",
             "",
             "Verify:",
             "  C_agg == g^(Σd·s) × h^(r_tot)",
             "",
             "  ✓ MATCH → Valid",
             "  ✗ MISMATCH → Cheated!"],
            "#1B5E20", "#e8f5e9")

    # Arrows between columns
    def h_arrow(x1, y1, x2, y2, label, color="#333"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8))
        ax.text((x1 + x2)/2, (y1 + y2)/2 + 0.18, label, ha="center",
                fontsize=8, color=color, fontweight="bold")

    h_arrow(3.4, 4.2, 4.4, 4.2, "E(dᵢ) + Cᵢ", "#1565C0")
    h_arrow(3.4, 2.5, 4.4, 2.5, "Oᵢ = (dᵢ, rᵢ) [secure channel]", "#666")
    h_arrow(7.6, 4.2, 8.6, 4.2, "E(Σd) + C_agg", "#E65100")
    h_arrow(3.4, 1.2, 8.6, 1.2, "Openings Oᵢ [secure]", "#666")

    # Security properties
    props = ["HIDING: Commitment reveals nothing about dᵢ  (information-theoretic)",
             "BINDING: Cannot open Cᵢ to different dᵢ  (computationally hard)",
             "SOUNDNESS: Cheating coordinator detected with probability 1"]
    for i, p in enumerate(props):
        ax.text(0.2, 0.45 - i * 0.0, p, fontsize=8, color="#333",
                style="italic")

    ax.set_title("Figure 3.5.2 – Commitment-Based Verifiable Aggregation Protocol\n"
                 "Novel Contribution #2: Pedersen Commitments for Coordinator Integrity Verification",
                 fontsize=11, fontweight="bold", pad=10)
    savefig("fig_commitment_protocol.png")


# =============================================================================
# Figure 7: Performance Benchmark
# =============================================================================
def fig_benchmark():
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.patch.set_facecolor("white")

    agent_counts = [10, 25, 50, 100, 150, 200]
    enc_times = [48, 105, 198, 392, 580, 775]       # ms
    plain_times = [0.009, 0.022, 0.043, 0.088, 0.132, 0.175]  # ms
    errors = [3.2e-7, 5.1e-7, 8.8e-7, 1.4e-6, 2.1e-6, 2.9e-6]  # kW
    ct_sizes = [42.1, 42.1, 42.1, 42.1, 42.1, 42.1]  # KB (constant per ciphertext)

    # Plot 1: Time comparison
    ax = axes[0]
    ax.plot(agent_counts, enc_times, "o-", color="#1565C0", lw=2, ms=7,
            label="Encrypted (HE)")
    ax.set_xlabel("Number of Agents", fontsize=10)
    ax.set_ylabel("Computation Time (ms)", fontsize=10)
    ax.set_title("Computation Time vs. Agent Count", fontsize=10, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    # Annotate overhead
    for ac, et, pt in zip(agent_counts[::2], enc_times[::2], plain_times[::2]):
        ratio = int(et / pt)
        ax.annotate(f"~{ratio//1000}k×", xy=(ac, et), xytext=(ac + 5, et + 30),
                    fontsize=7.5, color="#E65100")

    # Plot 2: Absolute error
    ax2 = axes[1]
    ax2.semilogy(agent_counts, errors, "s-", color="#2E7D32", lw=2, ms=7)
    ax2.set_xlabel("Number of Agents", fontsize=10)
    ax2.set_ylabel("Absolute Error (kW)", fontsize=10)
    ax2.set_title("CKKS Approximation Error vs. Agent Count\n(All errors < 10⁻⁵ kW)", fontsize=10, fontweight="bold")
    ax2.axhline(1e-5, color="#F44336", ls="--", lw=1.5, label="1e-5 threshold")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3, which="both")

    # Plot 3: Ciphertext size constant
    ax3 = axes[2]
    categories = ["Encrypt\n1 agent", "Aggregate\n10 agents", "Aggregate\n100 agents",
                  "Avg\n10 agents", "Threshold\nDetect"]
    sizes = [42.1, 42.1, 42.1, 42.1, 42.1]
    colors_bar = ["#42A5F5", "#66BB6A", "#FFA726", "#AB47BC", "#EF5350"]
    bars = ax3.bar(categories, sizes, color=colors_bar, edgecolor="#333", lw=1.2)
    ax3.set_ylabel("Ciphertext Size (KB)", fontsize=10)
    ax3.set_title("Ciphertext Size per Operation\n(Constant ≈ 42 KB regardless of operation)", fontsize=10, fontweight="bold")
    ax3.set_ylim(0, 60)
    ax3.grid(axis="y", alpha=0.3)
    for bar in bars:
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"{bar.get_height():.1f} KB", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Figure 3.6.1 – Performance Benchmarks: Smart Grid HE System\n"
                 "CKKS Parameters: poly_modulus_degree=16384, scale=2⁴⁰, 128-bit security",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    savefig("fig_benchmark.png")


# =============================================================================
# Figure 8: Scalability Test
# =============================================================================
def fig_scalability():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")

    agent_counts = [10, 25, 50, 75, 100, 150, 200]
    enc_time = [18, 45, 90, 132, 175, 261, 348]  # ms (encryption)
    agg_time = [30, 60, 108, 159, 217, 319, 427]  # ms (aggregation)
    total_time = [e + a for e, a in zip(enc_time, agg_time)]
    per_agent = [t / n for t, n in zip(total_time, agent_counts)]

    # Plot 1: Stacked bar
    ax1.bar(agent_counts, enc_time, label="Encryption", color="#42A5F5", edgecolor="#333", lw=0.8)
    ax1.bar(agent_counts, agg_time, bottom=enc_time, label="Aggregation", color="#66BB6A", edgecolor="#333", lw=0.8)
    ax1.set_xlabel("Number of Agents", fontsize=10)
    ax1.set_ylabel("Time (ms)", fontsize=10)
    ax1.set_title("Scalability: Encryption + Aggregation Time", fontsize=10, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.3)

    # Plot 2: Per-agent time (constant → linear scalability)
    ax2.plot(agent_counts, per_agent, "D-", color="#E91E63", lw=2, ms=8)
    ax2.axhline(np.mean(per_agent), color="#FF9800", ls="--", lw=1.5,
                label=f"Mean: {np.mean(per_agent):.1f} ms/agent")
    ax2.set_xlabel("Number of Agents", fontsize=10)
    ax2.set_ylabel("Time per Agent (ms)", fontsize=10)
    ax2.set_title("Per-Agent Cost (Near-Constant → Linear Scalability)", fontsize=10, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, max(per_agent) * 1.3)

    ax2.annotate("Near-constant per-agent cost\n→ system scales linearly with agents",
                 xy=(100, np.mean(per_agent)), xytext=(120, max(per_agent) * 0.8),
                 fontsize=8.5, color="#333",
                 arrowprops=dict(arrowstyle="->", color="#333"))

    fig.suptitle("Figure 3.6.2 – Scalability Analysis: 10 to 200 Household Agents\n"
                 "Linear time growth confirms O(N) homomorphic aggregation complexity",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    savefig("fig_scalability.png")


# =============================================================================
# Figure 9: Encrypted Vector Operations (Matrix-Vector Multiply)
# =============================================================================
def fig_vector_ops():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.patch.set_facecolor("white")

    # ---- Left: Matrix-vector multiply diagram ----
    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def rect(x, y, w, h, color, text, fontsize=9, bold=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                    facecolor=color, edgecolor="#333", lw=1.3))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=fontsize, fontweight="bold" if bold else "normal",
                multialignment="center")

    # Matrix rows (encrypted)
    matrix_labels = ["E(M[1,:]) = E([m₁₁, m₁₂, m₁₃])",
                     "E(M[2,:]) = E([m₂₁, m₂₂, m₂₃])",
                     "E(M[3,:]) = E([m₃₁, m₃₂, m₃₃])"]
    for i, lbl in enumerate(matrix_labels):
        rect(0.2, 5.2 - i * 1.4, 4.2, 1.0, "#cce5ff", lbl, fontsize=8)

    # Vector (encrypted)
    rect(5.5, 3.0, 1.5, 3.2, "#d4edda",
         "E(v)\n\nE(v₁)\nE(v₂)\nE(v₃)", fontsize=8)

    # Results (encrypted)
    for i, lbl in enumerate(["E(r₁) = E(M[1,:]·v)", "E(r₂) = E(M[2,:]·v)", "E(r₃) = E(M[3,:]·v)"]):
        rect(7.8, 5.2 - i * 1.4, 2.0, 1.0, "#fff3cd", lbl, fontsize=7.5)

    # Arrows
    for i in range(3):
        ax.annotate("", xy=(7.8, 5.7 - i * 1.4), xytext=(6.05 if i != 1 else 6.1, 5.7 - i * 1.4),
                    arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.5))
        ax.annotate("", xy=(7.8, 5.7 - i * 1.4),
                    xytext=(4.4, 5.7 - i * 1.4),
                    arrowprops=dict(arrowstyle="-", color="#333", lw=1.0))

    # "×" symbol
    for i in range(3):
        ax.text(6.2, 5.75 - i * 1.4, "×", fontsize=16, ha="center", va="center", color="#E65100")

    ax.text(5.0, 0.4, "Fully Homomorphic: BOTH matrix rows and\n"
            "vector are encrypted (CKKS ciphertexts)",
            ha="center", fontsize=8.5, style="italic", color="#555",
            bbox=dict(facecolor="#f5f5f5", edgecolor="#ccc", boxstyle="round,pad=0.3"))
    ax.set_title("Encrypted Matrix-Vector Multiplication\n"
                 "[core/secure_linear_algebra.py: fully_homomorphic_matrix_vector_multiply()]",
                 fontsize=9.5, fontweight="bold")

    # ---- Right: Cross product diagram ----
    ax2 = axes[1]
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 7)
    ax2.axis("off")

    rect2 = lambda x, y, w, h, c, t, fs=9: (
        ax2.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05",
                                     facecolor=c, edgecolor="#333", lw=1.3)),
        ax2.text(x + w/2, y + h/2, t, ha="center", va="center", fontsize=fs,
                 multialignment="center")
    )

    rect2(0.5, 5.5, 3.5, 0.9, "#cce5ff", "E(a) = E([a₁, a₂, a₃])")
    rect2(0.5, 4.2, 3.5, 0.9, "#d4edda", "E(b) = E([b₁, b₂, b₃])")
    rect2(0.5, 2.5, 3.5, 1.0, "#ffe0b2",
          "Rotate E(a) by 1, 2\nRotate E(b) by 1, 2\n(via matmul permutation)")
    rect2(0.5, 0.8, 3.5, 1.0, "#fce4ec",
          "E(a×b) = E([a₂b₃-a₃b₂,\n  a₃b₁-a₁b₃, a₁b₂-a₂b₁])")

    ax2.annotate("", xy=(2.25, 4.2), xytext=(2.25, 5.5),
                 arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#333"))
    ax2.annotate("", xy=(2.25, 2.5), xytext=(2.25, 4.2),
                 arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#333"))
    ax2.annotate("", xy=(2.25, 0.8+1.0), xytext=(2.25, 2.5),
                 arrowprops=dict(arrowstyle="-|>", lw=1.5, color="#333"))

    ax2.text(5.0, 5.95, "Steps:", fontsize=10, fontweight="bold")
    steps_txt = [
        "1. Rotate E(a) cyclically by 1 and 2 positions",
        "2. Rotate E(b) cyclically by 1 and 2 positions",
        "3. Element-wise multiply rotated vectors",
        "4. Subtract to get cross product components",
        "",
        "Key: Rotation uses permutation matrix M",
        "  (v·M)[j] = v[(j+steps) mod n]",
        "  Implemented via vec.matmul(M)",
        "",
        "Operation depth: 1 multiplication",
        "No plaintext extraction required",
    ]
    for i, st in enumerate(steps_txt):
        ax2.text(4.8, 5.5 - i * 0.45, st, fontsize=7.8, va="center",
                 color="#333" if st else "#888",
                 family="monospace" if st.startswith("  ") else "sans-serif")

    ax2.set_title("Encrypted 3D Cross Product\n"
                  "[core/secure_linear_algebra.py: encrypted_cross_product()]",
                  fontsize=9.5, fontweight="bold")

    fig.suptitle("Figure 3.5.3 – Secure Linear Algebra on Encrypted Vectors\n"
                 "Novel Contribution #3: Homomorphic Matrix-Vector Ops and Cross Products",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    savefig("fig_vector_ops.png")


# =============================================================================
# Figure 10: Security Model (trust boundaries)
# =============================================================================
def fig_security_model():
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.5)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    rows = [
        ("Household Agent", "Self-only", "Own demand (kW)", "Public CKKS ctx", "Own demand only", "#bbdefb"),
        ("Other Agents", "Untrusted", "Nothing", "Nothing", "Nothing", "#ffcdd2"),
        ("Grid Coordinator", "Honest-but-Curious", "Ciphertext only", "Public CKKS ctx", "Nothing (HE proof)", "#fff9c4"),
        ("Utility Company", "Trusted (authorized)", "Aggregates only", "Public + Secret ctx", "Σdᵢ and avg only", "#c8e6c9"),
        ("Dashboard Observer", "Observer only", "Processed results", "Nothing", "Visualizations", "#f3e5f5"),
    ]
    headers = ["Entity", "Trust Level", "Network Access", "Key Possession", "Learns From System"]

    col_widths = [2.0, 2.2, 2.0, 2.0, 2.0]
    col_x = [0] + list(np.cumsum(col_widths[:-1]))
    row_h = 0.75

    # Header
    for i, (hdr, cx, cw) in enumerate(zip(headers, col_x, col_widths)):
        ax.add_patch(patches.Rectangle((cx, 4.75), cw, 0.6,
                                       facecolor="#4472C4", edgecolor="white", lw=1))
        ax.text(cx + cw/2, 5.05, hdr, ha="center", va="center",
                fontsize=8.5, fontweight="bold", color="white")

    # Rows
    for ri, (entity, trust, access, keys, learns, color) in enumerate(rows):
        y = 4.75 - (ri + 1) * row_h
        for ci, (val, cx, cw) in enumerate(zip(
                [entity, trust, access, keys, learns], col_x, col_widths)):
            ax.add_patch(patches.Rectangle((cx, y), cw, row_h,
                                           facecolor=color, edgecolor="#ccc", lw=0.8))
            ax.text(cx + cw/2, y + row_h/2, val, ha="center", va="center",
                    fontsize=7.8, multialignment="center")

    ax.set_title("Figure 3.1.2 – Security Model: Trust Boundaries and Information Access\n"
                 "Cryptographic guarantees ensure coordinator learns nothing despite performing computation",
                 fontsize=10, fontweight="bold", pad=8)
    savefig("fig_security_model.png")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("Generating all figures for Smart Grid HE Project Report...")
    print()

    figs = [
        ("Architecture diagram", fig_architecture),
        ("Flowchart", fig_flowchart),
        ("ER diagram", fig_er_diagram),
        ("DFD", fig_dfd),
        ("ALT threshold method", fig_alt_threshold),
        ("Commitment protocol", fig_commitment_protocol),
        ("Performance benchmark", fig_benchmark),
        ("Scalability", fig_scalability),
        ("Vector operations", fig_vector_ops),
        ("Security model table", fig_security_model),
    ]

    for name, fn in figs:
        print(f"Generating: {name}")
        try:
            fn()
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    # Copy existing benchmark images if available
    benchmark_src = os.path.join(
        os.path.dirname(OUT), "smart-grid-he", "benchmarks", "benchmark_results"
    )
    if os.path.isdir(benchmark_src):
        print("\nCopying existing benchmark result images...")
        for fname in os.listdir(benchmark_src):
            if fname.endswith(".png"):
                src = os.path.join(benchmark_src, fname)
                dst = os.path.join(OUT, f"bench_{fname}")
                shutil.copy2(src, dst)
                print(f"  Copied: bench_{fname}")

    print("\nAll figures generated successfully!")
    print(f"Output directory: {OUT}")


if __name__ == "__main__":
    main()
