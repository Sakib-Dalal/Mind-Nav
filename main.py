import serial
import time
import csv
import threading
import random
import pyttsx3
import queue
from tkinter import *

# CONFIG
PORT = "/dev/cu.usbmodem1101"
BAUD_RATE = 115200
FILE_NAME = "eeg_precision_bci.csv"


class BCIApp(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.configure(bg="#050505")
        self.current_label = "REST"
        self.is_running = False

        # Initialize Speech Queue
        self.speech_queue = queue.Queue()
        threading.Thread(target=self._speech_worker, daemon=True).start()

        try:
            self.ser = serial.Serial(PORT, BAUD_RATE, timeout=0.01)
            time.sleep(2)
        except:
            print("Serial Port Error: Check connection.")
            self.ser = None

        self.mode = StringVar(value="Arrows + Mouse")
        self.init_ui()

    def _speech_worker(self):
        """Processes speech immediately to minimize latency."""
        engine = pyttsx3.init()
        engine.setProperty('rate', 200)  # Fast rate for better temporal alignment
        while True:
            text = self.speech_queue.get()
            if text is None: break
            engine.say(text)
            engine.runAndWait()
            self.speech_queue.task_done()

    def speak(self, text):
        """Clears old audio and injects the new command."""
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except:
                break
        self.speech_queue.put(text)

    def init_ui(self):
        self.menu = Frame(self.master, bg="#050505")
        self.menu.place(relx=0.5, rely=0.5, anchor="center")
        Label(self.menu, text="BCI PRECISION RECORDER", fg="#00FFCC", bg="#050505", font=("Courier", 22, "bold")).pack(
            pady=15)

        m = OptionMenu(self.menu, self.mode, "Arrows", "Mouse", "Arrows + Mouse")
        m.config(bg="#111", fg="white", highlightthickness=0)
        m.pack(pady=10)

        Button(self.menu, text="BEGIN SESSION", font=("Helvetica", 12, "bold"), command=self.start_bci, bg="#00FFCC",
               fg="black").pack(pady=25)

    def start_bci(self):
        if self.ser: self.ser.write(b"START\n")
        self.is_running = True
        self.menu.destroy()

        self.icon_disp = Label(self.master, text="", font=("Helvetica", 240), fg="white", bg="#050505")
        self.icon_disp.place(relx=0.5, rely=0.45, anchor="center")

        self.text_disp = Label(self.master, text="", fg="#00FFCC", bg="#050505", font=("Courier", 35))
        self.text_disp.place(relx=0.5, rely=0.85, anchor="center")

        # Define Classes and Pool
        self.label_map = {"REST": 0, "UP": 1, "DOWN": 2, "LEFT": 3, "RIGHT": 4, "CLICK": 5, "STOP": 6, "RELAX": 0}
        self.pool = []
        if "Arrows" in self.mode.get():
            self.pool += [("⬆️", "UP"), ("⬇️", "DOWN"), ("⬅️", "LEFT"), ("➡️", "RIGHT")]
        if "Mouse" in self.mode.get():
            self.pool += [("🟢", "CLICK"), ("❌", "STOP")]

        with open(FILE_NAME, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp_Unix", "Signal_mV", "Intent_Label", "Label_Class"])

        threading.Thread(target=self.data_logger, daemon=True).start()
        self.run_stimulus()

    def data_logger(self):
        with open(FILE_NAME, mode='a', newline='') as f:
            writer = csv.writer(f)
            while self.is_running:
                if self.ser and self.ser.in_waiting:
                    try:
                        line = self.ser.readline().decode('utf-8').strip()
                        if line:
                            writer.writerow([f"{time.time():.9f}", line, self.current_label,
                                             self.label_map.get(self.current_label, 0)])
                    except:
                        continue

    def run_stimulus(self):
        if not self.is_running: return
        icon, label = random.choice(self.pool)
        self.icon_disp.config(text=icon, fg="white")
        self.text_disp.config(text=label)
        self.current_label = label

        # Audio for: UP, DOWN, LEFT, RIGHT, CLICK, STOP
        self.speak(label)

        self.after(3000, self.run_rest)

    def run_rest(self):
        if not self.is_running: return
        # Alternate between "REST" and "RELAX" text/audio for variety
        rest_type = random.choice(["REST", "RELAX"])

        self.icon_disp.config(text="+", fg="#222")
        self.text_disp.config(text=rest_type)
        self.current_label = "REST"  # Keep class ID consistent for CSV

        # Audio for: REST or RELAX
        self.speak(rest_type)

        self.after(2000, self.run_stimulus)


def main():
    root = Tk()
    root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda e: root.destroy())
    BCIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()