"""
Mind-Nav — BCI Real-Time Tester
════════════════════════════════
• Reads live EEG from Arduino via Serial (or simulates if no Arduino)
• Predicts CLICK / REST using any of six trained models
• Side-by-side ACTUAL vs PREDICTED display with confidence bar
• Optional TCP socket server → sends predictions to Raspberry Pi Pico W

Press ESC to exit at any time.
"""

import time
import math
import threading
import collections
import socket

import numpy as np
import tkinter as tk

from config import (
    BG, ACCENT, DIM, GRID_COLOR, TEXT_MAIN, TEXT_SUB, RING_BASE,
    COL_CLICK, COL_REST, COL_CORRECT, COL_WRONG,
    LABEL_NAMES, WIN_LEN, WAVE_POINTS,
    STIM_DURATION, REST_DURATION, SOCKET_PORT,
)
from models import ModelManager
from pico_server import PicoServer
from serial_reader import SerialReader


class BCITesterApp:

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
        self.root.title("Mind-Nav  ◈  BCI Real-Time Tester")

        self.root.update_idletasks()
        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+0+0")

        # Session state
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
        self.serial_reader = None
        self.selected_model = ""

        self.cv = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self.cv.pack(fill=tk.BOTH, expand=True)
        self.root.bind("<Escape>", lambda _e: self._quit())

        self.root.after(50, self._show_menu)

    # ══════════════════════════════════════════════════════════════════════
    #  MENU
    # ══════════════════════════════════════════════════════════════════════
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
        from config import PORT
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
            from tkinter import ttk
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

        # Pico W toggle
        self.cv.create_text(x0 + 40, row[2], text="PICO W SERVER:",
                            fill=TEXT_SUB, font=("Courier New", 11), anchor="w")
        self._pico_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.root,
                       variable=self._pico_var,
                       text=f"Enable  (TCP port {SOCKET_PORT})",
                       font=("Courier New", 11),
                       fg=TEXT_MAIN, bg=BG,
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

        # Button
        btn_y = y0 + 396
        tk.Button(self.root,
                  text="▶   BEGIN  TESTING",
                  font=("Courier New", 15, "bold"),
                  bg=ACCENT, fg=BG,
                  activebackground="#00C8A0", activeforeground=BG,
                  relief=tk.FLAT, bd=0, padx=30, pady=14,
                  cursor="hand2",
                  command=self._start_session
                  ).place(x=cx - 145, y=btn_y, width=290, height=54)

        self.cv.create_text(
            cx, y0 + 464,
            text=f"Models:  {', '.join(models) if models else 'NONE'}",
            fill=TEXT_SUB, font=("Courier New", 10))

    # ══════════════════════════════════════════════════════════════════════
    #  START SESSION
    # ══════════════════════════════════════════════════════════════════════
    def _start_session(self):
        if not self.model_mgr.available_models():
            from tkinter import messagebox
            messagebox.showerror("No Models",
                                 "No models loaded.\n"
                                 "Place .joblib / .pt files in ../Notebook/")
            return

        for widget in self.root.winfo_children():
            if not isinstance(widget, tk.Canvas):
                widget.destroy()

        port = self._port_var.get().strip()
        self.serial_reader = SerialReader(port, self.predict_buf, self.wave_buf)
        self.serial_reader.connect()

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

        self.serial_reader.start()
        self.root.after(500, self._run_stimulus)
        self._animate()

    # ══════════════════════════════════════════════════════════════════════
    #  SESSION UI
    # ══════════════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════════════
    #  STIMULUS SEQUENCE
    # ══════════════════════════════════════════════════════════════════════
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
        if not self.is_running:
            return
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

    # ══════════════════════════════════════════════════════════════════════
    #  UI HELPERS
    # ══════════════════════════════════════════════════════════════════════
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

    # ══════════════════════════════════════════════════════════════════════
    #  ANIMATION LOOP (~30 fps)
    # ══════════════════════════════════════════════════════════════════════
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
