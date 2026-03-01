# EEG Recorder — Mind-Nav Data Collection Tool

Standalone fullscreen application for capturing labelled EEG training data using an Arduino, BioAmp EXG Pill, and ADS1115 ADC.

---

## Requirements

```bash
pip install pyserial numpy
```

Python 3.9 or later is required.

---

## Hardware Setup

| Component | Role |
|-----------|------|
| Arduino Uno | Reads ADC over I2C, applies DSP filters, streams over USB serial |
| BioAmp EXG Pill | Amplifies the EEG signal (High Gain, BandPass enabled, 2-electrode mode) |
| ADS1115 ADC | 250 SPS, gain +-4.096 V, connected to Arduino via I2C |

1. Connect the BioAmp EXG Pill to the Arduino A0 pin and the ADS1115 to the I2C pins (SDA/SCL).
2. Flash the provided Arduino sketch to the Arduino Uno.
3. Attach EEG electrodes according to the 10-20 system (see `Media/` in the root directory).
4. Connect the Arduino to your computer via USB.

---

## Configuration

Open `main.py` and verify the top-level constants match your setup:

```python
PORT      = "/dev/cu.usbmodem1101"   # Serial port of your Arduino
BAUD_RATE = 115200
FILE_NAME = "../Data/eeg_precision_bci.csv"
```

Change `PORT` to match your system:
- macOS: `/dev/cu.usbmodem*` or `/dev/tty.usbserial*`
- Linux: `/dev/ttyUSB0` or `/dev/ttyACM0`
- Windows: `COM3`, `COM4`, etc.

---

## Running the Recorder

```bash
cd EEG_Recorder
python main.py
```

The application opens in fullscreen with a neural-lab style interface. The live EEG waveform is drawn in real time once the Arduino is connected.

---

## Session Setup Screen

On launch you will see the **Session Setup** menu with the following options:

### Recording Duration

Six canvas radio tiles let you set a time limit for the session:

| Tile | Duration |
|------|----------|
| (inf symbol) | Record indefinitely until manually stopped |
| 5 min | Auto-stop after 5 minutes |
| 15 min | Auto-stop after 15 minutes |
| 30 min | Auto-stop after 30 minutes |
| 1 hr | Auto-stop after 1 hour |
| 2 hr | Auto-stop after 2 hours |

Click a tile to select it (selected tile shows a cyan border and filled dot). The default is infinite.

### Begin Session

Click `>> BEGIN SESSION` to start recording. The button is disabled and greyed out if no Arduino is detected (shown as DISCONNECTED in the menu).

---

## Session Screen

Once a session starts, the screen switches to the live recording view:

- **EEG Waveform** — scrolling oscilloscope display of the raw signal
- **Elapsed Time** — total active recording time (pauses excluded)
- **Remaining Time** — shown as `REM: MM:SS` if a duration limit is set, or `LIMIT: INF` for infinite sessions
- **Status Indicator** — blinks `RECORDING` in green during active capture; shows `PAUSED` in amber when paused
- **Trial Counters** — number of CLICK and REST stimuli presented so far

The application cycles through CLICK and REST stimulus windows automatically, presenting visual and audio (via text-to-speech) cues.

---

## Session Controls

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume recording |
| `Esc` | Stop session and exit |

### Pause Behaviour

- Pressing `Space` immediately stops stimulus presentation and shows a full-screen PAUSED overlay.
- The EEG serial buffer continues to drain in the background to prevent data loss.
- The elapsed time counter freezes during a pause and resumes accurately on resume.
- Pressing `Space` again hides the overlay and restarts the stimulus loop.

---

## Data Output

All recorded data is written to the path defined in `FILE_NAME` (default: `../Data/eeg_precision_bci.csv`).

**Append mode** — if the file already exists, new session data is appended to the end of the file. The CSV header (`timestamp,eeg_value,label`) is only written once, when the file is new or empty. You can run multiple sessions safely without losing previous recordings.

### CSV Format

| Column | Description |
|--------|-------------|
| `timestamp` | Unix timestamp of the sample (seconds, float) |
| `eeg_value` | Raw ADC reading from the ADS1115 |
| `label` | `1` for CLICK stimulus window, `0` for REST |

---

## Stimulus Sequence

The recorder runs an automated trial sequence:

1. **CLICK window** — a CLICK stimulus is displayed for `STIM_DURATION` ms (default 2000 ms). Perform your mental task (e.g. imagining a hand clench).
2. **REST window** — a REST prompt is displayed for `REST_DURATION` ms (default 3000 ms). Relax and remain still.
3. The cycle repeats until the session is stopped or the time limit is reached.

Adjust `STIM_DURATION` and `REST_DURATION` in `main.py` to match your preferred trial length.

---

## After Recording

The CSV file is ready for use with the training notebook:

```bash
cd Notebook
jupyter notebook BCI_Notebook.ipynb
```

The notebook loads `Data/eeg_precision_bci.csv`, extracts features, and trains all six BCI classification models.
