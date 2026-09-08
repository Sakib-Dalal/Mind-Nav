"""
Mind-Nav — Feature Extraction
══════════════════════════════
42-feature extraction pipeline for single-channel EEG epochs.
Identical to the training notebook feature set.
"""

import numpy as np
from scipy.stats import skew, kurtosis
from scipy.signal import welch
from scipy.integrate import trapezoid

from config import FS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _band_power(f, pxx, lo, hi):
    """Absolute power in frequency band [lo, hi] Hz via trapezoidal rule."""
    idx = (f >= lo) & (f <= hi)
    return float(trapezoid(pxx[idx], f[idx])) if idx.sum() > 0 else 0.0


def _spectral_entropy(pxx):
    """Shannon entropy of the normalised PSD."""
    p = pxx / (pxx.sum() + 1e-10)
    return float(-np.sum(p * np.log2(p + 1e-10)))


def _hjorth(x):
    """Hjorth parameters: Activity, Mobility, Complexity."""
    d1 = np.diff(x)
    d2 = np.diff(d1)
    act = float(np.var(x))
    mob = float(np.sqrt(np.var(d1) / (act + 1e-10)))
    comp = float(np.sqrt(np.var(d2) / (np.var(d1) + 1e-10)) / (mob + 1e-10))
    return act, mob, comp


# ── Main extractor ────────────────────────────────────────────────────────────

def extract_features(ep: np.ndarray) -> np.ndarray:
    """
    Extract 42 features from a 1-D EEG epoch.

    Returns a 1-D float32 array of length 42.
    """
    ep = ep.astype(np.float64)
    nperseg = min(128, len(ep))
    d1 = np.diff(ep)
    half = len(ep) // 2

    # ── Time-domain (18 features) ─────────────────────────────────────────
    td = [
        float(np.mean(ep)), float(np.std(ep)), float(np.var(ep)),
        float(skew(ep)), float(kurtosis(ep)),
        float(np.sqrt(np.mean(ep ** 2))),
        float(np.max(ep) - np.min(ep)),
        float(np.mean(np.abs(ep))),
        float(np.sum(np.diff(np.sign(ep)) != 0)),
        float(np.percentile(ep, 10)), float(np.percentile(ep, 25)),
        float(np.percentile(ep, 75)), float(np.percentile(ep, 90)),
        float(np.sum(np.abs(d1))),
        float(np.mean(ep[:half])), float(np.mean(ep[half:])),
        float(np.std(ep[:half])), float(np.std(ep[half:])),
    ]

    # ── Hjorth (3 features) ───────────────────────────────────────────────
    act, mob, comp = _hjorth(ep)

    # ── Autocorrelation (5 features) ──────────────────────────────────────
    ac = np.correlate(ep, ep, mode='full')
    ac = ac[len(ac) // 2:]
    ac = ac / (ac[0] + 1e-10)
    autocorr = [float(ac[lag]) if lag < len(ac) else 0.0
                for lag in [1, 2, 5, 10, 20]]

    # ── Frequency-domain (16 features) ────────────────────────────────────
    f, pxx = welch(ep, fs=FS, nperseg=nperseg)
    pxx = np.maximum(pxx, 1e-12)
    d_ = _band_power(f, pxx, 2, 4)
    t_ = _band_power(f, pxx, 4, 8)
    a_ = _band_power(f, pxx, 8, 13)
    b_ = _band_power(f, pxx, 13, 30)
    g_ = _band_power(f, pxx, 30, 45)
    tot = _band_power(f, pxx, 1, 50)

    fd = [
        d_, t_, a_, b_, g_, tot,
        d_ / (tot + 1e-10), t_ / (tot + 1e-10),
        a_ / (tot + 1e-10), b_ / (tot + 1e-10),
        a_ / (b_ + 1e-10), t_ / (a_ + 1e-10),
        (a_ + b_) / (d_ + t_ + 1e-10),
        _spectral_entropy(pxx),
        float(f[np.argmax(pxx)]),
        float(np.sum(pxx * f) / (np.sum(pxx) + 1e-10)),
    ]

    return np.array(td + [act, mob, comp] + autocorr + fd, dtype=np.float32)
