"""
Mind-Nav — Pico W TCP Server
═════════════════════════════
Lightweight TCP socket server that broadcasts BCI predictions
(CLICK / REST) to connected Raspberry Pi Pico W clients.
"""

import socket
import threading

from config import SOCKET_HOST, SOCKET_PORT


class PicoServer:
    """
    TCP server that accepts connections from Pico W clients
    and broadcasts prediction labels to all connected clients.
    """

    def __init__(self, host: str = SOCKET_HOST, port: int = SOCKET_PORT):
        self._host = host
        self._port = port
        self._clients: list = []
        self._lock = threading.Lock()
        self._running = False
        self._srv_sock = None

    def start(self):
        """Start accepting client connections in a background thread."""
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        self._srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv_sock.bind((self._host, self._port))
        self._srv_sock.listen(5)
        self._srv_sock.settimeout(1.0)
        print(f"[PicoServer] Listening on {self._host}:{self._port}")
        while self._running:
            try:
                conn, addr = self._srv_sock.accept()
                print(f"[PicoServer] Pico W connected from {addr}")
                with self._lock:
                    self._clients.append(conn)
            except socket.timeout:
                continue
            except Exception:
                break

    def broadcast(self, label: str):
        """Send a label string to all connected clients."""
        msg = (label + "\n").encode()
        dead = []
        with self._lock:
            for conn in self._clients:
                try:
                    conn.sendall(msg)
                except Exception:
                    dead.append(conn)
            for d in dead:
                self._clients.remove(d)

    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def stop(self):
        """Shut down the server and close all connections."""
        self._running = False
        with self._lock:
            for conn in self._clients:
                try:
                    conn.close()
                except Exception:
                    pass
            self._clients.clear()
        if self._srv_sock:
            try:
                self._srv_sock.close()
            except Exception:
                pass
