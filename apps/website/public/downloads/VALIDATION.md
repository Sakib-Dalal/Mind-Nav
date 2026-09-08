# Validation record — 8 September 2026

## Build and automated checks

- Rust core and desktop integration tests: signal attenuation, Welch power normalization, nonfinite/flat rejection, explicit return-to-rest, held-intent debounce, protocol rejection, legacy CSV labels/timing, trial-separated training, model serialization, practice scoring, complete recording/training/reload, mismatched-source rejection, crash recovery, stale-input disarming, and source-switch timing.
- TypeScript scanner tests: row/key selection, recovery after two missed cycles, pause/resume, and scannable Pause/Finish controls.
- `svelte-check` and production Vite build.
- `cargo fmt --all --check` and Clippy with warnings denied.
- macOS release `.app` produced by Tauri, using the new crown icon.
- Arduino Uno compilation using Adafruit ADS1X15 2.6.2: 7,864 bytes flash (24%) and 489 bytes static RAM (23%). No hardware was flashed.

The native integration test drives the actual Rust recorder with deterministic synthetic samples, automatically finishes after two minutes of sample time, writes CSV/JSON, trains a model, reloads it, and checks source gating. It is a software integration test, not a physical EEG or native GUI test.

## Browser interface checks

Reviewed the light/dark workspace, device setup, recorder, model creation screen, patient communication board, and settings. Checked one-switch row-to-key selection with Enter, Escape pause, message persistence across navigation, quick phrases, keyboard controls, larger text, reduced motion, and empty-state behavior. Scan timers give a full dwell after selecting a row; highlighted rows scroll into view on shorter displays. Preview and simulated data are explicitly labeled.

Native macOS UI automation could not be completed because Computer Use permission was unavailable. Serial hardware, native speech playback, native file dialogs, packaging on Windows/Linux, signing/notarization, and patient usability require further validation in their target environments. The native `.app` compiles, but its full UI/device flow was not manually exercised through macOS automation.

## Existing-data compatibility check

Ran the Rust CSV training example against the unchanged `Data/eeg_precision_bci.csv`:

| Measure | Result |
|---|---:|
| Parsed samples | 292,734 |
| Estimated legacy capture rate | 163 Hz |
| Accepted one-second windows | 1,279 |
| REST / SELECT windows | 512 / 767 |
| Included trials | 513 |
| Five-fold balanced accuracy | 87.07% |
| SELECT precision / recall | 89.88% / 89.18% |
| REST false-positive rate | 15.04% |

Confusion matrix: true REST → 435 REST, 77 SELECT; true SELECT → 83 REST, 684 SELECT. Metrics use a 0.5 classification threshold. This confirms legacy parsing and training; it is **not** a benchmark improvement over the original models, a calibrated probability of intent, or evidence of suitability for patient use. The recording was already filtered and its host timestamps only estimate acquisition timing. Legacy models cannot arm live v2 input.

## Remaining product validation

Validate the conversion-ready wire and measured timing on the actual board, gain-specific quality thresholds, isolated electrode acquisition, latency/false activations across days, and caregiver/patient workflows with intended users. The native classifier is one inspectable Rust baseline; the six original architectures and optional Pico Wi-Fi LED experiment remain archived research. Current communication acts only inside the app and speaks locally; no emergency alert is transmitted.
