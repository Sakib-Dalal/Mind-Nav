"""
BCI Precision Recorder — EEG with ADS1115 + BioAmp EXG Pill
============================================================
Neural-lab aesthetic UI for professional EEG-based BCI data collection

Hardware: Arduino Uno + ADS1115 (16-bit ADC) + BioAmp EXG Pill
Paradigm: Motor Imagery / Mental Task Classification
Sample Rate: 256 Hz

Features:
- Real-time EEG waveform visualization
- Stimulus presentation with voice cues
- Automated trial sequencing (CLICK vs REST)
- High-precision timestamped data logging
- Session statistics and countdown timers
- Dark neural-lab themed interface
"""

import os
import serial
import time
import csv
import threading
import random
import queue
import math
import collections
import sys
import platform
from tkinter import *
from tkinter import messagebox

# Optional: Text-to-speech (install with: pip install pyttsx3)
try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[WARNING] pyttsx3 not installed. Voice cues disabled.")
    print("          Install with: pip install pyttsx3")

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Serial port configuration
# Windows: "COM3", "COM4", etc.
# Linux/Mac: "/dev/ttyUSB0", "/dev/cu.usbmodem1101", etc.
PORT = "/dev/cu.usbmodem1101"  # ← CHANGE THIS TO YOUR ARDUINO PORT
BAUD_RATE = 115200

# Data output file
FILE_NAME = "eeg_precision_bci.csv"

# Trial timing (milliseconds)
STIM_DURATION = 4000  # How long to show stimulus (motor imagery cue)
REST_DURATION = 3000  # How long to show rest cue

# Waveform display
WAVE_POINTS = 512  # Number of samples shown on screen
WAVE_HEIGHT = 90  # Pixels (half-height of waveform)

# Task labels and their numeric class IDs
LABEL_MAP = {
    "REST": 0,
    "RELAX": 0,
    "CLICK": 1,  # Imagine clicking mouse / hand movement
    "SQUEEZE": 2,  # Imagine squeezing fist (optional)
}

# Visual stimulus icons and colors
DIRECTION_ICONS = {
    "CLICK": "●",  # Circle for click/grasp
    "SQUEEZE": "◆",  # Diamond for squeeze
}

DIRECTION_COLORS = {
    "CLICK": "#4ADE80",  # Green
    "SQUEEZE": "#F59E0B",  # Amber
}

# ═══════════════════════════════════════════════════════════════════════════
# COLOR PALETTE (Neural Lab Theme)
# ═══════════════════════════════════════════════════════════════════════════

BG = "#04080F"  # Deep dark blue-black
ACCENT = "#00F5C4"  # Cyan-green accent
DIM = "#0A1A14"  # Darker green
GRID_COLOR = "#081810"  # Subtle grid
TEXT_MAIN = "#E0FFF6"  # Light cyan-white
TEXT_SUB = "#3A7A65"  # Muted green-gray
RING_BASE = "#0D2A22"  # Dark ring color


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION CLASS
# ═══════════════════════════════════════════════════════════════════════════

class BCIApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.configure(bg=BG)
        self.root.title("EEG BCI Precision Recorder")

        # State variables
        self.is_running = False
        self.is_paused = False
        self.current_label = "REST"
        self.trial_count = 0
        self.session_start = None
        self.session_elapsed = 0.0   # accumulated seconds (survives pauses)
        self._pause_start = None      # time.time() when paused
        self._stim_start_ms = 0
        self._stim_duration = STIM_DURATION

        # Recording duration limit: None = infinite
        self.max_duration = None      # seconds; set from menu
        self._duration_var = None     # tkinter StringVar for menu radio buttons

        # Auto-stop after queued stimulus finishes
        self._pending_stop = False

        # Signal buffer for waveform display
        self.wave_buf = collections.deque([500.0] * WAVE_POINTS, maxlen=WAVE_POINTS)

        # Initialize serial connection
        self.ser = None
        self._init_serial()

        # Initialize text-to-speech
        if TTS_AVAILABLE:
            self.speech_queue = queue.Queue()
            threading.Thread(target=self._speech_worker, daemon=True).start()

        # Setup UI
        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        root.geometry(f"{self.W}x{self.H}+0+0")

        self.cv = Canvas(self.root, width=self.W, height=self.H,
                         bg=BG, highlightthickness=0)
        self.cv.pack(fill=BOTH, expand=True)

        self._draw_static_bg()
        self._build_menu()

        # Key bindings
        self.root.bind("<Escape>", lambda e: self._quit())
        self.root.bind("<space>", lambda e: self._toggle_pause())

        # Start animation loop
        self._animate()

    # ───────────────────────────────────────────────────────────────────────
    # SERIAL CONNECTION
    # ───────────────────────────────────────────────────────────────────────

    def _init_serial(self):
        """Initialize serial connection to Arduino."""
        try:
            self.ser = serial.Serial(PORT, BAUD_RATE, timeout=0.01)
            time.sleep(2.5)  # Wait for Arduino reset
            self.ser.reset_input_buffer()
            print(f"[Serial] Connected to {PORT} at {BAUD_RATE} baud")
        except serial.SerialException as e:
            print(f"[Serial ERROR] {e}")
            print(f"[Serial] Could not open {PORT}")
            print("[Serial] Please check:")
            print("  1. Arduino is connected via USB")
            print("  2. Correct port name in PORT variable")
            print("  3. No other program is using the port")

            response = messagebox.askretrycancel(
                "Serial Connection Error",
                f"Could not connect to Arduino on {PORT}\n\n"
                f"Error: {e}\n\n"
                "Check port name and try again?")

            if response:
                self._init_serial()  # Retry
            else:
                self.ser = None

    # ───────────────────────────────────────────────────────────────────────
    # UI DRAWING - STATIC BACKGROUND
    # ───────────────────────────────────────────────────────────────────────

    def _draw_static_bg(self):
        """Draw grid, corners, and header/footer bars."""
        # Grid lines
        for x in range(0, self.W, 60):
            self.cv.create_line(x, 0, x, self.H, fill=GRID_COLOR, width=1)
        for y in range(0, self.H, 60):
            self.cv.create_line(0, y, self.W, y, fill=GRID_COLOR, width=1)

        # Corner brackets
        s = 32
        corners = [
            ((20, 20), (1, 1)),
            ((self.W - 20, 20), (-1, 1)),
            ((20, self.H - 20), (1, -1)),
            ((self.W - 20, self.H - 20), (-1, -1))
        ]
        for (cx, cy), (dx, dy) in corners:
            self.cv.create_line(cx, cy, cx + dx * s, cy, fill=ACCENT, width=2)
            self.cv.create_line(cx, cy, cx, cy + dy * s, fill=ACCENT, width=2)

        # Header bar
        self.cv.create_rectangle(0, 0, self.W, 54, fill="#020C09", outline="")
        self.cv.create_line(0, 54, self.W, 54, fill=ACCENT, width=1)
        self.cv.create_text(self.W // 2, 27,
                            text="◈   EEG  BCI  PRECISION  RECORDER   ◈",
                            fill=ACCENT, font=("Courier New", 17, "bold"))

        # Footer bar
        self.cv.create_rectangle(0, self.H - 40, self.W, self.H, fill="#020C09", outline="")
        self.cv.create_line(0, self.H - 40, self.W, self.H - 40, fill=TEXT_SUB, width=1)
        self.cv.create_text(self.W // 2, self.H - 20,
                            text="ESC: EXIT  |  SPACE: PAUSE/RESUME",
                            fill=TEXT_SUB, font=("Courier New", 11))

    # ───────────────────────────────────────────────────────────────────────
    # UI DRAWING - MENU
    # ───────────────────────────────────────────────────────────────────────

    def _build_menu(self):
        """Build the startup menu with session info and duration selector."""
        cx, cy = self.W // 2, self.H // 2
        cw, ch = 580, 520
        x0, y0 = cx - cw // 2, cy - ch // 2

        # Menu panel with double border
        self.cv.create_rectangle(x0, y0, x0 + cw, y0 + ch,
                                 fill="#020D08", outline=ACCENT, width=1, tags="menu")
        self.cv.create_rectangle(x0 + 4, y0 + 4, x0 + cw - 4, y0 + ch - 4,
                                 fill="", outline=RING_BASE, width=1, tags="menu")

        # Title
        self.cv.create_text(cx, y0 + 52, text="SESSION  SETUP",
                            fill=ACCENT, font=("Courier New", 28, "bold"), tags="menu")
        self.cv.create_line(x0 + 40, y0 + 80, x0 + cw - 40, y0 + 80,
                            fill=RING_BASE, width=1, tags="menu")

        # Info text
        info_y = y0 + 120
        self.cv.create_text(cx, info_y, text="MOTOR IMAGERY PARADIGM",
                            fill=TEXT_SUB, font=("Courier New", 12, "bold"), tags="menu")
        self.cv.create_text(cx, info_y + 28, text="Tasks: CLICK (hand movement) vs REST",
                            fill=TEXT_SUB, font=("Courier New", 10), tags="menu")
        self.cv.create_text(cx, info_y + 46, text="Hardware: Arduino + ADS1115 + BioAmp EXG Pill",
                            fill=TEXT_SUB, font=("Courier New", 10), tags="menu")

        # Connection status
        status_color = "#4ADE80" if self.ser else "#EF4444"
        status_text = "● CONNECTED" if self.ser else "● DISCONNECTED"
        self.cv.create_text(cx, info_y + 78, text=status_text,
                            fill=status_color, font=("Courier New", 11, "bold"), tags="menu")

        # ── Recording duration selector ──────────────────────────────────────
        dur_y = info_y + 115
        self.cv.create_text(cx, dur_y, text="RECORDING  DURATION",
                            fill=ACCENT, font=("Courier New", 10, "bold"), tags="menu")
        self.cv.create_line(x0 + 60, dur_y + 14, x0 + cw - 60, dur_y + 14,
                            fill=RING_BASE, width=1, tags="menu")

        # Duration options: (label, seconds)  — None = infinite
        self._duration_opts = [
            ("∞",       None),
            ("5 min",   5 * 60),
            ("15 min",  15 * 60),
            ("30 min",  30 * 60),
            ("1 hr",    60 * 60),
            ("2 hr",    120 * 60),
        ]
        self.max_duration = None          # default = infinite
        self._duration_var = StringVar(value="∞")

        # Layout: 3 columns × 2 rows of radio tiles
        self._radio_items = {}           # label -> {"tile", "ring", "dot"}
        cols = 3
        btn_w, btn_h = 160, 44
        gap_x, gap_y = 18, 12

        total_w = cols * btn_w + (cols - 1) * gap_x
        bx0 = cx - total_w // 2
        by0 = dur_y + 30

        for idx, (lbl, secs) in enumerate(self._duration_opts):
            row = idx // cols
            col = idx % cols
            bx = bx0 + col * (btn_w + gap_x)
            by = by0 + row * (btn_h + gap_y)

            # Background tile
            tile = self.cv.create_rectangle(
                bx, by, bx + btn_w, by + btn_h,
                fill="#061410", outline="#0D2A22", width=1,
                tags=("menu", f"dur_tile_{lbl}"))

            # Radio outer ring
            r_outer, r_inner = 9, 5
            rx, ry = bx + 22, by + btn_h // 2
            ring = self.cv.create_oval(
                rx - r_outer, ry - r_outer,
                rx + r_outer, ry + r_outer,
                outline=TEXT_SUB, width=2, fill="#020D08",
                tags=("menu", f"dur_ring_{lbl}"))

            # Inner fill dot (shown when selected)
            dot = self.cv.create_oval(
                rx - r_inner, ry - r_inner,
                rx + r_inner, ry + r_inner,
                fill="", outline="",
                tags=("menu", f"dur_dot_{lbl}"))

            # Option label text
            self.cv.create_text(
                rx + r_outer + 10, ry,
                text=lbl,
                fill=TEXT_MAIN,
                font=("Courier New", 13, "bold"),
                anchor=W,
                tags=("menu", f"dur_lbl_{lbl}"))

            # Invisible hit-zone covers the full tile for easy clicking
            hit = self.cv.create_rectangle(
                bx, by, bx + btn_w, by + btn_h,
                fill="", outline="",
                tags=("menu", f"dur_hit_{lbl}"))

            # Click + hover bindings on every sub-element
            for item in (tile, ring, dot, hit):
                self.cv.tag_bind(
                    item, "<Button-1>",
                    lambda e, s=secs, l=lbl: self._select_duration(s, l))
                self.cv.tag_bind(
                    item, "<Enter>",
                    lambda e, tl=tile, rg=ring: self._dur_hover(tl, rg, True))
                self.cv.tag_bind(
                    item, "<Leave>",
                    lambda e, tl=tile, rg=ring, lb=lbl: self._dur_hover(tl, rg, False, lb))

            lbl_tag = f"dur_lbl_{lbl}"
            self.cv.tag_bind(lbl_tag, "<Button-1>",
                             lambda e, s=secs, l=lbl: self._select_duration(s, l))
            self.cv.tag_bind(lbl_tag, "<Enter>",
                             lambda e, tl=tile, rg=ring: self._dur_hover(tl, rg, True))
            self.cv.tag_bind(lbl_tag, "<Leave>",
                             lambda e, tl=tile, rg=ring, lb=lbl: self._dur_hover(tl, rg, False, lb))

            self._radio_items[lbl] = {"tile": tile, "ring": ring, "dot": dot}

        # Pre-select default (∞) with full visual state
        self._select_duration(None, "∞")

        # ── Begin button ───────────────────────────────────────────────────────
        btn_area_bottom = by0 + 2 * (btn_h + gap_y) - gap_y
        self.begin_btn = Button(self.root,
                                text="▶   BEGIN  SESSION",
                                font=("Courier New", 16, "bold"),
                                bg=ACCENT if self.ser else "#555555",
                                fg=BG,
                                activebackground="#00C8A0", activeforeground=BG,
                                relief=FLAT, bd=0, padx=30, pady=16, cursor="hand2",
                                command=self.start_bci,
                                state=NORMAL if self.ser else DISABLED)
        self.cv.create_window(cx, btn_area_bottom + 46, window=self.begin_btn,
                              width=320, tags="menu")

        # Technical specs
        self.cv.create_text(cx, btn_area_bottom + 110,
                            text=f"PORT: {PORT}",
                            fill=TEXT_SUB, font=("Courier New", 9), tags="menu")
        self.cv.create_text(cx, btn_area_bottom + 127,
                            text=f"BAUD: {BAUD_RATE}  |  Fs: 256 Hz  |  ADC: 16-bit",
                            fill=TEXT_SUB, font=("Courier New", 9), tags="menu")

    def _dur_hover(self, tile_id, ring_id, entering, lbl=None):
        """Highlight a duration tile on hover (skip if it is already selected)."""
        is_selected = (lbl is not None and self._duration_var.get() == lbl)
        if entering and not is_selected:
            self.cv.itemconfig(tile_id, fill="#0A1F18", outline=TEXT_SUB)
            self.cv.itemconfig(ring_id, outline=TEXT_MAIN)
        elif not entering and not is_selected:
            self.cv.itemconfig(tile_id, fill="#061410", outline="#0D2A22")
            self.cv.itemconfig(ring_id, outline=TEXT_SUB)

    def _select_duration(self, secs, lbl):
        """Update canvas radio indicators to reflect the chosen duration."""
        self.max_duration = secs
        self._duration_var.set(lbl)

        for opt_lbl, items in self._radio_items.items():
            if opt_lbl == lbl:
                # Selected: cyan ring + filled dot + accent tile border
                self.cv.itemconfig(items["ring"], outline=ACCENT, width=2, fill="#061410")
                self.cv.itemconfig(items["dot"],  fill=ACCENT, outline=ACCENT)
                self.cv.itemconfig(items["tile"], fill="#051A12", outline=ACCENT)
            else:
                # Deselected: dim ring, hidden dot, dark tile
                self.cv.itemconfig(items["ring"], outline=TEXT_SUB, width=2, fill="#020D08")
                self.cv.itemconfig(items["dot"],  fill="", outline="")
                self.cv.itemconfig(items["tile"], fill="#061410", outline="#0D2A22")

    def _set_duration(self, secs):
        """Store chosen duration limit (None = infinite)."""
        self.max_duration = secs

    # ───────────────────────────────────────────────────────────────────────
    # SESSION START
    # ───────────────────────────────────────────────────────────────────────

    def start_bci(self):
        """Initialize and start BCI recording session."""
        if not self.ser:
            messagebox.showerror("Error", "No serial connection to Arduino!")
            return

        # Send START command to Arduino
        try:
            self.ser.write(b"START\n")
            self.ser.flush()
        except Exception as e:
            messagebox.showerror("Serial Error", f"Failed to start Arduino:\n{e}")
            return

        # Set state
        self.is_running = True
        self.is_paused = False
        self._pending_stop = False
        self.session_start = time.time()
        self.session_elapsed = 0.0
        self._pause_start = None
        self.trial_count = 0

        # Snapshot duration limit chosen in menu
        # (max_duration was set by _set_duration via radio buttons)
        dur_label = "∞" if self.max_duration is None else f"{self.max_duration}s"
        print(f"[Session] Duration limit: {dur_label}")

        # Clear menu and rebuild UI
        for w in self.root.winfo_children():
            if not isinstance(w, Canvas):
                w.destroy()

        self.cv.delete("all")
        self._draw_static_bg()
        self._build_session_ui()

        # Task pool (which tasks to present)
        self.pool = ["CLICK"]  # Add "SQUEEZE" if using multiple tasks

        # ── CSV: append if file exists, write header only for new files ──────
        import os
        file_exists = os.path.isfile(FILE_NAME) and os.path.getsize(FILE_NAME) > 0
        try:
            with open(FILE_NAME, 'a', newline='') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow([
                        "Timestamp_Unix",
                        "Timestamp_Ms",
                        "Signal_Raw",
                        "Intent_Label",
                        "Label_Class"
                    ])
        except Exception as e:
            messagebox.showerror("File Error", f"Could not open CSV file:\n{e}")
            self.is_running = False
            return

        # Start data logging thread
        threading.Thread(target=self._data_logger, daemon=True).start()

        # Start stimulus sequence after short delay
        self.root.after(800, self._run_stimulus)

        print(f"[Session] Recording started → {FILE_NAME} (append mode)")

    # ───────────────────────────────────────────────────────────────────────
    # UI DRAWING - SESSION
    # ───────────────────────────────────────────────────────────────────────

    def _build_session_ui(self):
        """Build the main recording interface."""
        cx, cy = self.W // 2, self.H // 2 - 40

        # Concentric rings around stimulus
        for r in [168, 208, 248]:
            self.cv.create_oval(cx - r, cy - r, cx + r, cy + r,
                                outline=RING_BASE, width=1)

        # Animated pulse ring
        self.ring_pulse = self.cv.create_oval(
            cx - 160, cy - 160, cx + 160, cy + 160,
            outline=ACCENT, width=2)

        # Countdown arc
        self.arc_item = self.cv.create_arc(
            cx - 186, cy - 186, cx + 186, cy + 186,
            start=90, extent=0,
            outline=ACCENT, width=4, style=ARC)

        # Stimulus icon (large symbol)
        self.icon_item = self.cv.create_text(
            cx, cy - 18, text="",
            fill=ACCENT, font=("Courier New", 190, "bold"), anchor=CENTER)

        # Stimulus label (text below icon)
        self.label_item = self.cv.create_text(
            cx, cy + 134, text="",
            fill=ACCENT, font=("Courier New", 30, "bold"), anchor=CENTER)

        # Recording indicator
        self.status_item = self.cv.create_text(
            self.W - 24, 27, text="● RECORDING",
            fill=ACCENT, font=("Courier New", 11, "bold"), anchor=E)

        # Waveform display panel
        wy = self.H - 155
        self.wave_wy = wy
        self.wave_w = int(self.W * 0.75)
        self.wave_y0 = wy - WAVE_HEIGHT
        self.wave_y1 = wy + WAVE_HEIGHT

        # Waveform panel background
        self.cv.create_rectangle(
            self.W // 2 - self.wave_w // 2 - 2, self.wave_y0 - 10,
            self.W // 2 + self.wave_w // 2 + 2, self.wave_y1 + 10,
            fill="#020C09", outline=TEXT_SUB, width=1)

        # Center line (baseline)
        self.cv.create_line(
            self.W // 2 - self.wave_w // 2, wy,
            self.W // 2 + self.wave_w // 2, wy,
            fill=RING_BASE, width=1, dash=(4, 8))

        # Y-axis label
        self.cv.create_text(
            self.W // 2 - self.wave_w // 2 - 12, wy,
            text="EEG", fill=TEXT_SUB,
            font=("Courier New", 10), anchor=E)

        # Waveform line
        self.wave_line = self.cv.create_line(
            0, 0, 1, 1, fill=ACCENT, width=1.5, smooth=True)

        # Statistics panel
        self.stat_trial = self.cv.create_text(
            24, self.H - 20, text="TRIAL: 0",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)
        self.stat_time = self.cv.create_text(
            190, self.H - 20, text="TIME: 00:00",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)
        self.stat_label = self.cv.create_text(
            390, self.H - 20, text="CLASS: 0 [REST]",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)
        self.stat_dur = self.cv.create_text(
            self.W - 190, self.H - 20, text="LIMIT: ∞",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)

        # PAUSED overlay (hidden initially)
        self.paused_overlay = self.cv.create_rectangle(
            0, 0, self.W, self.H,
            fill="#000000", outline="", stipple="gray50", state="hidden")
        self.paused_text = self.cv.create_text(
            self.W // 2, self.H // 2,
            text="⏸  PAUSED\n\nPress SPACE to resume",
            fill=ACCENT, font=("Courier New", 36, "bold"),
            justify=CENTER, state="hidden")

    # ───────────────────────────────────────────────────────────────────────
    # ANIMATION LOOP
    # ───────────────────────────────────────────────────────────────────────

    def _animate(self):
        """Main animation loop (~30 FPS)."""
        if self.is_running:
            self._draw_waveform()
            self._update_countdown()
            self._pulse_ring()
            self._update_stats()

        self.root.after(33, self._animate)  # ~30 FPS

    def _pulse_ring(self):
        """Animate the pulsing ring around stimulus."""
        if not hasattr(self, 'ring_pulse'):
            return

        t = time.time()
        scale = 1.0 + 0.02 * math.sin(t * 2.5)
        cx, cy = self.W // 2, self.H // 2 - 40
        r = int(160 * scale)
        self.cv.coords(self.ring_pulse, cx - r, cy - r, cx + r, cy + r)

        # Color pulse
        v = int(180 + 75 * abs(math.sin(t * 2.5)))
        color = f"#{0:02x}{v:02x}{(v // 2 + 80):02x}"
        self.cv.itemconfig(self.ring_pulse, outline=color)

    def _update_countdown(self):
        """Update countdown arc around stimulus."""
        if not hasattr(self, 'arc_item'):
            return

        elapsed = (time.time() * 1000) - self._stim_start_ms
        frac = min(elapsed / self._stim_duration, 1.0)
        self.cv.itemconfig(self.arc_item, extent=-360 * frac)

    def _draw_waveform(self):
        """Draw real-time EEG waveform."""
        if not hasattr(self, 'wave_line'):
            return

        buf = list(self.wave_buf)
        n = len(buf)
        if n < 2:
            return

        cx = self.W // 2
        ww = self.wave_w
        wy = self.wave_wy

        # Auto-scale to visible range
        mean_val = sum(buf) / n
        deviations = [abs(v - mean_val) for v in buf]
        max_dev = max(deviations) if deviations else 1.0
        scale = WAVE_HEIGHT * 0.9 / max(max_dev, 50.0)

        # Build point list
        pts = []
        for i, v in enumerate(buf):
            x = cx - ww // 2 + int(i / (n - 1) * ww)
            y = wy - int((v - mean_val) * scale)
            pts += [x, y]

        self.cv.coords(self.wave_line, *pts)

    def _update_stats(self):
        """Update statistics panel."""
        if not hasattr(self, 'stat_trial'):
            return

        # Update elapsed only while running and not paused.
        # Pause compensation: _toggle_pause shifts session_start forward by the
        # pause duration, so (now - session_start) is always active-only time.
        if self.is_running and not self.is_paused and self.session_start:
            self.session_elapsed = time.time() - self.session_start

        elapsed = int(self.session_elapsed)
        m, s = divmod(elapsed, 60)

        self.cv.itemconfig(self.stat_trial, text=f"TRIAL: {self.trial_count}")
        self.cv.itemconfig(self.stat_time, text=f"TIME: {m:02d}:{s:02d}")

        label_class = LABEL_MAP.get(self.current_label, 0)
        self.cv.itemconfig(self.stat_label,
                           text=f"CLASS: {label_class}  [{self.current_label}]")

        # Duration limit display
        if hasattr(self, 'stat_dur'):
            if self.max_duration is None:
                limit_str = "LIMIT: ∞"
            else:
                rem = max(0, int(self.max_duration - elapsed))
                rm, rs = divmod(rem, 60)
                limit_str = f"REM: {rm:02d}:{rs:02d}"
            self.cv.itemconfig(self.stat_dur, text=limit_str)

            # Auto-stop when time limit reached
            if self.max_duration is not None and elapsed >= self.max_duration:
                if self.is_running and not self._pending_stop:
                    self._pending_stop = True
                    self.root.after(0, self._auto_stop)

        # Blinking recording / paused indicator
        if self.is_paused:
            self.cv.itemconfig(self.status_item, text="⏸  PAUSED",
                               fill="#F59E0B")
        else:
            blink = "● RECORDING" if int(time.time() * 2) % 2 == 0 else "○ RECORDING"
            self.cv.itemconfig(self.status_item, text=blink, fill=ACCENT)

    # ───────────────────────────────────────────────────────────────────────
    # STIMULUS SEQUENCE
    # ───────────────────────────────────────────────────────────────────────

    def _run_stimulus(self):
        """Present stimulus (task cue)."""
        if not self.is_running or self.is_paused or self._pending_stop:
            return

        # Select random task
        label = random.choice(self.pool)
        color = DIRECTION_COLORS.get(label, ACCENT)
        icon = DIRECTION_ICONS.get(label, "?")

        self.current_label = label
        self._stim_start_ms = time.time() * 1000
        self._stim_duration = STIM_DURATION
        self.trial_count += 1

        # Update display
        self.cv.itemconfig(self.icon_item, text=icon, fill=color)
        self.cv.itemconfig(self.label_item, text=label, fill=color)
        self.cv.itemconfig(self.arc_item, outline=color)
        self.cv.itemconfig(self.ring_pulse, outline=color)

        # Voice cue
        self.speak(label)

        # Schedule rest period
        self.root.after(STIM_DURATION, self._run_rest)

    def _run_rest(self):
        """Present rest cue."""
        if not self.is_running or self._pending_stop:
            return

        rest_word = "REST"
        self.current_label = rest_word
        self._stim_start_ms = time.time() * 1000
        self._stim_duration = REST_DURATION

        # Update display
        self.cv.itemconfig(self.icon_item, text="+", fill=RING_BASE)
        self.cv.itemconfig(self.label_item, text=rest_word, fill=TEXT_SUB)
        self.cv.itemconfig(self.arc_item, outline=TEXT_SUB)
        self.cv.itemconfig(self.ring_pulse, outline=TEXT_SUB)

        # Voice cue
        self.speak(rest_word)

        # Schedule next stimulus (skip if pending auto-stop)
        if not self._pending_stop:
            self.root.after(REST_DURATION, self._run_stimulus)

    # ───────────────────────────────────────────────────────────────────────
    # DATA LOGGER
    # ───────────────────────────────────────────────────────────────────────

    def _data_logger(self):
        """Background thread for reading and logging serial data."""
        session_start_ms = time.time() * 1000

        with open(FILE_NAME, 'a', newline='') as f:
            writer = csv.writer(f)

            while self.is_running or self.is_paused:
                # Skip data while paused (drain buffer silently)
                if self.is_paused:
                    if self.ser and self.ser.in_waiting:
                        self.ser.reset_input_buffer()
                    time.sleep(0.05)
                    continue

                if self.ser and self.ser.in_waiting:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()

                        # Skip empty lines and debug messages
                        if not line or line.startswith('#'):
                            continue

                        # Parse signal value
                        try:
                            signal_value = float(line)
                        except ValueError:
                            continue

                        # Update waveform buffer
                        self.wave_buf.append(signal_value)

                        # Log to CSV
                        timestamp_unix = time.time()
                        timestamp_ms = (time.time() * 1000) - session_start_ms
                        label_class = LABEL_MAP.get(self.current_label, 0)

                        writer.writerow([
                            f"{timestamp_unix:.9f}",
                            f"{timestamp_ms:.3f}",
                            f"{signal_value:.4f}",
                            self.current_label,
                            label_class
                        ])

                        # Flush every 100 samples to disk
                        if int(timestamp_ms) % 100 < 4:
                            f.flush()

                    except Exception as e:
                        print(f"[Data Logger] Error: {e}")
                        continue
                else:
                    time.sleep(0.001)  # Small sleep to reduce CPU usage

    # ───────────────────────────────────────────────────────────────────────
    # TEXT-TO-SPEECH
    # ───────────────────────────────────────────────────────────────────────

    def _speech_worker(self):
        """Background thread for text-to-speech."""
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 0.9)

        while True:
            text = self.speech_queue.get()
            if text is None:
                break
            try:
                engine.say(text)
                engine.runAndWait()
            except:
                pass
            self.speech_queue.task_done()

    def speak(self, text):
        """Queue text for speech synthesis."""
        if not TTS_AVAILABLE:
            return

        # Clear queue (keep only latest cue)
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break

        self.speech_queue.put(text)

    # ───────────────────────────────────────────────────────────────────────
    # CONTROLS
    # ───────────────────────────────────────────────────────────────────────

    def _toggle_pause(self):
        """Pause/resume recording (spacebar). Only active during a session."""
        if not hasattr(self, 'arc_item'):
            # Not in a session yet – ignore
            return

        if not self.is_paused:
            # ── Pause ─────────────────────────────────────────────────────────
            self.is_paused = True
            self._pause_start = time.time()
            # Show overlay
            self.cv.itemconfig(self.paused_overlay, state="normal")
            self.cv.itemconfig(self.paused_text, state="normal")
            self.cv.tag_raise(self.paused_text)
            print("[Session] PAUSED")
        else:
            # ── Resume ────────────────────────────────────────────────────────
            if self._pause_start is not None:
                pause_dur = time.time() - self._pause_start
                # Shift session_start forward so elapsed doesn't count pause time
                if self.session_start is not None:
                    self.session_start += pause_dur
                self._pause_start = None
            self.is_paused = False
            # Hide overlay
            self.cv.itemconfig(self.paused_overlay, state="hidden")
            self.cv.itemconfig(self.paused_text, state="hidden")
            print("[Session] RESUMED")
            # Re-kick stimulus loop
            self.root.after(100, self._run_stimulus)

    def _auto_stop(self):
        """Called when the recording duration limit has been reached."""
        if not self.is_running:
            return
        print("[Session] Duration limit reached – stopping.")
        self.is_running = False
        self.is_paused = False
        if TTS_AVAILABLE:
            self.speak("Session complete")
        messagebox.showinfo(
            "Session Complete",
            f"The scheduled recording duration has finished.\n"
            f"Data saved to {FILE_NAME}"
        )
        self._quit()

    def _quit(self):
        """Cleanup and exit application."""
        print("[Session] Shutting down...")

        self.is_running = False

        # Stop speech
        if TTS_AVAILABLE:
            self.speech_queue.put(None)

        # Close serial
        if self.ser:
            try:
                self.ser.write(b"STOP\n")
                self.ser.flush()
                time.sleep(0.1)
                self.ser.close()
                print("[Serial] Connection closed")
            except Exception as e:
                print(f"[Serial] Error closing: {e}")

        print(f"[Session] Data saved to {FILE_NAME}")
        self.root.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Initialize and run the BCI application."""
    root = Tk()

    # Set fullscreen based on platform
    if platform.system() == "Darwin":  # macOS
        root.attributes("-fullscreen", True)
    elif platform.system() == "Windows":
        root.state('zoomed')
    else:  # Linux
        root.attributes("-fullscreen", True)

    root.resizable(False, False)

    # Create and run app
    app = BCIApp(root)

    print("=" * 70)
    print("EEG BCI PRECISION RECORDER")
    print("=" * 70)
    print(f"Port: {PORT} @ {BAUD_RATE} baud")
    print(f"Output: {FILE_NAME}")
    print("Controls:")
    print("  ESC   - Exit application")
    print("  SPACE - Pause/Resume recording")
    print("=" * 70)

def set_window_icon(root: Tk):
    """Safely load and set the window icon, handling PyInstaller bundles."""
    try:
        # Determine base path (PyInstaller sets sys._MEIPASS)
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        icon_path = os.path.join(base_path, "Media", "Mind-Nav-Logo.png")
        if os.path.exists(icon_path):
            img = PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception as e:
        print(f"[Warning] Could not load window icon: {e}")

def main():
    root = Tk()
    root.attributes("-fullscreen", True)
    root.resizable(False, False)
    set_window_icon(root)
    app = BCIApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[Interrupt] Exiting...")
        app._quit()

if __name__ == "__main__":
    main()