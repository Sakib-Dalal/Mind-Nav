import serial
import time
import csv
import threading
import random
from tkinter import *

# CONFIG
PORT = "/dev/cu.usbmodem1101"  # Double check this in Arduino IDE
BAUD_RATE = 115200
FILE_NAME = "eeg_precision_bci.csv"


class BCIApp(Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.master.configure(bg="#050505")
        self.current_label = "REST"
        self.is_running = False

        try:
            self.ser = serial.Serial(PORT, BAUD_RATE, timeout=0.01)
            time.sleep(2)  # Bootloader delay
        except:
            print("Serial Port Error: Check connection.")
            self.ser = None

        self.mode = StringVar(value="Arrows")
        self.init_ui()

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

        with open(FILE_NAME, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp_Unix", "Signal_mV_HighPrec", "Intent_Label", "Label_Class"])

        threading.Thread(target=self.data_logger, daemon=True).start()

        self.label_map = {"REST": 0, "UP": 1, "DOWN": 2, "LEFT": 3, "RIGHT": 4, "CLICK": 5, "STOP": 6}
        self.pool = []
        if "Arrows" in self.mode.get(): self.pool += [("⬆️", "UP"), ("⬇️", "DOWN"), ("⬅️", "LEFT"), ("➡️", "RIGHT")]
        if "Mouse" in self.mode.get(): self.pool += [("🟢️", "CLICK"), ("❌", "STOP")]

        self.run_stimulus()

    def data_logger(self):
        """Captures raw strings from serial to maintain 8-decimal integrity"""
        with open(FILE_NAME, mode='a', newline='') as f:
            writer = csv.writer(f)
            while self.is_running:
                if self.ser and self.ser.in_waiting:
                    try:
                        line = self.ser.readline().decode('utf-8').strip()
                        if line:
                            # Use high-precision time.time()
                            writer.writerow([f"{time.time():.9f}", line, self.current_label,
                                             self.label_map.get(self.current_label, 0)])
                    except:
                        continue

    def run_stimulus(self):
        if not self.is_running: return
        icon, label = random.choice(self.pool)
        self.icon_disp.config(text=icon)
        self.text_disp.config(text=label)
        self.current_label = label
        self.after(3500, self.run_rest)

    def run_rest(self):
        if not self.is_running: return
        self.icon_disp.config(text="+", fg="#222")  # Subtle fixation cross
        self.text_disp.config(text="RELAX")
        self.current_label = "REST"
        self.after(2000, self.run_stimulus)


def main():
    root = Tk()
    root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda e: root.destroy())
    BCIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()