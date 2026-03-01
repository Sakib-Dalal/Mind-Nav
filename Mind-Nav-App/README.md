# Mind-Nav App — Unified BCI Application

Python desktop application providing two modes of BCI interaction: a real-time model tester and a QWERTY scanning virtual keyboard. Both modes read live EEG data from an Arduino over USB serial and run inference using trained classification models.

---

## Requirements

```bash
pip install scikit-learn numpy scipy torch torchvision joblib pyserial
```

Python 3.9 or later is required. Model files must be present in `../Notebook/` before running.

---

## File Overview

| File | Purpose |
|------|---------|
| `main.py` | Unified launcher — entry point, mode selection menu |
| `tester.py` | BCI Real-Time Tester UI |
| `keyboard.py` | BCI Virtual Keyboard UI |
| `config.py` | Shared constants, serial port, colour palette |
| `features.py` | 42-feature EEG extraction pipeline |
| `models.py` | Model loading, inference, and ModelManager |
| `serial_reader.py` | Arduino serial reader with simulation fallback |
| `pico_server.py` | TCP socket server for Pico W LED clients |

---

## Running the Application

```bash
cd Mind-Nav-App
python main.py
```

The launcher opens in fullscreen and presents two options:

- **BCI REAL-TIME TESTER** — validate model accuracy against live stimuli
- **BCI VIRTUAL KEYBOARD** — type hands-free using mental CLICK detection

Press `Esc` at any time to exit.

---

## Configuration

Edit `config.py` to match your hardware and file paths:

```python
PORT        = "/dev/cu.usbmodem1101"   # Arduino serial port
BAUD_RATE   = 115200
SOCKET_PORT = 5005                     # TCP port for Pico W server
```

Change `PORT` to match your system:
- macOS: `/dev/cu.usbmodem*`
- Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`
- Windows: `COM3`, `COM4`, etc.

Model files are loaded automatically from `../Notebook/`. If no models are found, the AI mode will be unavailable.

---

## BCI Real-Time Tester

Tests how well your trained models classify your EEG in real time, without making irreversible inputs.

### Setup Screen

| Field | Description |
|-------|-------------|
| Arduino Port | Serial port of your connected Arduino |
| Model | Dropdown of all detected model files |
| Pico W Server | Enable TCP broadcast to a connected Pico W LED controller |

Click `>> BEGIN TESTING` to start the session.

### Session Screen

- The **left panel** shows the actual stimulus being presented (REST or CLICK).
- The **right panel** shows the model's prediction and a confidence bar.
- A match displays `[OK]  CORRECT` in green; a mismatch shows `[X]  MISMATCH` in red.
- The status bar at the bottom tracks trial count, accuracy percentage, and session time.
- The status indicator in the top-right corner blinks `● LIVE` during active inference; switches to amber `PAUSED` when paused.

### Mental Task Guide

**During REST** — relax your face and jaw, keep eyes open and still, do not perform any deliberate mental task.  
**During CLICK** — perform the mental action your models were trained on (e.g. imagining a hand clench or a physical blink).

### Session Controls

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume stimulus sequence |
| `Esc` | Stop session and exit |

When paused, stimulus presentation halts and a full-screen overlay is shown. The animate loop continues running so the UI stays responsive. Pressing `Space` again resumes from the next stimulus.

---

## BCI Virtual Keyboard

A fullscreen QWERTY scanning keyboard for hands-free text entry via BCI or manual control.

### Setup Screen

| Setting | Description |
|---------|-------------|
| Input Mode | **Spacebar (Manual)** — press `Enter` to simulate a CLICK for testing. **AI (BCI Model)** — live EEG inference drives key selection. |
| Arduino Port | Serial port (AI mode only) |
| Model | Model to use for inference (AI mode only) |
| Scan Speed (ms) | Duration each row or key is highlighted before advancing. Range: 400–3000 ms. |
| Conf. Threshold | Minimum prediction confidence to register as a CLICK. Range: 30%–95%. (AI mode only) |
| Pico W Server | Broadcast CLICK/REST to a connected Pico W (AI mode only) |
| Show Waveform | Display a live scrolling EEG trace at the bottom (AI mode only) |

Click `>> START KEYBOARD` to begin.

### How Scanning Works

The keyboard uses a two-phase row-then-key scanning process:

1. **Row scan** — the keyboard highlights one row at a time in green, advancing at the configured scan speed.
2. **CLICK to select a row** — when the row containing your target key is highlighted, perform a mental CLICK (or press `Enter` in manual mode).
3. **Key scan** — the keyboard then highlights keys one at a time within the selected row.
4. **CLICK to select a key** — when the scanner reaches your target key, perform another CLICK to type it.
5. **Auto-reset** — if no CLICK is detected within two full scan cycles, the scanner resets automatically to row-scan mode.

### Special Keys

| Key | Function |
|-----|----------|
| SPACE | Insert a space character into the output |
| CLEAR | Clear the entire output text box |
| Backspace symbol | Delete the last typed character |
| Return symbol | Insert a newline |

### Session Controls

| Key | Action |
|-----|--------|
| `Enter` | Simulate a CLICK (manual / testing mode only) |
| `Space` | Pause / Resume scanning |
| `Backspace` | Delete last character and reset scan to row 1 |
| `Esc` | Exit the keyboard |

The status indicator in the top-right corner blinks `● SCANNING` during active scanning and switches to amber `PAUSED` when paused.

### Tuning

- Raise `CONF. THRESHOLD` if the model is generating false positives (accidental selections).
- Lower `CONF. THRESHOLD` if the model rarely triggers even when you intend a CLICK.
- Increase `SCAN SPEED` if the scanner moves faster than you can react.
- Both sliders can be adjusted live during a session without restarting.

---

## Pico W LED Integration

The app can optionally broadcast CLICK/REST predictions over TCP to a Raspberry Pi Pico W LED controller.

1. Configure and flash `Microcontroller/pico_led.py` onto the Pico W (see root README).
2. Enable **Pico W Server** in the setup screen before starting a session.
3. The server starts a TCP listener on `SOCKET_PORT` (default 5005).
4. The Pico W connects automatically and its LED mirrors the live predictions.

---

## Model Files

Place the following files in `../Notebook/` before running the app:

| File | Model |
|------|-------|
| `BCI_MODEL.joblib` | ET + RF Ensemble (scikit-learn) |
| `BCI_SCALER.joblib` | StandardScaler for 42-feature input |
| `BCI_FNN.pt` | Feedforward Neural Network (PyTorch) |
| `BCI_CNN.pt` | Convolutional Neural Network (PyTorch) |
| `BCI_Hybrid.pt` | Hybrid CNN + FNN (PyTorch) |
| `BCI_Transformer.pt` | Transformer Encoder (PyTorch) |
| `BCI_TransformerHybrid.pt` | Transformer + FNN (PyTorch) |

Models are discovered and loaded automatically at startup. Any missing files are skipped and a warning is shown in the setup screen.
