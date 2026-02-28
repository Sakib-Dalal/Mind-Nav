"""
Mind-Nav — Shared Configuration
════════════════════════════════
All constants, colour palette, keyboard layout, and path setup
shared by the BCI Tester and BCI Keyboard applications.
"""

import os

# ══════════════════════════════════════════════════════════════════════════════
#  HARDWARE / SIGNAL CONFIG
# ══════════════════════════════════════════════════════════════════════════════
PORT = "/dev/cu.usbmodem1101"       # Arduino serial port
BAUD_RATE = 115200
FS = 256                            # Hz — must match Arduino SAMPLE_RATE
WIN_LEN = 256                       # samples per prediction window (1 s)
N_FEATURES = 42

# Tester stimulus timings
STIM_DURATION = 3000                # ms — CLICK stimulus duration
REST_DURATION = 2000                # ms — REST period
WAVE_POINTS = 300                   # waveform display buffer size

# TCP Socket for Pico W
SOCKET_HOST = "0.0.0.0"
SOCKET_PORT = 9000

# ══════════════════════════════════════════════════════════════════════════════
#  PATHS
# ══════════════════════════════════════════════════════════════════════════════
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(SCRIPT_DIR, "..", "Notebook")

# ══════════════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE
# ══════════════════════════════════════════════════════════════════════════════
BG          = "#04080F"
BG_DARKER   = "#020608"
ACCENT      = "#00F5C4"
ACCENT_DIM  = "#00A882"
DIM         = "#0A1A14"
GRID_COLOR  = "#081810"
TEXT_MAIN   = "#E0FFF6"
TEXT_SUB    = "#3A7A65"
RING_BASE   = "#0D2A22"

# Keyboard-specific colours
KEY_BG        = "#0C1E18"
KEY_BORDER    = "#1A3A2E"
KEY_TEXT      = "#8ABFAD"
KEY_HL_BG     = "#003D30"
KEY_HL_BORDER = ACCENT
KEY_HL_TEXT   = "#FFFFFF"
KEY_SEL_BG    = ACCENT
KEY_SEL_TEXT  = BG
ROW_HL_BG     = "#061A14"

# Shared status colours
COL_CLICK   = "#4ADE80"
COL_REST    = "#3A7A65"
COL_CORRECT = "#00F5C4"
COL_WRONG   = "#FF4D6A"
CONF_HIGH   = "#00F5C4"
CONF_LOW    = "#FF4D6A"

# ══════════════════════════════════════════════════════════════════════════════
#  LABELS
# ══════════════════════════════════════════════════════════════════════════════
LABEL_NAMES = {0: "REST", 1: "CLICK"}

# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARD LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
KEYBOARD_ROWS = [
    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L", "'"],
    ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "?"],
    ["SPACE", "⌫", "CLEAR", "⏎"],
]
