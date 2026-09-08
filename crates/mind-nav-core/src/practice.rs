use crate::SAMPLE_RATE;
use serde::Serialize;

/// Guided live validation is separate from training and never generates actions.
#[derive(Clone, Default, Serialize)]
pub struct Practice {
    pub running: bool,
    pub samples: usize,
    pub trials: usize,
    pub correct: usize,
    pub skipped: usize,
    pub confusion: [[usize; 2]; 2],
    #[serde(skip)]
    sum: f64,
    #[serde(skip)]
    valid: usize,
}
impl Practice {
    pub fn start(&mut self) {
        *self = Self {
            running: true,
            ..Default::default()
        };
    }
    pub fn label(&self) -> usize {
        (self.samples / (SAMPLE_RATE * 5)) % 2
    }
    pub fn observe(&mut self, probability: Option<f64>, usable: bool, threshold: f64) {
        if !self.running {
            return;
        }
        let label = self.label();
        if self.samples % (SAMPLE_RATE * 5) >= SAMPLE_RATE * 4 && usable {
            if let Some(p) = probability.filter(|p| p.is_finite()) {
                self.sum += p;
                self.valid += 1;
            }
        }
        self.samples += 1;
        if self.samples.is_multiple_of(SAMPLE_RATE * 5) {
            if self.valid < SAMPLE_RATE {
                self.skipped += 1;
            } else {
                let prediction = (self.sum / self.valid as f64 >= threshold) as usize;
                self.confusion[label][prediction] += 1;
                self.trials += 1;
                self.correct += (prediction == label) as usize;
            }
            self.sum = 0.0;
            self.valid = 0;
            if self.samples >= SAMPLE_RATE * 120 {
                self.running = false;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn counts_whole_trials_and_skips_bad_signal() {
        let mut p = Practice::default();
        p.start();
        for _ in 0..1250 {
            p.observe(Some(0.1), true, 0.8);
        }
        for _ in 0..1250 {
            p.observe(Some(0.9), true, 0.8);
        }
        for _ in 0..1250 {
            p.observe(None, false, 0.8);
        }
        assert_eq!(p.trials, 2);
        assert_eq!(p.correct, 2);
        assert_eq!(p.skipped, 1);
        assert_eq!(p.confusion, [[1, 0], [0, 1]]);
    }
}
