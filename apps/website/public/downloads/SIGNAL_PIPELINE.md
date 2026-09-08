# Signal and evaluation contract

`mind-nav-core` contains the acquisition-independent DSP, CSV parser, trainer, practice scorer, and intent gate. The same causal filter and feature extractor serve native recording data and live inference. No Python inference process, notebook runtime, cloud API, or Python model loader is used.

## Filtering and windows

Model configuration stores sample rate, high/low-pass frequencies, notch, source domain, and feature version. The filters are normalized RBJ biquads in transposed direct-form II: Butterworth high/low-pass stages, and Q=30 notch. Initial DC offset subtraction limits startup transients. Nonfinite samples and invalid configurations are rejected.

Native inference uses 500 samples (two seconds), updating around four times/second. Training uses non-overlapping windows, with three seconds of startup settling and a 500 ms transition guard. Labels, explicit trial IDs, and timestamp discontinuities delimit groups. Filtering is causal in both paths and does not use future samples.

Welch PSD uses one-second Hann segments with 50% overlap, DC detrending, and one-sided power/Hz normalization. Bands are 0.5–4, 4–8, 8–13, 13–30, and 30–40 Hz. Version 1 has 20 features: log/relative powers, log RMS, Hjorth mobility/complexity, zero crossings, standardized third/fourth moments, alpha/beta and theta/alpha log ratios, band entropy, and normalized line length.

Quality checks reject nonfinite values, flat input, ADC rail clipping, exceptionally large excursions, and abrupt changes relative to RMS. These are gain-dependent heuristics, not electrode impedance measurements or validated EEG quality scores. Smooth movement artifacts can pass, and useful signals can be rejected. Causal filters introduce latency and cannot perfectly separate artifacts from brain activity.

## Training

The initial native classifier is deterministic class-balanced logistic regression with L2 regularization. It is an inspectable small-data baseline, not a reproduction of all six original model architectures or evidence of superior accuracy.

Five folds assign whole trials chronologically within each class. A trial never appears in both training and validation, and each scaler is fitted only to the training rows. Out-of-fold predictions produce balanced accuracy, select precision/recall, rest false-positive rate, confusion counts, and per-fold scores. After evaluation, the final model is fitted on all eligible data.

These are **within-recording, trial-separated** results, not independent person/day/session tests. Causal filter history may span adjacent trials. Hyperparameters are fixed; scores are not calibrated probabilities of user intent. Report metrics use a 0.5 threshold; runtime defaults to 0.8 plus temporal gating, so their operating points differ.

## Actions and practice

Runtime smooths scores with EMA alpha 0.4, requires three consecutive qualifying predictions, applies a 1.5-second cooldown, and requires return below 0.4 before rearming. Poor-quality windows reset the gate. Source/config changes, gaps, and disconnects disarm BCI input. A held intent produces a single selection edge.

BCI selects within the app’s scanning board; it does not control a wheelchair or inject OS-wide keystrokes. Undo, pause, and a scannable exit remain available. “I need help” speaks on the current device only.

Practice never arms input. Each five-second trial is scored once from the final second’s scores, at the selected threshold. A full second of usable samples is required; otherwise the trial is skipped. Practice data is separate from training. Synthetic results are labeled Demo.

## Legacy import

Signal columns: `raw_mv`, `Signal_Raw`, `Signal_mV`, `eeg_value`. Labels: REST/0 and SELECT/CLICK/1/5; `-1` marks unlabelled data. Imports reject nonfinite values, unknown labels, mixed demo/hardware domains, conflicting declared rates, files over 256 MB, and more than five million samples. Training accepts up to 20,000 windows.

Timing detection prefers native `sample_rate` metadata. Otherwise it estimates the median rate across 200-sample spans from up to 10,000 legacy rows; the rounded rate must be 125–1000 Hz. This estimate is vulnerable to host timestamp batching and clock changes. Explicit nominal 250/256 Hz overrides are available.

Legacy values map through `(value - 500) / 2`, matching the original firmware’s display transform. Earlier filtering cannot be undone. Legacy epochs are one second to accommodate shorter REST trials; that contract is recorded in the dataset summary. These models remain comparison-only and cannot arm live native input. New device/demo models must match their runtime source and filter configuration exactly.

## References

- [W3C Audio EQ Cookbook](https://www.w3.org/TR/audio-eq-cookbook/) — biquad coefficient definitions.
- [Welch, 1967](https://doi.org/10.1109/TAU.1967.1161901) — averaging modified periodograms.
- [scikit-learn common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage) — training-only preprocessing, a conceptual reference without a Python dependency.
- [Texas Instruments ADS1115](https://www.ti.com/product/ADS1115) — supported rates and input limits.
