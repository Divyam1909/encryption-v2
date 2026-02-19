import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import threading
import time
from typing import List
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
        self.btn_calc_cross["state"] = "normal"
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

        # Tab 1: Cross Product
        self.tab_cross = ttk.Frame(notebook)
        notebook.add(self.tab_cross, text="Physics (Cross Product)")
        self.build_cross_product_tab()

        # Tab 2: Matrix Transform (Flexible)
        self.tab_matrix = ttk.Frame(notebook)
        notebook.add(self.tab_matrix, text="Linear Algebra (Matrix)")
        self.build_matrix_tab()

        # Tab 3: Noise/Depth Demo
        self.tab_noise = ttk.Frame(notebook)
        notebook.add(self.tab_noise, text="Research: Noise & Depth")
        self.build_noise_tab()

    # --- TAB 1: CROSS PRODUCT ---
    def build_cross_product_tab(self):
        container = ttk.Frame(self.tab_cross, padding="20")
        container.pack(fill=tk.BOTH, expand=True)

        # Inputs
        input_frame = ttk.LabelFrame(container, text="Input Vectors (3D)", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # Vector A
        ttk.Label(input_frame, text="Position (r):").grid(row=0, column=0, padx=5, pady=5)
        self.entry_a = [ttk.Entry(input_frame, width=8) for _ in range(3)]
        vals_a = ["2.0", "5.0", "3.0"]
        for i, e in enumerate(self.entry_a):
            e.insert(0, vals_a[i])
            e.grid(row=0, column=i+1)
        ttk.Label(input_frame, text="(x, y, z)").grid(row=0, column=4, padx=5)

        # Vector B
        ttk.Label(input_frame, text="Force (F):").grid(row=1, column=0, padx=5, pady=5)
        self.entry_b = [ttk.Entry(input_frame, width=8) for _ in range(3)]
        vals_b = ["10.0", "0.0", "-5.0"]
        for i, e in enumerate(self.entry_b):
            e.insert(0, vals_b[i])
            e.grid(row=1, column=i+1)

        # Action
        self.btn_calc_cross = ttk.Button(container, text="Encrypt & Compute Torque", command=self.run_cross_product, state="disabled")
        self.btn_calc_cross.pack(pady=10)

        # Output
        self.out_cross = tk.Text(container, height=15, width=60)
        self.out_cross.pack(fill=tk.BOTH, expand=True)

    # --- TAB 2: MATRIX TRANSFORM ---
    def build_matrix_tab(self):
        container = ttk.Frame(self.tab_matrix, padding="10")
        container.pack(fill=tk.BOTH, expand=True)
        
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

        # Output with steps
        out_frame = ttk.LabelFrame(container, text="Computation Steps & Results", padding="5")
        out_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.out_matrix = scrolledtext.ScrolledText(out_frame, height=12, width=70, wrap=tk.WORD)
        self.out_matrix.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for formatting
        self.out_matrix.tag_configure('step', foreground='blue', font=('Courier', 9, 'bold'))
        self.out_matrix.tag_configure('result', foreground='green', font=('Courier', 10, 'bold'))
        self.out_matrix.tag_configure('error_tag', foreground='red')
        self.out_matrix.tag_configure('header', foreground='purple', font=('Courier', 10, 'bold'))

    def on_operation_change(self):
        """Handle operation type change."""
        self.update_matrix_grid()
    
    def clear_matrix_output(self):
        """Clear the output text."""
        self.out_matrix.delete(1.0, tk.END)
    
    def load_matrix_example(self):
        """Load an example based on current operation."""
        op = self.matrix_op_var.get()
        
        if op == "matrix_vector":
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

        intro = ttk.Label(container, text="Demonstrate 'Leveled' Homomorphic Encryption:\nMultiply a vector repeatedly until noise overwhelms the signal.\nThe coefficient modulus chain determines how many multiplications are possible.", justify=tk.CENTER)
        intro.pack(pady=10)

        ctrl = ttk.Frame(container)
        ctrl.pack(pady=5)

        ttk.Label(ctrl, text="Multiplications:").pack(side=tk.LEFT)
        self.mult_depth = tk.IntVar(value=10)
        ttk.Spinbox(ctrl, from_=1, to=50, textvariable=self.mult_depth, width=5).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(ctrl, text="  FHE Depth:").pack(side=tk.LEFT, padx=(10, 0))
        self.fhe_depth_var = tk.StringVar(value="standard")
        depth_combo = ttk.Combobox(ctrl, textvariable=self.fhe_depth_var, 
                                    values=["light (4-6 mults)", "standard (8-10 mults)", "deep (12-15 mults)", "ultra deep (18-20 mults)"],
                                    width=20, state="readonly")
        depth_combo.pack(side=tk.LEFT, padx=5)
        depth_combo.current(1)  # Default to standard (8-10 mults)

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

    # --- LOGIC ---

    def log_cross(self, msg):
        self.out_cross.insert(tk.END, msg + "\n")
        self.out_cross.see(tk.END)

    def log_matrix(self, msg):
        self.out_matrix.insert(tk.END, msg + "\n")
        self.out_matrix.see(tk.END)

    def run_cross_product(self):
        try:
            A = [float(e.get()) for e in self.entry_a]
            B = [float(e.get()) for e in self.entry_b]
            
            self.out_cross.delete(1.0, tk.END)
            self.log_cross(f"A: {A}, B: {B}")

            # Plaintext
            expected = np.cross(A, B)
            self.log_cross(f"Expected: {expected}")

            # Encrypted
            self.status_var.set("Computing...")
            self.root.update()
            
            enc_A = self.coordinator.encrypt_demand(A, "a")
            enc_B = self.coordinator.encrypt_demand(B, "b")
            
            enc_res = self.algebra.encrypted_cross_product(enc_A, enc_B)
            
            dec_res = self.utility.decrypt_demand(enc_res)[:3]
            self.log_cross(f"Decrypted: {np.array(dec_res)}")
            
            error = np.linalg.norm(dec_res - expected)
            self.log_cross(f"Error: {error:.2e}")
            self.status_var.set("Ready")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def run_matrix_transform(self):
        """Execute fully homomorphic matrix/vector operation with detailed step logging."""
        threading.Thread(target=self._matrix_transform_worker, daemon=True).start()
    
    def _matrix_transform_worker(self):
        """Worker thread for matrix operations using project's SmartGridFHE."""
        try:
            op = self.matrix_op_var.get()
            rows = self.rows_var.get()
            cols = self.cols_var.get()
            
            # Clear output
            self.root.after(0, lambda: self.out_matrix.delete(1.0, tk.END))
            
            # Use project's SmartGridFHE with standard parameters
            # poly_modulus_degree=16384, coeff_mod=[60, 40, 40, 40, 60] as per project docs
            self.status_var.set("Initializing SmartGridFHE (CKKS, 128-bit security)...")
            self.root.update_idletasks()
            
            # Create utility (has secret key for decryption) and coordinator (public only)
            utility = SmartGridFHE()  # Has secret key
            public_ctx = utility.get_public_context()
            coordinator = SmartGridFHE.from_context(public_ctx)  # Public only - cannot decrypt
            algebra = SecureLinearAlgebra(coordinator)
            
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
                for i, row in enumerate(M):
                    enc_row = coordinator.encrypt_demand(row, f"matrix_row_{i}")
                    enc_matrix_rows.append(enc_row)
                    total_matrix_size += enc_row.get_size_kb()
                    log_step(f"        E(row_{i+1}): {enc_row.get_size_kb():.1f} KB | checksum: {enc_row.checksum}")
                log_step(f"        Total encrypted matrix size: {total_matrix_size:.1f} KB")
                time.sleep(0.1)
                
                # Step 2: Encrypt the vector
                self.status_var.set("Step 2: Encrypting input vector...")
                log_step("\nStep 2: Encrypting INPUT VECTOR")
                enc_V: EncryptedDemand = coordinator.encrypt_demand(V, "input_vector")
                log_step(f"        E(v): {enc_V.get_size_kb():.1f} KB | checksum: {enc_V.checksum}")
                time.sleep(0.1)
                
                # Step 3: Fully homomorphic matrix-vector multiplication
                self.status_var.set("Step 3: Computing E(M) @ E(v)...")
                log_step("\nStep 3: FULLY HOMOMORPHIC Matrix-Vector Multiplication")
                log_step("        Computing E(row_i) · E(v) for each row (encrypted dot products)")
                
                enc_results: List[EncryptedDemand] = algebra.fully_homomorphic_matrix_vector_multiply(
                    enc_matrix_rows, enc_V, rows, cols, log_step
                )
                time.sleep(0.1)
                
                # Step 4: Decrypt results
                self.status_var.set("Step 4: Decrypting results...")
                log_step("\nStep 4: Utility decrypts each result element (has SECRET key)")
                decrypted = []
                for i, enc_res in enumerate(enc_results):
                    dec_val = utility.decrypt_demand(enc_res)[0]
                    decrypted.append(dec_val)
                    log_step(f"        Decrypt E(result[{i+1}]) → {dec_val:.6f}")
                
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
                enc_V: EncryptedDemand = coordinator.encrypt_demand(V, "input_vector")
                log_step(f"        E(v): {enc_V.get_size_kb():.1f} KB | checksum: {enc_V.checksum}")
                time.sleep(0.1)
                
                # Step 2: Compute M @ E(v) row by row
                self.status_var.set("Step 2: Computing M @ E(v)...")
                log_step("\nStep 2: Computing M @ E(v) homomorphically")
                
                enc_results: List[EncryptedDemand] = algebra.plaintext_matrix_encrypted_vector_multiply(
                    M, enc_V, rows, cols, log_step
                )
                time.sleep(0.1)
                
                # Step 3: Decrypt results
                self.status_var.set("Step 3: Decrypting results...")
                log_step("\nStep 3: Utility decrypts results")
                decrypted = []
                for i, enc_res in enumerate(enc_results):
                    dec_val = utility.decrypt_demand(enc_res)[0]
                    decrypted.append(dec_val)
                    log_step(f"        Decrypt E(result[{i+1}]) → {dec_val:.6f}")
                
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
                enc_a: EncryptedDemand = coordinator.encrypt_demand(V1, "vector_a")
                log_step(f"        E(a) ciphertext: {enc_a.get_size_kb():.1f} KB")
                time.sleep(0.1)
                
                log_step("\nStep 2: Agent B encrypts vector B using PUBLIC context")
                enc_b: EncryptedDemand = coordinator.encrypt_demand(V2, "vector_b")
                log_step(f"        E(b) ciphertext: {enc_b.get_size_kb():.1f} KB")
                time.sleep(0.1)
                
                # Step 2: Homomorphic multiplication (ciphertext * ciphertext)
                self.status_var.set("Step 3: Computing E(a) * E(b)...")
                log_step("\nStep 3: Homomorphic ciphertext-ciphertext multiplication")
                log_step("        E(a) × E(b) = E(a × b)")
                log_step("        Auto-relinearization reduces ciphertext size")
                log_step("        Auto-rescaling manages noise growth")
                
                enc_result: EncryptedDemand = coordinator.compute_elementwise_product(enc_a, enc_b)
                log_step(f"        Result ciphertext: {enc_result.get_size_kb():.1f} KB")
                time.sleep(0.1)
                
                # Step 3: Decrypt
                self.status_var.set("Step 4: Decrypting result...")
                log_step("\nStep 4: Utility decrypts result (SECRET key required)")
                decrypted = utility.decrypt_demand(enc_result)[:size]
                
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
                enc_a: EncryptedDemand = coordinator.encrypt_demand(V1, "vector_a")
                log_step(f"        E(a) ciphertext: {enc_a.get_size_kb():.1f} KB")
                time.sleep(0.1)
                
                log_step("\nStep 2: Agent B encrypts vector B")
                enc_b: EncryptedDemand = coordinator.encrypt_demand(V2, "vector_b")
                log_step(f"        E(b) ciphertext: {enc_b.get_size_kb():.1f} KB")
                time.sleep(0.1)
                
                # Step 2: Homomorphic dot product
                self.status_var.set("Step 3: Computing dot product...")
                log_step("\nStep 3: Homomorphic dot product computation")
                log_step("        E(a) × E(b) element-wise → E([a₀b₀, a₁b₁, ...])")
                log_step("        sum(E(a×b)) → E(Σ aᵢbᵢ)")
                
                enc_result: EncryptedDemand = coordinator.compute_dot_product(enc_a, enc_b)
                log_step(f"        Result ciphertext: {enc_result.get_size_kb():.1f} KB")
                time.sleep(0.1)
                
                # Step 3: Decrypt
                self.status_var.set("Step 4: Decrypting result...")
                log_step("\nStep 4: Utility decrypts scalar result")
                decrypted = utility.decrypt_demand(enc_result)[0]
                
                self.root.after(0, lambda: self._append_matrix_log("\n--- RESULTS ---\n", 'header'))
                self.root.after(0, lambda: self._append_matrix_log(f"Decrypted Result: {decrypted:.6f}", 'result'))
                self.root.after(0, lambda: self._append_matrix_log(f"Expected Result:  {expected:.6f}", 'result'))
                
                error = abs(decrypted - expected)
                self.root.after(0, lambda: self._append_matrix_log(f"Numerical Error:  {error:.2e}", 'result'))
            
            self.root.after(0, lambda: self._append_matrix_log(
                "\n\nComputation completed successfully!\n" +
                "Privacy preserved: Coordinator never saw plaintext values.", 'result'))
            self.status_var.set("Ready - Computation complete")

        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self._append_matrix_log(error_msg, 'error_tag'))
            self.status_var.set(f"Error: {str(e)}")
    
    def _append_matrix_log(self, msg, tag=None):
        """Append message to matrix output with optional formatting."""
        self.out_matrix.insert(tk.END, msg + "\n", tag)
        self.out_matrix.see(tk.END)

    def run_stress_test(self):
        threading.Thread(target=self._stress_test_worker).start()

    def _stress_test_worker(self):
        try:
            depth = self.mult_depth.get()
            val = 2.0
            
            # Determine coefficient modulus chain and poly_modulus_degree based on selected depth
            # Following project's cryptography_guide.md:
            # - poly_modulus_degree: 8192 or 16384 (128-bit security)
            # - coeff_mod determines multiplicative depth
            # - Total bits must be <= max for poly_modulus_degree
            #   For 8192: max ~218 bits, for 16384: max ~438 bits
            fhe_depth = self.fhe_depth_var.get()
            
            if "light" in fhe_depth:
                # Light depth: ~4-6 multiplications
                # poly_mod=16384: max ~438 bits total
                # [60, 40*5, 60] = 320 bits <= 438 ✓
                # Middle primes: 5 (allows ~5 mults)
                poly_mod = 16384
                coeff_mod = [60] + [40] * 5 + [60]  # 320 bits
                max_mults = 5
            elif "standard" in fhe_depth:
                # Standard depth: ~8-10 multiplications (DEFAULT)
                # poly_mod=32768: max ~880 bits total
                # [60, 40*10, 60] = 520 bits <= 880 ✓
                # Middle primes: 10 (allows ~10 mults)
                poly_mod = 32768
                coeff_mod = [60] + [40] * 10 + [60]  # 520 bits
                max_mults = 10
            elif "ultra" in fhe_depth:
                # Ultra deep: ~18-20 multiplications for extreme research
                # poly_mod=32768: max ~880 bits total
                # [60, 40*20, 60] = 920 > 880, use 35-bit primes
                # [50, 35*20, 50] = 800 bits <= 880 ✓
                # Middle primes: 20 (allows ~20 mults)
                poly_mod = 32768
                coeff_mod = [50] + [35] * 20 + [50]  # 800 bits
                max_mults = 20
            else:  # deep
                # Deep depth: ~12-15 multiplications
                # poly_mod=32768: max ~880 bits total
                # [60, 40*15, 60] = 720 bits <= 880 ✓
                # Middle primes: 15 (allows ~15 mults)
                poly_mod = 32768
                coeff_mod = [60] + [40] * 15 + [60]  # 720 bits
                max_mults = 15
            
            total_bits = sum(coeff_mod)
            self.status_var.set(f"Initializing FHE: poly_mod={poly_mod}, ~{max_mults} mult depth, {total_bits} total bits...")
            
            # Create a new FHE engine with the selected parameters for stress test
            stress_utility = SmartGridFHE(poly_modulus_degree=poly_mod, coeff_mod_bit_sizes=coeff_mod)
            
            # Encrypt initial value
            enc = stress_utility.encrypt_demand([val], "stress")
            
            errors = []
            x_axis = []
            
            curr_enc = enc
            curr_expected = val
            failed_at = None  # Track where we failed
            
            for i in range(1, depth + 1):
                self.status_var.set(f"Stress Test: Multiplication {i}/{depth}...")
                
                if failed_at is None:
                    try:
                        # Perform Multiplication
                        # We use multiply_plain with 1.0. This consumes depth (rescale) 
                        # but keeps value stable.
                        # Repeatedly doing this eventually exhausts the coefficient modulus chain.
                        curr_enc = stress_utility.multiply_plain(curr_enc, 1.0)
                        
                        # Decrypt to check error
                        res = stress_utility.decrypt_demand(curr_enc)[0]
                        err = abs(res - curr_expected)
                        errors.append(err + 1e-15) # Avoid log(0)
                        x_axis.append(i)
                        
                    except Exception as e:
                        print(f"Failed at step {i}: {e}")
                        failed_at = i
                        # Add the failure point with high error
                        errors.append(1e10)  # Large value for plot to indicate failure
                        x_axis.append(i)
                else:
                    # Already failed - continue filling with high error values
                    # to show the complete requested depth range
                    errors.append(1e10)
                    x_axis.append(i)
                
                # Update plot after each iteration (whether successful or not)
                self.root.after(10, self.update_plot, list(x_axis), list(errors))
                
                # Small delay to allow GUI to update and show progress
                time.sleep(0.05)
            
            if failed_at:
                self.status_var.set(f"Stress Test Complete. Noise exhausted at multiplication {failed_at}.")
            else:
                self.status_var.set("Stress Test Complete.")
            
        except Exception as e:
            print(f"Stress error: {e}")
            self.status_var.set(f"Stress Test Error: {e}")

    def update_plot(self, x, y):
        self.ax.clear()
        self.ax.set_title("Decryption Error vs. Operations")
        self.ax.set_xlabel("Operations")
        self.ax.set_ylabel("Error (Log Scale)")
        self.ax.set_yscale("log")
        
        # Separate successful operations from failed ones
        success_x = []
        success_y = []
        fail_x = []
        fail_y = []
        
        for xi, yi in zip(x, y):
            if yi >= 1e9:  # Failed operations (high error marker)
                fail_x.append(xi)
                fail_y.append(yi)
            else:
                success_x.append(xi)
                success_y.append(yi)
        
        # Plot successful operations in blue
        if success_x:
            self.ax.plot(success_x, success_y, 'b-o', label='Successful', markersize=6)
        
        # Plot failed operations in red
        if fail_x:
            self.ax.plot(fail_x, fail_y, 'r-x', label='Noise Exhausted', markersize=8, linewidth=2)
            
            # Add a vertical line at the failure point
            if success_x:
                failure_point = min(fail_x)
                self.ax.axvline(x=failure_point, color='red', linestyle='--', alpha=0.5, 
                               label=f'Noise limit (~{failure_point-1} mults)')
        
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc='upper left', fontsize=8)
        
        # Set y-axis limits for better visualization
        if success_y:
            min_err = min(success_y)
            self.ax.set_ylim(min_err * 0.1, 1e12)
        
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = EncryptedVectorGUI(root)
    root.mainloop()
