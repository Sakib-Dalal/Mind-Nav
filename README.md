# Mind-Nav — Brain-Controlled Navigation via EEG

> Control your computer with your mind. Mind-Nav is a full-stack Brain-Computer Interface (BCI) system that captures raw EEG brainwaves, trains machine-learning and deep-learning models to detect mental intent, and translates that intent into real-time navigation actions.

---

## Project Structure

```
Mind-Nav/
├── Data/                       # Raw and processed EEG recordings (CSV)
├── EEG_Recorder/               # C++ application to capture live EEG data
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

### 1. `EEG_Recorder/` — Hardware Signal Capture (C++)

A C++ application that interfaces directly with an EEG headset to record raw brain signals. It streams or saves timestamped EEG samples (in millivolt readings) alongside intent labels to a CSV file, which serves as the training dataset for all downstream models.

**Output format:**

| Column | Description |
|---|---|
| `Timestamp_Unix` | Unix epoch timestamp |
| `Signal_mV` | Raw EEG amplitude in mV (baseline ~500 mV) |
| `Intent_Label` | Human-readable label: `REST` or `CLICK` |
| `Label_Class` | Numeric label: `0` (REST) or `5` (CLICK) |

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

#### 🧠 BCI Real-Time Tester
- **Reads live EEG data** from the hardware recorder in real time
- **Runs inference** with trained models to classify each window as REST or CLICK
- **Side-by-side display**: Actual stimulus vs. Model prediction with confidence bars
- **Accuracy tracking**: Trial count, correct predictions, session timer
- **Pico W support**: Optional TCP server broadcasts predictions to connected Pico W clients

#### ⌨ BCI Virtual Keyboard
- **QWERTY scanning keyboard** with row → column selection
- **Two input modes**: Spacebar (manual) or AI (BCI model)
- **Live control**: Adjustable scan speed and confidence threshold sliders
- **Pico W support**: Broadcasts CLICK/REST predictions during AI scanning

**Run with:**
```bash
cd Mind-Nav-App
python main.py
```

---

### 5. `Microcontroller/` — Pico W LED Controller

A MicroPython script for the Raspberry Pi Pico W that connects to the Mind-Nav app via TCP and controls the on-board LED:

- **LED ON** when the model detects `CLICK` (active mental intent)
- **LED OFF** when the model detects `REST` (relaxed state)
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

### 1. Record EEG Data

Compile and run the C++ recorder in `EEG_Recorder/` with your EEG headset connected. This will generate your `eeg_precision_bci.csv` in the `Data/` folder.

### 2. Train the Models

Open and run `Notebook/BCI_Notebook.ipynb` end-to-end. This will produce all seven model artefact files ready for deployment.

### 3. Run the Application

```bash
cd Mind-Nav-App
python main.py
```

Select **BCI Tester** to test model accuracy or **BCI Keyboard** to type with your mind.

### 4. (Optional) Set Up Pico W

Follow the steps in [Microcontroller section](#5-microcontroller--pico-w-led-controller) to connect a Pico W for physical LED feedback.

---

## Tech Stack

| Layer | Technology |
|---|---|
| EEG Capture | C++ (hardware interface) |
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

```
EEG Headset
     │
     ▼
EEG_Recorder (C++)           ← captures raw brainwave signal at 256 Hz
     │
     ▼
Data/ (CSV)                  ← timestamped Signal_mV + intent labels
     │
     ▼
Notebook (Python)            ← segment → extract 42 features → train 6 models
     │
     ▼
Saved Models (.pt / .joblib)
     │
     ▼
Mind-Nav-App (Python)        ← real-time inference → REST / CLICK
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
