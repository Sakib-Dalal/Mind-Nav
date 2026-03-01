"""
Mind-Nav — BCI Virtual Keyboard
════════════════════════════════
• Displays a QWERTY virtual keyboard on screen
• Scans through keys (row → column) automatically
• Detects mental CLICK via trained BCI models to select keys
• Supports Arduino EEG input or simulation mode
• Press ENTER to simulate a click (testing without hardware)
• Press SPACE to pause / resume scanning
• Optional Pico W server broadcasts CLICK/REST predictions

Press ESC to exit at any time.
"""

import time
import math
import threading
import collections

import numpy as np
import tkinter as tk
from tkinter import ttk

from config import (
    BG, BG_DARKER, ACCENT, ACCENT_DIM, DIM, GRID_COLOR,
    TEXT_MAIN, TEXT_SUB, RING_BASE,
    KEY_BG, KEY_BORDER, KEY_TEXT, KEY_HL_BG, KEY_HL_BORDER, KEY_HL_TEXT,
    KEY_SEL_BG, KEY_SEL_TEXT, COL_CLICK, COL_REST,
    CONF_HIGH, CONF_LOW,
    LABEL_NAMES, KEYBOARD_ROWS, WIN_LEN, PORT, SOCKET_PORT,
    WAVE_POINTS
)
from models import ModelManager
from pico_server import PicoServer
from serial_reader import SerialReader


class VirtualKeyboardApp:

    # ── Scan phases ───────────────────────────────────────────────────────
    PHASE_ROW = "row"
    PHASE_KEY = "key"

    def __init__(self, root: tk.Tk, *, on_back=None):
        """
        Parameters
        ----------
        root : tk.Tk
            Root Tkinter window.
        on_back : callable | None
            If provided, called to return to the main menu.
        """
        self.root = root
        self.on_back = on_back
        self.root.configure(bg=BG)
        self.root.title("Mind-Nav  ◈  BCI Virtual Keyboard")

        self.root.update_idletasks()
        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+0+0")

        # ── State ─────────────────────────────────────────────────────────
        self.is_running = False
        self.typed_text = ""
        self.scan_speed_ms = 1200
        self.confidence_threshold = 0.5
        self.selected_model = ""
        self.input_mode = "spacebar"
        self.sim_click = False
        self.is_paused = False

        # Scan state
        self.scan_phase = self.PHASE_ROW
        self.current_row = 0
        self.current_key = 0
        self.row_cycle_count = 0
        self.key_cycle_count = 0
        self.MAX_CYCLES = 2

        # Key geometry storage
        self.key_rects: list[list[tuple]] = []
        self.key_canvas_ids: list[list[dict]] = []

        # EEG data buffer
        self.predict_buf = collections.deque(maxlen=WIN_LEN)

        # Models & I/O
        self.model_mgr = ModelManager()
        self.serial_reader = None
        self.pico_server = PicoServer()
        self.pico_active = False

        # Waveform toggle & rendering
        self.show_waveform = False
        self.wave_buf = collections.deque([0.0] * WAVE_POINTS, maxlen=WAVE_POINTS)

        # Debouncing state (cooldown after a CLICK)
        self.in_cooldown = False
        self.cooldown_end_time = 0.0
        self.COOLDOWN_DUR_MS = 600

        # Latest prediction info
        self.last_pred_label = "---"
        self.last_pred_conf = 0.0

        # Canvas
        self.cv = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self.cv.pack(fill=tk.BOTH, expand=True)

        # Bindings
        self.root.bind("<Escape>", lambda _: self._quit())
        self.root.bind("<space>", self._on_space)
        self.root.bind("<Return>", self._on_enter)
        self.root.bind("<KP_Enter>", self._on_enter)
        self.root.bind("<BackSpace>", self._on_backspace)

        self.root.after(50, self._show_menu)

    # ══════════════════════════════════════════════════════════════════════
    #  MENU / SETUP SCREEN
    # ══════════════════════════════════════════════════════════════════════
    def _show_menu(self):
        self.cv.delete("all")
        self._draw_grid()
        self._draw_header("◈   MIND-NAV  BCI  KEYBOARD   ◈")
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
        cw, ch = 700, 640
        x0, y0 = cx - cw // 2, cy - ch // 2

        # Card background
        self.cv.create_rectangle(x0, y0, x0 + cw, y0 + ch,
                                 fill="#020D08", outline=ACCENT, width=1)
        self.cv.create_text(cx, y0 + 46, text="KEYBOARD  SETUP",
                            fill=ACCENT, font=("Courier New", 24, "bold"))
        self.cv.create_line(x0 + 40, y0 + 72, x0 + cw - 40, y0 + 72,
                            fill=RING_BASE, width=1)

        row_y = [y0 + 90, y0 + 145, y0 + 200, y0 + 255, y0 + 310, y0 + 365, y0 + 420]

        # ── Input mode selector (canvas-native radio tiles) ─────────────────
        self.cv.create_text(x0 + 40, row_y[0] - 2, text="INPUT MODE:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._mode_var = tk.StringVar(value="spacebar")
        self._ai_widgets: list[tuple[tk.Widget, dict]] = []
        self._ai_canvas_ids: list[int] = []
        self._mode_items: dict = {}   # mode_val -> {tile, ring, dot}

        mode_opts = [
            ("spacebar", "Spacebar  (Manual)"),
            ("ai",       "AI  (BCI Model)"),
        ]
        tile_w, tile_h = 230, 40
        gap = 14
        total_modes_w = len(mode_opts) * tile_w + (len(mode_opts) - 1) * gap
        mx0 = cx - total_modes_w // 2
        my  = row_y[0] - tile_h // 2 + 4

        for col, (mval, mlbl) in enumerate(mode_opts):
            bx = mx0 + col * (tile_w + gap)
            by = my

            tile = self.cv.create_rectangle(
                bx, by, bx + tile_w, by + tile_h,
                fill="#061410", outline="#0D2A22", width=1,
                tags=("menu", f"mode_tile_{mval}"))

            r_outer, r_inner = 8, 4
            rx, ry = bx + 20, by + tile_h // 2
            ring = self.cv.create_oval(
                rx - r_outer, ry - r_outer,
                rx + r_outer, ry + r_outer,
                outline=TEXT_SUB, width=2, fill="#020D08",
                tags=("menu", f"mode_ring_{mval}"))

            dot = self.cv.create_oval(
                rx - r_inner, ry - r_inner,
                rx + r_inner, ry + r_inner,
                fill="", outline="",
                tags=("menu", f"mode_dot_{mval}"))

            self.cv.create_text(
                rx + r_outer + 10, ry,
                text=mlbl,
                fill=TEXT_MAIN,
                font=("Courier New", 11, "bold"),
                anchor="w",
                tags=("menu", f"mode_lbl_{mval}"))

            hit = self.cv.create_rectangle(
                bx, by, bx + tile_w, by + tile_h,
                fill="", outline="",
                tags=("menu", f"mode_hit_{mval}"))

            for item in (tile, ring, dot, hit):
                self.cv.tag_bind(
                    item, "<Button-1>",
                    lambda e, v=mval: self._select_mode(v))
                self.cv.tag_bind(
                    item, "<Enter>",
                    lambda e, tl=tile, rg=ring: self._mode_hover(tl, rg, True))
                self.cv.tag_bind(
                    item, "<Leave>",
                    lambda e, tl=tile, rg=ring, v=mval: self._mode_hover(tl, rg, False, v))

            lbl_tag = f"mode_lbl_{mval}"
            self.cv.tag_bind(lbl_tag, "<Button-1>",
                             lambda e, v=mval: self._select_mode(v))
            self.cv.tag_bind(lbl_tag, "<Enter>",
                             lambda e, tl=tile, rg=ring: self._mode_hover(tl, rg, True))
            self.cv.tag_bind(lbl_tag, "<Leave>",
                             lambda e, tl=tile, rg=ring, v=mval: self._mode_hover(tl, rg, False, v))

            self._mode_items[mval] = {"tile": tile, "ring": ring, "dot": dot}

        # Pre-select default
        self._select_mode("spacebar")

        # ── Arduino port ──────────────────────────────────────────────────
        cid_port = self.cv.create_text(x0 + 40, row_y[1], text="ARDUINO PORT:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._ai_canvas_ids.append(cid_port)
        self._port_var = tk.StringVar(value=PORT)
        port_entry = tk.Entry(self.root, textvariable=self._port_var,
                 bg=DIM, fg=ACCENT, insertbackground=ACCENT,
                 font=("Courier New", 12), relief=tk.FLAT, bd=0)
        port_entry.place(x=cx - 40, y=row_y[1] - 9, width=260, height=26)
        self._ai_widgets.append(
            (port_entry, dict(x=cx - 40, y=row_y[1] - 9, width=260, height=26)))

        # ── Model selector ────────────────────────────────────────────────
        models = self.model_mgr.available_models()
        cid_model = self.cv.create_text(x0 + 40, row_y[2], text="MODEL:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._ai_canvas_ids.append(cid_model)
        if models:
            self._model_var = tk.StringVar(value=models[0])
            cb = ttk.Combobox(self.root, textvariable=self._model_var,
                              values=models, state="readonly",
                              font=("Courier New", 12))
            cb.place(x=cx - 40, y=row_y[2] - 10, width=260, height=28)
            self._ai_widgets.append(
                (cb, dict(x=cx - 40, y=row_y[2] - 10, width=260, height=28)))
        else:
            self._model_var = tk.StringVar(value="")
            cid_nowarn = self.cv.create_text(cx + 80, row_y[2],
                                text="[!]  No models found",
                                fill="#FF4D6A", font=("Courier New", 11))
            self._ai_canvas_ids.append(cid_nowarn)

        # ── Scan speed ────────────────────────────────────────────────────
        self.cv.create_text(x0 + 40, row_y[3], text="SCAN SPEED (ms):",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._speed_var = tk.IntVar(value=1200)
        tk.Scale(self.root, variable=self._speed_var,
                 from_=400, to=3000, orient=tk.HORIZONTAL,
                 bg=DIM, fg=ACCENT, troughcolor=RING_BASE,
                 highlightthickness=0, bd=0, length=240,
                 font=("Courier New", 9)
                 ).place(x=cx - 40, y=row_y[3] - 18)

        # ── Confidence threshold ──────────────────────────────────────────
        cid_thresh = self.cv.create_text(x0 + 40, row_y[4],
                            text="CONF. THRESHOLD:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._ai_canvas_ids.append(cid_thresh)
        self._thresh_var = tk.DoubleVar(value=0.50)
        thresh_scale = tk.Scale(self.root, variable=self._thresh_var,
                 from_=0.30, to=0.95, resolution=0.05,
                 orient=tk.HORIZONTAL,
                 bg=DIM, fg=ACCENT, troughcolor=RING_BASE,
                 highlightthickness=0, bd=0, length=240,
                 font=("Courier New", 9))
        thresh_scale.place(x=cx - 40, y=row_y[4] - 18)
        self._ai_widgets.append(
            (thresh_scale, dict(x=cx - 40, y=row_y[4] - 18)))

        # ── Pico W toggle ────────────────────────────────────────────────
        cid_pico = self.cv.create_text(x0 + 40, row_y[5],
                            text="PICO W SERVER:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._ai_canvas_ids.append(cid_pico)
        self._pico_var = tk.BooleanVar(value=False)
        pico_cb = tk.Checkbutton(self.root,
                       variable=self._pico_var,
                       text=f"Enable  (TCP port {SOCKET_PORT})",
                       font=("Courier New", 10),
                       fg=TEXT_MAIN, bg=DIM,
                       activebackground=DIM,
                       activeforeground=ACCENT,
                       selectcolor=RING_BASE)
        pico_cb.place(x=cx - 40, y=row_y[5] - 12)
        self._ai_widgets.append(
            (pico_cb, dict(x=cx - 40, y=row_y[5] - 12)))

        # ── Waveform toggle ──────────────────────────────────────────────
        cid_wave = self.cv.create_text(x0 + 40, row_y[6],
                            text="SHOW WAVEFORM:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._ai_canvas_ids.append(cid_wave)
        self._wave_var = tk.BooleanVar(value=True)
        wave_cb = tk.Checkbutton(self.root,
                       variable=self._wave_var,
                       text="Live scrolling EEG trace",
                       font=("Courier New", 10),
                       fg=TEXT_MAIN, bg=DIM,
                       activebackground=DIM,
                       activeforeground=ACCENT,
                       selectcolor=RING_BASE)
        wave_cb.place(x=cx - 40, y=row_y[6] - 12)
        self._ai_widgets.append(
            (wave_cb, dict(x=cx - 40, y=row_y[6] - 12)))

        # ── Errors ────────────────────────────────────────────────────────
        if self.model_mgr.errors:
            ey = y0 + 440
            self.cv.create_text(cx, ey, text="Warnings:",
                                fill="#FF4D6A", font=("Courier New", 9))
            for i, err in enumerate(self.model_mgr.errors[:3]):
                self.cv.create_text(cx, ey + 14 + i * 14,
                                    text=err[:84], fill="#FF4D6A",
                                    font=("Courier New", 8))

        # ── Start button ──────────────────────────────────────────────────
        tk.Button(self.root,
                  text=">>  START  KEYBOARD",
                  font=("Courier New", 15, "bold"),
                  bg=ACCENT, fg=BG,
                  activebackground="#00C8A0", activeforeground=BG,
                  relief=tk.FLAT, bd=0, padx=30, pady=14,
                  cursor="hand2",
                  command=self._start_keyboard
                  ).place(x=cx - 155, y=y0 + 505, width=310, height=54)

        # ── Info ──────────────────────────────────────────────────────────
        self.cv.create_text(
            cx, y0 + 585,
            text=f"Models:  {', '.join(models) if models else 'NONE'}   |   "
                 f"ENTER = simulate click   |   SPACE = pause   |   ESC = quit",
            fill=TEXT_SUB, font=("Courier New", 9))

        # Apply initial mode visibility
        self._on_mode_change()

    # ══════════════════════════════════════════════════════════════════════
    #  MODE CHANGE
    # ══════════════════════════════════════════════════════════════════════
    def _select_mode(self, mode_val: str):
        """Update canvas radio tiles and trigger AI widget visibility."""
        self._mode_var.set(mode_val)
        for mval, items in self._mode_items.items():
            if mval == mode_val:
                self.cv.itemconfig(items["ring"], outline=ACCENT, width=2, fill="#061410")
                self.cv.itemconfig(items["dot"],  fill=ACCENT, outline=ACCENT)
                self.cv.itemconfig(items["tile"], fill="#051A12", outline=ACCENT)
            else:
                self.cv.itemconfig(items["ring"], outline=TEXT_SUB, width=2, fill="#020D08")
                self.cv.itemconfig(items["dot"],  fill="", outline="")
                self.cv.itemconfig(items["tile"], fill="#061410", outline="#0D2A22")
        self._on_mode_change()

    def _mode_hover(self, tile_id, ring_id, entering, mode_val=None):
        """Subtle highlight on hover (skip if tile is already selected)."""
        is_selected = (mode_val is not None and self._mode_var.get() == mode_val)
        if entering and not is_selected:
            self.cv.itemconfig(tile_id, fill="#0A1F18", outline=TEXT_SUB)
            self.cv.itemconfig(ring_id, outline=TEXT_MAIN)
        elif not entering and not is_selected:
            self.cv.itemconfig(tile_id, fill="#061410", outline="#0D2A22")
            self.cv.itemconfig(ring_id, outline=TEXT_SUB)

    def _on_mode_change(self):
        """Show/hide AI-specific widgets based on selected input mode."""
        is_ai = self._mode_var.get() == "ai"
        for w, place_kw in self._ai_widgets:
            if is_ai:
                w.place(**place_kw)
                w.lift()
            else:
                w.place_forget()
        for cid in self._ai_canvas_ids:
            state = tk.NORMAL if is_ai else tk.HIDDEN
            self.cv.itemconfig(cid, state=state)

    # ══════════════════════════════════════════════════════════════════════
    #  START KEYBOARD SESSION
    # ══════════════════════════════════════════════════════════════════════
    def _start_keyboard(self):
        self.input_mode = self._mode_var.get()

        if self.input_mode == "ai" and not self.model_mgr.available_models():
            from tkinter import messagebox
            messagebox.showerror("No Models",
                                 "No models loaded.\n"
                                 "Place model files in ../Notebook/")
            return

        # Destroy menu widgets
        for widget in self.root.winfo_children():
            if not isinstance(widget, tk.Canvas):
                widget.destroy()

        # Read settings
        self.scan_speed_ms = self._speed_var.get()
        self.confidence_threshold = self._thresh_var.get()
        self.selected_model = (self._model_var.get()
                               if self.input_mode == "ai" else "Spacebar")

        # Connect serial + Pico W (AI mode only)
        if self.input_mode == "ai":
            port = self._port_var.get().strip()
            self.show_waveform = self._wave_var.get()
            
            # Pass wave_buf to SerialReader only if we want to display it
            wbuf = self.wave_buf if self.show_waveform else None
            self.serial_reader = SerialReader(port, self.predict_buf, wbuf)
            
            self.serial_reader.connect()

            if self._pico_var.get():
                self.pico_server.start()
                self.pico_active = True
        else:
            self.serial_reader = None

        # Reset state
        self.is_running = True
        self.typed_text = ""
        self.scan_phase = self.PHASE_ROW
        self.current_row = 0
        self.current_key = 0
        self.row_cycle_count = 0
        self.key_cycle_count = 0

        # Build the keyboard UI
        self.cv.delete("all")
        self._draw_grid()
        mode_label = self.selected_model.upper()
        self._draw_header(f"◈  BCI KEYBOARD  —  {mode_label}  ◈")
        self._draw_footer()
        self._build_keyboard_ui()

        # Start data reader thread (AI mode only)
        if self.serial_reader:
            self.serial_reader.start()

        # Start scan loop
        self.root.after(800, self._scan_step)

        # Start animation loop
        self._animate()

    # ══════════════════════════════════════════════════════════════════════
    #  BUILD KEYBOARD UI
    # ══════════════════════════════════════════════════════════════════════
    def _build_keyboard_ui(self):
        cx = self.W // 2

        # ── Text output area ──────────────────────────────────────────────
        text_y = 80
        text_h = 100
        text_w = int(self.W * 0.85)
        tx0 = cx - text_w // 2
        self.cv.create_rectangle(tx0, text_y, tx0 + text_w, text_y + text_h,
                                 fill=BG_DARKER, outline=KEY_BORDER, width=2,
                                 tags="text_bg")
        self.cv.create_text(tx0 + 12, text_y + 8, text="OUTPUT:",
                            fill=TEXT_SUB, font=("Courier New", 9),
                            anchor="nw", tags="text_label")
        self.text_display = self.cv.create_text(
            tx0 + 16, text_y + 32,
            text="▌", fill=TEXT_MAIN,
            font=("Courier New", 22), anchor="nw",
            width=text_w - 32, tags="text_out")

        # ── Keyboard keys ─────────────────────────────────────────────────
        # Adjust keyboard placement to leave room for the wave display if checked
        bottom_clearance = 250 if getattr(self, "show_waveform", False) else 160
        key_area_top = text_y + text_h + 30
        key_area_height = self.H - key_area_top - bottom_clearance
        row_count = len(KEYBOARD_ROWS)
        key_h = min(64, int(key_area_height / row_count) - 10)
        key_gap = 8

        self.key_rects = []
        self.key_canvas_ids = []

        for ri, row_keys in enumerate(KEYBOARD_ROWS):
            row_rects = []
            row_ids = []

            total_keys = len(row_keys)
            is_special_row = (ri == len(KEYBOARD_ROWS) - 1)

            if is_special_row:
                normal_w = min(72, int((self.W * 0.75) / 10) - key_gap)
                space_w = normal_w * 3 + key_gap * 2
                total_w = space_w + (total_keys - 1) * (normal_w + key_gap) + key_gap
            else:
                normal_w = min(72, int((self.W * 0.75) / total_keys) - key_gap)
                total_w = total_keys * (normal_w + key_gap)

            rx0 = cx - total_w // 2
            ry = key_area_top + ri * (key_h + key_gap + 4)

            cur_x = rx0
            for ki, key_label in enumerate(row_keys):
                if is_special_row and key_label == "SPACE":
                    kw = space_w
                else:
                    kw = normal_w

                rect_id = self.cv.create_rectangle(
                    cur_x, ry, cur_x + kw, ry + key_h,
                    fill=KEY_BG, outline=KEY_BORDER, width=2,
                    tags=f"key_{ri}_{ki}")

                display_label = " " if key_label == "SPACE" else key_label
                text_id = self.cv.create_text(
                    cur_x + kw // 2, ry + key_h // 2,
                    text=display_label, fill=KEY_TEXT,
                    font=("Courier New", 16 if not is_special_row else 13, "bold"),
                    tags=f"keytext_{ri}_{ki}")

                row_rects.append((cur_x, ry, kw, key_h, key_label))
                row_ids.append({"rect": rect_id, "text": text_id})

                cur_x += kw + key_gap

            self.key_rects.append(row_rects)
            self.key_canvas_ids.append(row_ids)

        # ── Status / info bar ─────────────────────────────────────────
        status_y = self.H - (280 if getattr(self, "show_waveform", False) else 190)
        self.cv.create_line(40, status_y, self.W - 40, status_y,
                            fill=KEY_BORDER, width=1)

        # Phase indicator
        self.phase_text = self.cv.create_text(
            60, status_y + 20, text="PHASE: ROW SCAN",
            fill=ACCENT, font=("Courier New", 11, "bold"), anchor="w")

        # AI-only: prediction display + confidence bar
        if self.input_mode == "ai":
            self.pred_text = self.cv.create_text(
                60, status_y + 42, text="PREDICTION: ---  |  CONF: ---",
                fill=TEXT_SUB, font=("Courier New", 10), anchor="w")

            bar_x = self.W // 2 + 60
            bar_w = 200
            self.cv.create_rectangle(bar_x, status_y + 16, bar_x + bar_w,
                                     status_y + 30, fill=DIM,
                                     outline=KEY_BORDER)
            self.conf_bar = self.cv.create_rectangle(
                bar_x, status_y + 16, bar_x, status_y + 30,
                fill=ACCENT, outline="")
            self._conf_bar_x = bar_x
            self._conf_bar_w = bar_w
            self._conf_bar_y1 = status_y + 16
            self._conf_bar_y2 = status_y + 30

            self.cv.create_text(bar_x - 8, status_y + 23, text="CONF:",
                                fill=TEXT_SUB, font=("Courier New", 9),
                                anchor="e")
            self.conf_pct_text = self.cv.create_text(
                bar_x + bar_w + 10, status_y + 23, text="",
                fill=TEXT_SUB, font=("Courier New", 9, "bold"), anchor="w")
        else:
            self.pred_text = None
            self.conf_bar = None
            self.conf_pct_text = None
            self.cv.create_text(
                60, status_y + 42,
                text="MODE: SPACEBAR  |  Press ENTER to select",
                fill=TEXT_SUB, font=("Courier New", 10), anchor="w")

        # Model & mode info
        mode_str = ("LIVE" if (self.serial_reader and not self.serial_reader.is_simulation)
                    else "SIMULATION") if self.input_mode == "ai" else "SPACEBAR"
        self.cv.create_text(
            self.W - 60, status_y + 20,
            text=f"MODEL: {self.selected_model}",
            fill=TEXT_SUB, font=("Courier New", 10), anchor="e")
        self.mode_text = self.cv.create_text(
            self.W - 60, status_y + 42,
            text=f"MODE: {mode_str}  |  SPEED: {self.scan_speed_ms}ms"
                 + (f"  |  THRESH: {self.confidence_threshold:.0%}"
                    if self.input_mode == "ai" else ""),
            fill=TEXT_SUB, font=("Courier New", 9), anchor="e")

        # ── Live control sliders ──────────────────────────────────────
        ctrl_y = status_y + 60
        self.cv.create_line(40, ctrl_y, self.W - 40, ctrl_y,
                            fill=KEY_BORDER, width=1)

        ctrl_label_x = 60
        slider_x = 240
        slider_len = 220

        # Scan speed slider (always shown)
        self.cv.create_text(ctrl_label_x, ctrl_y + 20,
                            text="SCAN SPEED (ms):",
                            fill=TEXT_SUB, font=("Courier New", 10),
                            anchor="w")
        tk.Scale(self.root, variable=self._speed_var,
                 from_=400, to=3000, orient=tk.HORIZONTAL,
                 bg=DIM, fg=ACCENT, troughcolor=RING_BASE,
                 highlightthickness=0, bd=0, length=slider_len,
                 font=("Courier New", 8)
                 ).place(x=slider_x, y=ctrl_y + 6)

        # Confidence threshold slider (AI mode only)
        if self.input_mode == "ai":
            thresh_label_x = self.W // 2 + 20
            thresh_slider_x = self.W // 2 + 220
            self.cv.create_text(thresh_label_x, ctrl_y + 20,
                                text="CONF. THRESHOLD:",
                                fill=TEXT_SUB, font=("Courier New", 10),
                                anchor="w")
            tk.Scale(self.root, variable=self._thresh_var,
                     from_=0.30, to=0.95, resolution=0.05,
                     orient=tk.HORIZONTAL,
                     bg=DIM, fg=ACCENT, troughcolor=RING_BASE,
                     highlightthickness=0, bd=0, length=slider_len,
                     font=("Courier New", 8)
                     ).place(x=thresh_slider_x, y=ctrl_y + 6)

        # Live dot — top-right of header so it doesn't overlap the title
        self.live_dot = self.cv.create_text(
            self.W - 16, 27, text="● SCANNING",
            fill=ACCENT, font=("Courier New", 10, "bold"), anchor="e")

        # Pico W status
        if self.pico_active:
            self.cv.create_text(
                self.W - 60, ctrl_y + 20,
                text=f"PICO W: ● ON  (port {SOCKET_PORT})",
                fill=ACCENT, font=("Courier New", 9), anchor="e")

        # Hint
        hint = ("ENTER = simulate click   |   SPACE = pause   |   BACKSPACE = delete & reset scan   |   ESC = quit"
                if self.input_mode == "ai"
                else "ENTER = select   |   SPACE = pause   |   BACKSPACE = delete & reset scan   |   ESC = quit")
        self.cv.create_text(
            cx, self.H - 28,
            text=hint,
            fill=TEXT_SUB, font=("Courier New", 9))

        # ── PAUSED overlay (hidden until Space is pressed) ─────────────
        self._paused_overlay = self.cv.create_rectangle(
            0, 0, self.W, self.H,
            fill="#000000", outline="", stipple="gray50", state="hidden")
        self._paused_text = self.cv.create_text(
            cx, self.H // 2,
            text="⏸  PAUSED\n\nPress SPACE to resume",
            fill="#00F5C4", font=("Courier New", 36, "bold"),
            justify=tk.CENTER, state="hidden")

        # ── Waveform (AI + selected only) ─────────────────────────
        if self.input_mode == "ai" and getattr(self, "show_waveform", False):
            wy, ww = self.H - 110, int(self.W * 0.88)
            self._wave_wy = wy
            self._wave_ww = ww
            self._wave_H = 45
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

    # ══════════════════════════════════════════════════════════════════════
    #  SCANNING LOGIC
    # ══════════════════════════════════════════════════════════════════════
    def _scan_step(self):
        if not self.is_running or self.is_paused:
            return

        # Dynamically read current slider values
        try:
            self.scan_speed_ms = self._speed_var.get()
        except Exception:
            pass
        try:
            self.confidence_threshold = self._thresh_var.get()
        except Exception:
            pass

        click_detected = self._check_for_click()

        if self.scan_phase == self.PHASE_ROW:
            self._handle_row_scan(click_detected)
        else:
            self._handle_key_scan(click_detected)

        self._update_key_visuals()

        self.root.after(self.scan_speed_ms, self._scan_step)

    def _check_for_click(self) -> bool:
        # Check cooldown
        if self.in_cooldown:
            if time.time() >= self.cooldown_end_time:
                self.in_cooldown = False
            else:
                self.last_pred_label = "COOLDOWN"
                self.last_pred_conf = 0.0
                return False
        if self.sim_click:
            self.sim_click = False
            self.last_pred_label = "CLICK (SPACE)"
            self.last_pred_conf = 1.0
            return True

        if self.input_mode == "spacebar":
            self.last_pred_label = "WAITING"
            self.last_pred_conf = 0.0
            return False

        # AI mode: check model prediction
        window = np.array(list(self.predict_buf), dtype=np.float32)
        if len(window) < 32:
            self.last_pred_label = "WAITING"
            self.last_pred_conf = 0.0
            return False

        try:
            label_idx, conf = self.model_mgr.predict(
                self.selected_model, window)
            self.last_pred_label = LABEL_NAMES[label_idx]
            self.last_pred_conf = conf

            # Broadcast to Pico W
            if self.pico_active:
                self.pico_server.broadcast(LABEL_NAMES[label_idx])

            if label_idx == 1 and conf >= self.confidence_threshold:
                # Click detected, enter cooldown
                self.in_cooldown = True
                self.cooldown_end_time = time.time() + (self.COOLDOWN_DUR_MS / 1000.0)
                return True
        except Exception as e:
            print(f"[Scan] Prediction error: {e}")
            self.last_pred_label = "ERROR"
            self.last_pred_conf = 0.0

        return False

    def _handle_row_scan(self, click_detected: bool):
        if click_detected:
            self.scan_phase = self.PHASE_KEY
            self.current_key = 0
            self.key_cycle_count = 0
            self._flash_row_selection()
        else:
            self.current_row = (self.current_row + 1) % len(KEYBOARD_ROWS)
            if self.current_row == 0:
                self.row_cycle_count += 1
                if self.row_cycle_count >= self.MAX_CYCLES:
                    self.current_row = 0
                    self.row_cycle_count = 0

    def _handle_key_scan(self, click_detected: bool):
        row_keys = KEYBOARD_ROWS[self.current_row]

        if click_detected:
            selected_row = self.current_row
            selected_key = self.current_key
            selected_label = row_keys[selected_key]
            self.scan_phase = self.PHASE_ROW
            self.current_row = 0
            self.current_key = 0
            self.row_cycle_count = 0
            self.key_cycle_count = 0
            self._select_key(selected_label, selected_row, selected_key)
        else:
            self.current_key = (self.current_key + 1) % len(row_keys)
            if self.current_key == 0:
                self.key_cycle_count += 1
                if self.key_cycle_count >= self.MAX_CYCLES:
                    self.scan_phase = self.PHASE_ROW
                    self.current_row = 0
                    self.current_key = 0
                    self.key_cycle_count = 0

    def _select_key(self, key_label: str,
                     flash_row: int = None, flash_key: int = None):
        """Process the selected key."""
        if key_label == "SPACE":
            self.typed_text += " "
        elif key_label == "⌫":
            self.typed_text = self.typed_text[:-1]
        elif key_label == "CLEAR":
            self.typed_text = ""
        elif key_label == "⏎":
            self.typed_text += "\n"
        else:
            self.typed_text += key_label

        if flash_row is not None and flash_key is not None:
            self._flash_key_selection(flash_row, flash_key)

        self._update_text_display()

    def _flash_key_selection(self, ri: int, ki: int):
        """Briefly flash the selected key green."""
        if not self.is_running: return
        ids = self.key_canvas_ids[ri][ki]
        self.cv.itemconfig(ids["rect"], fill=KEY_SEL_BG, outline=ACCENT)
        self.cv.itemconfig(ids["text"], fill=KEY_SEL_TEXT)
        self.root.after(300, lambda: self._reset_key_style(ri, ki))

    def _flash_row_selection(self):
        """Briefly flash the selected row."""
        if not self.is_running: return
        for ki, ids in enumerate(self.key_canvas_ids[self.current_row]):
            self.cv.itemconfig(ids["rect"], fill="#004D3D", outline=ACCENT)
        self.root.after(250, self._update_key_visuals)

    def _reset_key_style(self, ri, ki):
        """Reset a key to its normal style."""
        if not self.is_running: return
        ids = self.key_canvas_ids[ri][ki]
        self.cv.itemconfig(ids["rect"], fill=KEY_BG, outline=KEY_BORDER)
        self.cv.itemconfig(ids["text"], fill=KEY_TEXT)

    # ══════════════════════════════════════════════════════════════════════
    #  VISUAL UPDATES
    # ══════════════════════════════════════════════════════════════════════
    def _update_key_visuals(self):
        """Update key highlights based on current scan state."""
        if not self.is_running:
            return
            
        for ri, row_ids in enumerate(self.key_canvas_ids):
            for ki, ids in enumerate(row_ids):
                if self.scan_phase == self.PHASE_ROW:
                    if ri == self.current_row:
                        self.cv.itemconfig(ids["rect"],
                                           fill=KEY_HL_BG,
                                           outline=KEY_HL_BORDER, width=2)
                        self.cv.itemconfig(ids["text"], fill=KEY_HL_TEXT)
                    else:
                        self.cv.itemconfig(ids["rect"],
                                           fill=KEY_BG,
                                           outline=KEY_BORDER, width=2)
                        self.cv.itemconfig(ids["text"], fill=KEY_TEXT)
                else:  # PHASE_KEY
                    if ri == self.current_row and ki == self.current_key:
                        self.cv.itemconfig(ids["rect"],
                                           fill=ACCENT_DIM,
                                           outline=ACCENT, width=3)
                        self.cv.itemconfig(ids["text"], fill="#FFFFFF")
                    elif ri == self.current_row:
                        self.cv.itemconfig(ids["rect"],
                                           fill=KEY_HL_BG,
                                           outline=KEY_BORDER, width=2)
                        self.cv.itemconfig(ids["text"], fill=KEY_TEXT)
                    else:
                        self.cv.itemconfig(ids["rect"],
                                           fill=KEY_BG,
                                           outline=KEY_BORDER, width=2)
                        self.cv.itemconfig(ids["text"], fill=KEY_TEXT)

        # Update phase text
        if self.scan_phase == self.PHASE_ROW:
            phase_str = f"PHASE: ROW SCAN  ▸  Row {self.current_row + 1}/{len(KEYBOARD_ROWS)}"
        else:
            row_keys = KEYBOARD_ROWS[self.current_row]
            key_label = row_keys[self.current_key]
            phase_str = (f"PHASE: KEY SCAN  ▸  "
                         f"Row {self.current_row + 1} · "
                         f"Key [{key_label}]  "
                         f"({self.current_key + 1}/{len(row_keys)})")
        self.cv.itemconfig(self.phase_text, text=phase_str)

        # Update prediction display (AI mode only)
        if self.pred_text is not None:
            pred_str = (f"PREDICTION: {self.last_pred_label}  |  "
                        f"CONF: {self.last_pred_conf:.1%}")
            self.cv.itemconfig(self.pred_text, text=pred_str)

        # Update confidence bar (AI mode only)
        if self.conf_bar is not None:
            filled = int(self._conf_bar_w * self.last_pred_conf)
            bar_color = (CONF_HIGH if self.last_pred_conf
                         >= self.confidence_threshold else CONF_LOW)
            self.cv.coords(self.conf_bar,
                           self._conf_bar_x, self._conf_bar_y1,
                           self._conf_bar_x + filled, self._conf_bar_y2)
            self.cv.itemconfig(self.conf_bar, fill=bar_color)
            self.cv.itemconfig(self.conf_pct_text,
                               text=f"{self.last_pred_conf:.0%}",
                               fill=bar_color)

        mode_str = ("LIVE" if (self.serial_reader and not self.serial_reader.is_simulation)
                     else "SIMULATION") if self.input_mode == "ai" else "SPACEBAR"
        status_str = f"MODE: {mode_str}  |  SPEED: {self.scan_speed_ms}ms"
        if self.input_mode == "ai":
            status_str += f"  |  THRESH: {self.confidence_threshold:.0%}"
        self.cv.itemconfig(self.mode_text, text=status_str)

    def _update_text_display(self):
        display = self.typed_text + "▌"
        self.cv.itemconfig(self.text_display, text=display)

    # ══════════════════════════════════════════════════════════════════════
    #  ANIMATION LOOP (~30 fps)
    # ══════════════════════════════════════════════════════════════════════
    def _animate(self):
        if not self.is_running:
            return

        if self.is_paused:
            # Keep the dot showing PAUSED in amber
            self.cv.itemconfig(self.live_dot, text="⏸  PAUSED",
                               fill="#F59E0B")
        else:
            blink = "● SCANNING" if int(time.time() * 2) % 2 == 0 else "○ SCANNING"
            self.cv.itemconfig(self.live_dot, text=blink, fill=ACCENT)

        self._pulse_current_key()

        if getattr(self, "show_waveform", False) and self.input_mode == "ai":
            self._draw_waveform()

        self.root.after(33, self._animate)

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

    def _pulse_current_key(self):
        """Add a subtle pulse effect to the current scan target."""
        t = time.time()
        pulse = 0.5 + 0.5 * math.sin(t * 4.0)

        if self.scan_phase == self.PHASE_KEY:
            ri, ki = self.current_row, self.current_key
            if ri < len(self.key_canvas_ids) and ki < len(self.key_canvas_ids[ri]):
                ids = self.key_canvas_ids[ri][ki]
                w = 2 + int(pulse * 2)
                self.cv.itemconfig(ids["rect"], width=w)

    # ══════════════════════════════════════════════════════════════════════
    #  INPUT HANDLERS
    # ══════════════════════════════════════════════════════════════════════
    def _on_space(self, event):
        """Pause or resume scanning (Space bar)."""
        if not self.is_running or not hasattr(self, '_paused_overlay'):
            return
        if not self.is_paused:
            self.is_paused = True
            self.cv.itemconfig(self._paused_overlay, state="normal")
            self.cv.itemconfig(self._paused_text, state="normal")
            self.cv.tag_raise(self._paused_text)
            print("[Keyboard] PAUSED")
        else:
            self.is_paused = False
            self.cv.itemconfig(self._paused_overlay, state="hidden")
            self.cv.itemconfig(self._paused_text, state="hidden")
            print("[Keyboard] RESUMED")
            # Re-kick the scan loop
            self.root.after(self.scan_speed_ms, self._scan_step)

    def _on_enter(self, event):
        """Simulate a click when Enter is pressed."""
        if self.is_running and not self.is_paused:
            self.sim_click = True

    def _on_backspace(self, event):
        """Delete last typed character and reset scan to the first row."""
        if self.is_running:
            # Remove last character from typed text
            self.typed_text = self.typed_text[:-1]
            self._update_text_display()
            # Reset scan back to row-scan phase, row 0
            self.scan_phase = self.PHASE_ROW
            self.current_row = 0
            self.current_key = 0
            self.row_cycle_count = 0
            self.key_cycle_count = 0
            self._update_key_visuals()

    # ══════════════════════════════════════════════════════════════════════
    #  DRAWING HELPERS
    # ══════════════════════════════════════════════════════════════════════
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
        
        if self.on_back:
            tk.Button(self.root,
                      text="◁  MAIN  MENU",
                      font=("Courier New", 11, "bold"),
                      bg="#020C09", fg=TEXT_SUB,
                      activebackground=RING_BASE, activeforeground=ACCENT,
                      relief=tk.FLAT, bd=0, padx=10, pady=4,
                      cursor="hand2",
                      command=self._go_back
                      ).place(x=20, y=13, width=160, height=28)

    def _draw_footer(self):
        self.cv.create_rectangle(0, self.H - 40, self.W, self.H,
                                 fill="#020C09", outline="")
        self.cv.create_line(0, self.H - 40, self.W, self.H - 40,
                            fill=TEXT_SUB, width=1)

    # ══════════════════════════════════════════════════════════════════════
    #  NAVIGATION
    # ══════════════════════════════════════════════════════════════════════
    def _go_back(self):
        self._quit(destroy_root=False)
        if self.on_back:
            self.on_back()

    def _quit(self, destroy_root=True):
        self.is_running = False
        self.pico_server.stop()
        if self.serial_reader:
            self.serial_reader.stop()
        if destroy_root:
            self.root.destroy()
