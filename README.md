# Mind-Nav — Brain-Controlled Navigation via EEG

> Mind-Nav is a full-stack Brain-Computer Interface (BCI) system that captures raw EEG brainwaves, trains machine-learning and deep-learning models to detect mental intent, and translates that intent into real-time navigation actions.

---

## Project Structure

```text
Mind-Nav/
├── Data/                       # Raw and processed EEG recordings (CSV)
├── EEG_Recorder/               # EEG data collection application
│   └── main.py                 # Standalone recorder UI (entry point)
├── Microcontroller/            # MicroPython — Pico W LED controller
│   └── pico_led.py
├── Mind-Nav-App/               # Python application — unified BCI suite
│   ├── main.py                 # Unified launcher (entry point)
│   ├── tester.py               # BCI Real-Time Tester UI
│   ├── keyboard.py             # BCI Virtual Keyboard UI
│   ├── config.py               # Shared constants & colour palette
│   ├── features.py             # 42-feature EEG extraction
│   ├── models.py               # Model definitions & ModelManager
│   ├── serial_reader.py        # Arduino serial reader + simulation
│   ├── pico_server.py          # TCP server for Pico W clients
│   └── pyproject.toml
└── Notebook/                   # Jupyter notebooks — model training
    ├── BCI_Notebook.ipynb
    ├── BCI_MODEL.joblib
    ├── BCI_SCALER.joblib
    ├── BCI_FNN.pt
    ├── BCI_CNN.pt
    ├── BCI_Hybrid.pt
    ├── BCI_Transformer.pt
    └── BCI_TransformerHybrid.pt
```

---

## Overview

Mind-Nav is an end-to-end BCI pipeline built around two mental states:

| Intent | Label | Description |
|--------|-------|-------------|
| REST   | `0`   | Relaxed, no action intended |
| CLICK  | `1`   | Active mental intent to click or interact |

EEG signals are captured at **256 Hz**, cleaned, segmented into trials, and fed into six trained classifiers. The best-performing model is deployed inside the navigation app to issue real-time commands purely from brainwave data.

---

## Hardware

The system interfaces with an EEG headset using the following components:

- **BioAmp EXG Pill** — High Gain, BandPass enabled, 2-electrode mode
- **ADS1115 ADC** — 250 SPS, gain ±4.096 V
- **Arduino Uno** — Reads ADC over I2C, applies 0.5 Hz high-pass and 40 Hz low-pass DSP filters, streams data over USB serial at 115200 baud

**Electrode placement** follows the 10-20 international system. Reference images are in the `Media/` directory.

---

## Getting Started

### Prerequisites

Install Python dependencies:

```bash
pip install scikit-learn pandas numpy matplotlib scipy torch torchvision joblib pyserial
```

### Step 1 — Flash the Arduino

Flash the provided Arduino sketch to your Arduino Uno. The sketch streams filtered EEG samples over serial continuously; the application issues `START` / `STOP` automatically.

### Step 2 — Record EEG Data

Run the EEG Recorder to capture labelled training data:

```bash
cd EEG_Recorder
python main.py
```

See [EEG Recorder](#eeg-recorder) section below for full usage.

### Step 3 — Train the Models

Open and run `Notebook/BCI_Notebook.ipynb` end-to-end. This loads `Data/eeg_precision_bci.csv`, extracts 42 features, trains all six models, and saves the model files into `Notebook/`.

### Step 4 — Run the BCI Application

```bash
cd Mind-Nav-App
python main.py
```

Select **BCI Real-Time Tester** to validate model accuracy, or **BCI Virtual Keyboard** to type hands-free.

### Step 5 — (Optional) Set Up Pico W

Follow the [Microcontroller](#microcontroller--pico-w) section to connect a Raspberry Pi Pico W for physical LED feedback.

---

## Components

### EEG Recorder

A standalone fullscreen application for capturing clean, labelled EEG training data.

**Launch:**
```bash
cd EEG_Recorder
python main.py
```

**Setup Screen**

On launch you will see the Session Setup menu:

1. **Recording Duration** — Select how long the session should run: infinite, 5 min, 15 min, 30 min, 1 hr, or 2 hr. Click the desired tile to select it (cyan border = selected).
2. **Begin Session** — Click `>> BEGIN SESSION` to start recording. The button is disabled if no Arduino is detected.

**Session Controls**

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume recording |
| `Esc` | Stop session and exit |

**Data Output**

- Data is written to `Data/eeg_precision_bci.csv`.
- If the file already exists, new data is **appended** rather than overwritten, so you can run multiple sessions without losing previous recordings.
- The CSV header is only written once (when the file is new or empty).
- The UI displays elapsed time, remaining time (if a duration limit is set), and live EEG waveform.

**Pause Behaviour**

Pressing `Space` shows a full-screen PAUSED overlay and temporarily halts stimulus presentation. The EEG buffer continues to drain in the background. Pressing `Space` again resumes exactly where the session left off.

---

### BCI Real-Time Tester

Validates how well your trained models interpret your brainwaves live, without making irreversible inputs.

**Launch:**
```bash
cd Mind-Nav-App
python main.py          # then select "BCI REAL-TIME TESTER"
```

**Setup Screen**

| Field | Description |
|-------|-------------|
| Arduino Port | Serial port your Arduino is connected to (e.g. `/dev/cu.usbmodem1101` on macOS, `COM3` on Windows) |
| Model | Dropdown of all detected model files in `Notebook/` |
| Pico W Server | Enable TCP socket server to broadcast predictions to a connected Pico W |

Click `>> BEGIN TESTING` to start.

**Session Screen**

- The left panel shows the **Actual Stimulus** (REST or CLICK) being presented.
- The right panel shows the **Model Prediction** with a confidence bar.
- When the prediction matches the stimulus, `[OK]  CORRECT` is displayed in green. Mismatches show `[X]  MISMATCH` in red.
- Live accuracy, trial count, and session elapsed time are shown in the status bar.

**During REST** — relax your face and jaw, keep your eyes open and still.  
**During CLICK** — perform the mental task your models were trained on (e.g. imagining a hand clench).

**Session Controls**

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume the stimulus sequence |
| `Esc` | Stop session and exit |

---

### BCI Virtual Keyboard

A fullscreen QWERTY scanning keyboard for hands-free text entry.

**Launch:**
```bash
cd Mind-Nav-App
python main.py          # then select "BCI VIRTUAL KEYBOARD"
```

**Setup Screen**

| Setting | Description |
|---------|-------------|
| Input Mode | **Spacebar (Manual)** — use Enter key to simulate clicks for testing. **AI (BCI Model)** — live EEG inference selects keys. |
| Arduino Port | Serial port (AI mode only) |
| Model | Model to use for inference (AI mode only) |
| Scan Speed (ms) | Time each row/key is highlighted before advancing. Range: 400–3000 ms. |
| Conf. Threshold | Minimum model confidence required to count a prediction as a CLICK. Range: 30%–95%. (AI mode only) |
| Pico W Server | Enable TCP broadcast to a connected Pico W (AI mode only) |
| Show Waveform | Display a live scrolling EEG trace at the bottom of the screen (AI mode only) |

Click `>> START KEYBOARD` to begin.

**How Scanning Works**

1. The keyboard scans **row by row**, highlighting one row at a time in green.
2. When the row containing your target key is highlighted, perform a mental CLICK (or press `Enter` in manual mode) to select that row.
3. The keyboard then scans **key by key** within that row.
4. When the scanner lands on your target key, perform another CLICK to type it.
5. If no selection is made within two full cycles, the scanner resets to row-scan automatically.

**Special Keys**

| Key | Function |
|-----|----------|
| `SPACE` | Insert a space character |
| `CLEAR` | Clear the entire output text |
| `[backspace]` | Delete the last character |
| `[enter]` | Insert a newline |

**Session Controls**

| Key | Action |
|-----|--------|
| `Enter` | Simulate a CLICK (manual / testing mode) |
| `Space` | Pause / Resume scanning |
| `Backspace` | Delete last character and reset scan to row 1 |
| `Esc` | Exit the keyboard |

**Tuning Tips**

- If you see false positives (keys selected when you did not intend), raise the `CONF. THRESHOLD` slider.
- If the scanner moves too quickly for you to react, increase the `SCAN SPEED` slider.
- Both sliders are adjustable live during a session without restarting.

---

### Microcontroller — Pico W

A MicroPython script for the Raspberry Pi Pico W that connects to the Mind-Nav app over TCP and controls the on-board LED:

- LED ON when the model detects CLICK (active mental intent)
- LED OFF when the model detects REST (relaxed state)
- Auto-reconnects on connection loss

**Setup:**

1. Flash MicroPython firmware onto your Pico W.
2. Edit `WIFI_SSID`, `WIFI_PASS`, and `SERVER_IP` in `Microcontroller/pico_led.py`.
3. Copy `pico_led.py` to the Pico W and rename it `main.py`.
4. Enable **Pico W Server** in the Mind-Nav app settings before starting a session.
5. Power on the Pico W — it will connect automatically.

---

## Model Training Pipeline

Six models are trained in `Notebook/BCI_Notebook.ipynb` using **5-fold Stratified Cross-Validation**:

| # | Model | Input | Architecture |
|---|-------|-------|--------------|
| 1 | ET + RF Ensemble | 42 features | Soft-voting: ExtraTreesClassifier + RandomForestClassifier (500 trees each, balanced class weights) |
| 2 | FNN | 42 features | 3x (Linear -> BatchNorm -> ReLU -> Dropout 0.4) -> classifier |
| 3 | Hybrid CNN + FNN | Raw window + 42 features | Dual-branch: CNN (128-d) + FNN (64-d) fused to 192-d MLP |
| 4 | Transformer | Raw EEG window (256 samples) | Patch-based Transformer Encoder with CLS token |
| 5 | Transformer + FNN | Raw window + 42 features | Transformer branch + FNN branch fused (128-d -> MLP) |

All PyTorch models use the Adam optimiser with cosine annealing learning rate schedule and cross-entropy loss.

**42 Features extracted per trial:**

- **Time-domain:** Mean, std, variance, peak-to-peak, RMS, skewness, kurtosis, zero-crossing rate, mean absolute value
- **Frequency-domain (Welch PSD):** Absolute and relative band power for Delta (0.5-4 Hz), Theta (4-8 Hz), Alpha (8-13 Hz), Beta (13-30 Hz), Gamma (30-100 Hz); spectral entropy; peak frequency; spectral centroid
- **Cross-band ratios:** Alpha/Beta, Theta/Alpha, and other clinically motivated power ratios

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| EEG Capture | Arduino Uno, BioAmp EXG Pill, ADS1115 |
| Data Analysis | Python, pandas, NumPy, SciPy |
| Visualisation | Matplotlib |
| Classical ML | scikit-learn (ExtraTrees, RandomForest, VotingClassifier) |
| Deep Learning | PyTorch (FNN, CNN, Hybrid, Transformer) |
| Model Persistence | joblib, torch.save / torch.load |
| Desktop UI | Tkinter (full-screen canvas) |
| Microcontroller | MicroPython (Raspberry Pi Pico W) |
| Communication | TCP Sockets, Serial (USB) |

---

## Signal Flow

```text
EEG Headset (BioAmp)
     |
     v
Arduino Uno + ADS1115        -- captures and filters raw brainwave signal at 256 Hz
     |
     v
Mind-Nav-App (Python)        -- accepts serial stream, segments windows
     |
     v
Saved Models (.pt / .joblib) -- extracts 42 features, runs classification
     |
     v
UI Output                    -- real-time inference (REST / CLICK)
     |
     |---> Virtual Keyboard  -- type with your mind
     |---> BCI Tester        -- validate model accuracy
     +---> Pico W (TCP)      -- LED ON = CLICK, LED OFF = REST
```

---

## Media

### Connection

![EEG Headset](Media/connection-with-cable.png)

### Electrode Placement

![Electrode Placement](Media/eeg_placement.png)

### 10-20 System

![10-20 System](Media/10-20-system.png)

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
