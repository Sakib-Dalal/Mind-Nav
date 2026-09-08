"""
Mind-Nav — Unified Launcher
════════════════════════════
Single entry-point that presents a mode-selection menu:
  [BCI]  BCI Real-Time Tester
  [KB]   BCI Virtual Keyboard

Run with:  python main.py
Press ESC to exit at any time.
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", message="enable_nested_tensor is True")

import os
os.environ.setdefault("PYTORCH_MPS_DISABLE_VALIDATION", "1")

import tkinter as tk

from config import BG, ACCENT, DIM, GRID_COLOR, TEXT_SUB, RING_BASE


class MindNavLauncher:
    """Full-screen mode-selection menu for the Mind-Nav BCI suite."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.configure(bg=BG)
        self.root.title("Mind-Nav  ◈  BCI Suite")

        # Ensure window is realized before reading dimensions
        self.root.update_idletasks()
        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+0+0")

        self.root.bind("<Escape>", lambda _: self.root.destroy())

        # Defer drawing until the window is fully mapped on macOS
        self.root.after(100, self._draw_menu)

    def _draw_menu(self):
        # Destroy any leftover widgets or canvases from sub-apps
        for widget in self.root.winfo_children():
            widget.destroy()

        self.cv = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self.cv.pack(fill=tk.BOTH, expand=True)

        # Background grid
        for x in range(0, self.W, 60):
            self.cv.create_line(x, 0, x, self.H, fill=GRID_COLOR, width=1)
        for y in range(0, self.H, 60):
            self.cv.create_line(0, y, self.W, y, fill=GRID_COLOR, width=1)

        # Corner brackets
        sz = 32
        for (bx, by), (dx, dy) in [
            ((20, 20), (1, 1)),
            ((self.W - 20, 20), (-1, 1)),
            ((20, self.H - 20), (1, -1)),
            ((self.W - 20, self.H - 20), (-1, -1)),
        ]:
            self.cv.create_line(bx, by, bx + dx * sz, by, fill=ACCENT, width=2)
            self.cv.create_line(bx, by, bx, by + dy * sz, fill=ACCENT, width=2)

        # Header
        self.cv.create_rectangle(0, 0, self.W, 54, fill="#020C09", outline="")
        self.cv.create_line(0, 54, self.W, 54, fill=ACCENT, width=1)
        self.cv.create_text(self.W // 2, 27,
                            text="◈   MIND-NAV  ◈  BCI  SUITE   ◈",
                            fill=ACCENT, font=("Courier New", 16, "bold"))

        # Footer
        self.cv.create_rectangle(0, self.H - 40, self.W, self.H,
                                 fill="#020C09", outline="")
        self.cv.create_line(0, self.H - 40, self.W, self.H - 40,
                            fill=TEXT_SUB, width=1)
        self.cv.create_text(self.W // 2, self.H - 20,
                            text="Brain-Controlled Navigation via EEG   |   ESC = quit",
                            fill=TEXT_SUB, font=("Courier New", 9))

        cx, cy = self.W // 2, self.H // 2

        # Card
        cw, ch = 560, 380
        x0, y0 = cx - cw // 2, cy - ch // 2
        self.cv.create_rectangle(x0, y0, x0 + cw, y0 + ch,
                                 fill="#020D08", outline=ACCENT, width=1)
        self.cv.create_text(cx, y0 + 50, text="SELECT  MODE",
                            fill=ACCENT, font=("Courier New", 26, "bold"))
        self.cv.create_line(x0 + 40, y0 + 80, x0 + cw - 40, y0 + 80,
                            fill=RING_BASE, width=1)

        self.cv.create_text(cx, y0 + 110,
                            text="Choose how you want to use Mind-Nav:",
                            fill=TEXT_SUB, font=("Courier New", 11))

        # ── BCI Tester button ─────────────────────────────────────────────
        btn_w, btn_h = 420, 64
        btn1_y = y0 + 150
        tk.Button(self.root,
                  text="BCI  REAL-TIME  TESTER",
                  font=("Courier New", 14, "bold"),
                  bg=ACCENT, fg=BG,
                  activebackground="#00C8A0", activeforeground=BG,
                  relief=tk.FLAT, bd=0, padx=20, pady=12,
                  cursor="hand2",
                  command=self._launch_tester
                  ).place(x=cx - btn_w // 2, y=btn1_y,
                          width=btn_w, height=btn_h)

        self.cv.create_text(cx, btn1_y + btn_h + 14,
                            text="Test model accuracy with CLICK/REST stimulus cycles",
                            fill=TEXT_SUB, font=("Courier New", 9))

        # ── BCI Keyboard button ───────────────────────────────────────────
        btn2_y = btn1_y + btn_h + 40
        tk.Button(self.root,
                  text="BCI  VIRTUAL  KEYBOARD",
                  font=("Courier New", 14, "bold"),
                  bg=DIM, fg=ACCENT,
                  activebackground=RING_BASE, activeforeground=ACCENT,
                  relief=tk.FLAT, bd=0, padx=20, pady=12,
                  cursor="hand2",
                  command=self._launch_keyboard
                  ).place(x=cx - btn_w // 2, y=btn2_y,
                          width=btn_w, height=btn_h)

        self.cv.create_text(cx, btn2_y + btn_h + 14,
                            text="Type with your mind using row/column scanning",
                            fill=TEXT_SUB, font=("Courier New", 9))

    # ══════════════════════════════════════════════════════════════════════
    #  LAUNCHERS
    # ══════════════════════════════════════════════════════════════════════
    def _clear(self):
        """Remove all canvas items and floating widgets."""
        for widget in self.root.winfo_children():
            widget.destroy()

    def _launch_tester(self):
        self._clear()
        from tester import BCITesterApp
        BCITesterApp(self.root, on_back=self._draw_menu)

    def _launch_keyboard(self):
        self._clear()
        from keyboard import VirtualKeyboardApp
        VirtualKeyboardApp(self.root, on_back=self._draw_menu)


# ══════════════════════════════════════════════════════════════════════════════
def set_window_icon(root: tk.Tk):
    """Safely load and set the window icon, handling PyInstaller bundles."""
    try:
        # Determine base path (PyInstaller sets sys._MEIPASS)
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        icon_path = os.path.join(base_path, "Media", "Mind-Nav-Logo.png")
        if os.path.exists(icon_path):
            img = tk.PhotoImage(file=icon_path)
            root.iconphoto(True, img)
    except Exception as e:
        print(f"[Warning] Could not load window icon: {e}")

def main():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.resizable(False, False)
    set_window_icon(root)
    MindNavLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()
