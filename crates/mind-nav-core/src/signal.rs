use rustfft::{num_complex::Complex, FftPlanner};
use serde::{Deserialize, Serialize};
use std::f64::consts::PI;

use crate::{Error, Result, SAMPLE_RATE};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct FilterConfig {
    pub sample_rate: usize,
    pub high_pass: f64,
    pub low_pass: f64,
    /// 0 = disabled, otherwise 50 or 60 Hz.
    pub notch: u16,
}
impl Default for FilterConfig {
    fn default() -> Self {
        Self {
            sample_rate: SAMPLE_RATE,
            high_pass: 0.5,
            low_pass: 40.0,
            notch: 50,
        }
    }
}
impl FilterConfig {
    pub fn validate(&self) -> Result<()> {
        if !(125..=1000).contains(&self.sample_rate)
            || !self.high_pass.is_finite()
            || !self.low_pass.is_finite()
            || self.high_pass < 0.1
            || self.high_pass >= self.low_pass
            || self.low_pass >= self.sample_rate as f64 / 2.0
            || ![0, 50, 60].contains(&self.notch)
            || self.notch as f64 >= self.sample_rate as f64 / 2.0
        {
            return Err(Error::Invalid("Invalid filter configuration".into()));
        }
        Ok(())
    }
}

/// Transposed direct-form II RBJ biquad. All filters are causal in both paths.
struct Biquad {
    b: [f64; 3],
    a: [f64; 2],
    z: [f64; 2],
}
impl Biquad {
    fn new(hz: f64, fs: f64, kind: u8) -> Self {
        let w = 2.0 * PI * hz / fs;
        let q = if kind == 2 {
            30.0
        } else {
            std::f64::consts::FRAC_1_SQRT_2
        };
        let alpha = w.sin() / (2.0 * q);
        let c = w.cos();
        let b = match kind {
            0 => [(1.0 - c) / 2.0, 1.0 - c, (1.0 - c) / 2.0],
            1 => [(1.0 + c) / 2.0, -(1.0 + c), (1.0 + c) / 2.0],
            _ => [1.0, -2.0 * c, 1.0],
        };
        let a0 = 1.0 + alpha;
        Self {
            b: b.map(|v| v / a0),
            a: [-2.0 * c / a0, (1.0 - alpha) / a0],
            z: [0.0; 2],
        }
    }
    fn next(&mut self, x: f64) -> f64 {
        let y = self.b[0] * x + self.z[0];
        self.z[0] = self.b[1] * x - self.a[0] * y + self.z[1];
        self.z[1] = self.b[2] * x - self.a[1] * y;
        y
    }
}

pub struct Pipeline {
    filters: Vec<Biquad>,
    baseline: Option<f64>,
    pub count: usize,
}
impl Pipeline {
    pub fn new(config: &FilterConfig) -> Result<Self> {
        config.validate()?;
        let fs = config.sample_rate as f64;
        let mut filters = vec![Biquad::new(config.high_pass, fs, 1)];
        if config.notch != 0 {
            filters.push(Biquad::new(config.notch as f64, fs, 2));
        }
        filters.push(Biquad::new(config.low_pass, fs, 0));
        Ok(Self {
            filters,
            baseline: None,
            count: 0,
        })
    }
    pub fn next(&mut self, x: f64) -> Option<f64> {
        if !x.is_finite() {
            return None;
        }
        // Initial DC offset subtraction avoids a rail-sized start-up transient.
        let mut y = x - *self.baseline.get_or_insert(x);
        for f in &mut self.filters {
            y = f.next(y);
        }
        self.count += 1;
        y.is_finite().then_some(y)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, Default)]
pub struct Quality {
    pub usable: bool,
    pub score: u8,
    pub reason: String,
    pub rms: f64,
    pub peak_to_peak: f64,
}
pub fn quality(raw: &[f64], filtered: &[f64], check_rails: bool) -> Quality {
    if filtered.len() < 64
        || raw.len() != filtered.len()
        || raw.iter().chain(filtered).any(|x| !x.is_finite())
    {
        return Quality {
            reason: "Waiting for signal".into(),
            ..Default::default()
        };
    }
    let mean = filtered.iter().sum::<f64>() / filtered.len() as f64;
    let rms =
        (filtered.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / filtered.len() as f64).sqrt();
    let lo = filtered.iter().copied().fold(f64::INFINITY, f64::min);
    let hi = filtered.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let flat = raw
        .windows(2)
        .filter(|v| (v[1] - v[0]).abs() < 1e-8)
        .count() as f64
        / (raw.len() - 1) as f64;
    let clipped =
        check_rails && raw.iter().filter(|v| **v < 1.0 || **v > 4999.0).count() > raw.len() / 100;
    let spike = filtered
        .windows(2)
        .any(|v| (v[1] - v[0]).abs() > rms.max(0.1) * 8.0);
    let reason = if clipped {
        "ADC clipping — check gain and connection"
    } else if flat > 0.95 || rms < 0.02 {
        "Flat signal — check electrodes"
    } else if spike || hi - lo > 1200.0 {
        "Artifact detected — selections paused"
    } else {
        "Signal ready"
    };
    let usable = reason == "Signal ready";
    Quality {
        usable,
        score: if usable { 96 } else { 25 },
        reason: reason.into(),
        rms,
        peak_to_peak: hi - lo,
    }
}

pub const FEATURE_COUNT: usize = 20;

/// Welch PSD, one-second Hann segments, 50% overlap, normalized to power/Hz.
pub fn band_powers(x: &[f64], fs: usize) -> [f64; 5] {
    let n = fs.min(x.len());
    if n < 8 {
        return [0.0; 5];
    }
    let hann: Vec<_> = (0..n)
        .map(|i| 0.5 - 0.5 * (2.0 * PI * i as f64 / (n - 1) as f64).cos())
        .collect();
    let norm = hann.iter().map(|v| v * v).sum::<f64>() * fs as f64;
    let fft = FftPlanner::new().plan_fft_forward(n);
    let mut powers = vec![0.0; n / 2 + 1];
    let mut count = 0;
    for start in (0..=x.len() - n).step_by(n / 2) {
        let mean = x[start..start + n].iter().sum::<f64>() / n as f64;
        let mut buf: Vec<_> = (0..n)
            .map(|i| Complex::new((x[start + i] - mean) * hann[i], 0.0))
            .collect();
        fft.process(&mut buf);
        for (i, p) in powers.iter_mut().enumerate() {
            let scale = if i == 0 || (n.is_multiple_of(2) && i == n / 2) {
                1.0
            } else {
                2.0
            };
            *p += buf[i].norm_sqr() * scale / norm;
        }
        count += 1;
    }
    let bands = [
        (0.5, 4.0),
        (4.0, 8.0),
        (8.0, 13.0),
        (13.0, 30.0),
        (30.0, 40.01),
    ];
    bands.map(|(lo, hi)| {
        powers
            .iter()
            .enumerate()
            .filter_map(|(i, p)| {
                let hz = i as f64 * fs as f64 / n as f64;
                (hz >= lo && hz < hi).then_some(p / count as f64 * fs as f64 / n as f64)
            })
            .sum()
    })
}

pub fn features(x: &[f64], fs: usize) -> [f64; FEATURE_COUNT] {
    let n = x.len().max(1) as f64;
    let mean = x.iter().sum::<f64>() / n;
    let variance = x.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / n;
    let rms = variance.sqrt().max(1e-9);
    let d: Vec<_> = x.windows(2).map(|v| v[1] - v[0]).collect();
    let dd: Vec<_> = d.windows(2).map(|v| v[1] - v[0]).collect();
    let energy = |v: &[f64]| v.iter().map(|v| v * v).sum::<f64>() / v.len().max(1) as f64;
    let mob = (energy(&d) / variance.max(1e-9)).sqrt();
    let comp = (energy(&dd) / energy(&d).max(1e-9)).sqrt() / mob.max(1e-9);
    let bands = band_powers(x, fs);
    let total = bands.iter().sum::<f64>().max(1e-12);
    let mut f = [0.0; FEATURE_COUNT];
    for i in 0..5 {
        f[i] = (bands[i] + 1e-12).ln();
        f[5 + i] = bands[i] / total;
    }
    f[10] = rms.ln();
    f[11] = mob;
    f[12] = comp;
    f[13] = x
        .windows(2)
        .filter(|v| (v[0] - mean) * (v[1] - mean) < 0.0)
        .count() as f64
        / n;
    f[14] = x.iter().map(|v| ((v - mean) / rms).powi(3)).sum::<f64>() / n;
    f[15] = x.iter().map(|v| ((v - mean) / rms).powi(4)).sum::<f64>() / n;
    f[16] = ((bands[2] + 1e-12) / (bands[3] + 1e-12)).ln();
    f[17] = ((bands[1] + 1e-12) / (bands[2] + 1e-12)).ln();
    f[18] = -bands
        .iter()
        .map(|b| {
            let p = b / total;
            p * (p + 1e-12).ln()
        })
        .sum::<f64>();
    f[19] = d.iter().map(|v| v.abs()).sum::<f64>() / (n * rms);
    f.map(|v| if v.is_finite() { v } else { 0.0 })
}

/// Debounced select edge. Requires a return to REST before another selection.
#[derive(Default)]
pub struct IntentGate {
    streak: u8,
    armed: bool,
    last_ms: u64,
    smooth: f64,
    initialized: bool,
}
impl IntentGate {
    pub fn reset(&mut self) {
        *self = Self::default();
    }
    pub fn update(&mut self, probability: f64, usable: bool, threshold: f64, now_ms: u64) -> bool {
        if !usable || !probability.is_finite() {
            self.reset();
            return false;
        }
        self.smooth = if self.initialized {
            0.4 * probability + 0.6 * self.smooth
        } else {
            self.initialized = true;
            probability
        };
        if self.smooth < 0.4 {
            self.armed = true;
            self.streak = 0;
        }
        if self.smooth >= threshold {
            self.streak = self.streak.saturating_add(1);
        } else {
            self.streak = 0;
        }
        if self.armed && self.streak >= 3 && now_ms.saturating_sub(self.last_ms) >= 1500 {
            self.armed = false;
            self.last_ms = now_ms;
            self.streak = 0;
            return true;
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn sine(hz: f64, n: usize) -> Vec<f64> {
        (0..n)
            .map(|i| (2.0 * PI * hz * i as f64 / 250.0).sin())
            .collect()
    }
    #[test]
    fn filters_reject_line_noise_and_preserve_alpha() {
        let amplitude = |hz| {
            let mut p = Pipeline::new(&FilterConfig::default()).unwrap();
            let y: Vec<_> = sine(hz, 5000)
                .into_iter()
                .filter_map(|x| p.next(x))
                .skip(2500)
                .collect();
            (y.iter().map(|x| x * x).sum::<f64>() / y.len() as f64).sqrt()
        };
        assert!(amplitude(10.0) > 0.65);
        assert!(amplitude(50.0) < 0.02);
        assert!(amplitude(0.1) < 0.05);
    }
    #[test]
    fn welch_finds_alpha() {
        let b = band_powers(&sine(10.0, 500), 250);
        assert!(b[2] > 0.49 && b[2] < 0.51);
        assert!(b[3] < 0.001);
    }
    #[test]
    fn flat_and_nonfinite_signals_are_rejected() {
        assert!(!quality(&[0.0; 500], &[0.0; 500], false).usable);
        assert!(features(&[0.0; 500], 250).iter().all(|x| x.is_finite()));
        let mut p = Pipeline::new(&FilterConfig::default()).unwrap();
        assert!(p.next(f64::NAN).is_none());
    }
    #[test]
    fn gate_requires_rest_and_never_repeats_held_intent() {
        let mut g = IntentGate::default();
        let mut clicks = 0;
        g.update(0.0, true, 0.8, 0);
        for i in 1..50 {
            clicks += g.update(0.99, true, 0.8, i * 250) as usize;
        }
        assert_eq!(clicks, 1);
        assert!(!g.update(1.0, false, 0.8, 20000));
    }
    #[test]
    fn high_input_at_start_does_not_count_as_a_return_to_rest() {
        let mut gate = IntentGate::default();
        for i in 0..50 {
            assert!(!gate.update(0.99, true, 0.8, i * 250));
        }
    }
}
