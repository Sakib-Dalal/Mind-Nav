use crate::{
    dataset::{Dataset, DatasetSummary, Epoch},
    signal::{FilterConfig, FEATURE_COUNT},
    Error, Result, FEATURE_VERSION,
};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Metrics {
    pub balanced_accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub false_positive_rate: f64,
    pub confusion: [[usize; 2]; 2],
    pub folds: usize,
    pub fold_accuracy: Vec<f64>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Model {
    pub id: String,
    pub name: String,
    pub created_at: u64,
    pub feature_version: u32,
    pub config: FilterConfig,
    pub dataset: DatasetSummary,
    pub metrics: Metrics,
    pub mean: [f64; FEATURE_COUNT],
    pub scale: [f64; FEATURE_COUNT],
    pub weights: [f64; FEATURE_COUNT],
    pub bias: f64,
}
impl Model {
    pub fn validate(&self) -> Result<()> {
        self.config.validate()?;
        if self.feature_version != FEATURE_VERSION
            || self
                .mean
                .iter()
                .chain(&self.scale)
                .chain(&self.weights)
                .any(|v| !v.is_finite())
            || !self.bias.is_finite()
            || self.scale.iter().any(|s| *s <= 0.0)
        {
            return Err(Error::Invalid(
                "Model is invalid or uses an unsupported feature version".into(),
            ));
        }
        Ok(())
    }
    pub fn predict(&self, x: &[f64; FEATURE_COUNT]) -> f64 {
        sigmoid(
            self.bias
                + (0..FEATURE_COUNT)
                    .map(|i| {
                        self.weights[i] * ((x[i] - self.mean[i]) / self.scale[i]).clamp(-10.0, 10.0)
                    })
                    .sum::<f64>(),
        )
    }
}
fn sigmoid(x: f64) -> f64 {
    1.0 / (1.0 + (-x.clamp(-40.0, 40.0)).exp())
}

/// Assign whole trials chronologically within each class; no shared trial across folds.
pub fn grouped_folds(epochs: &[Epoch], folds: usize) -> Result<BTreeMap<usize, usize>> {
    if folds < 2 {
        return Err(Error::Invalid("At least two folds required".into()));
    }
    let mut groups: BTreeMap<usize, usize> = BTreeMap::new();
    for e in epochs {
        if e.label > 1 {
            return Err(Error::Invalid("Labels must be binary".into()));
        }
        if groups
            .insert(e.group, e.label)
            .is_some_and(|l| l != e.label)
        {
            return Err(Error::Invalid("A trial contains mixed labels".into()));
        }
    }
    let mut assignment = BTreeMap::new();
    for label in 0..2 {
        let ids: Vec<_> = groups
            .iter()
            .filter(|(_, v)| **v == label)
            .map(|(g, _)| *g)
            .collect();
        if ids.len() < folds {
            return Err(Error::Invalid(format!(
                "Record at least {folds} clean trials of each intent before training"
            )));
        }
        for (i, g) in ids.iter().enumerate() {
            assignment.insert(*g, (i * folds / ids.len()).min(folds - 1));
        }
    }
    Ok(assignment)
}

fn fit(
    rows: &[&Epoch],
) -> (
    [f64; FEATURE_COUNT],
    [f64; FEATURE_COUNT],
    [f64; FEATURE_COUNT],
    f64,
) {
    let n = rows.len() as f64;
    let mean = std::array::from_fn(|i| rows.iter().map(|e| e.x[i]).sum::<f64>() / n);
    let scale = std::array::from_fn(|i| {
        (rows.iter().map(|e| (e.x[i] - mean[i]).powi(2)).sum::<f64>() / n)
            .sqrt()
            .max(1e-6)
    });
    let x: Vec<[f64; FEATURE_COUNT]> = rows
        .iter()
        .map(|e| std::array::from_fn(|i| ((e.x[i] - mean[i]) / scale[i]).clamp(-10.0, 10.0)))
        .collect();
    let counts = [
        rows.iter().filter(|e| e.label == 0).count() as f64,
        rows.iter().filter(|e| e.label == 1).count() as f64,
    ];
    let mut w = [0.0; FEATURE_COUNT];
    let mut bias = 0.0;
    // Balanced, L2-regularized logistic regression; fixed seed-free batch optimization.
    for step in 0..500 {
        let mut grad = [0.0; FEATURE_COUNT];
        let mut gb = 0.0;
        for (e, x) in rows.iter().zip(&x) {
            let p = sigmoid(bias + w.iter().zip(x).map(|(w, x)| w * x).sum::<f64>());
            let error = (p - e.label as f64) * n / (2.0 * counts[e.label]);
            gb += error;
            for j in 0..FEATURE_COUNT {
                grad[j] += error * x[j];
            }
        }
        let rate = 0.08 / (1.0 + step as f64 / 250.0);
        for j in 0..FEATURE_COUNT {
            w[j] -= rate * (grad[j] / n + 0.02 * w[j]);
        }
        bias -= rate * gb / n;
    }
    (mean, scale, w, bias)
}
fn metrics(cm: [[usize; 2]; 2]) -> (f64, f64, f64, f64) {
    let tn = cm[0][0] as f64;
    let fp = cm[0][1] as f64;
    let fn_ = cm[1][0] as f64;
    let tp = cm[1][1] as f64;
    let recall = tp / (tp + fn_).max(1.0);
    let specificity = tn / (tn + fp).max(1.0);
    (
        (recall + specificity) / 2.0,
        tp / (tp + fp).max(1.0),
        recall,
        1.0 - specificity,
    )
}
pub fn train(
    data: &Dataset,
    name: &str,
    id: &str,
    created_at: u64,
    mut progress: impl FnMut(u8),
) -> Result<Model> {
    if name.trim().is_empty() || name.len() > 80 {
        return Err(Error::Invalid("Model name must be 1–80 characters".into()));
    }
    if data.epochs.len() > 20_000 {
        return Err(Error::Invalid(
            "Use at most 20,000 training windows per model".into(),
        ));
    }
    if data.epochs.iter().flat_map(|e| e.x).any(|x| !x.is_finite()) {
        return Err(Error::Invalid("Features must be finite".into()));
    }
    let folds = 5;
    let assignment = grouped_folds(&data.epochs, folds)?;
    let mut cm = [[0; 2]; 2];
    let mut fold_accuracy = Vec::new();
    let empty = Metrics {
        balanced_accuracy: 0.0,
        precision: 0.0,
        recall: 0.0,
        false_positive_rate: 0.0,
        confusion: cm,
        folds,
        fold_accuracy: vec![],
    };
    let mut model = Model {
        id: id.into(),
        name: name.trim().into(),
        created_at,
        feature_version: FEATURE_VERSION,
        config: data.config.clone(),
        dataset: data.summary.clone(),
        metrics: empty,
        mean: [0.0; FEATURE_COUNT],
        scale: [1.0; FEATURE_COUNT],
        weights: [0.0; FEATURE_COUNT],
        bias: 0.0,
    };
    for fold in 0..folds {
        let training: Vec<_> = data
            .epochs
            .iter()
            .filter(|e| assignment[&e.group] != fold)
            .collect();
        let validation: Vec<_> = data
            .epochs
            .iter()
            .filter(|e| assignment[&e.group] == fold)
            .collect();
        let train_groups: BTreeSet<_> = training.iter().map(|e| e.group).collect();
        debug_assert!(validation.iter().all(|e| !train_groups.contains(&e.group)));
        (model.mean, model.scale, model.weights, model.bias) = fit(&training);
        let mut fold_cm = [[0; 2]; 2];
        for e in validation {
            let prediction = (model.predict(&e.x) >= 0.5) as usize;
            cm[e.label][prediction] += 1;
            fold_cm[e.label][prediction] += 1;
        }
        fold_accuracy.push(metrics(fold_cm).0);
        progress(((fold + 1) * 15) as u8);
    }
    let (balanced_accuracy, precision, recall, false_positive_rate) = metrics(cm);
    model.metrics = Metrics {
        balanced_accuracy,
        precision,
        recall,
        false_positive_rate,
        confusion: cm,
        folds,
        fold_accuracy,
    };
    (model.mean, model.scale, model.weights, model.bias) =
        fit(&data.epochs.iter().collect::<Vec<_>>());
    model.validate()?;
    progress(100);
    Ok(model)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn group_split_and_saved_model_round_trip() {
        let epochs: Vec<_> = (0..20)
            .flat_map(|g| {
                (0..3).map(move |_| Epoch {
                    x: [if g % 2 == 0 { -1.0 } else { 1.0 }; FEATURE_COUNT],
                    label: g % 2,
                    group: g,
                })
            })
            .collect();
        let assignments = grouped_folds(&epochs, 5).unwrap();
        assert_eq!(assignments.len(), 20);
        let data = Dataset {
            summary: DatasetSummary {
                samples: 30000,
                windows: 60,
                window_samples: 500,
                rest_windows: 30,
                select_windows: 30,
                trials: 20,
                rejected_windows: 0,
                duration_seconds: 120.0,
                source: "demo".into(),
                name: "test".into(),
            },
            epochs,
            config: FilterConfig::default(),
        };
        let model = train(&data, "Test", "test", 0, |_| {}).unwrap();
        assert!(model.metrics.balanced_accuracy > 0.99);
        let saved = serde_json::to_string(&model).unwrap();
        let restored: Model = serde_json::from_str(&saved).unwrap();
        restored.validate().unwrap();
        assert!(restored.predict(&[1.0; FEATURE_COUNT]) > 0.8);
        assert!(restored.predict(&[-1.0; FEATURE_COUNT]) < 0.2);
    }
    #[test]
    fn refuses_too_few_trials() {
        assert!(grouped_folds(
            &[Epoch {
                x: [0.0; FEATURE_COUNT],
                label: 0,
                group: 0
            }],
            5
        )
        .is_err());
    }
}
