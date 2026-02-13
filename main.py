import serial
import time
import csv
import threading
import random
import pyttsx3
import queue
from tkinter import *

# ── CONFIG ───────────────────────────────────────────────────
PORT = "/dev/cu.usbmodem1101"   # macOS — change to "COMx" on Windows
BAUD_RATE = 115200
FILE_NAME = "eeg_precision_bci.csv"
# ─────────────────────────────────────────────────────────────


class BCIApp(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.configure(bg="#050505")
        self.current_label = "REST"
        self.is_running = False

        # ── Speech engine (dedicated thread, minimal latency) ──
        self.speech_queue = queue.Queue()
        threading.Thread(target=self._speech_worker, daemon=True).start()

        # ── Serial connection ──────────────────────────────────
        try:
            self.ser = serial.Serial(PORT, BAUD_RATE, timeout=0.01)
            time.sleep(2)           # wait for Arduino to reset
            self.ser.reset_input_buffer()
        except Exception as e:
            print(f"[Serial] Could not open {PORT}: {e}")
            self.ser = None

        self.mode = StringVar(value="Arrows + Mouse")
        self.init_ui()

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
        """Drop stale items and queue the latest command immediately."""
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break
        self.speech_queue.put(text)

    # ── UI ────────────────────────────────────────────────────
    def init_ui(self):
        self.menu = Frame(self.master, bg="#050505")
        self.menu.place(relx=0.5, rely=0.5, anchor="center")

        Label(
            self.menu,
            text="BCI PRECISION RECORDER",
            fg="#00FFCC", bg="#050505",
            font=("Courier", 22, "bold"),
        ).pack(pady=15)

        OptionMenu(
            self.menu, self.mode,
            "Arrows", "Mouse", "Arrows + Mouse",
        ).pack(pady=10)

        Button(
            self.menu,
            text="BEGIN SESSION",
            font=("Helvetica", 12, "bold"),
            command=self.start_bci,
            bg="#00FFCC", fg="black",
        ).pack(pady=25)

    # ── Session start ─────────────────────────────────────────
    def start_bci(self):
        if self.ser:
            self.ser.write(b"START\n")

        self.is_running = True
        self.menu.destroy()

        self.icon_disp = Label(
            self.master, text="",
            font=("Helvetica", 220),
            fg="white", bg="#050505",
        )
        self.icon_disp.place(relx=0.5, rely=0.44, anchor="center")

        self.text_disp = Label(
            self.master, text="",
            fg="#00FFCC", bg="#050505",
            font=("Courier", 35),
        )
        self.text_disp.place(relx=0.5, rely=0.85, anchor="center")

        # ── Label definitions ──────────────────────────────────
        # Class IDs match the standard MI-BCI convention:
        #   0 = Rest, 1 = Up, 2 = Down, 3 = Left, 4 = Right,
        #   5 = Click, 6 = Stop
        self.label_map = {
            "REST": 0, "RELAX": 0,
            "UP":   1, "DOWN": 2,
            "LEFT": 3, "RIGHT": 4,
            "CLICK": 5, "STOP":  6,
        }

        # Pool uses Unicode arrows + colored circles (cross-platform safe)
        self.pool = []
        if "Arrows" in self.mode.get():
            self.pool += [
                ("↑", "UP"),
                ("↓", "DOWN"),
                ("←", "LEFT"),
                ("→", "RIGHT"),
            ]
        if "Mouse" in self.mode.get():
            self.pool += [
                ("●", "CLICK"),
                ("✕", "STOP"),
            ]

        # ── CSV header ─────────────────────────────────────────
        with open(FILE_NAME, mode='w', newline='') as f:
            csv.writer(f).writerow(
                ["Timestamp_Unix", "Signal_mV", "Intent_Label", "Label_Class"]
            )

        threading.Thread(target=self.data_logger, daemon=True).start()
        self.run_stimulus()

    # ── Data logger (background thread) ──────────────────────
    def data_logger(self):
        """Reads serial lines as fast as they arrive and timestamps them."""
        with open(FILE_NAME, mode='a', newline='') as f:
            writer = csv.writer(f)
            while self.is_running:
                if self.ser and self.ser.in_waiting:
                    try:
                        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            writer.writerow([
                                f"{time.time():.9f}",
                                line,
                                self.current_label,
                                self.label_map.get(self.current_label, 0),
                            ])
                    except Exception:
                        continue
                else:
                    # Yield CPU when nothing is waiting
                    time.sleep(0.0005)

    # ── Stimulus loop ─────────────────────────────────────────
    def run_stimulus(self):
        """Show a random directional/action cue for 3 seconds."""
        if not self.is_running:
            return
        icon, label = random.choice(self.pool)
        self.icon_disp.config(text=icon, fg="white")
        self.text_disp.config(text=label)
        self.current_label = label
        self.speak(label)
        self.after(3000, self.run_rest)

    def run_rest(self):
        """Show a rest cross for 2 seconds between stimuli."""
        if not self.is_running:
            return
        rest_word = random.choice(["REST", "RELAX"])
        self.icon_disp.config(text="+", fg="#333333")
        self.text_disp.config(text=rest_word)
        self.current_label = "REST"    # unified class 0 for both variants
        self.speak(rest_word)
        self.after(2000, self.run_stimulus)


# ── Entry point ───────────────────────────────────────────────
def main():
    root = Tk()
    root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda e: root.destroy())
    BCIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
