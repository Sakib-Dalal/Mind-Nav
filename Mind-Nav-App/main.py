"""
BCI Real-Time Tester  —  bci_tester.py
═══════════════════════════════════════
• Reads live EEG from Arduino via Serial (or simulates if no Arduino)
• Predicts CLICK / REST using any of four trained models
• Side-by-side ACTUAL vs PREDICTED display with confidence bar
• Optional TCP socket server → sends predictions to Raspberry Pi Pico W

Required files (same directory):
  BCI_MODEL.joblib   BCI_SCALER.joblib
  BCI_FNN.pt         BCI_CNN.pt         BCI_Hybrid.pt

Press ESC to exit at any time.
"""

import warnings

# ── Silence sklearn version-mismatch pickle warnings ──────────────────────────
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

import serial
import time
import threading
import random
import math
import collections
import socket
import os

import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk

from scipy.stats import skew, kurtosis
from scipy.signal import welch
from scipy.integrate import trapezoid

import sklearn

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG  — edit these to match your setup
# ══════════════════════════════════════════════════════════════════════════════
PORT = "/dev/cu.usbmodem1101"  # Windows: "COM3"  Linux: "/dev/ttyACM0"
BAUD_RATE = 115200
FS = 256  # Hz — must match Arduino SAMPLE_RATE
WIN_LEN = 256  # samples per prediction window (1 second)
N_FEATURES = 42
STIM_DURATION = 3000  # ms — must match recorder
REST_DURATION = 2000  # ms — must match recorder
WAVE_POINTS = 300

SOCKET_HOST = "0.0.0.0"
SOCKET_PORT = 9000

# ── Colour palette ─────────────────────────────────────────────────────────────
BG = "#04080F"
ACCENT = "#00F5C4"
DIM = "#0A1A14"
GRID_COLOR = "#081810"
TEXT_MAIN = "#E0FFF6"
TEXT_SUB = "#3A7A65"
RING_BASE = "#0D2A22"
COL_CLICK = "#4ADE80"
COL_REST = "#3A7A65"
COL_CORRECT = "#00F5C4"
COL_WRONG = "#FF4D6A"

LABEL_NAMES = {0: "REST", 1: "CLICK"}


# ══════════════════════════════════════════════════════════════════════════════
#  PyTorch model architectures  (must exactly match training notebook)
# ══════════════════════════════════════════════════════════════════════════════
def build_torch_classes():
    """Import torch and define all model classes. Returns them as a bundle."""
    import torch
    import torch.nn as nn

    class BCIConvBlock(nn.Module):
        def __init__(self, in_ch, out_ch, kernel=7, pool=2, dropout=0.3):
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv1d(in_ch, out_ch, kernel_size=kernel, padding=kernel // 2),
                nn.BatchNorm1d(out_ch),
                nn.ReLU(),
                nn.MaxPool1d(pool),
                nn.Dropout(dropout),
            )

        def forward(self, x):
            return self.block(x)

    class BCIFNN(nn.Module):
        def __init__(self, in_features=42, hidden=None, dropout=0.4, n_classes=2):
            super().__init__()
            if hidden is None:
                hidden = [128, 64, 32]
            layers, prev = [], in_features
            for h in hidden:
                layers += [nn.Linear(prev, h), nn.BatchNorm1d(h),
                           nn.ReLU(), nn.Dropout(dropout)]
                prev = h
            layers.append(nn.Linear(prev, n_classes))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x)

    class BCICNN(nn.Module):
        def __init__(self, win_len=256, n_classes=2, dropout=0.4):
            super().__init__()
            self.encoder = nn.Sequential(
                BCIConvBlock(1, 32, kernel=15, pool=2, dropout=dropout),
                BCIConvBlock(32, 64, kernel=9, pool=2, dropout=dropout),
                BCIConvBlock(64, 128, kernel=5, pool=2, dropout=dropout),
            )
            self.gap = nn.AdaptiveAvgPool1d(1)
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(128, 64), nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, n_classes),
            )

        def forward(self, x):
            x = x.unsqueeze(1)  # (B, 1, WIN_LEN)
            x = self.encoder(x)
            x = self.gap(x)
            return self.classifier(x)

    class BCIHybrid(nn.Module):
        def __init__(self, win_len=256, n_feat=42, dropout=0.4, n_classes=2):
            super().__init__()
            self.cnn_branch = nn.Sequential(
                BCIConvBlock(1, 32, kernel=15, pool=2, dropout=dropout),
                BCIConvBlock(32, 64, kernel=9, pool=2, dropout=dropout),
                BCIConvBlock(64, 128, kernel=5, pool=2, dropout=dropout),
                nn.AdaptiveAvgPool1d(1),
            )
            self.fnn_branch = nn.Sequential(
                nn.Linear(n_feat, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(dropout),
                nn.Linear(128, 64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(dropout),
            )
            self.fusion = nn.Sequential(
                nn.Linear(192, 64), nn.BatchNorm1d(64), nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, n_classes),
            )

        def forward(self, raw, feat):
            cnn_out = self.cnn_branch(raw.unsqueeze(1)).squeeze(-1)  # (B, 128)
            fnn_out = self.fnn_branch(feat)  # (B, 64)
            return self.fusion(torch.cat([cnn_out, fnn_out], dim=1))

    return torch, BCIFNN, BCICNN, BCIHybrid


# ══════════════════════════════════════════════════════════════════════════════
#  Feature extraction  (identical to notebook — 42 features)
# ══════════════════════════════════════════════════════════════════════════════
def _band_power(f, pxx, lo, hi):
    idx = (f >= lo) & (f <= hi)
    return float(trapezoid(pxx[idx], f[idx])) if idx.sum() > 0 else 0.0


def _spectral_entropy(pxx):
    p = pxx / (pxx.sum() + 1e-10)
    return float(-np.sum(p * np.log2(p + 1e-10)))


def _hjorth(x):
    d1 = np.diff(x);
    d2 = np.diff(d1)
    act = float(np.var(x))
    mob = float(np.sqrt(np.var(d1) / (act + 1e-10)))
    comp = float(np.sqrt(np.var(d2) / (np.var(d1) + 1e-10)) / (mob + 1e-10))
    return act, mob, comp


def extract_features(ep: np.ndarray) -> np.ndarray:
    ep = ep.astype(np.float64)
    nperseg = min(128, len(ep))
    d1 = np.diff(ep)
    half = len(ep) // 2

    td = [
        float(np.mean(ep)), float(np.std(ep)), float(np.var(ep)),
        float(skew(ep)), float(kurtosis(ep)),
        float(np.sqrt(np.mean(ep ** 2))),
        float(np.max(ep) - np.min(ep)),
        float(np.mean(np.abs(ep))),
        float(np.sum(np.diff(np.sign(ep)) != 0)),
        float(np.percentile(ep, 10)), float(np.percentile(ep, 25)),
        float(np.percentile(ep, 75)), float(np.percentile(ep, 90)),
        float(np.sum(np.abs(d1))),
        float(np.mean(ep[:half])), float(np.mean(ep[half:])),
        float(np.std(ep[:half])), float(np.std(ep[half:])),
    ]

    act, mob, comp = _hjorth(ep)

    ac = np.correlate(ep, ep, mode='full')
    ac = ac[len(ac) // 2:]
    ac = ac / (ac[0] + 1e-10)
    autocorr = [float(ac[lag]) if lag < len(ac) else 0.0
                for lag in [1, 2, 5, 10, 20]]

    f, pxx = welch(ep, fs=FS, nperseg=nperseg)
    pxx = np.maximum(pxx, 1e-12)
    d_ = _band_power(f, pxx, 2, 4)
    t_ = _band_power(f, pxx, 4, 8)
    a_ = _band_power(f, pxx, 8, 13)
    b_ = _band_power(f, pxx, 13, 30)
    g_ = _band_power(f, pxx, 30, 45)
    tot = _band_power(f, pxx, 1, 50)

    fd = [
        d_, t_, a_, b_, g_, tot,
        d_ / (tot + 1e-10), t_ / (tot + 1e-10),
        a_ / (tot + 1e-10), b_ / (tot + 1e-10),
        a_ / (b_ + 1e-10), t_ / (a_ + 1e-10),
        (a_ + b_) / (d_ + t_ + 1e-10),
        _spectral_entropy(pxx),
        float(f[np.argmax(pxx)]),
        float(np.sum(pxx * f) / (np.sum(pxx) + 1e-10)),
    ]

    return np.array(td + [act, mob, comp] + autocorr + fd, dtype=np.float32)


# ══════════════════════════════════════════════════════════════════════════════
#  ModelManager  —  loads and runs inference for all four models
# ══════════════════════════════════════════════════════════════════════════════
class ModelManager:
    def __init__(self):
        self.ensemble = None
        self.scaler = None
        self.fnn = None  # (model, torch)
        self.cnn = None  # (model, torch)
        self.hybrid = None  # (model, torch)
        self.device = None
        self.errors: list[str] = []

    def load_all(self):
        """Load every model file that exists. Errors stored, never raised."""

        # ── sklearn ensemble ──────────────────────────────────────────────────
        try:
            import joblib
            from sklearn.utils.validation import check_is_fitted
            loaded = joblib.load("BCI_MODEL.joblib")
            try:
                check_is_fitted(loaded)
                self.ensemble = loaded
            except Exception:
                self.errors.append(
                    "BCI_MODEL.joblib: NOT fitted — add "
                    "ensemble.fit(X_scaled, y_bin) before joblib.dump()"
                )
        except FileNotFoundError:
            self.errors.append("BCI_MODEL.joblib: file not found")
        except Exception as e:
            self.errors.append(f"BCI_MODEL.joblib: {e}")

        # ── scaler ────────────────────────────────────────────────────────────
        try:
            import joblib
            self.scaler = joblib.load("BCI_SCALER.joblib")
        except FileNotFoundError:
            self.errors.append("BCI_SCALER.joblib: file not found")
        except Exception as e:
            self.errors.append(f"BCI_SCALER.joblib: {e}")

        # ── PyTorch models ────────────────────────────────────────────────────
        try:
            torch, BCIFNN, BCICNN, BCIHybrid = build_torch_classes()
            # CPU inference: these models are tiny (<5 ms/prediction).
            # Avoids MPS CHECK_PFPROJ warnings on Apple Silicon for batch=1.
            self.device = torch.device("cpu")

            specs = [
                ("fnn", "BCI_FNN.pt",
                 lambda: BCIFNN(in_features=N_FEATURES)),
                ("cnn", "BCI_CNN.pt",
                 lambda: BCICNN(win_len=WIN_LEN)),
                ("hybrid", "BCI_Hybrid.pt",
                 lambda: BCIHybrid(win_len=WIN_LEN, n_feat=N_FEATURES)),
            ]
            for attr, fname, builder in specs:
                try:
                    model = builder().to(self.device)
                    state = torch.load(fname, map_location=self.device,
                                       weights_only=True)
                    model.load_state_dict(state)
                    model.eval()
                    setattr(self, attr, (model, torch))
                except FileNotFoundError:
                    self.errors.append(f"{fname}: file not found")
                except Exception as e:
                    self.errors.append(f"{fname}: {e}")

        except ImportError:
            self.errors.append(
                "PyTorch not installed — FNN/CNN/Hybrid unavailable")

    def available_models(self) -> list[str]:
        out = []
        if self.ensemble and self.scaler: out.append("ET+RF Ensemble")
        if self.fnn:                      out.append("FNN")
        if self.cnn:                      out.append("CNN")
        if self.hybrid:                   out.append("Hybrid CNN+FNN")
        return out

    # ── private helpers ───────────────────────────────────────────────────────
    def _prep_features(self, raw: np.ndarray) -> np.ndarray:
        feats = extract_features(raw).reshape(1, -1)
        if self.scaler is not None:
            feats = self.scaler.transform(feats)
        return feats.astype(np.float32)

    @staticmethod
    def _prep_raw(raw: np.ndarray) -> np.ndarray:
        w = raw.astype(np.float32)
        w = (w - w.mean()) / (w.std() + 1e-8)
        if len(w) < WIN_LEN:
            w = np.pad(w, (0, WIN_LEN - len(w)))
        else:
            w = w[:WIN_LEN]
        return w

    def predict(self, model_name: str,
                raw_window: np.ndarray) -> tuple[int, float]:
        """
        Returns (label_idx, confidence).
          label_idx : 0 = REST, 1 = CLICK
          confidence: 0.0 – 1.0
        """
        try:
            if model_name == "ET+RF Ensemble":
                feats = self._prep_features(raw_window)
                proba = self.ensemble.predict_proba(feats)[0]
                classes = list(self.ensemble.classes_)  # [0,1] or [0,5]
                best = int(np.argmax(proba))
                raw_cls = classes[best]
                label = 1 if raw_cls == 5 else int(raw_cls != 0)
                return label, float(proba[best])

            elif model_name == "FNN":
                model, torch = self.fnn
                ft = torch.tensor(self._prep_features(raw_window),
                                  dtype=torch.float32).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(ft), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

            elif model_name == "CNN":
                model, torch = self.cnn
                rt = torch.tensor(self._prep_raw(raw_window),
                                  dtype=torch.float32).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(rt), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

            elif model_name == "Hybrid CNN+FNN":
                model, torch = self.hybrid
                rt = torch.tensor(self._prep_raw(raw_window),
                                  dtype=torch.float32).unsqueeze(0).to(self.device)
                ft = torch.tensor(self._prep_features(raw_window),
                                  dtype=torch.float32).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(rt, ft), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

        except Exception as e:
            print(f"[Predict Error] {model_name}: {e}")

        return 0, 0.5  # safe fallback


# ══════════════════════════════════════════════════════════════════════════════
#  TCP Socket Server  (streams predictions to Raspberry Pi Pico W)
# ══════════════════════════════════════════════════════════════════════════════
class PicoServer:
    def __init__(self, host: str = SOCKET_HOST, port: int = SOCKET_PORT):
        self._host = host
        self._port = port
        self._clients: list = []
        self._lock = threading.Lock()
        self._running = False
        self._srv_sock = None

    def start(self):
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        self._srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv_sock.bind((self._host, self._port))
        self._srv_sock.listen(5)
        self._srv_sock.settimeout(1.0)
        print(f"[PicoServer] Listening on {self._host}:{self._port}")
        while self._running:
            try:
                conn, addr = self._srv_sock.accept()
                print(f"[PicoServer] Pico W connected from {addr}")
                with self._lock:
                    self._clients.append(conn)
            except socket.timeout:
                continue
            except Exception:
                break

    def broadcast(self, label: str):
        msg = (label + "\n").encode()
        dead = []
        with self._lock:
            for conn in self._clients:
                try:
                    conn.sendall(msg)
                except Exception:
                    dead.append(conn)
            for d in dead:
                self._clients.remove(d)

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def stop(self):
        self._running = False
        if self._srv_sock:
            try:
                self._srv_sock.close()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  Main Tkinter Application
# ══════════════════════════════════════════════════════════════════════════════
class BCITesterApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.configure(bg=BG)
        self.root.title("BCI Real-Time Tester")

        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+0+0")

        # session state
        self.is_running = False
        self.current_label = "REST"
        self.trial_count = 0
        self.correct_count = 0
        self.session_start = None
        self._stim_start_ms = 0.0
        self._stim_duration = float(STIM_DURATION)

        self.wave_buf = collections.deque([0.0] * WAVE_POINTS, maxlen=WAVE_POINTS)
        self.predict_buf = collections.deque(maxlen=WIN_LEN)

        self.model_mgr = ModelManager()
        self.pico_server = PicoServer()
        self.pico_active = False
        self.ser = None

        self.cv = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self.cv.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<Escape>", lambda _e: self._quit())

        self._show_menu()

    # ══════════════════════════════════════════════════════════════════════════
    #  MENU
    # ══════════════════════════════════════════════════════════════════════════
    def _show_menu(self):
        self.cv.delete("all")
        self._draw_grid()
        self._draw_header("◈   BCI  REAL-TIME  TESTER   ◈")
        self._draw_footer()
        cx, cy = self.W // 2, self.H // 2
        self.cv.create_text(cx, cy - 60, text="Loading models…",
                            fill=TEXT_SUB, font=("Courier New", 14),
                            tags="loading")
        threading.Thread(target=self._load_bg, daemon=True).start()

    def _load_bg(self):
        self.model_mgr.load_all()
        self.root.after(0, self._populate_menu)

    def _populate_menu(self):
        self.cv.delete("loading")
        cx, cy = self.W // 2, self.H // 2
        cw, ch = 680, 500
        x0, y0 = cx - cw // 2, cy - ch // 2

        self.cv.create_rectangle(x0, y0, x0 + cw, y0 + ch,
                                 fill="#020D08", outline=ACCENT, width=1)
        self.cv.create_text(cx, y0 + 46, text="SESSION  SETUP",
                            fill=ACCENT, font=("Courier New", 24, "bold"))
        self.cv.create_line(x0 + 40, y0 + 72, x0 + cw - 40, y0 + 72,
                            fill=RING_BASE, width=1)

        row = [y0 + 106, y0 + 158, y0 + 212]

        # Arduino port
        self.cv.create_text(x0 + 40, row[0], text="ARDUINO PORT:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._port_var = tk.StringVar(value=PORT)
        tk.Entry(self.root, textvariable=self._port_var,
                 bg=DIM, fg=ACCENT, insertbackground=ACCENT,
                 font=("Courier New", 12), relief=tk.FLAT, bd=0
                 ).place(x=cx - 50, y=row[0] - 9, width=260, height=26)

        # Model selector
        models = self.model_mgr.available_models()
        self.cv.create_text(x0 + 40, row[1], text="MODEL:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        if models:
            self._model_var = tk.StringVar(value=models[0])
            cb = ttk.Combobox(self.root, textvariable=self._model_var,
                              values=models, state="readonly",
                              font=("Courier New", 12))
            cb.place(x=cx - 50, y=row[1] - 10, width=260, height=28)
            self.root.option_add("*TCombobox*Listbox.background", DIM)
            self.root.option_add("*TCombobox*Listbox.foreground", ACCENT)
        else:
            self._model_var = tk.StringVar(value="")
            self.cv.create_text(cx + 80, row[1],
                                text="⚠  No models found — check file paths",
                                fill=COL_WRONG, font=("Courier New", 11))

        # Pico W toggle  — FIX: only ONE fg= argument (duplicate caused TypeError)
        self.cv.create_text(x0 + 40, row[2], text="PICO W SERVER:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._pico_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.root,
                       variable=self._pico_var,
                       text=f"Enable  (TCP port {SOCKET_PORT})",
                       font=("Courier New", 11),
                       fg=TEXT_MAIN,  # single fg= — no duplicate
                       bg=BG,
                       activebackground=BG,
                       activeforeground=ACCENT,
                       selectcolor=DIM
                       ).place(x=cx - 50, y=row[2] - 12)

        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            local_ip = "127.0.0.1"
        self.cv.create_text(cx, y0 + 264,
                            text=f"Pico W connects to  {local_ip}:{SOCKET_PORT}",
                            fill=TEXT_SUB, font=("Courier New", 10))

        # Errors / warnings
        if self.model_mgr.errors:
            self.cv.create_text(cx, y0 + 296,
                                text="Warnings:", fill=COL_WRONG,
                                font=("Courier New", 9))
            for i, err in enumerate(self.model_mgr.errors[:4]):
                self.cv.create_text(cx, y0 + 312 + i * 15,
                                    text=err[:84], fill=COL_WRONG,
                                    font=("Courier New", 8))

        # Begin button
        tk.Button(self.root,
                  text="▶   BEGIN  TESTING",
                  font=("Courier New", 15, "bold"),
                  bg=ACCENT, fg=BG,
                  activebackground="#00C8A0", activeforeground=BG,
                  relief=tk.FLAT, bd=0, padx=30, pady=14,
                  cursor="hand2",
                  command=self._start_session
                  ).place(x=cx - 145, y=y0 + 396, width=290, height=54)

        self.cv.create_text(
            cx, y0 + 464,
            text=f"Models available:  {', '.join(models) if models else 'NONE'}",
            fill=TEXT_SUB, font=("Courier New", 10))

    # ══════════════════════════════════════════════════════════════════════════
    #  START SESSION
    # ══════════════════════════════════════════════════════════════════════════
    def _start_session(self):
        if not self.model_mgr.available_models():
            messagebox.showerror("No Models",
                                 "No models loaded.\n"
                                 "Place .joblib / .pt files next to bci_tester.py.")
            return

        for widget in self.root.winfo_children():
            if not isinstance(widget, tk.Canvas):
                widget.destroy()

        port = self._port_var.get().strip()
        try:
            self.ser = serial.Serial(port, BAUD_RATE, timeout=0.01)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.ser.write(b"START\n")
            print(f"[Serial] Connected on {port}")
        except Exception as e:
            print(f"[Serial] {e}  —  SIMULATION mode")
            self.ser = None

        if self._pico_var.get():
            self.pico_server.start()
            self.pico_active = True

        self.selected_model = self._model_var.get()
        self.is_running = True
        self.session_start = time.time()
        self.trial_count = 0
        self.correct_count = 0

        self.cv.delete("all")
        self._draw_grid()
        self._draw_header(f"◈   BCI  TESTER  —  {self.selected_model.upper()}   ◈")
        self._draw_footer()
        self._build_session_ui()

        threading.Thread(target=self._data_reader, daemon=True).start()
        self.root.after(500, self._run_stimulus)
        self._animate()

    # ══════════════════════════════════════════════════════════════════════════
    #  SESSION UI
    # ══════════════════════════════════════════════════════════════════════════
    def _build_session_ui(self):
        cx = self.W // 2
        cy = self.H // 2 - 60
        lx = self.W // 4
        rx = self.W * 3 // 4

        self.cv.create_line(cx, 64, cx, self.H - 45,
                            fill=RING_BASE, width=1, dash=(4, 8))
        self.cv.create_text(lx, 80, text="ACTUAL  STIMULUS",
                            fill=TEXT_SUB, font=("Courier New", 13, "bold"))
        self.cv.create_text(rx, 80, text="MODEL  PREDICTION",
                            fill=TEXT_SUB, font=("Courier New", 13, "bold"))
        self.cv.create_line(40, 94, cx - 20, 94, fill=RING_BASE, width=1)
        self.cv.create_line(cx + 20, 94, self.W - 40, 94, fill=RING_BASE, width=1)

        for col_cx in (lx, rx):
            for r in (130, 160, 190):
                self.cv.create_oval(col_cx - r, cy - r, col_cx + r, cy + r,
                                    outline=RING_BASE, width=1)

        self.actual_ring = self.cv.create_oval(
            lx - 122, cy - 122, lx + 122, cy + 122, outline=ACCENT, width=2)
        self.pred_ring = self.cv.create_oval(
            rx - 122, cy - 122, rx + 122, cy + 122, outline=TEXT_SUB, width=2)

        self.actual_arc = self.cv.create_arc(
            lx - 148, cy - 148, lx + 148, cy + 148,
            start=90, extent=0, outline=ACCENT, width=4, style=tk.ARC)
        self.pred_arc = self.cv.create_arc(
            rx - 148, cy - 148, rx + 148, cy + 148,
            start=90, extent=0, outline=TEXT_SUB, width=4, style=tk.ARC)

        self.actual_icon = self.cv.create_text(
            lx, cy - 14, text="", fill=ACCENT,
            font=("Courier New", 110, "bold"), anchor=tk.CENTER)
        self.pred_icon = self.cv.create_text(
            rx, cy - 14, text="", fill=TEXT_SUB,
            font=("Courier New", 110, "bold"), anchor=tk.CENTER)

        self.actual_label_item = self.cv.create_text(
            lx, cy + 100, text="WAITING", fill=ACCENT,
            font=("Courier New", 26, "bold"), anchor=tk.CENTER)
        self.pred_label_item = self.cv.create_text(
            rx, cy + 100, text="---", fill=TEXT_SUB,
            font=("Courier New", 26, "bold"), anchor=tk.CENTER)

        # Confidence bar
        bar_y = cy + 138
        self._bar_rx = rx
        self._bar_w = 240
        self._bar_y = bar_y
        self.cv.create_rectangle(rx - 120, bar_y, rx + 120, bar_y + 14,
                                 fill=DIM, outline=RING_BASE, width=1)
        self.conf_bar = self.cv.create_rectangle(
            rx - 120, bar_y, rx - 120, bar_y + 14,
            fill=ACCENT, outline="", width=0)
        self.conf_text = self.cv.create_text(
            rx, bar_y + 7, text="",
            fill=BG, font=("Courier New", 9, "bold"))

        self.match_item = self.cv.create_text(
            cx, cy + 178, text="",
            fill=COL_CORRECT, font=("Courier New", 16, "bold"),
            anchor=tk.CENTER)

        # EEG waveform
        wy, ww = self.H - 148, int(self.W * 0.88)
        self._wave_wy = wy
        self._wave_ww = ww
        self._wave_H = 60
        self.cv.create_rectangle(
            cx - ww // 2 - 2, wy - self._wave_H - 8,
            cx + ww // 2 + 2, wy + self._wave_H + 8,
            fill="#020C09", outline=TEXT_SUB, width=1)
        self.cv.create_line(cx - ww // 2, wy, cx + ww // 2, wy,
                            fill=RING_BASE, width=1, dash=(4, 8))
        self.cv.create_text(cx - ww // 2 - 10, wy, text="EEG",
                            fill=TEXT_SUB, font=("Courier New", 9), anchor=tk.E)
        self.wave_line = self.cv.create_line(0, 0, 1, 1,
                                             fill=ACCENT, width=1, smooth=True)

        # Status bar
        sby = self.H - 18
        self.stat_trial = self.cv.create_text(
            24, sby, text="TRIAL: 0",
            fill=TEXT_SUB, font=("Courier New", 10), anchor=tk.W)
        self.stat_accuracy = self.cv.create_text(
            200, sby, text="ACCURACY: ---",
            fill=TEXT_SUB, font=("Courier New", 10), anchor=tk.W)
        self.stat_time = self.cv.create_text(
            430, sby, text="TIME: 00:00",
            fill=TEXT_SUB, font=("Courier New", 10), anchor=tk.W)
        self.stat_pico = self.cv.create_text(
            self.W - 24, sby,
            text=f"PICO: {'● ON' if self.pico_active else '○ OFF'}",
            fill=ACCENT if self.pico_active else TEXT_SUB,
            font=("Courier New", 10), anchor=tk.E)
        self.stat_clients = self.cv.create_text(
            self.W - 24, sby - 14, text="",
            fill=TEXT_SUB, font=("Courier New", 9), anchor=tk.E)
        self.status_dot = self.cv.create_text(
            cx, 27, text="● LIVE", fill=ACCENT, font=("Courier New", 10))

    # ══════════════════════════════════════════════════════════════════════════
    #  STIMULUS SEQUENCE
    # ══════════════════════════════════════════════════════════════════════════
    def _run_stimulus(self):
        if not self.is_running:
            return
        self.trial_count += 1
        self.current_label = "CLICK"
        self._stim_start_ms = time.time() * 1000
        self._stim_duration = STIM_DURATION

        self._set_actual("CLICK", COL_CLICK)
        self._set_pred("---", TEXT_SUB, 0.0)
        self.cv.itemconfig(self.match_item, text="")

        # ── FIX: snapshot the label NOW so the async prediction callback can
        # compare against it correctly.  By the time the thread finishes,
        # self.current_label will already be "REST" (set by _run_rest).
        actual_snapshot = "CLICK"

        self.root.after(STIM_DURATION,
                        lambda: self._do_prediction(actual_snapshot))
        self.root.after(STIM_DURATION, self._run_rest)

    def _run_rest(self):
        if not self.is_running:
            return
        self.current_label = "REST"
        self._stim_start_ms = time.time() * 1000
        self._stim_duration = REST_DURATION

        self._set_actual("+", COL_REST, label_text="REST")
        self.root.after(REST_DURATION, self._run_stimulus)

    def _do_prediction(self, actual_label: str):
        window = np.array(list(self.predict_buf), dtype=np.float32)
        model_name = self.selected_model

        if len(window) < 32:
            self._show_prediction(0, 0.5, actual_label)
            return

        def _run():
            label_idx, conf = self.model_mgr.predict(model_name, window)
            self.root.after(
                0, lambda: self._show_prediction(label_idx, conf, actual_label))

        threading.Thread(target=_run, daemon=True).start()

    def _show_prediction(self, label_idx: int, conf: float,
                         actual_label: str):
        """
        actual_label is passed in explicitly (not read from self.current_label)
        because self.current_label has already been changed to "REST" by the
        time this callback fires.
        """
        label_str = LABEL_NAMES[label_idx]
        color = COL_CLICK if label_str == "CLICK" else COL_REST
        self._set_pred(label_str, color, conf)

        actual_idx = 1 if actual_label == "CLICK" else 0
        if label_idx == actual_idx:
            self.correct_count += 1
            self.cv.itemconfig(self.match_item,
                               text="✓  CORRECT", fill=COL_CORRECT)
        else:
            self.cv.itemconfig(self.match_item,
                               text="✗  MISMATCH", fill=COL_WRONG)

        if self.pico_active:
            self.pico_server.broadcast(label_str)

    # ══════════════════════════════════════════════════════════════════════════
    #  UI HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _set_actual(self, icon_text: str, color: str, label_text: str = None):
        lbl = label_text or icon_text
        icon = "●" if icon_text == "CLICK" else icon_text
        self.cv.itemconfig(self.actual_icon, text=icon, fill=color)
        self.cv.itemconfig(self.actual_label_item, text=lbl, fill=color)
        self.cv.itemconfig(self.actual_ring, outline=color)
        self.cv.itemconfig(self.actual_arc, outline=color)

    def _set_pred(self, label_text: str, color: str, conf: float):
        icon = "●" if label_text == "CLICK" else ("+" if label_text == "REST" else "?")
        self.cv.itemconfig(self.pred_icon, text=icon, fill=color)
        self.cv.itemconfig(self.pred_label_item, text=label_text, fill=color)
        self.cv.itemconfig(self.pred_ring, outline=color)
        self.cv.itemconfig(self.pred_arc, outline=color)
        if conf > 0.0:
            filled = int(self._bar_w * conf)
            x0 = self._bar_rx - self._bar_w // 2
            self.cv.coords(self.conf_bar,
                           x0, self._bar_y,
                           x0 + filled, self._bar_y + 14)
            self.cv.itemconfig(self.conf_bar, fill=color)
            self.cv.itemconfig(self.conf_text, text=f"{conf * 100:.0f}%")

    # ══════════════════════════════════════════════════════════════════════════
    #  ANIMATION LOOP  (~30 fps)
    # ══════════════════════════════════════════════════════════════════════════
    def _animate(self):
        if not self.is_running:
            return
        self._draw_waveform()
        self._update_countdown()
        self._pulse_rings()
        self._update_stats()
        self.root.after(33, self._animate)

    def _pulse_rings(self):
        t = time.time()
        s = 1.0 + 0.018 * math.sin(t * 2.5)
        r = int(122 * s)
        cy = self.H // 2 - 60
        for cx_col, ring in ((self.W // 4, self.actual_ring),
                             (self.W * 3 // 4, self.pred_ring)):
            self.cv.coords(ring, cx_col - r, cy - r, cx_col + r, cy + r)

    def _update_countdown(self):
        elapsed = (time.time() * 1000) - self._stim_start_ms
        frac = min(elapsed / max(self._stim_duration, 1.0), 1.0)
        ext = -360.0 * frac
        self.cv.itemconfig(self.actual_arc, extent=ext)
        self.cv.itemconfig(self.pred_arc, extent=ext)

    def _draw_waveform(self):
        buf = list(self.wave_buf)
        if len(buf) < 2:
            return
        cx = self.W // 2
        ww = self._wave_ww
        wy = self._wave_wy
        norm = max(max(abs(v) for v in buf), 1.0)
        pts = []
        for i, v in enumerate(buf):
            x = cx - ww // 2 + int(i / (len(buf) - 1) * ww)
            y = wy - int((v / norm) * self._wave_H * 0.85)
            pts += [x, y]
        self.cv.coords(self.wave_line, *pts)

    def _update_stats(self):
        elapsed = int(time.time() - (self.session_start or time.time()))
        m, s = divmod(elapsed, 60)
        acc_str = (f"{self.correct_count / self.trial_count * 100:.1f}%"
                   if self.trial_count > 0 else "---")
        self.cv.itemconfig(self.stat_trial, text=f"TRIAL: {self.trial_count}")
        self.cv.itemconfig(self.stat_accuracy, text=f"ACCURACY: {acc_str}")
        self.cv.itemconfig(self.stat_time, text=f"TIME: {m:02d}:{s:02d}")
        blink = "● LIVE" if int(time.time() * 2) % 2 == 0 else "○ LIVE"
        self.cv.itemconfig(self.status_dot, text=blink)
        if self.pico_active:
            self.cv.itemconfig(self.stat_clients,
                               text=f"PICO CLIENTS: {self.pico_server.client_count()}")

    # ══════════════════════════════════════════════════════════════════════════
    #  DATA READER  (daemon thread)
    # ══════════════════════════════════════════════════════════════════════════
    def _data_reader(self):
        while self.is_running:
            if self.ser:
                if self.ser.in_waiting:
                    try:
                        line = (self.ser.readline()
                                .decode("utf-8", errors="ignore").strip())
                        if line:
                            val = float(line) - 500.0
                            self.wave_buf.append(val)
                            self.predict_buf.append(val)
                    except Exception:
                        pass
                else:
                    time.sleep(0.0005)
            else:
                # Simulation mode — synthetic EEG
                t = time.time()
                val = (10 * math.sin(2 * math.pi * 10 * t) +
                       5 * math.sin(2 * math.pi * 20 * t) +
                       random.gauss(0, 3))
                self.wave_buf.append(val)
                self.predict_buf.append(val)
                time.sleep(1.0 / FS)

    # ══════════════════════════════════════════════════════════════════════════
    #  STATIC DRAWING HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _draw_grid(self):
        for x in range(0, self.W, 60):
            self.cv.create_line(x, 0, x, self.H, fill=GRID_COLOR, width=1)
        for y in range(0, self.H, 60):
            self.cv.create_line(0, y, self.W, y, fill=GRID_COLOR, width=1)
        sz = 32
        for (bx, by), (dx, dy) in [
            ((20, 20), (1, 1)),
            ((self.W - 20, 20), (-1, 1)),
            ((20, self.H - 20), (1, -1)),
            ((self.W - 20, self.H - 20), (-1, -1)),
        ]:
            self.cv.create_line(bx, by, bx + dx * sz, by, fill=ACCENT, width=2)
            self.cv.create_line(bx, by, bx, by + dy * sz, fill=ACCENT, width=2)

    def _draw_header(self, title: str):
        self.cv.create_rectangle(0, 0, self.W, 54, fill="#020C09", outline="")
        self.cv.create_line(0, 54, self.W, 54, fill=ACCENT, width=1)
        self.cv.create_text(self.W // 2, 27, text=title,
                            fill=ACCENT, font=("Courier New", 16, "bold"))

    def _draw_footer(self):
        self.cv.create_rectangle(0, self.H - 40, self.W, self.H,
                                 fill="#020C09", outline="")
        self.cv.create_line(0, self.H - 40, self.W, self.H - 40,
                            fill=TEXT_SUB, width=1)

    # ══════════════════════════════════════════════════════════════════════════
    #  QUIT
    # ══════════════════════════════════════════════════════════════════════════
    def _quit(self):
        self.is_running = False
        self.pico_server.stop()
        if self.ser:
            try:
                self.ser.write(b"STOP\n")
                self.ser.close()
            except Exception:
                pass
        self.root.destroy()


# ══════════════════════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.resizable(False, False)
    BCITesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
