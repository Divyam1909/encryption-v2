import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import threading
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from core.fhe_engine import SmartGridFHE
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
        container = ttk.Frame(self.tab_matrix, padding="20")
        container.pack(fill=tk.BOTH, expand=True)

        # Controls
        ctrl_frame = ttk.Frame(container)
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(ctrl_frame, text="Dimension:").pack(side=tk.LEFT)
        self.dim_var = tk.IntVar(value=3)
        self.dim_combo = ttk.Combobox(ctrl_frame, textvariable=self.dim_var, values=[2, 3, 4], width=5, state="readonly")
        self.dim_combo.pack(side=tk.LEFT, padx=5)
        self.dim_combo.bind("<<ComboboxSelected>>", self.update_matrix_grid)

        # Matrix/Vector Container
        self.mv_container = ttk.Frame(container)
        self.mv_container.pack(fill=tk.BOTH, expand=True)
        
        self.update_matrix_grid() # Initial build

        # Action
        self.btn_calc_matrix = ttk.Button(container, text="Encrypt & Transform", command=self.run_matrix_transform, state="disabled")
        self.btn_calc_matrix.pack(pady=10)

        # Output
        self.out_matrix = tk.Text(container, height=10, width=60)
        self.out_matrix.pack(fill=tk.BOTH, expand=True)

    def update_matrix_grid(self, event=None):
        # Clear previous
        for widget in self.mv_container.winfo_children():
            widget.destroy()

        dim = self.dim_var.get()

        # Vector Input
        v_frame = ttk.LabelFrame(self.mv_container, text=f"Input Vector ({dim}D)", padding="10")
        v_frame.pack(fill=tk.X, pady=5)
        
        self.entry_v = []
        for i in range(dim):
            e = ttk.Entry(v_frame, width=8)
            e.insert(0, "1.0") # Default
            e.pack(side=tk.LEFT, padx=2)
            self.entry_v.append(e)

        # Matrix Input
        m_frame = ttk.LabelFrame(self.mv_container, text=f"Transformation Matrix ({dim}x{dim})", padding="10")
        m_frame.pack(fill=tk.X, pady=5)

        self.matrix_entries = []
        # Identity matrix default
        for r in range(dim):
            row_entries = []
            frame_row = ttk.Frame(m_frame)
            frame_row.pack()
            for c in range(dim):
                e = ttk.Entry(frame_row, width=8)
                val = "1.0" if r == c else "0.0"
                e.insert(0, val)
                e.pack(side=tk.LEFT, padx=2, pady=2)
                row_entries.append(e)
            self.matrix_entries.append(row_entries)

    # --- TAB 3: NOISE DEMO ---
    def build_noise_tab(self):
        container = ttk.Frame(self.tab_noise, padding="20")
        container.pack(fill=tk.BOTH, expand=True)

        intro = ttk.Label(container, text="Demonstrate 'Leveled' Homomorphic Encryption:\nMultiply a vector repeatedly until noise overwhelms the signal.", justify=tk.CENTER)
        intro.pack(pady=10)

        ctrl = ttk.Frame(container)
        ctrl.pack(pady=5)

        ttk.Label(ctrl, text="Multiplications:").pack(side=tk.LEFT)
        self.mult_depth = tk.IntVar(value=10)
        ttk.Spinbox(ctrl, from_=1, to=50, textvariable=self.mult_depth, width=5).pack(side=tk.LEFT, padx=5)

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
        try:
            dim = self.dim_var.get()
            V = [float(e.get()) for e in self.entry_v]
            
            M = []
            for r in range(dim):
                row = []
                for c in range(dim):
                    row.append(float(self.matrix_entries[r][c].get()))
                M.append(row)
            
            self.out_matrix.delete(1.0, tk.END)
            self.log_matrix(f"Matrix ({dim}x{dim}): Input {V}")
            
            # Plaintext
            expected = np.dot(M, V)
            self.log_matrix(f"Expected: {expected}")
            
            # Encrypted
            self.status_var.set("Computing...")
            self.root.update()
            
            enc_V = self.coordinator.encrypt_demand(V, "v")
            enc_res = self.algebra.linear_transform_encrypted(M, enc_V)
            
            dec_res = self.utility.decrypt_demand(enc_res)[:dim]
            self.log_matrix(f"Decrypted: {np.array(dec_res)}")
            
            error = np.linalg.norm(dec_res - expected)
            self.log_matrix(f"Error: {error:.2e}")
            self.status_var.set("Ready")

        except Exception as e:
             messagebox.showerror("Error", str(e))

    def run_stress_test(self):
        threading.Thread(target=self._stress_test_worker).start()

    def _stress_test_worker(self):
        try:
            depth = self.mult_depth.get()
            val = 2.0
            
            # Encrypt initial value
            enc = self.utility.encrypt_demand([val], "stress")
            
            errors = []
            x_axis = []
            
            curr_enc = enc
            curr_expected = val
            
            for i in range(1, depth + 1):
                self.status_var.set(f"Stress Test: Multiplication {i}/{depth}...")
                
                try:
                    # Perform Multiplication
                    # We use multiply_plain with 1.0. This consumes depth (rescale) 
                    # but keeps value stable.
                    # Repeatedly doing this eventually exhausts the coefficient modulus chain.
                    curr_enc = self.utility.multiply_plain(curr_enc, 1.0)
                    
                    # Decrypt to check error
                    res = self.utility.decrypt_demand(curr_enc)[0]
                    err = abs(res - curr_expected)
                    errors.append(err + 1e-15) # Avoid log(0)
                    
                except Exception as e:
                    print(f"Failed at step {i}: {e}")
                    # If we hit scale limit or decryption failure, fill remaining with high error
                    for _ in range(i, depth + 1):
                        errors.append(1e10) # Large value for plot
                    break
                
                x_axis.append(i)
                self.root.after(10, self.update_plot, x_axis, errors)
            
            self.status_var.set("Stress Test Complete.")
            
        except Exception as e:
            print(f"Stress error: {e}")

    def update_plot(self, x, y):
        self.ax.clear()
        self.ax.set_title("Decryption Error vs. Operations")
        self.ax.set_xlabel("Operations")
        self.ax.set_ylabel("Error (Log Scale)")
        self.ax.set_yscale("log")
        self.ax.plot(x, y, 'b-o')
        self.ax.grid(True)
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    app = EncryptedVectorGUI(root)
    root.mainloop()
