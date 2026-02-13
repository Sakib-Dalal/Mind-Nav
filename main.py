"""
BCI Precision Recorder — Redesigned UI
Neural-lab aesthetic: dark canvas, animated rings, live EEG waveform,
countdown arc, session statistics panel.
"""

import serial
import time
import csv
import threading
import random
import pyttsx3
import queue
import math
import collections
from tkinter import *

# ── CONFIG ───────────────────────────────────────────────────
PORT      = "/dev/cu.usbmodem1101"
BAUD_RATE = 115200
FILE_NAME = "eeg_precision_bci.csv"

STIM_DURATION  = 3000   # ms
REST_DURATION  = 2000   # ms
WAVE_POINTS    = 300
WAVE_HEIGHT    = 90     # px half-height

# Color palette
BG         = "#04080F"
ACCENT     = "#00F5C4"
DIM        = "#0A1A14"
GRID_COLOR = "#081810"
TEXT_MAIN  = "#E0FFF6"
TEXT_SUB   = "#3A7A65"
RING_BASE  = "#0D2A22"

LABEL_MAP = {
    "REST": 0, "RELAX": 0,
    "UP":   1, "DOWN":  2,
    "LEFT": 3, "RIGHT": 4,
    "CLICK": 5, "STOP":  6,
}

DIRECTION_ICONS = {
    "UP": "↑", "DOWN": "↓", "LEFT": "←",
    "RIGHT": "→", "CLICK": "●", "STOP": "✕",
}

DIRECTION_COLORS = {
    "UP":    "#00F5C4",
    "DOWN":  "#00C8FF",
    "LEFT":  "#FF9500",
    "RIGHT": "#A78BFA",
    "CLICK": "#4ADE80",
    "STOP":  "#FF4060",
}


class BCIApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.configure(bg=BG)

        self.is_running      = False
        self.current_label   = "REST"
        self.trial_count     = 0
        self.session_start   = None
        self._stim_start_ms  = 0
        self._stim_duration  = STIM_DURATION

        self.wave_buf = collections.deque([0.0] * WAVE_POINTS, maxlen=WAVE_POINTS)

        self.speech_queue = queue.Queue()
        threading.Thread(target=self._speech_worker, daemon=True).start()

        try:
            self.ser = serial.Serial(PORT, BAUD_RATE, timeout=0.01)
            time.sleep(2)
            self.ser.reset_input_buffer()
        except Exception as e:
            print(f"[Serial] {e}")
            self.ser = None

        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        root.geometry(f"{self.W}x{self.H}+0+0")

        self.cv = Canvas(self.root, width=self.W, height=self.H,
                         bg=BG, highlightthickness=0)
        self.cv.pack(fill=BOTH, expand=True)

        self._draw_static_bg()
        self._build_menu()
        self.root.bind("<Escape>", lambda e: self._quit())
        self._animate()

    # ── Static background ──────────────────────────────────────
    def _draw_static_bg(self):
        for x in range(0, self.W, 60):
            self.cv.create_line(x, 0, x, self.H, fill=GRID_COLOR, width=1)
        for y in range(0, self.H, 60):
            self.cv.create_line(0, y, self.W, y, fill=GRID_COLOR, width=1)

        s = 32
        for (cx, cy), (dx, dy) in [
            ((20,20),(1,1)), ((self.W-20,20),(-1,1)),
            ((20,self.H-20),(1,-1)), ((self.W-20,self.H-20),(-1,-1))
        ]:
            self.cv.create_line(cx, cy, cx+dx*s, cy, fill=ACCENT, width=2)
            self.cv.create_line(cx, cy, cx, cy+dy*s, fill=ACCENT, width=2)

        self.cv.create_rectangle(0, 0, self.W, 54, fill="#020C09", outline="")
        self.cv.create_line(0, 54, self.W, 54, fill=ACCENT, width=1)
        self.cv.create_text(self.W//2, 27,
            text="◈   BCI  PRECISION  RECORDER   ◈",
            fill=ACCENT, font=("Courier New", 17, "bold"))

        self.cv.create_rectangle(0, self.H-40, self.W, self.H, fill="#020C09", outline="")
        self.cv.create_line(0, self.H-40, self.W, self.H-40, fill=TEXT_SUB, width=1)
        self.cv.create_text(self.W//2, self.H-20,
            text="PRESS  ESC  TO  EXIT",
            fill=TEXT_SUB, font=("Courier New", 11))

    # ── Menu ──────────────────────────────────────────────────
    def _build_menu(self):
        cx, cy = self.W//2, self.H//2
        cw, ch = 500, 360
        x0, y0 = cx-cw//2, cy-ch//2

        self.cv.create_rectangle(x0, y0, x0+cw, y0+ch,
            fill="#020D08", outline=ACCENT, width=1, tags="menu")
        self.cv.create_rectangle(x0+4, y0+4, x0+cw-4, y0+ch-4,
            fill="", outline=RING_BASE, width=1, tags="menu")

        self.cv.create_text(cx, y0+48, text="SESSION  SETUP",
            fill=ACCENT, font=("Courier New", 26, "bold"), tags="menu")
        self.cv.create_line(x0+40, y0+74, x0+cw-40, y0+74,
            fill=RING_BASE, width=1, tags="menu")

        self.cv.create_text(cx, y0+108, text="SELECT  PARADIGM",
            fill=TEXT_SUB, font=("Courier New", 11), tags="menu")

        self.mode_var = StringVar(value="Arrows + Mouse")
        modes = ["Arrows", "Mouse", "Arrows + Mouse"]
        self.mode_btns = {}
        total_w = len(modes)*134 + (len(modes)-1)*10
        bx = cx - total_w//2
        for m in modes:
            btn = Button(self.root, text=m,
                font=("Courier New", 12, "bold"),
                bg=DIM, fg=TEXT_SUB,
                activebackground=ACCENT, activeforeground=BG,
                relief=FLAT, bd=0, padx=10, pady=9, cursor="hand2",
                command=lambda v=m: self._select_mode(v))
            self.cv.create_window(bx+67, y0+148, window=btn, width=134, tags="menu")
            self.mode_btns[m] = btn
            bx += 144
        self._select_mode("Arrows + Mouse")

        self.begin_btn = Button(self.root,
            text="▶   BEGIN  SESSION",
            font=("Courier New", 15, "bold"),
            bg=ACCENT, fg=BG,
            activebackground="#00C8A0", activeforeground=BG,
            relief=FLAT, bd=0, padx=30, pady=14, cursor="hand2",
            command=self.start_bci)
        self.cv.create_window(cx, y0+250, window=self.begin_btn,
            width=290, tags="menu")

        self.cv.create_text(cx, y0+318,
            text=f"PORT: {PORT}   |   BAUD: {BAUD_RATE}   |   Fs: 256 Hz",
            fill=TEXT_SUB, font=("Courier New", 10), tags="menu")

    def _select_mode(self, val):
        self.mode_var.set(val)
        for m, btn in self.mode_btns.items():
            btn.config(bg=ACCENT if m == val else DIM,
                       fg=BG     if m == val else TEXT_SUB)

    # ── Start session ─────────────────────────────────────────
    def start_bci(self):
        if self.ser:
            self.ser.write(b"START\n")
        self.is_running    = True
        self.session_start = time.time()

        for w in self.root.winfo_children():
            if not isinstance(w, Canvas):
                w.destroy()

        self.cv.delete("all")
        self._draw_static_bg()
        self._build_session_ui()

        self.pool = []
        if "Arrows" in self.mode_var.get():
            self.pool += ["UP", "DOWN", "LEFT", "RIGHT"]
        if "Mouse" in self.mode_var.get():
            self.pool += ["CLICK", "STOP"]

        with open(FILE_NAME, 'w', newline='') as f:
            csv.writer(f).writerow(
                ["Timestamp_Unix", "Signal_mV", "Intent_Label", "Label_Class"])

        threading.Thread(target=self._data_logger, daemon=True).start()
        self.root.after(600, self._run_stimulus)

    # ── Session canvas ────────────────────────────────────────
    def _build_session_ui(self):
        cx, cy = self.W//2, self.H//2 - 40

        # Decorative rings
        for r in [168, 208, 248]:
            self.cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                outline=RING_BASE, width=1)

        # Breathing ring (animated)
        self.ring_pulse = self.cv.create_oval(
            cx-160, cy-160, cx+160, cy+160,
            outline=ACCENT, width=2)

        # Countdown arc
        self.arc_item = self.cv.create_arc(
            cx-186, cy-186, cx+186, cy+186,
            start=90, extent=0,
            outline=ACCENT, width=4, style=ARC)

        # Icon & label
        self.icon_item = self.cv.create_text(
            cx, cy-18, text="",
            fill=ACCENT, font=("Courier New", 190, "bold"), anchor=CENTER)

        self.label_item = self.cv.create_text(
            cx, cy+134, text="",
            fill=ACCENT, font=("Courier New", 30, "bold"), anchor=CENTER)

        # Recording indicator
        self.status_item = self.cv.create_text(
            self.W-24, 27, text="● RECORDING",
            fill=ACCENT, font=("Courier New", 11), anchor=E)

        # ── Waveform panel ─────────────────────────────────
        wy = self.H - 155
        self.wave_wy  = wy
        self.wave_w   = int(self.W * 0.72)
        self.wave_y0  = wy - WAVE_HEIGHT
        self.wave_y1  = wy + WAVE_HEIGHT

        self.cv.create_rectangle(
            self.W//2 - self.wave_w//2 - 2, self.wave_y0 - 10,
            self.W//2 + self.wave_w//2 + 2, self.wave_y1 + 10,
            fill="#020C09", outline=TEXT_SUB, width=1)
        self.cv.create_line(
            self.W//2 - self.wave_w//2, wy,
            self.W//2 + self.wave_w//2, wy,
            fill=RING_BASE, width=1, dash=(4, 8))
        self.cv.create_text(
            self.W//2 - self.wave_w//2 - 10, wy,
            text="EEG", fill=TEXT_SUB,
            font=("Courier New", 10), anchor=E)

        self.wave_line = self.cv.create_line(
            0, 0, 1, 1, fill=ACCENT, width=1, smooth=True)

        # ── Stats footer ───────────────────────────────────
        self.stat_trial = self.cv.create_text(
            24, self.H-20, text="TRIAL: 0",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)
        self.stat_time = self.cv.create_text(
            190, self.H-20, text="TIME: 00:00",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)
        self.stat_label = self.cv.create_text(
            390, self.H-20, text="CLASS: ---",
            fill=TEXT_SUB, font=("Courier New", 11), anchor=W)

    # ── Animation loop (≈30 fps) ──────────────────────────────
    def _animate(self):
        if self.is_running:
            self._draw_waveform()
            self._update_countdown()
            self._pulse_ring()
            self._update_stats()
        self.root.after(33, self._animate)

    def _pulse_ring(self):
        t = time.time()
        scale = 1.0 + 0.02 * math.sin(t * 2.5)
        cx, cy = self.W//2, self.H//2 - 40
        r = int(160 * scale)
        self.cv.coords(self.ring_pulse, cx-r, cy-r, cx+r, cy+r)
        v = int(180 + 75 * abs(math.sin(t * 2.5)))
        self.cv.itemconfig(self.ring_pulse,
            outline=f"#{0:02x}{v:02x}{(v//2+80):02x}")

    def _update_countdown(self):
        if not hasattr(self, 'arc_item'):
            return
        elapsed = (time.time() * 1000) - self._stim_start_ms
        frac    = min(elapsed / self._stim_duration, 1.0)
        self.cv.itemconfig(self.arc_item, extent=-360 * frac)

    def _draw_waveform(self):
        if not hasattr(self, 'wave_line'):
            return
        buf  = list(self.wave_buf)
        n    = len(buf)
        if n < 2:
            return
        cx   = self.W // 2
        ww   = self.wave_w
        wy   = self.wave_wy
        norm = max(max(abs(v) for v in buf), 1.0)
        pts  = []
        for i, v in enumerate(buf):
            x = cx - ww//2 + int(i / (n-1) * ww)
            y = wy - int((v / norm) * WAVE_HEIGHT * 0.85)
            pts += [x, y]
        self.cv.coords(self.wave_line, *pts)

    def _update_stats(self):
        if not hasattr(self, 'stat_trial'):
            return
        elapsed = int(time.time() - (self.session_start or time.time()))
        m, s = divmod(elapsed, 60)
        self.cv.itemconfig(self.stat_trial, text=f"TRIAL: {self.trial_count}")
        self.cv.itemconfig(self.stat_time,  text=f"TIME: {m:02d}:{s:02d}")
        self.cv.itemconfig(self.stat_label,
            text=f"CLASS: {LABEL_MAP.get(self.current_label,0)}  [{self.current_label}]")
        blink = "● RECORDING" if int(time.time()*2) % 2 == 0 else "○ RECORDING"
        self.cv.itemconfig(self.status_item, text=blink)

    # ── Stimulus / rest sequence ──────────────────────────────
    def _run_stimulus(self):
        if not self.is_running:
            return
        label = random.choice(self.pool)
        color = DIRECTION_COLORS.get(label, ACCENT)

        self.current_label  = label
        self._stim_start_ms = time.time() * 1000
        self._stim_duration = STIM_DURATION
        self.trial_count   += 1

        self.cv.itemconfig(self.icon_item,  text=DIRECTION_ICONS[label], fill=color)
        self.cv.itemconfig(self.label_item, text=label, fill=color)
        self.cv.itemconfig(self.arc_item,   outline=color)
        self.cv.itemconfig(self.ring_pulse, outline=color)
        self.speak(label)
        self.root.after(STIM_DURATION, self._run_rest)

    def _run_rest(self):
        if not self.is_running:
            return
        rest_word = random.choice(["REST", "RELAX"])
        self.current_label  = "REST"
        self._stim_start_ms = time.time() * 1000
        self._stim_duration = REST_DURATION

        self.cv.itemconfig(self.icon_item,  text="+",       fill=RING_BASE)
        self.cv.itemconfig(self.label_item, text=rest_word, fill=TEXT_SUB)
        self.cv.itemconfig(self.arc_item,   outline=TEXT_SUB)
        self.cv.itemconfig(self.ring_pulse, outline=TEXT_SUB)
        self.speak(rest_word)
        self.root.after(REST_DURATION, self._run_stimulus)

    # ── Data logger ───────────────────────────────────────────
    def _data_logger(self):
        with open(FILE_NAME, 'a', newline='') as f:
            writer = csv.writer(f)
            while self.is_running:
                if self.ser and self.ser.in_waiting:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            try:
                                self.wave_buf.append(float(line) - 500.0)
                            except ValueError:
                                pass
                            writer.writerow([
                                f"{time.time():.9f}", line,
                                self.current_label,
                                LABEL_MAP.get(self.current_label, 0),
                            ])
                    except Exception:
                        continue
                else:
                    time.sleep(0.0005)

    # ── Speech ────────────────────────────────────────────────
    def _speech_worker(self):
        engine = pyttsx3.init()
        engine.setProperty('rate', 200)
        while True:
            text = self.speech_queue.get()
            if text is None:
                break
            engine.say(text)
            engine.runAndWait()
            self.speech_queue.task_done()

    def speak(self, text):
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
        self.speech_queue.put(text)

    # ── Quit ──────────────────────────────────────────────────
    def _quit(self):
        self.is_running = False
        self.speech_queue.put(None)
        if self.ser:
            try:
                self.ser.write(b"STOP\n")
                self.ser.close()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = Tk()
    root.attributes("-fullscreen", True)
    root.resizable(False, False)
    BCIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()