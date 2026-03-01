# Mind-Nav — Brain-Controlled Navigation via EEG

> Control your computer with your mind. Mind-Nav is a full-stack Brain-Computer Interface (BCI) system that captures raw EEG brainwaves, trains machine-learning and deep-learning models to detect mental intent, and translates that intent into real-time navigation actions.

---

## Project Structure

```text
Mind-Nav/
├── Data/                       # Raw and processed EEG recordings (CSV)
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
|---|---|---|
| **REST** | `0` | Relaxed, no action intended |
| **CLICK** | `5` | Active mental intent to click/interact |

EEG signals are captured at **256 Hz**, cleaned, segmented into trials, and fed into six trained classifiers. The best model is then deployed inside the navigation app to issue real-time computer commands purely from brainwave data.

---

## Components

### 1. Hardware Signal Capture (Arduino)

The system interfaces directly with an EEG headset using an Arduino Uno, BioAmp EXG Pill, and ADS1115 ADC to record raw brain signals. It streams EEG samples in real-time over a USB serial connection, which serves as the input for both data collection and live inference.

Hardware Configuration:
- **BioAmp EXG Pill**: Configured for High Gain and BandPass enabled, operating in 2-electrode mode.
- **ADS1115 ADC**: Configured for 250 SPS with a gain of ±4.096V to capture the precise millivolt signal.
- **Arduino Uno**: Reads the ADC over I2C and applies standard DSP filters (0.5 Hz high-pass, 40 Hz low-pass) before transmitting the data via serial.

---

### 2. `Data/` — EEG Dataset

Contains the recorded EEG CSV file (`eeg_precision_bci.csv`) used for training and evaluation.

**Dataset statistics:**

| Property | Value |
|---|---|
| Sampling rate | 256 Hz |
| Total samples (trimmed) | 72,589 |
| Total duration | ~283.6 seconds |
| REST samples | 28,658 |
| CLICK samples | 43,931 |

The first 500 samples (≈ 2 seconds) are discarded during preprocessing to remove headset initialisation noise.

---

### 3. `Notebook/` — Model Training & Evaluation

The core ML pipeline, documented step-by-step in a Jupyter notebook.

#### Pipeline Steps

**Data Loading & Preprocessing**
- Load `eeg_precision_bci.csv` and trim initialisation noise
- Zero-centre the signal by subtracting the 500 mV baseline offset
- Inspect class distribution and recording duration

**EEG Visualisation**
- Plot the first 30 seconds of the EEG waveform with a per-class colour overlay
- Visualise the label track alongside the raw signal

**Trial Segmentation**
- Detect label transitions to split the continuous stream into discrete trials
- Each contiguous run of the same label becomes one segmented trial

**Feature Engineering — 42 Features per Trial**

Features are extracted per trial across three groups:

- **Time-domain:** Mean, std, variance, peak-to-peak, RMS, skewness, kurtosis, zero-crossing rate, mean absolute value
- **Frequency-domain (Welch PSD):** Absolute and relative band power for Delta (0.5–4 Hz), Theta (4–8 Hz), Alpha (8–13 Hz), Beta (13–30 Hz), and Gamma (30–100 Hz); spectral entropy; peak frequency; spectral centroid
- **Cross-band ratios:** Alpha/Beta, Theta/Alpha, and other clinically motivated power ratios

#### Models Trained

Six models are trained and compared using **5-fold Stratified Cross-Validation**:

| # | Model | Input | Architecture |
|---|---|---|---|
| 1 | **ET + RF Ensemble** (scikit-learn) | 42 features | Soft-voting: ExtraTreesClassifier + RandomForestClassifier (500 trees each, balanced class weights) |
| 2 | **FNN** (PyTorch) | 42 features | 3× `Linear → BatchNorm → ReLU → Dropout(0.4)` → classifier |
| 3 | **CNN** (PyTorch) | Raw EEG window (256 samples) | 3× `Conv1D → BatchNorm → ReLU → MaxPool → Dropout` → GlobalAvgPool → Linear |
| 4 | **Hybrid CNN + FNN** (PyTorch) | Raw window + 42 features | Dual-branch: CNN (→128-d) + FNN (→64-d) fused (192-d → MLP → 2 classes) |
| 5 | **Transformer** (PyTorch) | Raw EEG window (256 samples) | Patch-based Transformer Encoder with CLS token classification |
| 6 | **Transformer + FNN** (PyTorch) | Raw window + 42 features | Transformer branch + FNN branch fused (128-d → MLP → 2 classes) |

All PyTorch models use the Adam optimiser with a cosine annealing learning-rate schedule and cross-entropy loss.

#### Saved Artefacts

| File | Contents |
|---|---|
| `BCI_MODEL.joblib` | Sklearn ET+RF ensemble (fitted on full dataset) |
| `BCI_SCALER.joblib` | `StandardScaler` for the 42-feature matrix |
| `BCI_FNN.pt` | PyTorch FNN weights |
| `BCI_CNN.pt` | PyTorch CNN weights |
| `BCI_Hybrid.pt` | PyTorch Hybrid CNN+FNN weights |
| `BCI_Transformer.pt` | PyTorch Transformer weights |
| `BCI_TransformerHybrid.pt` | PyTorch Transformer+FNN weights |

---

### 4. `Mind-Nav-App/` — Unified BCI Application (Python)

A single Python application with two modes selectable from a launcher menu:

#### BCI Real-Time Tester
- Reads live EEG data from the hardware recorder via serial connection
- Runs inference with trained models to classify each window as REST or CLICK
- Provides a side-by-side display of actual stimulus vs model prediction with confidence bars
- Tracks accuracy via trial count, correct predictions, and session timer
- Supports an optional TCP server to broadcast predictions to connected Pico W clients

#### BCI Virtual Keyboard
- QWERTY scanning keyboard with row and column selection
- Supports two input modes: Spacebar for manual input and AI for BCI model prediction
- Features adjustable live control over scan speed and confidence threshold
- Broadcasts CLICK/REST predictions during AI scanning to connected Pico W clients

**Run with:**
```bash
cd Mind-Nav-App
python main.py
```

---

### 5. `Microcontroller/` — Pico W LED Controller

A MicroPython script for the Raspberry Pi Pico W that connects to the Mind-Nav app via TCP and controls the on-board LED:

- LED ON when the model detects `CLICK` (active mental intent)
- LED OFF when the model detects `REST` (relaxed state)
- Auto-reconnects on connection loss

**Setup:**
1. Flash MicroPython firmware onto your Pico W
2. Edit `WIFI_SSID`, `WIFI_PASS`, and `SERVER_IP` in `pico_led.py`
3. Copy `pico_led.py` to the Pico W as `main.py`
4. Enable "Pico W Server" in the Mind-Nav app settings
5. Power on the Pico W — it will connect automatically

---

## Getting Started

### Prerequisites

```bash
pip install scikit-learn pandas numpy matplotlib scipy torch torchvision joblib pyserial
```

### 1. Compile hardware sketch
Flash the provided Arduino sketch to your Arduino Uno connected to the BioAmp EXG Pill.

### 2. Train the Models

Open and run `Notebook/BCI_Notebook.ipynb` end-to-end to generate all model files.

### 3. Run the Application

```bash
cd Mind-Nav-App
python main.py
```

Select **BCI Tester** to test model accuracy or **BCI Keyboard** to type with your mind.

### 4. (Optional) Set Up Pico W

Follow the steps in [Microcontroller section](#5-microcontroller--pico-w-led-controller) to connect a Pico W for physical LED feedback.

---

## Usage

### 1. Using the Arduino Recorder
The Arduino sketch works alongside the BioAmp hardware to capture brain signals. 
- **Setup:** Connect the BioAmp EXG Pill to the Arduino A0 pin, and the ADS1115 to I2C. Connect your electrodes as described in the pinout section.
- **Recording:** If you are recording raw CSV data for training, you can open the Arduino IDE Serial Monitor at 115200 baud and type `START` to begin. Type `STOP` to end.
- **Live Mode:** You do not need the IDE open for live use. The Mind-Nav App will automatically send `START` and `STOP` behind the scenes when you launch the UI.

### 2. Using the BCI Real-Time Tester
The Tester mode provides insights into how well your models interpret your brainwaves on the fly without making irreversible inputs.
- Launch the main menu via `python main.py` and select "BCI Tester".
- Select your Arduino's serial port (e.g., `/dev/cu.usbmodem1101`) and the model you wish to test (e.g., "Transformer" or "ET+RF Ensemble").
- During the **REST** prompt (`+` icon), relax your face and jaw, keeping your eyes open and stationary.
- During the **CLICK** prompt (`●` icon), perform the mental task your models were trained on (such as imagining a hand clench or physical blink).
- The right side of the screen will display the Model Prediction and its confidence percentage, glowing green for correct matches.

### 3. Using the BCI Virtual Keyboard
The Virtual Keyboard allows hands-free text entry via mind control.
- Launch the main menu via `python main.py` and select "BCI Keyboard".
- Choose your input mode: **Spacebar (manual)** for testing, or **AI (BCI Model)** for true brain control.
- The UI scans row-by-row. When the row containing your desired letter is highlighted green, perform your mental "CLICK" to select it.
- After a row is selected, it will scan key-by-key. Perform your mental "CLICK" when the scanner lands on your target letter.
- **Tuning:** If you notice false positives, increase the `CONF. THRESHOLD` slider. If the scanner moves too fast for you to react, increase the `SCAN SPEED` slider up to 3000ms.

---

## Tech Stack

| Layer | Technology |
|---|---|
| EEG Capture | Arduino Uno, BioAmp EXG Pill, ADS1115 |
| Data Analysis | Python, pandas, NumPy, SciPy |
| Visualisation | Matplotlib |
| Classical ML | scikit-learn (ExtraTrees, RandomForest, VotingClassifier) |
| Deep Learning | PyTorch (FNN, CNN, Hybrid, Transformer) |
| Model Persistence | joblib, `torch.save` / `torch.load` |
| Desktop UI | Tkinter (full-screen canvas) |
| Microcontroller | MicroPython (Raspberry Pi Pico W) |
| Communication | TCP Sockets, Serial (USB) |

---

## How It Works — End to End

```text
EEG Headset (BioAmp)
     │
     ▼
Arduino Uno + ADS1115        ← captures and filters raw brainwave signal at 256 Hz
     │
     ▼
Mind-Nav-App (Python)        ← accepts serial stream, segments windows
     │
     ▼
Saved Models (.pt / .joblib) ← extracts 42 features, runs classification
     │
     ▼
UI Output                    ← real-time inference (REST / CLICK)
     │
     ├──▶ Virtual Keyboard   ← type with your mind
     └──▶ Pico W (TCP)       ← LED ON = CLICK, LED OFF = REST
```

---

## Media

### Connection

![EEG Headset](Media/connection-with-cable.png)

### Electrode Placement
![Electrode Placement](Media/eeg_placement.png)

### 10-20 System
![10-20 System](Media/10-20-system.png)

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
