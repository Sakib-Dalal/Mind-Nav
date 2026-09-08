<p align="center"><img src="apps/desktop/static/crown.svg" width="84" alt="Mind-Nav crown" /></p>
<h1 align="center">Mind-Nav</h1>
<p align="center"><strong>A little thought. A world of possibility.</strong><br/>One local workspace for EEG recording, personal model creation, and accessible communication.</p>

The recorder, notebook training workflow, real-time tester, and scanning keyboard are now a **Rust + Tauri 2 + Svelte 5 desktop application**. The active product has no Python dependency. Arduino acquisition firmware remains C++.

## Run

Install stable Rust, Node.js 22.12+ or a newer supported LTS, and your operating system’s [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/).

```sh
cd apps/desktop
npm ci
npm run tauri dev
```

Build a macOS application:

```sh
npm run tauri -- build --bundles app
```

The application is created at `target/release/bundle/macos/Mind-Nav.app` at the repository root. Signing/notarization and Windows/Linux installers require platform-specific release configuration. Windows needs WebView2; Linux needs WebKitGTK 4.1, libudev development packages, and `spd-say` for speech.

`npm run dev` serves a **browser design preview** at `http://localhost:1487`. Navigation, appearance, communication, and an illustrative waveform work there. Device access, recordings, saved models, and training require the desktop app and run in Rust. The preview never fabricates model reports or saved recordings.

## Your workflow

1. **Connect:** select the Arduino serial port or explicitly start Demo mode. Connection errors never silently switch to simulation.
2. **Record:** follow alternating five-second REST and SELECT cues. Imagine a consistent action; movement is not required. Pause/resume, set a duration, and save locally.
3. **Create:** choose a recording or import CSV in Model Studio. Train locally, review trial-separated validation and false positives, then explicitly activate the model.
4. **Practice:** check the model with a separate guided sequence. One prediction is scored per trial. Practice never selects keys or feeds its results back into training.
5. **Communicate:** use quick phrases, spoken messages, or the row/column scanning keyboard. A switch mapped to Enter selects a row, then a key. Enable BCI input after checking the model and signal. Patient view focuses on large communication targets.

Light is the default theme; dark, larger text, reduced motion, spoken cues, adjustable scanning (0.6–5 seconds), and adjustable selection thresholds are available. Quick phrases cover yes/no, water, help, discomfort, and thanks. Undo, pause, and a scannable Finish action support recovery. Composed messages survive navigation within the app, and are cleared when it closes.

## Signal processing and models

- 250 SPS conversion-ready acquisition with sequence numbers, device timestamps, and raw ADC mV.
- One causal Rust preprocessing pipeline for training and inference: second-order 0.5 Hz high-pass, 50/60 Hz notch (Q=30), and second-order 40 Hz low-pass.
- Flat-signal, clipping, artifact, gap, and disconnect checks; three-second filter settling and 500 ms trial-transition guards.
- Two-second native windows and 20 spectral/time-domain features using Hann-windowed Welch PSD.
- Class-balanced, L2-regularized logistic regression, with scaling fitted separately inside each training fold. Whole trials remain in one fold.
- Versioned JSON models with preprocessing/source contracts, balanced accuracy, precision, recall, confusion counts, and false-positive rate.
- Smoothed selection scores, three consecutive qualifying predictions, a 1.5-second cooldown, and return-to-rest rearming.

These changes improve consistency, evaluation hygiene, and failure handling; they do **not** establish better clinical decoding accuracy. Single-channel EEG remains vulnerable to movement artifacts and person/day variability. See [signal design](docs/SIGNAL_PIPELINE.md).

## Hardware

Flash [the v2 Arduino sketch](firmware/arduino/mind_nav/mind_nav.ino) with the Adafruit ADS1X15 library. It targets an Uno, ADS1115, and BioAmp output on ADS1115 A0.

**New wire: ADS1115 ALERT/RDY → Uno D2.** Conversion-ready interrupts replace the old nominal 256 Hz polling assumption. The ADC range is ±6.144 V to accommodate the existing 0–5 V amplifier output, while its supply/input limits still apply. See [wiring and protocol](docs/HARDWARE.md).

Waveforms are labeled **ADC mV**, not electrode µV; electrode amplitude requires measured amplifier gain. Use suitable isolated acquisition hardware before connecting electrodes to a person.

## Data and migration

CSV recordings, JSON models, and preferences live in the OS application data directory for `app.mindnav.desktop`, shown in Settings. Export uses native save dialogs. CSV buffers flush every second; metadata writes atomically. Interrupted recordings can be recovered, with possible loss of the last unflushed samples. The app does not encrypt files or upload data.

The original Python applications, notebooks, trained weights, and optional MicroPython Pico Wi-Fi experiment are preserved in [`legacy/`](legacy/README.md), outside the build. Existing EEG recordings remain in `Data/` and `legacy/Notebook/`.

Import recognizes native CSVs and legacy signal columns with REST/CLICK labels encoded as `0/1` or `0/5`. **Detect timing** prefers native metadata or estimates legacy timestamp spacing; this is an estimate, not ADC calibration. Legacy models use one-second comparison windows to accommodate the old shorter trials. Their firmware already filtered/scaled the signal, so they are comparison-only. Record new v2 raw data for live input.

Python `.joblib` and PyTorch `.pt` weights are not silently converted. Train new portable Rust models in Model Studio. The old six-model architecture comparison and optional Pico Wi-Fi feedback are retained as research references rather than current runtime features.

## Layout

```text
apps/desktop/                 Svelte interface and Tauri application
  src/components/             Overview, recorder, studio, practice, communication
  src-tauri/src/              Rust acquisition, persistence, commands, speech
  static/crown.svg            Original crown identity, editable vector
crates/mind-nav-core/          Rust DSP, CSV processing, training, intent gating
firmware/arduino/mind_nav/     C++ acquisition firmware
Data/                         Existing EEG recordings
docs/                         Hardware, signal design, validation
legacy/                       Original research code and model artifacts
```

## Project handbook website

The complete Svelte documentation website lives in [`apps/website/`](apps/website/README.md). It includes setup guides, requirements, an interactive v2 wiring diagram, firmware downloads, recording and model workflows, communication, the signal pipeline, data migration, validation, and troubleshooting.

```sh
cd apps/website
npm ci
npm run dev
```

Open `http://127.0.0.1:1490`. Use `npm run check` and `npm run build` in that directory to validate and produce the static site. The handbook is separate from the native desktop application.

## Verification

```sh
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo fmt --all --check
cd apps/desktop
npm run check
npm test
npm run build
```

From the repository root:

```sh
arduino-cli compile --fqbn arduino:avr:uno firmware/arduino/mind_nav
cargo run -p mind-nav-core --example train_csv -- Data/eeg_precision_bci.csv
```

This is a working **research product foundation**, not a clinically validated assistive device. Hardware-in-the-loop and supervised usability evaluation remain necessary. “I need help” speaks locally; it does not contact a caregiver or emergency service. See [validation](docs/VALIDATION.md).
