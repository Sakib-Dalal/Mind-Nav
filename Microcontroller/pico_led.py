"""
Mind-Nav — Pico W LED Controller
══════════════════════════════════
MicroPython script for the Raspberry Pi Pico W.

Connects to the Mind-Nav BCI app's TCP server and toggles the
on-board LED based on brain-intent predictions:
  • LED ON  → CLICK detected (active mental intent)
  • LED OFF → REST  detected (relaxed state)

Setup:
  1. Flash MicroPython firmware onto your Pico W
  2. Edit WIFI_SSID and WIFI_PASS below
  3. Set SERVER_IP to your computer's local IP address
  4. Copy this file to the Pico W as main.py
"""

import network
import socket
import time
from machine import Pin

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION — edit these for your network
# ══════════════════════════════════════════════════════════════════════════════
WIFI_SSID  = "YOUR_WIFI_SSID"       # ← your WiFi network name
WIFI_PASS  = "YOUR_WIFI_PASSWORD"   # ← your WiFi password
SERVER_IP  = "192.168.1.100"        # ← IP of the computer running Mind-Nav
SERVER_PORT = 9000                  # must match SOCKET_PORT in config.py

# ══════════════════════════════════════════════════════════════════════════════
#  HARDWARE
# ══════════════════════════════════════════════════════════════════════════════
led = Pin("LED", Pin.OUT)           # on-board LED on Pico W


# ══════════════════════════════════════════════════════════════════════════════
#  WiFi CONNECTION
# ══════════════════════════════════════════════════════════════════════════════
def connect_wifi():
    """Connect to the configured WiFi network. Blocks until connected."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print(f"[WiFi] Already connected: {wlan.ifconfig()[0]}")
        return wlan

    print(f"[WiFi] Connecting to '{WIFI_SSID}'…")
    wlan.connect(WIFI_SSID, WIFI_PASS)

    # Wait up to 15 seconds
    for _ in range(30):
        if wlan.isconnected():
            break
        time.sleep(0.5)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"[WiFi] Connected — IP: {ip}")
    else:
        print("[WiFi] Connection FAILED — check SSID/password")

    return wlan


# ══════════════════════════════════════════════════════════════════════════════
#  TCP CLIENT
# ══════════════════════════════════════════════════════════════════════════════
def connect_server():
    """
    Open a TCP connection to the Mind-Nav BCI app.
    Returns the socket, or None on failure.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))
        print(f"[TCP] Connected to {SERVER_IP}:{SERVER_PORT}")
        return sock
    except Exception as e:
        print(f"[TCP] Connection failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # ── Connect to WiFi ───────────────────────────────────────────────────
    wlan = connect_wifi()
    if not wlan.isconnected():
        print("[Main] No WiFi — halting.")
        # Blink LED rapidly to indicate error
        for _ in range(20):
            led.toggle()
            time.sleep(0.15)
        led.off()
        return

    # ── Indicate WiFi success: 3 slow blinks ──────────────────────────────
    for _ in range(3):
        led.on()
        time.sleep(0.3)
        led.off()
        time.sleep(0.3)

    # ── Main reconnection loop ────────────────────────────────────────────
    while True:
        sock = connect_server()
        if sock is None:
            print("[Main] Retrying in 3 seconds…")
            # Blink LED to indicate searching
            for _ in range(6):
                led.toggle()
                time.sleep(0.25)
            led.off()
            time.sleep(1.5)
            continue

        # ── Read predictions ──────────────────────────────────────────────
        buf = b""
        try:
            while True:
                data = sock.recv(64)
                if not data:
                    print("[TCP] Server closed connection")
                    break

                buf += data

                # Process all complete lines
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    label = line.decode("utf-8").strip().upper()

                    if label == "CLICK":
                        led.on()
                    elif label == "REST":
                        led.off()

        except Exception as e:
            print(f"[TCP] Error: {e}")

        finally:
            try:
                sock.close()
            except Exception:
                pass

        # Connection lost — turn off LED and retry
        led.off()
        print("[Main] Reconnecting in 2 seconds…")
        time.sleep(2)


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
