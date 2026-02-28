"""
Mind-Nav — Serial Reader
════════════════════════
Handles Arduino serial connection and simulation-mode EEG generation.
Feeds data into prediction and waveform display buffers.
"""

import time
import math
import random
import threading

import serial

from config import BAUD_RATE, FS


class SerialReader:
    """
    Reads EEG data from an Arduino serial port.
    Falls back to simulation mode if the port is unavailable.
    """

    def __init__(self, port: str, predict_buf, wave_buf=None):
        """
        Parameters
        ----------
        port : str
            Serial port path (e.g. "/dev/cu.usbmodem1101").
        predict_buf : collections.deque
            Buffer for prediction samples.
        wave_buf : collections.deque | None
            Optional buffer for waveform display samples (tester mode).
        """
        self.port = port
        self.predict_buf = predict_buf
        self.wave_buf = wave_buf
        self.ser = None
        self.is_simulation = True
        self._running = False

    def connect(self) -> bool:
        """Try to open the serial port. Returns True on success."""
        try:
            self.ser = serial.Serial(self.port, BAUD_RATE, timeout=0.01)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.is_simulation = False
            print(f"[Serial] Connected on {self.port}")
            return True
        except Exception as e:
            print(f"[Serial] {e}  —  SIMULATION mode")
            self.ser = None
            self.is_simulation = True
            return False

    def start(self):
        """Start the data-reading thread."""
        self._running = True
        threading.Thread(target=self._reader_loop, daemon=True).start()

    def stop(self):
        """Stop reading and close the serial port."""
        self._running = False
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass

    def _reader_loop(self):
        """Main reading loop (runs in daemon thread)."""
        while self._running:
            if self.ser:
                if self.ser.in_waiting:
                    try:
                        line = (self.ser.readline()
                                .decode("utf-8", errors="ignore").strip())
                        if line:
                            val = float(line) - 500.0
                            self.predict_buf.append(val)
                            if self.wave_buf is not None:
                                self.wave_buf.append(val)
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
                self.predict_buf.append(val)
                if self.wave_buf is not None:
                    self.wave_buf.append(val)
                time.sleep(1.0 / FS)
