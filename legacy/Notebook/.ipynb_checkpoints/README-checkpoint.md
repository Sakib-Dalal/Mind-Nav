# 🧠 Brain-Computer Interface (BCI) — EEG Click Detection Notebook

A complete machine-learning and deep-learning pipeline for classifying EEG brain signals into two intent classes: **REST** and **CLICK**. The notebook progresses from raw signal loading all the way through four trained models and saved artefacts ready for deployment.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Dependencies & Setup](#dependencies--setup)
3. [Step 1 — Load & Preview EEG Data](#step-1--load--preview-eeg-data)
4. [Step 2 — Signal Normalisation & Dataset Summary](#step-2--signal-normalisation--dataset-summary)
5. [Step 3 — EEG Signal Visualisation](#step-3--eeg-signal-visualisation)
6. [Step 4 — Trial Segmentation](#step-4--trial-segmentation)
7. [Step 5 — Feature Engineering (42 Features per Trial)](#step-5--feature-engineering-42-features-per-trial)
8. [Step 6 — Band Power Distribution Visualisation](#step-6--band-power-distribution-visualisation)
9. [Step 7 — Sklearn Ensemble Model (ET + RF)](#step-7--sklearn-ensemble-model-et--rf)
10. [Step 8 — Model Evaluation & Confusion Matrix](#step-8--model-evaluation--confusion-matrix)
11. [Step 9 — Save & Load Sklearn Model](#step-9--save--load-sklearn-model)
12. [Step 10 — PyTorch Deep Learning Models](#step-10--pytorch-deep-learning-models)
13. [Step 11 — Feedforward Neural Network (FNN)](#step-11--feedforward-neural-network-fnn)
14. [Step 12 — Convolutional Neural Network (CNN)](#step-12--convolutional-neural-network-cnn)
15. [Step 13 — Hybrid CNN + FNN Model](#step-13--hybrid-cnn--fnn-model)
16. [Step 14 — Model Comparison](#step-14--model-comparison)
17. [Step 15 — Save & Load PyTorch Models](#step-15--save--load-pytorch-models)
18. [Output Files](#output-files)

---

## Project Overview

| Property | Value |
|---|---|
| Task | Binary EEG Classification |
| Classes | `REST` (label 0) · `CLICK` (label 5) |
| Sampling Rate | 256 Hz |
| Dataset | `eeg_precision_bci.csv` |
| Total Samples (after trim) | 72 589 (~283.6 seconds) |
| Frameworks | scikit-learn · PyTorch |

---

## Dependencies & Setup

The notebook installs all required packages at the top:

```
scikit-learn · pandas · numpy · matplotlib · scipy · torch · torchvision · joblib
```

Global constants are defined once and reused throughout:

- `FS = 256` — EEG sampling frequency in Hz
- `CLASS_NAMES = {0: 'REST', 5: 'CLICK'}` — human-readable label map
- `COLORS` — consistent colour scheme for all plots

---

## Step 1 — Load & Preview EEG Data

The raw CSV file `eeg_precision_bci.csv` is loaded with pandas. Each row represents a single EEG sample and contains four columns:

| Column | Description |
|---|---|
| `Timestamp_Unix` | Unix epoch timestamp |
| `Signal_mV` | Raw EEG amplitude in millivolts |
| `Intent_Label` | String label (`REST` or `CLICK`) |
| `Label_Class` | Numeric label (`0` or `5`) |

The first 500 rows (≈ 2 seconds) are dropped to remove initialisation artefacts before any analysis begins.

---

## Step 2 — Signal Normalisation & Dataset Summary

The raw signal is **zero-centred** by subtracting the 500 mV baseline offset, producing a signal that oscillates around 0 mV. A quick summary is then printed:

- Total number of samples and recording duration
- Per-class sample counts to check for class imbalance (REST: 28 658 · CLICK: 43 931)

---

## Step 3 — EEG Signal Visualisation

The first 30 seconds of the zero-centred EEG signal are plotted in a two-panel figure:

- **Top panel** — raw EEG waveform with coloured shading for each class segment (green = REST, blue = CLICK)
- **Bottom panel** — label track showing the ground-truth class at every time step

This gives an immediate visual check that the labelling aligns with the signal dynamics.

---

## Step 4 — Trial Segmentation

The continuous signal is split into **discrete trials** by detecting every label transition point. Each contiguous run of the same label becomes one trial. The resulting `segments` list stores, for each trial:

- start and end sample indices
- the slice of the EEG signal
- the majority class label

This segmented structure is the foundation for all downstream feature extraction and modelling.

---

## Step 5 — Feature Engineering (42 Features per Trial)

`scipy` is used to extract a rich set of **42 hand-crafted features** per trial, divided into three groups:

**Time-domain (per segment)**
- Mean, standard deviation, variance, peak-to-peak range
- Root mean square (RMS)
- Skewness and kurtosis (signal shape descriptors)
- Zero-crossing rate and mean absolute value

**Frequency-domain (via Welch PSD)**
- Absolute and relative band power for five EEG bands: Delta (0.5–4 Hz), Theta (4–8 Hz), Alpha (8–13 Hz), Beta (13–30 Hz), Gamma (30–100 Hz)
- Spectral entropy
- Peak frequency and spectral centroid

**Cross-band ratios**
- Alpha/Beta, Theta/Alpha, and other clinically motivated power ratios

The final feature matrix `X` has shape `(n_trials, 42)` and the label vector `y` contains the corresponding class for each trial.

---

## Step 6 — Band Power Distribution Visualisation

Five side-by-side violin/box plots display how the power in each EEG frequency band is distributed for REST vs CLICK trials. This provides intuitive evidence of which frequency bands are most discriminative between the two mental states.

---

## Step 7 — Sklearn Ensemble Model (ET + RF)

**Preprocessing:** The feature matrix `X` is standardised with `StandardScaler` (zero mean, unit variance) to produce `X_scaled`.

**Model architecture:** A soft-voting `VotingClassifier` combining two tree-based models:
- `ExtraTreesClassifier` — 500 trees, balanced class weights
- `RandomForestClassifier` — 500 trees, balanced class weights

Soft voting averages the predicted class probabilities from both classifiers before making a final decision, which is more robust than hard majority voting.

**Evaluation:** 5-fold Stratified Cross-Validation with `StratifiedKFold` is used to obtain unbiased accuracy estimates while preserving the class ratio in every fold.

---

## Step 8 — Model Evaluation & Confusion Matrix

Cross-validated predictions are generated for every sample and used to produce:

- **Classification report** — per-class precision, recall, F1-score and support
- **Confusion matrix heatmap** — a 2×2 grid (REST/CLICK × REST/CLICK) showing true vs predicted counts, rendered on a dark background for clarity

---

## Step 9 — Save & Load Sklearn Model

The fitted ensemble and scaler are persisted to disk using `joblib`:

- `BCI_MODEL.joblib` — the full `VotingClassifier` trained on all data
- `BCI_SCALER.joblib` — the `StandardScaler` fit on the training features

A loading cell demonstrates that the saved model can be correctly reloaded and is ready for inference.

---

## Step 10 — PyTorch Deep Learning Models

Three deep learning architectures are implemented in PyTorch to explore different ways of consuming the EEG data:

| Model | Input | Approach |
|---|---|---|
| FNN | 42 engineered features | Learns from hand-crafted domain features |
| CNN | Raw EEG window (256 samples) | Learns temporal patterns directly from the signal |
| Hybrid CNN + FNN | Raw window + 42 features | Dual-branch fusion of both representations |

**Shared setup:**
- Labels are remapped from `{0, 5}` to `{0, 1}` for binary PyTorch classification
- Raw EEG windows (`X_raw`) are fixed-length segments of `WIN_LEN` samples
- Device detection: models run on GPU if available, otherwise CPU
- All models are trained with `Adam` optimiser, `CrossEntropyLoss`, and a `CosineAnnealingLR` learning-rate scheduler

A generic `train_epoch` / cross-validation helper is defined once and reused across all three architectures.

---

## Step 11 — Feedforward Neural Network (FNN)

**Input:** 42 standardised engineered features per trial.

**Architecture (`BCIFNN`):**
```
Linear(42 → 128) → BatchNorm → ReLU → Dropout(0.4)
Linear(128 → 64)  → BatchNorm → ReLU → Dropout(0.4)
Linear(64 → 32)   → BatchNorm → ReLU → Dropout(0.4)
Linear(32 → 2)    → (logits)
```

The model is evaluated with 5-fold stratified CV. Per-fold accuracy, a classification report, confusion matrix, and training loss curves are plotted via the shared `plot_results` helper.

---

## Step 12 — Convolutional Neural Network (CNN)

**Input:** Raw EEG window of 256 samples treated as a 1-D temporal signal.

**Architecture (`BCICNN`):**
Three `BCIConvBlock` modules (each containing `Conv1d → BatchNorm → ReLU → MaxPool → Dropout`) progressively extract temporal features with increasing channel depth. A **global average pooling** layer collapses the temporal dimension, followed by a linear classifier head outputting 2 logits.

This architecture requires no manual feature engineering — it discovers discriminative patterns in the raw waveform automatically. The same 5-fold CV and plotting procedure is applied.

---

## Step 13 — Hybrid CNN + FNN Model

**Input:** Both the raw EEG window and the 42 engineered features simultaneously.

**Architecture (`BCIHybrid`):**
- **CNN branch** — processes the raw window and outputs a 128-d temporal embedding
- **FNN branch** — processes the 42 features and outputs a 64-d feature embedding
- **Fusion** — the two embeddings are concatenated (192-d) and passed through a final MLP (`192 → 64 → 2`) to produce class logits

By combining learned temporal representations with expert domain features, the hybrid model aims to capture complementary information that neither branch alone can access. The same 5-fold CV and plotting procedure is applied.

---

## Step 14 — Model Comparison

A bar chart summarises the 5-fold cross-validated accuracy (mean ± std) for all four models side by side:

- ET + RF Ensemble (sklearn)
- FNN (PyTorch)
- CNN (PyTorch)
- Hybrid CNN + FNN (PyTorch)

This allows a direct comparison of classical ML against deep learning approaches on the same EEG dataset.

---

## Step 15 — Save & Load PyTorch Models

All three PyTorch models are **retrained on the full dataset** (no held-out fold) for maximum generalisation, then saved:

| File | Contents |
|---|---|
| `BCI_FNN.pt` | FNN state dict |
| `BCI_CNN.pt` | CNN state dict |
| `BCI_Hybrid.pt` | Hybrid CNN+FNN state dict |

A loading demo reloads all three models and runs a forward pass on the first sample, printing each model's prediction alongside the ground truth.

---

## Output Files

| File | Description |
|---|---|
| `BCI_MODEL.joblib` | Sklearn ET+RF ensemble (fitted on all data) |
| `BCI_SCALER.joblib` | StandardScaler for the 42-feature matrix |
| `BCI_FNN.pt` | PyTorch FNN weights |
| `BCI_CNN.pt` | PyTorch CNN weights |
| `BCI_Hybrid.pt` | PyTorch Hybrid CNN+FNN weights |

To perform inference on new EEG data, load the scaler and the desired model file, extract the same 42 features (or raw window), and pass them through the corresponding network.