import tkinter as tk
from tkinter import ttk, scrolledtext
import numpy as np
import threading
import time
from typing import Dict, List
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from core.fhe_engine import SmartGridFHE, EncryptedDemand
from core.secure_linear_algebra import SecureLinearAlgebra


class EncryptedVectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Encrypted Vector Research Dashboard")
        self.root.geometry("1000x800")
        
        # Initialize FHE (can take a moment)
        self.status_var = tk.StringVar(value="Initializing FHE Engine...")
        
        # UI Setup
        self.create_widgets()
        
        # Background init of FHE
        threading.Thread(target=self.init_fhe, daemon=True).start()

    def init_fhe(self):
        try:
            # Re-init with standard params
            self.utility = SmartGridFHE()
            public_ctx = self.utility.get_public_context()
            self.coordinator = SmartGridFHE.from_context(public_ctx)
            self.algebra = SecureLinearAlgebra(self.coordinator)
            self.status_var.set("FHE Ready. 128-bit Security (CKKS).")
            self.enable_buttons()
        except Exception as e:
            self.status_var.set(f"Error initializing FHE: {e}")

    def enable_buttons(self):
        self.btn_calc_matrix["state"] = "normal"
        self.btn_run_stress["state"] = "normal"

    def create_widgets(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status Bar
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # Notebook (Tabs)
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Matrix Transform (Flexible)
        self.tab_matrix = ttk.Frame(notebook)
        notebook.add(self.tab_matrix, text="Linear Algebra (Matrix)")
        self.build_matrix_tab()

        # Tab 2: Noise/Depth Demo
        self.tab_noise = ttk.Frame(notebook)
        notebook.add(self.tab_noise, text="Research: Noise & Depth")
        self.build_noise_tab()
    # --- TAB 1: MATRIX TRANSFORM ---
    def build_matrix_tab(self):
        # Make the full tab vertically scrollable (not only inner log boxes).
        outer = ttk.Frame(self.tab_matrix)
        outer.pack(fill=tk.BOTH, expand=True)

        self.matrix_tab_canvas = tk.Canvas(outer, highlightthickness=0)
        self.matrix_tab_scroll = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=self.matrix_tab_canvas.yview)
        self.matrix_tab_canvas.configure(yscrollcommand=self.matrix_tab_scroll.set)
        self.matrix_tab_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.matrix_tab_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        container = ttk.Frame(self.matrix_tab_canvas, padding="10")
        self.matrix_tab_window = self.matrix_tab_canvas.create_window((0, 0), window=container, anchor="nw")

        def _on_container_configure(event):
            self.matrix_tab_canvas.configure(scrollregion=self.matrix_tab_canvas.bbox("all"))

        def _on_canvas_configure(event):
            # Keep inner frame width synced so widgets align properly.
            self.matrix_tab_canvas.itemconfigure(self.matrix_tab_window, width=event.width)

        def _on_wheel(event):
            if event.delta:
                self.matrix_tab_canvas.yview_scroll(int(-event.delta / 120), "units")
            elif getattr(event, "num", None) == 4:
                self.matrix_tab_canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                self.matrix_tab_canvas.yview_scroll(1, "units")

        def _bind_wheel(_event):
            self.matrix_tab_canvas.bind_all("<MouseWheel>", _on_wheel)
            self.matrix_tab_canvas.bind_all("<Button-4>", _on_wheel)
            self.matrix_tab_canvas.bind_all("<Button-5>", _on_wheel)

        def _unbind_wheel(_event):
            self.matrix_tab_canvas.unbind_all("<MouseWheel>")
            self.matrix_tab_canvas.unbind_all("<Button-4>")
            self.matrix_tab_canvas.unbind_all("<Button-5>")

        container.bind("<Configure>", _on_container_configure)
        self.matrix_tab_canvas.bind("<Configure>", _on_canvas_configure)
        self.matrix_tab_canvas.bind("<Enter>", _bind_wheel)
        self.matrix_tab_canvas.bind("<Leave>", _unbind_wheel)
        
        # Title
        title = ttk.Label(container, text="Fully Homomorphic Matrix-Vector Operations", 
                         font=('Helvetica', 12, 'bold'))
        title.pack(pady=(0, 10))

        # Top controls frame
        ctrl_frame = ttk.LabelFrame(container, text="Matrix Dimensions", padding="10")
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        dim_row = ttk.Frame(ctrl_frame)
        dim_row.pack(fill=tk.X)
        
        ttk.Label(dim_row, text="Rows:").pack(side=tk.LEFT, padx=(0, 5))
        self.rows_var = tk.IntVar(value=3)
        self.rows_spin = ttk.Spinbox(dim_row, from_=1, to=10, textvariable=self.rows_var, width=5,
                                      command=self.update_matrix_grid)
        self.rows_spin.pack(side=tk.LEFT, padx=(0, 15))
        self.rows_spin.bind('<Return>', self.update_matrix_grid)
        
        ttk.Label(dim_row, text="Columns:").pack(side=tk.LEFT, padx=(0, 5))
        self.cols_var = tk.IntVar(value=3)
        self.cols_spin = ttk.Spinbox(dim_row, from_=1, to=10, textvariable=self.cols_var, width=5,
                                      command=self.update_matrix_grid)
        self.cols_spin.pack(side=tk.LEFT, padx=(0, 15))
        self.cols_spin.bind('<Return>', self.update_matrix_grid)
        
        ttk.Button(dim_row, text="Update Grid", command=self.update_matrix_grid).pack(side=tk.LEFT, padx=10)
        
        # Operation type selector
        op_frame = ttk.LabelFrame(container, text="Operation Type", padding="10")
        op_frame.pack(fill=tk.X, pady=5)
        
        self.matrix_op_var = tk.StringVar(value="fully_encrypted_mv")
        ops = [
            ("FULLY ENCRYPTED: E(M) @ E(v) → E(result)", "fully_encrypted_mv"),
            ("Plaintext Matrix × Encrypted Vector: M @ E(v)", "plaintext_matrix_enc_vector"),
            ("Vector Element-wise: E(a) * E(b)", "vector_elementwise"),
            ("Vector Dot Product: E(a) · E(b)", "vector_dot"),
        ]
        for text, value in ops:
            ttk.Radiobutton(op_frame, text=text, variable=self.matrix_op_var, 
                           value=value, command=self.on_operation_change).pack(anchor=tk.W)

        # Input container (will hold matrix and vector inputs)
        self.mv_container = ttk.Frame(container)
        self.mv_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.update_matrix_grid()  # Initial build

        # Action buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_calc_matrix = ttk.Button(btn_frame, text="Encrypt & Compute (Fully Homomorphic)", 
                                          command=self.run_matrix_transform, state="disabled")
        self.btn_calc_matrix.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Clear Output", command=self.clear_matrix_output).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Load Example", command=self.load_matrix_example).pack(side=tk.LEFT, padx=5)

        # Runtime profiling panel
        profile_frame = ttk.LabelFrame(container, text="Runtime Profiling", padding="8")
        profile_frame.pack(fill=tk.X, pady=5)
        self.profile_vars: Dict[str, tk.StringVar] = {
            "mode": tk.StringVar(value="-"),
            "encrypt": tk.StringVar(value="-"),
            "multiply": tk.StringVar(value="-"),
            "rescale": tk.StringVar(value="-"),
            "decrypt": tk.StringVar(value="-"),
            "total": tk.StringVar(value="-"),
            "throughput": tk.StringVar(value="-"),
        }
        profile_rows = [
            ("Operation", "mode"),
            ("Encrypt time", "encrypt"),
            ("Multiply time", "multiply"),
            ("Rescale time", "rescale"),
            ("Decrypt time", "decrypt"),
            ("Total latency", "total"),
            ("Throughput", "throughput"),
        ]
        for idx, (label, key) in enumerate(profile_rows):
            ttk.Label(profile_frame, text=f"{label}:", width=18).grid(row=idx, column=0, sticky=tk.W, padx=(0, 8), pady=1)
            ttk.Label(
                profile_frame,
                textvariable=self.profile_vars[key],
                font=('Consolas', 9),
                foreground='#1f5d99'
            ).grid(row=idx, column=1, sticky=tk.W, pady=1)

        # Cryptographic artefacts panel (ciphertext visibility + verification)
        crypto_frame = ttk.LabelFrame(container, text="Cryptographic Outputs & Verification", padding="8")
        crypto_frame.pack(fill=tk.BOTH, pady=5)
        opt_row = ttk.Frame(crypto_frame)
        opt_row.pack(fill=tk.X, pady=(0, 5))
        self.show_full_cipher_var = tk.BooleanVar(value=False)
        self.show_full_ciphertext = False
        ttk.Checkbutton(
            opt_row,
            text="Show full ciphertext bytes (very long)",
            variable=self.show_full_cipher_var,
            command=self._on_toggle_full_ciphertext
        ).pack(side=tk.LEFT)
        self.crypto_out = scrolledtext.ScrolledText(
            crypto_frame, height=12, width=70, wrap=tk.WORD, font=('Consolas', 8),
            selectbackground='#d9e2f2', selectforeground='#111111'
        )
        self.crypto_out.pack(fill=tk.BOTH, expand=True)
        self.crypto_out.tag_configure('step', foreground='#0b5ed7', font=('Consolas', 8, 'bold'))
        self.crypto_out.tag_configure('result', foreground='#146c43', font=('Consolas', 8, 'bold'))
        self.crypto_out.tag_configure('error_tag', foreground='#b02a37', font=('Consolas', 8, 'bold'))
        self.crypto_out.tag_configure('header', foreground='#6f42c1', font=('Consolas', 9, 'bold'))

        # Output with steps
        out_frame = ttk.LabelFrame(container, text="Computation Steps & Results", padding="5")
        out_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.out_matrix = scrolledtext.ScrolledText(
            out_frame, height=16, width=70, wrap=tk.WORD, font=('Consolas', 9),
            selectbackground='#d9e2f2', selectforeground='#111111'
        )
        self.out_matrix.pack(fill=tk.BOTH, expand=True)

        def _text_wheel(widget, event):
            if event.delta:
                widget.yview_scroll(int(-event.delta / 120), "units")
            elif getattr(event, "num", None) == 4:
                widget.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                widget.yview_scroll(1, "units")
            return "break"

        # Keep wheel scrolling local to each output box.
        self.out_matrix.bind("<MouseWheel>", lambda e: _text_wheel(self.out_matrix, e))
        self.out_matrix.bind("<Button-4>", lambda e: _text_wheel(self.out_matrix, e))
        self.out_matrix.bind("<Button-5>", lambda e: _text_wheel(self.out_matrix, e))
        self.crypto_out.bind("<MouseWheel>", lambda e: _text_wheel(self.crypto_out, e))
        self.crypto_out.bind("<Button-4>", lambda e: _text_wheel(self.crypto_out, e))
        self.crypto_out.bind("<Button-5>", lambda e: _text_wheel(self.crypto_out, e))
        
        # Configure text tags for formatting
        self.out_matrix.tag_configure('step', foreground='#0b5ed7', font=('Consolas', 9, 'bold'))
        self.out_matrix.tag_configure('result', foreground='#146c43', font=('Consolas', 9, 'bold'))
        self.out_matrix.tag_configure('error_tag', foreground='#b02a37', font=('Consolas', 9, 'bold'))
        self.out_matrix.tag_configure('header', foreground='#6f42c1', font=('Consolas', 10, 'bold'))

    def on_operation_change(self):
        """Handle operation type change."""
        self.update_matrix_grid()
    
    def clear_matrix_output(self):
        """Clear the output text."""
        self.out_matrix.delete(1.0, tk.END)
        self.crypto_out.delete(1.0, tk.END)
    
    def load_matrix_example(self):
        """Load an example based on current operation."""
        op = self.matrix_op_var.get()
        
        if op in ["fully_encrypted_mv", "plaintext_matrix_enc_vector"]:
            # 3x3 rotation matrix example
            self.rows_var.set(3)
            self.cols_var.set(3)
            self.update_matrix_grid()
            
            # Set rotation matrix (45 degrees around Z axis)
            import math
            angle = math.pi / 4
            rotation = [
                [math.cos(angle), -math.sin(angle), 0],
                [math.sin(angle), math.cos(angle), 0],
                [0, 0, 1]
            ]
            for i, row in enumerate(rotation):
                for j, val in enumerate(row):
                    self.matrix_entries[i][j].delete(0, tk.END)
                    self.matrix_entries[i][j].insert(0, f"{val:.4f}")
            
            # Set vector
            vector = [1.0, 0.0, 0.0]
            for i, val in enumerate(vector):
                self.entry_v[i].delete(0, tk.END)
                self.entry_v[i].insert(0, str(val))
                
        elif op in ["vector_elementwise", "vector_dot"]:
            self.cols_var.set(4)
            self.update_matrix_grid()
            
            vec_a = [1.0, 2.0, 3.0, 4.0]
            vec_b = [2.0, 3.0, 4.0, 5.0]
            
            for i, val in enumerate(vec_a):
                self.entry_v[i].delete(0, tk.END)
                self.entry_v[i].insert(0, str(val))
            for i, val in enumerate(vec_b):
                self.entry_v2[i].delete(0, tk.END)
                self.entry_v2[i].insert(0, str(val))

    def update_matrix_grid(self, event=None):
        """Update the input grid based on selected dimensions and operation."""
        # Clear previous
        for widget in self.mv_container.winfo_children():
            widget.destroy()

        rows = self.rows_var.get()
        cols = self.cols_var.get()
        op = self.matrix_op_var.get()
        
        if op == "fully_encrypted_mv":
            # FULLY ENCRYPTED: Both matrix and vector are encrypted
            m_frame = ttk.LabelFrame(self.mv_container, text=f"Matrix ({rows}x{cols}) - Will be ENCRYPTED", padding="10")
            m_frame.pack(fill=tk.X, pady=5)
            
            # Column headers
            header_frame = ttk.Frame(m_frame)
            header_frame.pack()
            ttk.Label(header_frame, text="", width=3).pack(side=tk.LEFT)
            for c in range(cols):
                ttk.Label(header_frame, text=f"c{c+1}", width=8).pack(side=tk.LEFT)
            
            self.matrix_entries = []
            for r in range(rows):
                row_frame = ttk.Frame(m_frame)
                row_frame.pack()
                ttk.Label(row_frame, text=f"r{r+1}", width=3).pack(side=tk.LEFT)
                row_entries = []
                for c in range(cols):
                    e = ttk.Entry(row_frame, width=8)
                    val = str(float(r * cols + c + 1))  # Sequential values
                    e.insert(0, val)
                    e.pack(side=tk.LEFT, padx=2, pady=1)
                    row_entries.append(e)
                self.matrix_entries.append(row_entries)

            # Vector input
            v_frame = ttk.LabelFrame(self.mv_container, text=f"Input Vector ({cols}D) - Will be ENCRYPTED", padding="10")
            v_frame.pack(fill=tk.X, pady=5)
            
            self.entry_v = []
            for i in range(cols):
                frame = ttk.Frame(v_frame)
                frame.pack(side=tk.LEFT, padx=2)
                ttk.Label(frame, text=f"v{i+1}").pack()
                e = ttk.Entry(frame, width=8)
                e.insert(0, str(float(i + 1)))
                e.pack()
                self.entry_v.append(e)
                
            # Info label
            info = ttk.Label(self.mv_container, 
                           text="TRUE FHE: E(M) @ E(v) → E(result). Both matrix AND vector are encrypted!",
                           font=('Helvetica', 9, 'italic'), foreground='green')
            info.pack(pady=5)
            
        elif op == "plaintext_matrix_enc_vector":
            # Plaintext matrix, encrypted vector
            m_frame = ttk.LabelFrame(self.mv_container, text=f"Matrix ({rows}x{cols}) - Plaintext", padding="10")
            m_frame.pack(fill=tk.X, pady=5)
            
            # Column headers
            header_frame = ttk.Frame(m_frame)
            header_frame.pack()
            ttk.Label(header_frame, text="", width=3).pack(side=tk.LEFT)
            for c in range(cols):
                ttk.Label(header_frame, text=f"c{c+1}", width=8).pack(side=tk.LEFT)
            
            self.matrix_entries = []
            for r in range(rows):
                row_frame = ttk.Frame(m_frame)
                row_frame.pack()
                ttk.Label(row_frame, text=f"r{r+1}", width=3).pack(side=tk.LEFT)
                row_entries = []
                for c in range(cols):
                    e = ttk.Entry(row_frame, width=8)
                    val = "1.0" if r == c else "0.0"
                    e.insert(0, val)
                    e.pack(side=tk.LEFT, padx=2, pady=1)
                    row_entries.append(e)
                self.matrix_entries.append(row_entries)

            # Vector input
            v_frame = ttk.LabelFrame(self.mv_container, text=f"Input Vector ({cols}D) - Will be ENCRYPTED", padding="10")
            v_frame.pack(fill=tk.X, pady=5)
            
            self.entry_v = []
            for i in range(cols):
                frame = ttk.Frame(v_frame)
                frame.pack(side=tk.LEFT, padx=2)
                ttk.Label(frame, text=f"v{i+1}").pack()
                e = ttk.Entry(frame, width=8)
                e.insert(0, "1.0")
                e.pack()
                self.entry_v.append(e)
                
            # Info label
            info = ttk.Label(self.mv_container, 
                           text="M @ E(v) → E(result). Matrix is plaintext, vector is encrypted.",
                           font=('Helvetica', 9, 'italic'))
            info.pack(pady=5)
            
        elif op in ["vector_elementwise", "vector_dot"]:
            # Two vector inputs for vector-vector operations
            size = cols  # Use cols as vector size
            
            # Vector A
            va_frame = ttk.LabelFrame(self.mv_container, text=f"Vector A ({size}D) - ENCRYPTED", padding="10")
            va_frame.pack(fill=tk.X, pady=5)
            
            self.entry_v = []
            for i in range(size):
                frame = ttk.Frame(va_frame)
                frame.pack(side=tk.LEFT, padx=2)
                ttk.Label(frame, text=f"a{i+1}").pack()
                e = ttk.Entry(frame, width=8)
                e.insert(0, str(i + 1.0))
                e.pack()
                self.entry_v.append(e)
            
            # Vector B
            vb_frame = ttk.LabelFrame(self.mv_container, text=f"Vector B ({size}D) - ENCRYPTED", padding="10")
            vb_frame.pack(fill=tk.X, pady=5)
            
            self.entry_v2 = []
            for i in range(size):
                frame = ttk.Frame(vb_frame)
                frame.pack(side=tk.LEFT, padx=2)
                ttk.Label(frame, text=f"b{i+1}").pack()
                e = ttk.Entry(frame, width=8)
                e.insert(0, str(i + 2.0))
                e.pack()
                self.entry_v2.append(e)
            
            # Info label
            if op == "vector_elementwise":
                info_text = "Result = E(a) * E(b) = E([a1*b1, a2*b2, ...]) - True ciphertext-ciphertext multiplication"
            else:
                info_text = "Result = E(a) · E(b) = E(sum(ai*bi)) - Homomorphic dot product"
            info = ttk.Label(self.mv_container, text=info_text, font=('Helvetica', 9, 'italic'))
            info.pack(pady=5)

    # --- TAB 3: NOISE DEMO ---
    def build_noise_tab(self):
        container = ttk.Frame(self.tab_noise, padding="20")
        container.pack(fill=tk.BOTH, expand=True)

        intro = ttk.Label(
            container,
            text=(
                "Research-grade CKKS depth stress test:\n"
                "Requested multiplications are used to AUTO-configure FHE parameters.\n"
                "Graph shows measured absolute/relative decryption error per operation (ciphertext x ciphertext)."
            ),
            justify=tk.CENTER
        )
        intro.pack(pady=10)

        ctrl = ttk.Frame(container)
        ctrl.pack(pady=5)

        ttk.Label(ctrl, text="Multiplications:").pack(side=tk.LEFT)
        self.mult_depth = tk.IntVar(value=10)
        self.mult_spin = ttk.Spinbox(
            ctrl, from_=1, to=50, textvariable=self.mult_depth, width=5, command=self.on_depth_change
        )
        self.mult_spin.pack(side=tk.LEFT, padx=5)
        self.mult_spin.bind('<Return>', self.on_depth_change)

        self.fhe_config_var = tk.StringVar(value="Auto FHE config pending...")
        ttk.Label(ctrl, textvariable=self.fhe_config_var, foreground="#1f5d99").pack(side=tk.LEFT, padx=(12, 5))

        self.btn_run_stress = ttk.Button(ctrl, text="Run Stress Test", command=self.run_stress_test, state="disabled")
        self.btn_run_stress.pack(side=tk.LEFT, padx=10)

        # Plot
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Decryption Error vs. Multiplicative Depth")
        self.ax.set_xlabel("Number of Multiplications")
        self.ax.set_ylabel("Error (Log Scale)")
        self.ax.set_yscale("log")
        self.canvas = FigureCanvasTkAgg(self.fig, master=container)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.on_depth_change()

    def _recommend_fhe_params(self, requested_mults: int):
        """Pick CKKS params from requested multiplicative depth (no bootstrapping)."""
        if requested_mults < 1:
            raise ValueError("Multiplications must be at least 1.")

        # Conservative limits for 128-bit security in this project setup.
        # 16384: ~438 bits, 32768: ~881 bits.
        poly_mod = 16384 if requested_mults <= 8 else 32768
        max_total_bits = 438 if poly_mod == 16384 else 881
        edge_prime_bits = 50  # First/last primes in chain
        overhead_bits = edge_prime_bits * 2

        available_middle_bits = max_total_bits - overhead_bits
        middle_prime_bits = available_middle_bits // requested_mults
        middle_prime_bits = min(40, middle_prime_bits)  # Cap for practical precision/perf balance

        if middle_prime_bits < 30:
            raise ValueError(
                f"Requested depth={requested_mults} exceeds practical leveled CKKS limits without bootstrapping "
                f"(minimum viable middle prime would be {middle_prime_bits} bits)."
            )

        coeff_mod = [edge_prime_bits] + [middle_prime_bits] * requested_mults + [edge_prime_bits]
        total_bits = sum(coeff_mod)

        # Keep scale safely below middle prime size to avoid fast scale mismatch failures.
        scale_bits = max(20, min(30, middle_prime_bits - 5))

        return {
            "poly_mod": poly_mod,
            "coeff_mod": coeff_mod,
            "middle_prime_bits": middle_prime_bits,
            "scale_bits": scale_bits,
            "total_bits": total_bits,
            "supported_mults": requested_mults,
        }

    def on_depth_change(self, event=None):
        """Update the auto-configuration preview based on requested multiplications."""
        try:
            depth = int(self.mult_depth.get())
            cfg = self._recommend_fhe_params(depth)
            self.fhe_config_var.set(
                "Auto FHE: "
                f"N={cfg['poly_mod']}, coeff=[50 + {cfg['middle_prime_bits']}x{depth} + 50] "
                f"({cfg['total_bits']} bits), scale=2^{cfg['scale_bits']}"
            )
            self.btn_run_stress["state"] = "normal"
        except Exception as e:
            self.fhe_config_var.set(f"Auto FHE unsupported for this depth: {e}")
            self.btn_run_stress["state"] = "disabled"

    # --- LOGIC ---

    def _detect_log_tag(self, msg: str):
        """Infer a default log tag when one isn't explicitly provided."""
        text = msg.strip().lower()
        if "error" in text or "traceback" in text:
            return 'error_tag'
        if text.startswith("step ") or text.startswith("--- homomorphic"):
            return 'step'
        if "result" in text or "expected" in text or "decrypted" in text or "numerical error" in text:
            return 'result'
        if "=" in msg or "fully homomorphic" in text or text.startswith("--- results"):
            return 'header'
        return None

    def _append_log(self, widget, msg, tag=None):
        """Append text, enforce end scroll, and auto-highlight key lines."""
        resolved_tag = tag if tag is not None else self._detect_log_tag(msg)
        text = msg if msg.endswith("\n") else msg + "\n"
        if resolved_tag:
            widget.insert(tk.END, text, resolved_tag)
        else:
            widget.insert(tk.END, text)
        # Force viewport to follow live computation output.
        widget.see(tk.END)
        widget.yview_moveto(1.0)
        widget.update_idletasks()

    def _profile_mode_label(self, op: str) -> str:
        labels = {
            "fully_encrypted_mv": "E(M) @ E(v)",
            "plaintext_matrix_enc_vector": "M @ E(v)",
            "vector_elementwise": "E(a) * E(b)",
            "vector_dot": "E(a) · E(b)",
        }
        return labels.get(op, op)

    def _reset_profile_panel(self, op: str):
        self.profile_vars["mode"].set(self._profile_mode_label(op))
        self.profile_vars["encrypt"].set("Running...")
        self.profile_vars["multiply"].set("Running...")
        self.profile_vars["rescale"].set("Auto (included in multiply)")
        self.profile_vars["decrypt"].set("Running...")
        self.profile_vars["total"].set("Running...")
        self.profile_vars["throughput"].set("Running...")

    def _update_profile_panel(self, profile: Dict[str, str]):
        for key, value in profile.items():
            if key in self.profile_vars:
                self.profile_vars[key].set(value)

    def _append_crypto_log(self, msg, tag=None):
        self._append_log(self.crypto_out, msg, tag)

    def _on_toggle_full_ciphertext(self):
        self.show_full_ciphertext = bool(self.show_full_cipher_var.get())

    def _format_ciphertext(self, enc_obj: EncryptedDemand) -> str:
        if self.show_full_ciphertext:
            return enc_obj.get_display_ciphertext(max_length=10_000_000)
        return enc_obj.get_display_ciphertext(max_length=140)

    def _log_encrypted_artifact(self, engine: SmartGridFHE, label: str, enc_obj: EncryptedDemand):
        """Log ciphertext material and basic integrity checks for research visibility."""
        verified = engine.verify_integrity(enc_obj)
        preview = self._format_ciphertext(enc_obj)
        self.root.after(0, lambda l=label: self._append_crypto_log(f"\n[{l}]", 'header'))
        self.root.after(0, lambda e=enc_obj: self._append_crypto_log(
            f"agent_id={e.agent_id} | size={e.get_size_kb():.2f} KB | vector_size={e.vector_size}", 'step'
        ))
        self.root.after(0, lambda e=enc_obj: self._append_crypto_log(
            f"checksum={e.checksum} | integrity_verified={verified}", 'result' if verified else 'error_tag'
        ))
        self.root.after(0, lambda p=preview: self._append_crypto_log(f"ciphertext(base64)={p}"))

    def run_matrix_transform(self):
        """Execute fully homomorphic matrix/vector operation with detailed step logging."""
        threading.Thread(target=self._matrix_transform_worker, daemon=True).start()
    
    def _matrix_transform_worker(self):
        """Worker thread for matrix operations using project's SmartGridFHE."""
        try:
            op = self.matrix_op_var.get()
            rows = self.rows_var.get()
            cols = self.cols_var.get()
            total_start = time.perf_counter()
            timing_encrypt = 0.0
            timing_multiply = 0.0
            timing_decrypt = 0.0
            cipher_mult_ops = 0
            output_count = 0
            
            # Clear output
            self.root.after(0, lambda: self.out_matrix.delete(1.0, tk.END))
            self.root.after(0, lambda: self.crypto_out.delete(1.0, tk.END))
            self.root.after(0, lambda op_val=op: self._reset_profile_panel(op_val))
            
            # Use project's SmartGridFHE with standard parameters
            # poly_modulus_degree=16384, coeff_mod=[60, 40, 40, 40, 60] as per project docs
            self.status_var.set("Initializing SmartGridFHE (CKKS, 128-bit security)...")
            self.root.update_idletasks()
            
            # Create utility (has secret key for decryption) and coordinator (public only)
            utility = SmartGridFHE()  # Has secret key
            public_ctx = utility.get_public_context()
            coordinator = SmartGridFHE.from_context(public_ctx)  # Public only - cannot decrypt
            algebra = SecureLinearAlgebra(coordinator)
            ctx_hash = utility.get_context_hash()
            self.root.after(0, lambda: self._append_crypto_log("=" * 72, 'header'))
            self.root.after(0, lambda: self._append_crypto_log("CRYPTOGRAPHIC SESSION DETAILS", 'header'))
            self.root.after(0, lambda h=ctx_hash: self._append_crypto_log(f"context_hash={h}", 'step'))
            self.root.after(0, lambda: self._append_crypto_log(
                f"utility_has_secret_key={utility.is_private()} | coordinator_has_secret_key={coordinator.is_private()}",
                'step'
            ))
            self.root.after(0, lambda: self._append_crypto_log("=" * 72, 'header'))
            
            def log_step(msg):
                """Thread-safe logging."""
                self.root.after(0, lambda m=msg: self._append_matrix_log(m, 'step'))
            
            if op == "fully_encrypted_mv":
                # FULLY HOMOMORPHIC: Both matrix AND vector are encrypted
                V = [float(e.get()) for e in self.entry_v]
                M = []
                for r in range(rows):
                    row = [float(self.matrix_entries[r][c].get()) for c in range(cols)]
                    M.append(row)
                
                # Log header
                self.root.after(0, lambda: self._append_matrix_log(
                    "=" * 60 + "\nTRUE FULLY HOMOMORPHIC MATRIX-VECTOR MULTIPLICATION\n" + 
                    "E(M) @ E(v) → E(result)\n" + "=" * 60, 'header'))
                self.root.after(0, lambda: self._append_matrix_log(
                    f"\nSecurity: 128-bit | poly_modulus_degree: 16384 | scale: 2^40", 'step'))
                self.root.after(0, lambda: self._append_matrix_log(f"\nMatrix ({rows}x{cols}) [Will be ENCRYPTED]:", 'header'))
                for i, row in enumerate(M):
                    self.root.after(0, lambda r=row, i=i: self._append_matrix_log(f"  Row {i+1}: {[f'{x:.4f}' for x in r]}"))
                self.root.after(0, lambda: self._append_matrix_log(f"\nInput Vector [Will be ENCRYPTED]: {V}", 'header'))
                
                # Compute expected result
                expected = np.dot(M, V)
                self.root.after(0, lambda: self._append_matrix_log(f"Expected (plaintext computation): {expected.tolist()}\n"))
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- HOMOMORPHIC COMPUTATION STEPS ---\n", 'header'))
                
                # Step 1: Encrypt each row of the matrix
                self.status_var.set("Step 1: Encrypting matrix rows...")
                log_step("Step 1: Encrypting MATRIX (each row as separate ciphertext)")
                enc_matrix_rows: List[EncryptedDemand] = []
                total_matrix_size = 0
                t0 = time.perf_counter()
                for i, row in enumerate(M):
                    enc_row = coordinator.encrypt_demand(row, f"matrix_row_{i}")
                    enc_matrix_rows.append(enc_row)
                    total_matrix_size += enc_row.get_size_kb()
                    log_step(f"        E(row_{i+1}): {enc_row.get_size_kb():.1f} KB | checksum: {enc_row.checksum}")
                    self._log_encrypted_artifact(coordinator, f"Encrypted Matrix Row {i+1}", enc_row)
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        Total encrypted matrix size: {total_matrix_size:.1f} KB")
                time.sleep(0.1)
                
                # Step 2: Encrypt the vector
                self.status_var.set("Step 2: Encrypting input vector...")
                log_step("\nStep 2: Encrypting INPUT VECTOR")
                t0 = time.perf_counter()
                enc_V: EncryptedDemand = coordinator.encrypt_demand(V, "input_vector")
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        E(v): {enc_V.get_size_kb():.1f} KB | checksum: {enc_V.checksum}")
                self._log_encrypted_artifact(coordinator, "Encrypted Input Vector", enc_V)
                time.sleep(0.1)
                
                # Step 3: Fully homomorphic matrix-vector multiplication
                self.status_var.set("Step 3: Computing E(M) @ E(v)...")
                log_step("\nStep 3: FULLY HOMOMORPHIC Matrix-Vector Multiplication")
                log_step("        Computing E(row_i) · E(v) for each row (encrypted dot products)")
                
                t0 = time.perf_counter()
                enc_results: List[EncryptedDemand] = algebra.fully_homomorphic_matrix_vector_multiply(
                    enc_matrix_rows, enc_V, rows, cols, log_step
                )
                timing_multiply += time.perf_counter() - t0
                cipher_mult_ops += rows
                output_count = rows
                time.sleep(0.1)
                
                # Step 4: Decrypt results
                self.status_var.set("Step 4: Decrypting results...")
                log_step("\nStep 4: Utility decrypts each result element (has SECRET key)")
                decrypted = []
                t0 = time.perf_counter()
                for i, enc_res in enumerate(enc_results):
                    dec_val = utility.decrypt_demand(enc_res)[0]
                    decrypted.append(dec_val)
                    log_step(f"        Decrypt E(result[{i+1}]) → {dec_val:.6f}")
                    self._log_encrypted_artifact(coordinator, f"Encrypted Result Element {i+1}", enc_res)
                timing_decrypt += time.perf_counter() - t0
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- RESULTS ---\n", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Decrypted Result: {[f'{x:.6f}' for x in decrypted]}", 'result'))
                self.root.after(0, lambda: self._append_matrix_log(f"Expected Result:  {[f'{x:.6f}' for x in expected.tolist()]}", 'result'))
                
                error = np.linalg.norm(np.array(decrypted) - expected)
                self.root.after(0, lambda: self._append_matrix_log(f"Numerical Error:  {error:.2e} (CKKS approximate arithmetic)", 'result'))
                self.root.after(0, lambda: self._append_matrix_log(
                    f"\nTotal Encrypted Data: {total_matrix_size + enc_V.get_size_kb():.1f} KB", 'step'))
                
            elif op == "plaintext_matrix_enc_vector":
                # Plaintext matrix × Encrypted vector (works for any shape)
                V = [float(e.get()) for e in self.entry_v]
                M = []
                for r in range(rows):
                    row = [float(self.matrix_entries[r][c].get()) for c in range(cols)]
                    M.append(row)
                
                # Log header
                self.root.after(0, lambda: self._append_matrix_log(
                    "=" * 60 + "\nPLAINTEXT MATRIX × ENCRYPTED VECTOR\n" + 
                    "M @ E(v) → E(result)\n" + "=" * 60, 'header'))
                self.root.after(0, lambda: self._append_matrix_log(
                    f"\nSecurity: 128-bit | poly_modulus_degree: 16384 | scale: 2^40", 'step'))
                self.root.after(0, lambda: self._append_matrix_log(f"\nMatrix ({rows}x{cols}) [Plaintext]:", 'header'))
                for i, row in enumerate(M):
                    self.root.after(0, lambda r=row, i=i: self._append_matrix_log(f"  Row {i+1}: {[f'{x:.4f}' for x in r]}"))
                self.root.after(0, lambda: self._append_matrix_log(f"\nInput Vector [ENCRYPTED]: {V}", 'header'))
                
                # Compute expected result
                expected = np.dot(M, V)
                self.root.after(0, lambda: self._append_matrix_log(f"Expected (plaintext computation): {expected.tolist()}\n"))
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- HOMOMORPHIC COMPUTATION STEPS ---\n", 'header'))
                
                # Step 1: Encrypt vector
                self.status_var.set("Step 1: Encrypting input vector...")
                log_step("Step 1: Encrypting input vector")
                t0 = time.perf_counter()
                enc_V: EncryptedDemand = coordinator.encrypt_demand(V, "input_vector")
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        E(v): {enc_V.get_size_kb():.1f} KB | checksum: {enc_V.checksum}")
                self._log_encrypted_artifact(coordinator, "Encrypted Input Vector", enc_V)
                time.sleep(0.1)
                
                # Step 2: Compute M @ E(v) row by row
                self.status_var.set("Step 2: Computing M @ E(v)...")
                log_step("\nStep 2: Computing M @ E(v) homomorphically")
                
                t0 = time.perf_counter()
                enc_results: List[EncryptedDemand] = algebra.plaintext_matrix_encrypted_vector_multiply(
                    M, enc_V, rows, cols, log_step
                )
                timing_multiply += time.perf_counter() - t0
                output_count = rows
                time.sleep(0.1)
                
                # Step 3: Decrypt results
                self.status_var.set("Step 3: Decrypting results...")
                log_step("\nStep 3: Utility decrypts results")
                decrypted = []
                t0 = time.perf_counter()
                for i, enc_res in enumerate(enc_results):
                    dec_val = utility.decrypt_demand(enc_res)[0]
                    decrypted.append(dec_val)
                    log_step(f"        Decrypt E(result[{i+1}]) → {dec_val:.6f}")
                    self._log_encrypted_artifact(coordinator, f"Encrypted Result Element {i+1}", enc_res)
                timing_decrypt += time.perf_counter() - t0
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- RESULTS ---\n", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Decrypted Result: {[f'{x:.6f}' for x in decrypted]}", 'result'))
                self.root.after(0, lambda: self._append_matrix_log(f"Expected Result:  {[f'{x:.6f}' for x in expected.tolist()]}", 'result'))
                
                error = np.linalg.norm(np.array(decrypted) - expected)
                self.root.after(0, lambda: self._append_matrix_log(f"Numerical Error:  {error:.2e}", 'result'))
                
            elif op == "vector_elementwise":
                # Vector-vector element-wise multiplication using compute_elementwise_product
                V1 = [float(e.get()) for e in self.entry_v]
                V2 = [float(e.get()) for e in self.entry_v2]
                size = len(V1)
                
                self.root.after(0, lambda: self._append_matrix_log(
                    "=" * 60 + "\nFULLY HOMOMORPHIC ELEMENT-WISE MULTIPLICATION\n" +
                    "E(a) * E(b) = E(a * b) - Ciphertext × Ciphertext\n" + "=" * 60, 'header'))
                self.root.after(0, lambda: self._append_matrix_log(
                    f"\nSecurity: 128-bit | poly_modulus_degree: 16384 | scale: 2^40", 'step'))
                self.root.after(0, lambda: self._append_matrix_log(f"\nVector A [ENCRYPTED]: {V1}", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Vector B [ENCRYPTED]: {V2}", 'header'))
                
                expected = np.array(V1) * np.array(V2)
                self.root.after(0, lambda: self._append_matrix_log(f"Expected (plaintext): {expected.tolist()}\n"))
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- HOMOMORPHIC COMPUTATION STEPS ---\n", 'header'))
                
                # Step 1: Encrypt both vectors
                self.status_var.set("Step 1: Encrypting vectors...")
                log_step("Step 1: Agent A encrypts vector A using PUBLIC context")
                t0 = time.perf_counter()
                enc_a: EncryptedDemand = coordinator.encrypt_demand(V1, "vector_a")
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        E(a) ciphertext: {enc_a.get_size_kb():.1f} KB")
                self._log_encrypted_artifact(coordinator, "Encrypted Vector A", enc_a)
                time.sleep(0.1)
                
                log_step("\nStep 2: Agent B encrypts vector B using PUBLIC context")
                t0 = time.perf_counter()
                enc_b: EncryptedDemand = coordinator.encrypt_demand(V2, "vector_b")
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        E(b) ciphertext: {enc_b.get_size_kb():.1f} KB")
                self._log_encrypted_artifact(coordinator, "Encrypted Vector B", enc_b)
                time.sleep(0.1)
                
                # Step 2: Homomorphic multiplication (ciphertext * ciphertext)
                self.status_var.set("Step 3: Computing E(a) * E(b)...")
                log_step("\nStep 3: Homomorphic ciphertext-ciphertext multiplication")
                log_step("        E(a) × E(b) = E(a × b)")
                log_step("        Auto-relinearization reduces ciphertext size")
                log_step("        Auto-rescaling manages noise growth")
                
                t0 = time.perf_counter()
                enc_result: EncryptedDemand = coordinator.compute_elementwise_product(enc_a, enc_b)
                timing_multiply += time.perf_counter() - t0
                cipher_mult_ops += 1
                output_count = size
                log_step(f"        Result ciphertext: {enc_result.get_size_kb():.1f} KB")
                self._log_encrypted_artifact(coordinator, "Encrypted Element-wise Result", enc_result)
                time.sleep(0.1)
                
                # Step 3: Decrypt
                self.status_var.set("Step 4: Decrypting result...")
                log_step("\nStep 4: Utility decrypts result (SECRET key required)")
                t0 = time.perf_counter()
                decrypted = utility.decrypt_demand(enc_result)[:size]
                timing_decrypt += time.perf_counter() - t0
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- RESULTS ---\n", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Decrypted Result: {[f'{x:.6f}' for x in decrypted]}", 'result'))
                self.root.after(0, lambda: self._append_matrix_log(f"Expected Result:  {[f'{x:.6f}' for x in expected.tolist()]}", 'result'))
                
                error = np.linalg.norm(np.array(decrypted) - expected)
                self.root.after(0, lambda: self._append_matrix_log(f"Numerical Error:  {error:.2e}", 'result'))
                
            elif op == "vector_dot":
                # Vector dot product using compute_dot_product
                V1 = [float(e.get()) for e in self.entry_v]
                V2 = [float(e.get()) for e in self.entry_v2]
                size = len(V1)
                
                self.root.after(0, lambda: self._append_matrix_log(
                    "=" * 60 + "\nFULLY HOMOMORPHIC DOT PRODUCT\n" +
                    "E(a) · E(b) = E(Σ aᵢ×bᵢ)\n" + "=" * 60, 'header'))
                self.root.after(0, lambda: self._append_matrix_log(
                    f"\nSecurity: 128-bit | poly_modulus_degree: 16384 | scale: 2^40", 'step'))
                self.root.after(0, lambda: self._append_matrix_log(f"\nVector A [ENCRYPTED]: {V1}", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Vector B [ENCRYPTED]: {V2}", 'header'))
                
                expected = np.dot(V1, V2)
                self.root.after(0, lambda: self._append_matrix_log(f"Expected (plaintext): {expected}\n"))
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- HOMOMORPHIC COMPUTATION STEPS ---\n", 'header'))
                
                # Step 1: Encrypt both vectors
                self.status_var.set("Step 1: Encrypting vectors...")
                log_step("Step 1: Agent A encrypts vector A")
                t0 = time.perf_counter()
                enc_a: EncryptedDemand = coordinator.encrypt_demand(V1, "vector_a")
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        E(a) ciphertext: {enc_a.get_size_kb():.1f} KB")
                self._log_encrypted_artifact(coordinator, "Encrypted Vector A", enc_a)
                time.sleep(0.1)
                
                log_step("\nStep 2: Agent B encrypts vector B")
                t0 = time.perf_counter()
                enc_b: EncryptedDemand = coordinator.encrypt_demand(V2, "vector_b")
                timing_encrypt += time.perf_counter() - t0
                log_step(f"        E(b) ciphertext: {enc_b.get_size_kb():.1f} KB")
                self._log_encrypted_artifact(coordinator, "Encrypted Vector B", enc_b)
                time.sleep(0.1)
                
                # Step 2: Homomorphic dot product
                self.status_var.set("Step 3: Computing dot product...")
                log_step("\nStep 3: Homomorphic dot product computation")
                log_step("        E(a) × E(b) element-wise → E([a₀b₀, a₁b₁, ...])")
                log_step("        sum(E(a×b)) → E(Σ aᵢbᵢ)")
                
                t0 = time.perf_counter()
                enc_result: EncryptedDemand = coordinator.compute_dot_product(enc_a, enc_b)
                timing_multiply += time.perf_counter() - t0
                cipher_mult_ops += 1
                output_count = 1
                log_step(f"        Result ciphertext: {enc_result.get_size_kb():.1f} KB")
                self._log_encrypted_artifact(coordinator, "Encrypted Dot-product Result", enc_result)
                time.sleep(0.1)
                
                # Step 3: Decrypt
                self.status_var.set("Step 4: Decrypting result...")
                log_step("\nStep 4: Utility decrypts scalar result")
                t0 = time.perf_counter()
                decrypted = utility.decrypt_demand(enc_result)[0]
                timing_decrypt += time.perf_counter() - t0
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- RESULTS ---\n", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Decrypted Result: {decrypted:.6f}", 'result'))
                self.root.after(0, lambda: self._append_matrix_log(f"Expected Result:  {expected:.6f}", 'result'))
                
                error = abs(decrypted - expected)
                self.root.after(0, lambda: self._append_matrix_log(f"Numerical Error:  {error:.2e}", 'result'))
            
            self.root.after(0, lambda: self._append_matrix_log(
                "\n\nComputation completed successfully!", 'result'))
            total_latency = time.perf_counter() - total_start
            rescale_note = (
                f"~{timing_multiply * 1000:.1f} ms (auto-rescale inside multiply)"
                if timing_multiply > 0 else "N/A"
            )
            throughput = output_count / total_latency if total_latency > 0 else 0.0
            ciph_mul_rate = cipher_mult_ops / total_latency if total_latency > 0 else 0.0
            profile = {
                "mode": self._profile_mode_label(op),
                "encrypt": f"{timing_encrypt * 1000:.1f} ms",
                "multiply": f"{timing_multiply * 1000:.1f} ms",
                "rescale": rescale_note,
                "decrypt": f"{timing_decrypt * 1000:.1f} ms",
                "total": f"{total_latency * 1000:.1f} ms",
                "throughput": f"{throughput:.2f} outputs/s | {ciph_mul_rate:.2f} ciph-mults/s",
            }
            self.root.after(0, lambda p=profile: self._update_profile_panel(p))
            self.status_var.set("Ready - Computation complete")

        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self._append_matrix_log(error_msg, 'error_tag'))
            self.root.after(0, lambda m=error_msg: self._append_crypto_log(m, 'error_tag'))
            total_latency = time.perf_counter() - total_start
            failed_profile = {
                "mode": self._profile_mode_label(op),
                "encrypt": f"{timing_encrypt * 1000:.1f} ms",
                "multiply": f"{timing_multiply * 1000:.1f} ms",
                "rescale": "Auto (included in multiply)",
                "decrypt": f"{timing_decrypt * 1000:.1f} ms",
                "total": f"{total_latency * 1000:.1f} ms (failed)",
                "throughput": "N/A",
            }
            self.root.after(0, lambda p=failed_profile: self._update_profile_panel(p))
            self.status_var.set(f"Error: {str(e)}")
    
    def _append_matrix_log(self, msg, tag=None):
        """Append message to matrix output with optional formatting."""
        self._append_log(self.out_matrix, msg, tag)

    def run_stress_test(self):
        threading.Thread(target=self._stress_test_worker).start()

    def _stress_test_worker(self):
        try:
            depth = self.mult_depth.get()
            val = 2.0

            cfg = self._recommend_fhe_params(depth)
            self.status_var.set(
                "Initializing auto FHE: "
                f"depth={depth}, N={cfg['poly_mod']}, {cfg['total_bits']} bits, scale=2^{cfg['scale_bits']}"
            )

            # Create FHE engine with auto-selected, depth-matched parameters.
            stress_utility = SmartGridFHE(
                poly_modulus_degree=cfg["poly_mod"],
                coeff_mod_bit_sizes=cfg["coeff_mod"],
                global_scale=2 ** cfg["scale_bits"]
            )
            
            # Encrypt initial value
            enc = stress_utility.encrypt_demand([val], "stress")
            
            abs_errors = []
            rel_errors = []
            x_axis = []
            
            curr_enc = enc
            curr_expected = val
            failed_at = None
            failure_reason = None
            multiplier = 1.125  # Meaningful repeated operation for depth/noise experiments.
            enc_multiplier = stress_utility.encrypt_demand([multiplier], "stress_multiplier")
            
            for i in range(1, depth + 1):
                self.status_var.set(f"Stress Test: Multiplication {i}/{depth}...")

                try:
                    # Fully homomorphic multiplication path: ciphertext x ciphertext.
                    curr_enc = stress_utility.multiply_encrypted(curr_enc, enc_multiplier)
                    curr_expected *= multiplier

                    # Decrypt and compute measured errors
                    res = stress_utility.decrypt_demand(curr_enc)[0]
                    abs_err = abs(res - curr_expected)
                    rel_err = abs_err / max(abs(curr_expected), 1e-12)

                    abs_errors.append(max(abs_err, 1e-18))
                    rel_errors.append(max(rel_err, 1e-18))
                    x_axis.append(i)

                    self.root.after(
                        10, self.update_plot, list(x_axis), list(abs_errors), list(rel_errors), failed_at, failure_reason
                    )
                except Exception as e:
                    failed_at = i
                    failure_reason = str(e)
                    self.root.after(
                        10, self.update_plot, list(x_axis), list(abs_errors), list(rel_errors), failed_at, failure_reason
                    )
                    break

                # Small delay to allow GUI to update and show progress
                time.sleep(0.05)
            
            if failed_at:
                self.status_var.set(
                    f"Stress Test stopped at multiplication {failed_at}: noise/depth limit reached ({failure_reason})"
                )
            else:
                self.status_var.set(
                    f"Stress Test complete: {depth} multiplications succeeded with auto depth configuration."
                )
            
        except Exception as e:
            print(f"Stress error: {e}")
            self.status_var.set(f"Stress Test Error: {e}")

    def update_plot(self, x, abs_y, rel_y, failure_step=None, failure_reason=None):
        self.ax.clear()
        self.ax.set_title("Measured CKKS Error vs. Operations")
        self.ax.set_xlabel("Operations")
        self.ax.set_ylabel("Error (Log Scale)")
        self.ax.set_yscale("log")

        if x and abs_y:
            self.ax.plot(x, abs_y, 'b-o', label='Absolute error |dec - expected|', markersize=5)
        if x and rel_y:
            self.ax.plot(x, rel_y, color='#2ca02c', marker='s', linestyle='--', label='Relative error', markersize=4)

        if failure_step is not None:
            self.ax.axvline(
                x=failure_step, color='red', linestyle='--', alpha=0.65,
                label=f'Failure at op {failure_step}'
            )
            if x and abs_y:
                top_y = max(max(abs_y), max(rel_y) if rel_y else max(abs_y))
                self.ax.annotate(
                    "Noise/depth limit reached",
                    xy=(failure_step, top_y),
                    xytext=(8, 8),
                    textcoords='offset points',
                    fontsize=8,
                    color='red'
                )

        self.ax.grid(True, alpha=0.3)
        if self.ax.get_legend_handles_labels()[0]:
            self.ax.legend(loc='upper left', fontsize=8)

        # Keep a stable floor for log-scale and auto-limit upper bound from data.
        all_errors = [v for v in abs_y + rel_y if v > 0]
        if all_errors:
            min_err = min(all_errors)
            max_err = max(all_errors)
            self.ax.set_ylim(max(min_err * 0.5, 1e-18), max_err * 5)
        
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = EncryptedVectorGUI(root)
    root.mainloop()
