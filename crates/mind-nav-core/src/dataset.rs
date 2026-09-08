use crate::{
    signal::{features, quality, FilterConfig, Pipeline, FEATURE_COUNT},
    Error, Result,
};
use serde::{Deserialize, Serialize};
use std::{io::Read, path::Path};

#[derive(Clone, Debug)]
pub struct Epoch {
    pub x: [f64; FEATURE_COUNT],
    pub label: usize,
    pub group: usize,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DatasetSummary {
    pub samples: usize,
    pub windows: usize,
    #[serde(default)]
    pub window_samples: usize,
    pub rest_windows: usize,
    pub select_windows: usize,
    pub trials: usize,
    pub rejected_windows: usize,
    pub duration_seconds: f64,
    pub source: String,
    pub name: String,
}
#[derive(Clone)]
pub struct Dataset {
    pub epochs: Vec<Epoch>,
    pub summary: DatasetSummary,
    pub config: FilterConfig,
}

pub fn read_file(path: &Path, config: FilterConfig) -> Result<Dataset> {
    if std::fs::metadata(path)?.len() > 256 * 1024 * 1024 {
        return Err(Error::Invalid("CSV exceeds the 256 MB import limit".into()));
    }
    read_csv(
        std::fs::File::open(path)?,
        path.file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .as_ref(),
        config,
    )
}

/// Prefer native metadata; otherwise robustly estimate legacy host timestamp spacing.
/// This is an estimate of the old capture clock, not a calibration of the ADC.
pub fn detect_sample_rate(path: &Path) -> Result<usize> {
    if std::fs::metadata(path)?.len() > 256 * 1024 * 1024 {
        return Err(Error::Invalid("CSV exceeds the 256 MB import limit".into()));
    }
    let mut reader = csv::Reader::from_path(path)?;
    let headers = reader.headers()?.clone();
    let declared = headers.iter().position(|h| h == "sample_rate");
    let time = headers
        .iter()
        .position(|h| ["timestamp", "Timestamp_Unix"].contains(&h));
    let mut anchor: Option<(usize, f64)> = None;
    let mut rates = Vec::new();
    for (index, row) in reader.records().take(10_000).enumerate() {
        let row = row?;
        if let Some(rate) = declared
            .and_then(|i| row.get(i))
            .and_then(|s| s.parse::<usize>().ok())
        {
            if (125..=1000).contains(&rate) {
                return Ok(rate);
            }
        }
        if let Some(t) = time
            .and_then(|i| row.get(i))
            .and_then(|s| s.parse::<f64>().ok())
            .filter(|t| t.is_finite())
        {
            // Multi-sample spans reduce distortion from USB bursts/host scheduling.
            if index < 500 {
                continue;
            }
            if let Some((start, prev)) = anchor {
                if index - start >= 200 {
                    let delta = t - prev;
                    if delta > 0.0 {
                        let rate = (index - start) as f64 / delta;
                        if (50.0..=2000.0).contains(&rate) {
                            rates.push(rate);
                        }
                    }
                    anchor = Some((index, t));
                }
            } else {
                anchor = Some((index, t));
            }
        }
    }
    if rates.len() < 3 {
        return Err(Error::Invalid(
            "Cannot estimate timing. Choose the recording's known sample rate.".into(),
        ));
    }
    rates.sort_by(f64::total_cmp);
    let rate = rates[rates.len() / 2].round() as usize;
    if !(125..=1000).contains(&rate) {
        return Err(Error::Invalid(format!(
            "Estimated rate {rate} Hz is outside the supported 125–1000 Hz range"
        )));
    }
    Ok(rate)
}

pub fn read_csv(reader: impl Read, name: &str, config: FilterConfig) -> Result<Dataset> {
    config.validate()?;
    let mut csv = csv::Reader::from_reader(reader);
    let headers = csv.headers()?.clone();
    let col = |names: &[&str]| headers.iter().position(|h| names.contains(&h));
    let value_col = col(&["raw_mv", "Signal_Raw", "Signal_mV", "eeg_value"])
        .ok_or_else(|| Error::Invalid("CSV needs raw_mv or legacy Signal_Raw column".into()))?;
    let label_col = col(&["label", "Label_Class", "Intent_Label"])
        .ok_or_else(|| Error::Invalid("CSV needs a label column".into()))?;
    let time_col = col(&["timestamp", "Timestamp_Unix"]);
    let trial_col = col(&["trial_id"]);
    let source_col = col(&["source"]);
    let fs_col = col(&["sample_rate"]);
    let legacy = headers.get(value_col) != Some("raw_mv");
    let mut pipeline = Pipeline::new(&config)?;
    let mut samples = 0;
    let mut epochs = Vec::new();
    let mut raw = Vec::new();
    let mut filtered = Vec::new();
    let mut last_label = None;
    let mut last_trial = String::new();
    let mut last_time = None;
    let mut group = 0;
    let mut in_trial = 0;
    let mut rejected = 0;
    let mut source = if legacy {
        "legacy".to_string()
    } else {
        String::new()
    };
    // V1 REST trials are shorter than two seconds at their nominal rate.
    // Their comparison-only path uses one-second epochs; native inference stays at two.
    let win = config.sample_rate * if legacy { 1 } else { 2 };
    for (row, result) in csv.records().enumerate() {
        let record = result?;
        let err = |message: &str| Error::Invalid(format!("CSV row {}: {message}", row + 2));
        if samples >= 5_000_000 {
            return Err(err("maximum 5 million samples"));
        }
        let mut x: f64 = record
            .get(value_col)
            .unwrap_or("")
            .parse()
            .map_err(|_| err("invalid signal value"))?;
        if !x.is_finite() {
            return Err(err("signal must be finite"));
        }
        if legacy {
            x = (x - 500.0) / 2.0;
        }
        if let Some(i) = fs_col {
            if record.get(i).and_then(|v| v.parse::<usize>().ok()) != Some(config.sample_rate) {
                return Err(err("sample rate differs from the selected rate"));
            }
        }
        if !legacy {
            let domain = source_col.and_then(|i| record.get(i)).unwrap_or("hardware");
            if !["demo", "hardware"].contains(&domain) {
                return Err(err("source must be demo or hardware"));
            }
            if source.is_empty() {
                source = domain.into();
            }
            if source != domain {
                return Err(err("demo and hardware samples cannot be mixed"));
            }
        }
        let label_text = record.get(label_col).unwrap_or("").trim();
        let label = match label_text {
            "0" | "REST" => Some(0),
            "1" | "5" | "CLICK" | "SELECT" => Some(1),
            "" | "-1" | "WARMUP" | "PAUSED" => None,
            _ => {
                return Err(err(
                    "label must be REST/0, SELECT/CLICK/1/5, or -1 for unlabelled",
                ))
            }
        };
        let time = if let Some(i) = time_col {
            let t: f64 = record
                .get(i)
                .unwrap_or("")
                .parse()
                .map_err(|_| err("invalid timestamp"))?;
            if !t.is_finite() {
                return Err(err("timestamp must be finite"));
            }
            Some(t)
        } else {
            None
        };
        let gap = time
            .zip(last_time)
            .is_some_and(|(t, prev)| t <= prev || t - prev > 0.1);
        let trial = trial_col.and_then(|i| record.get(i)).unwrap_or("");
        if label != last_label || gap || trial != last_trial {
            group += 1;
            in_trial = 0;
            raw.clear();
            filtered.clear();
        }
        if gap {
            pipeline = Pipeline::new(&config)?;
        }
        last_label = label;
        last_trial = trial.to_string();
        last_time = time;
        let y = pipeline.next(x).ok_or_else(|| err("filter failed"))?;
        samples += 1;
        in_trial += 1;
        // Warm-up after connection/gaps and a 500 ms transition guard per trial.
        if pipeline.count <= config.sample_rate * 3
            || in_trial <= config.sample_rate / 2
            || label.is_none()
        {
            continue;
        }
        raw.push(x);
        filtered.push(y);
        if raw.len() == win {
            if quality(&raw, &filtered, !legacy && source == "hardware").usable {
                epochs.push(Epoch {
                    x: features(&filtered, config.sample_rate),
                    label: label.unwrap(),
                    group,
                });
            } else {
                rejected += 1;
            }
            raw.clear();
            filtered.clear(); // Non-overlapping windows; groups never cross folds.
        }
    }
    let rest = epochs.iter().filter(|e| e.label == 0).count();
    let trials = epochs
        .iter()
        .map(|e| e.group)
        .collect::<std::collections::BTreeSet<_>>()
        .len();
    let summary = DatasetSummary {
        samples,
        windows: epochs.len(),
        window_samples: win,
        rest_windows: rest,
        select_windows: epochs.len() - rest,
        trials,
        rejected_windows: rejected,
        duration_seconds: samples as f64 / config.sample_rate as f64,
        source,
        name: name.into(),
    };
    Ok(Dataset {
        epochs,
        summary,
        config,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn estimates_legacy_clock_and_keeps_short_rest_trials() {
        let path = std::env::temp_dir().join(format!(
            "mindnav-legacy-{}.csv",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let mut csv = String::from("Timestamp_Unix,Signal_Raw,Label_Class\n");
        for i in 0..6400 {
            let t = i as f64 / 163.0 + if i % 2 == 0 { 0.0003 } else { -0.0003 };
            let x = 500.0 + 20.0 * (std::f64::consts::TAU * 10.0 * t).sin();
            csv.push_str(&format!("{t:.6},{x:.6},{}\n", (i / 300) % 2));
        }
        std::fs::write(&path, csv).unwrap();
        assert_eq!(detect_sample_rate(&path).unwrap(), 163);
        let data = read_file(
            &path,
            FilterConfig {
                sample_rate: 163,
                ..Default::default()
            },
        )
        .unwrap();
        assert_eq!(data.summary.window_samples, 163);
        assert!(data.summary.rest_windows >= 5 && data.summary.select_windows >= 5);
        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn recognizes_old_labels_without_loading_python() {
        let data = "Timestamp_Unix,Signal_Raw,Label_Class\n1,500,0\n1.004,501,5\n";
        let d = read_csv(data.as_bytes(), "old.csv", FilterConfig::default()).unwrap();
        assert_eq!(d.summary.source, "legacy");
        assert_eq!(d.summary.samples, 2);
    }
    #[test]
    fn rejects_mixed_sources_and_nonfinite_values() {
        let d = "raw_mv,label,source\n2500,0,demo\n2501,1,hardware\n";
        assert!(read_csv(d.as_bytes(), "mixed", FilterConfig::default()).is_err());
        assert!(read_csv(
            "raw_mv,label\nNaN,0\n".as_bytes(),
            "nan",
            FilterConfig::default()
        )
        .is_err());
    }
}
