use mind_nav_core::{
    dataset::{self, DatasetSummary},
    model::{self, Model},
    protocol,
    signal::{self, FilterConfig, IntentGate, Pipeline, Quality},
    SAMPLE_RATE, WINDOW,
};
use serde::{Deserialize, Serialize};
use std::{
    collections::VecDeque,
    fs,
    io::{BufRead, BufReader, Read, Write},
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};
use uuid::Uuid;

pub fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}
pub fn id() -> String {
    Uuid::new_v4().to_string()
}
pub fn atomic_json(path: &Path, data: &impl Serialize) -> Result<(), String> {
    let bytes = serde_json::to_vec_pretty(data).map_err(|e| e.to_string())?;
    let tmp = path.with_extension("tmp");
    let mut file = fs::File::create(&tmp).map_err(|e| e.to_string())?;
    file.write_all(&bytes)
        .and_then(|_| file.sync_all())
        .map_err(|e| e.to_string())?;
    fs::rename(tmp, path).map_err(|e| e.to_string())
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    pub theme: String,
    pub large_text: bool,
    pub reduced_motion: bool,
    pub scan_ms: u64,
    pub threshold: f64,
    pub notch: u16,
    pub voice_cues: bool,
    pub name: String,
    pub active_model: Option<String>,
}
impl Default for Settings {
    fn default() -> Self {
        Self {
            theme: "light".into(),
            large_text: false,
            reduced_motion: false,
            scan_ms: 1500,
            threshold: 0.8,
            notch: 50,
            voice_cues: true,
            name: "Explorer".into(),
            active_model: None,
        }
    }
}
impl Settings {
    pub fn validate(&self) -> Result<(), String> {
        if !["light", "dark"].contains(&self.theme.as_str())
            || !(600..=5000).contains(&self.scan_ms)
            || !self.threshold.is_finite()
            || !(0.6..=0.95).contains(&self.threshold)
            || ![0, 50, 60].contains(&self.notch)
            || self.name.trim().is_empty()
            || self.name.len() > 60
        {
            return Err("Invalid preferences".into());
        }
        Ok(())
    }
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Session {
    pub id: String,
    pub name: String,
    pub created_at: u64,
    pub source: String,
    pub samples: usize,
    pub duration_seconds: f64,
    pub rest_trials: usize,
    pub select_trials: usize,
    pub complete: bool,
    pub imported: bool,
    pub config: FilterConfig,
    pub summary: Option<DatasetSummary>,
}
#[derive(Clone, Serialize)]
pub struct Training {
    pub running: bool,
    pub progress: u8,
    pub message: String,
}
#[derive(Clone, Serialize)]
pub struct Snapshot {
    pub connected: bool,
    pub source: String,
    pub port: String,
    pub quality: Quality,
    pub waveform: Vec<f64>,
    pub bands: [f64; 5],
    pub sample_count: u64,
    pub dropped: u64,
    pub sample_rate: f64,
    pub recording: bool,
    pub paused: bool,
    pub elapsed: f64,
    pub cue: String,
    pub cue_remaining: f64,
    pub rest_trials: usize,
    pub select_trials: usize,
    pub probability: Option<f64>,
    pub armed: bool,
    pub selections: u64,
    pub error: Option<String>,
    pub training: Training,
    pub practice: mind_nav_core::practice::Practice,
}
struct Recording {
    meta: Session,
    writer: csv::Writer<fs::File>,
    count: usize,
    last_trial: u64,
    limit_samples: usize,
}
pub struct Runtime {
    pub directory: PathBuf,
    pub settings: Settings,
    pub sessions: Vec<Session>,
    pub models: Vec<Model>,
    pub training: Training,
    pub stop: Arc<AtomicBool>,
    pub snapshot: Snapshot,
    raw: VecDeque<f64>,
    filtered: VecDeque<f64>,
    pipeline: Pipeline,
    gate: IntentGate,
    record: Option<Recording>,
    pub last_sample: Instant,
    prediction_at: u64,
}
pub type Shared = Arc<Mutex<Runtime>>;
impl Runtime {
    pub fn new(directory: PathBuf) -> Result<Self, String> {
        fs::create_dir_all(directory.join("sessions")).map_err(|e| e.to_string())?;
        fs::create_dir_all(directory.join("models")).map_err(|e| e.to_string())?;
        let settings: Settings = fs::read(directory.join("settings.json"))
            .ok()
            .and_then(|b| serde_json::from_slice(&b).ok())
            .filter(|s: &Settings| s.validate().is_ok())
            .unwrap_or_default();
        let mut sessions: Vec<Session> = read_jsons(&directory.join("sessions"));
        sessions.retain(|s| Uuid::parse_str(&s.id).is_ok() && s.config.validate().is_ok());
        for session in sessions.iter_mut().filter(|s| !s.complete && !s.imported) {
            recover_session(&directory, session);
        }
        sessions.sort_by_key(|s| std::cmp::Reverse(s.created_at));
        let mut models: Vec<Model> = read_jsons(&directory.join("models"));
        models.retain(|m| m.validate().is_ok() && Uuid::parse_str(&m.id).is_ok());
        models.sort_by_key(|m| std::cmp::Reverse(m.created_at));
        let training = Training {
            running: false,
            progress: 0,
            message: "Ready to train".into(),
        };
        let pipeline = Pipeline::new(&FilterConfig {
            notch: settings.notch,
            ..Default::default()
        })
        .map_err(|e| e.to_string())?;
        Ok(Self {
            directory,
            settings,
            sessions,
            models,
            training: training.clone(),
            stop: Arc::new(AtomicBool::new(false)),
            snapshot: Snapshot {
                connected: false,
                source: "disconnected".into(),
                port: String::new(),
                quality: Quality {
                    reason: "Connect your device or explore demo mode".into(),
                    ..Default::default()
                },
                waveform: vec![],
                bands: [0.0; 5],
                sample_count: 0,
                dropped: 0,
                sample_rate: 0.0,
                recording: false,
                paused: false,
                elapsed: 0.0,
                cue: "REST".into(),
                cue_remaining: 5.0,
                rest_trials: 0,
                select_trials: 0,
                probability: None,
                armed: false,
                selections: 0,
                error: None,
                training,
                practice: Default::default(),
            },
            raw: VecDeque::new(),
            filtered: VecDeque::new(),
            pipeline,
            gate: IntentGate::default(),
            record: None,
            last_sample: Instant::now(),
            prediction_at: 0,
        })
    }
    pub fn set_armed(&mut self, armed: bool) -> Result<(), String> {
        if armed {
            if self.snapshot.practice.running {
                return Err("Finish practice before enabling BCI selections".into());
            }
            if self.snapshot.recording {
                return Err("Finish recording before enabling BCI selections".into());
            }
            if !self.snapshot.connected || !self.snapshot.quality.usable {
                return Err("A steady signal is needed before enabling selections".into());
            }
            let model = self.model().ok_or("Train and activate a model first")?;
            if model.dataset.source != self.snapshot.source || model.config != self.config() {
                return Err("This model has a different signal source or filter configuration. Train on the current device and filterself.".into());
            }
        }
        self.gate.reset();
        self.snapshot.armed = armed;
        Ok(())
    }
    pub fn config(&self) -> FilterConfig {
        FilterConfig {
            notch: self.settings.notch,
            ..Default::default()
        }
    }
    pub fn model(&self) -> Option<&Model> {
        self.settings
            .active_model
            .as_ref()
            .and_then(|id| self.models.iter().find(|m| &m.id == id))
    }
    pub fn reset_signal(&mut self) {
        self.raw.clear();
        self.filtered.clear();
        self.gate.reset();
        self.pipeline = Pipeline::new(&self.config()).expect("validated filter settings");
        self.snapshot.armed = false;
        self.snapshot.practice.running = false;
        self.snapshot.probability = None;
        self.snapshot.waveform.clear();
        self.snapshot.bands = [0.0; 5];
        self.snapshot.quality = Quality {
            reason: "Settling signal · 3 seconds".into(),
            ..Default::default()
        };
    }
    pub fn switch_source(&mut self, source: &str, port: &str) -> Result<(), String> {
        if self.record.is_some() {
            return Err("Finish the recording before changing the device".into());
        }
        self.stop.store(true, Ordering::SeqCst);
        self.stop = Arc::new(AtomicBool::new(false));
        self.reset_signal();
        self.snapshot.connected = true;
        self.snapshot.source = source.into();
        self.snapshot.port = port.into();
        self.snapshot.sample_count = 0;
        self.snapshot.dropped = 0;
        self.snapshot.sample_rate = 0.0;
        self.snapshot.error = None;
        self.last_sample = Instant::now();
        Ok(())
    }
    pub fn ingest(&mut self, x: f64, stamp: u64) {
        let Some(y) = self.pipeline.next(x) else {
            return;
        };
        self.last_sample = Instant::now();
        self.snapshot.sample_count += 1;
        self.snapshot.practice.observe(
            self.snapshot.probability,
            self.snapshot.quality.usable,
            self.settings.threshold,
        );
        self.raw.push_back(x);
        self.filtered.push_back(y);
        if self.raw.len() > WINDOW {
            self.raw.pop_front();
            self.filtered.pop_front();
        }
        if let Some(rec) = self.record.as_mut() {
            if !self.snapshot.paused {
                let trial = rec.count as u64 / (SAMPLE_RATE as u64 * 5);
                let label = trial % 2;
                if rec.last_trial != trial || rec.count == 0 {
                    if label == 0 {
                        rec.meta.rest_trials += 1;
                    } else {
                        rec.meta.select_trials += 1;
                    }
                    rec.last_trial = trial;
                }
                let timestamp = stamp as f64 / 1_000_000.0;
                let write = rec.writer.write_record([
                    format!("{timestamp:.6}"),
                    format!("{x:.6}"),
                    label.to_string(),
                    trial.to_string(),
                    self.snapshot.source.clone(),
                    SAMPLE_RATE.to_string(),
                ]);
                rec.count += 1;
                rec.meta.samples = rec.count;
                rec.meta.duration_seconds = rec.count as f64 / SAMPLE_RATE as f64;
                self.snapshot.elapsed = rec.meta.duration_seconds;
                self.snapshot.cue = if label == 0 { "REST" } else { "SELECT" }.into();
                self.snapshot.cue_remaining =
                    5.0 - (rec.count % (SAMPLE_RATE * 5)) as f64 / SAMPLE_RATE as f64;
                self.snapshot.rest_trials = rec.meta.rest_trials;
                self.snapshot.select_trials = rec.meta.select_trials;
                let flush = if rec.count % SAMPLE_RATE == 0 {
                    rec.writer.flush().map_err(|e| e.to_string())
                } else {
                    Ok(())
                };
                if let Err(e) = write.map_err(|e| e.to_string()).and(flush) {
                    self.snapshot.error = Some(format!("Recording write failed: {e}"));
                    let _ = self.finish_recording(false);
                } else if self
                    .record
                    .as_ref()
                    .is_some_and(|r| r.limit_samples > 0 && r.count >= r.limit_samples)
                {
                    if let Err(e) = self.finish_recording(true) {
                        self.snapshot.error = Some(e);
                    }
                }
            }
        }
        if self
            .snapshot
            .sample_count
            .saturating_sub(self.prediction_at)
            >= SAMPLE_RATE as u64 / 4
            || self.snapshot.sample_count < self.prediction_at
        {
            self.prediction_at = self.snapshot.sample_count;
            let raw: Vec<_> = self.raw.iter().copied().collect();
            let filtered: Vec<_> = self.filtered.iter().copied().collect();
            self.snapshot.waveform = filtered.clone();
            if self.pipeline.count < SAMPLE_RATE * 3 {
                return;
            }
            self.snapshot.quality =
                signal::quality(&raw, &filtered, self.snapshot.source == "hardware");
            self.snapshot.bands = signal::band_powers(&filtered, SAMPLE_RATE);
            let compatible = self.model().is_some_and(|m| {
                m.dataset.source == self.snapshot.source && m.config == self.config()
            });
            let probability = if compatible && filtered.len() == WINDOW {
                self.model()
                    .map(|m| m.predict(&signal::features(&filtered, SAMPLE_RATE)))
            } else {
                None
            };
            self.snapshot.probability = probability;
            if self.snapshot.armed
                && self.gate.update(
                    probability.unwrap_or(0.0),
                    self.snapshot.quality.usable && probability.is_some(),
                    self.settings.threshold,
                    now(),
                )
            {
                self.snapshot.selections += 1;
            }
        }
    }
    pub fn begin_recording(&mut self, name: String, minutes: u32) -> Result<(), String> {
        if !self.snapshot.connected {
            return Err("Connect a device or start demo mode first".into());
        }
        if self.record.is_some() {
            return Err("A recording is already running".into());
        }
        if self.snapshot.practice.running {
            return Err("Finish practice before recording".into());
        }
        if name.trim().is_empty() || name.len() > 80 || minutes > 120 {
            return Err(
                "Use a session name up to 80 characters and a duration up to 120 minutes".into(),
            );
        }
        let meta = Session {
            id: id(),
            name: name.trim().into(),
            created_at: now(),
            source: self.snapshot.source.clone(),
            samples: 0,
            duration_seconds: 0.0,
            rest_trials: 0,
            select_trials: 0,
            complete: false,
            imported: false,
            config: self.config(),
            summary: None,
        };
        let path = self
            .directory
            .join("sessions")
            .join(format!("{}.csv", meta.id));
        let mut writer = csv::Writer::from_path(path).map_err(|e| e.to_string())?;
        writer
            .write_record([
                "timestamp",
                "raw_mv",
                "label",
                "trial_id",
                "source",
                "sample_rate",
            ])
            .map_err(|e| e.to_string())?;
        writer.flush().map_err(|e| e.to_string())?;
        atomic_json(
            &self
                .directory
                .join("sessions")
                .join(format!("{}.json", meta.id)),
            &meta,
        )?;
        self.record = Some(Recording {
            meta,
            writer,
            count: 0,
            last_trial: 0,
            limit_samples: minutes as usize * 60 * SAMPLE_RATE,
        });
        self.snapshot.recording = true;
        self.snapshot.paused = false;
        self.snapshot.elapsed = 0.0;
        self.snapshot.rest_trials = 0;
        self.snapshot.select_trials = 0;
        self.snapshot.armed = false;
        self.gate.reset();
        Ok(())
    }
    pub fn finish_recording(&mut self, complete: bool) -> Result<(), String> {
        self.snapshot.recording = false;
        self.snapshot.paused = false;
        if let Some(mut rec) = self.record.take() {
            let flush = rec.writer.flush().map_err(|e| e.to_string());
            rec.meta.complete = complete && flush.is_ok();
            let saved = atomic_json(
                &self
                    .directory
                    .join("sessions")
                    .join(format!("{}.json", rec.meta.id)),
                &rec.meta,
            );
            self.sessions.insert(0, rec.meta);
            flush?;
            saved?;
        }
        Ok(())
    }
    pub fn disconnect(&mut self, reason: Option<String>) {
        self.stop.store(true, Ordering::SeqCst);
        if let Err(e) = self.finish_recording(reason.is_none()) {
            self.snapshot.error = Some(e);
        }
        self.snapshot.connected = false;
        self.snapshot.source = "disconnected".into();
        self.reset_signal();
        self.snapshot.quality.reason = "Device disconnected".into();
        if reason.is_some() {
            self.snapshot.error = reason;
        }
    }
    pub fn get_snapshot(&mut self) -> Snapshot {
        if self.snapshot.connected && self.last_sample.elapsed() > Duration::from_secs(3) {
            self.disconnect(Some(
                "No samples received for 3 seconds. Check the device and v2 firmware.".into(),
            ));
        }
        self.snapshot.training = self.training.clone();
        self.snapshot.clone()
    }
    pub fn session_path(&self, id: &str) -> Result<PathBuf, String> {
        if !self.sessions.iter().any(|s| s.id == id) {
            return Err("Session not found".into());
        }
        Ok(self.directory.join("sessions").join(format!("{id}.csv")))
    }
}
fn read_jsons<T: serde::de::DeserializeOwned>(dir: &Path) -> Vec<T> {
    fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .filter(|f| f.path().extension().is_some_and(|s| s == "json"))
        .filter_map(|f| fs::read(f.path()).ok())
        .filter_map(|b| serde_json::from_slice(&b).ok())
        .collect()
}

pub fn demo(shared: Shared) -> Result<(), String> {
    let stop = {
        let mut s = shared.lock().map_err(|e| e.to_string())?;
        s.switch_source("demo", "Built-in signal simulator")?;
        s.stop.clone()
    };
    thread::spawn(move || {
        let start = Instant::now();
        let epoch = now() * 1000;
        let mut count = 0;
        let mut rng = 123456789u32;
        while !stop.load(Ordering::SeqCst) {
            let target = (start.elapsed().as_secs_f64() * SAMPLE_RATE as f64) as u64;
            if let Ok(mut state) = shared.lock() {
                if !Arc::ptr_eq(&stop, &state.stop) {
                    break;
                }
                let pending = target.saturating_sub(count).min(SAMPLE_RATE as u64);
                for _ in 0..pending {
                    let t = count as f64 / SAMPLE_RATE as f64;
                    let select = state
                        .record
                        .as_ref()
                        .map(|r| (r.count / (SAMPLE_RATE * 5)) % 2 == 1)
                        .unwrap_or(if state.snapshot.practice.running {
                            state.snapshot.practice.label() == 1
                        } else {
                            (t as u64 / 5) % 2 == 1
                        });
                    let tau = std::f64::consts::TAU;
                    rng = rng.wrapping_mul(1664525).wrapping_add(1013904223);
                    let noise = (rng as f64 / u32::MAX as f64 - 0.5) * 4.0;
                    let x = 2500.0
                        + (if select { 4.0 } else { 18.0 }) * (tau * 10.0 * t).sin()
                        + (if select { 16.0 } else { 3.0 }) * (tau * 20.0 * t).sin()
                        + 3.0 * (tau * 6.0 * t).sin()
                        + noise
                        + 1.5 * (tau * 50.0 * t).sin();
                    state.ingest(x, epoch + count * 4000);
                    count += 1;
                }
                state.snapshot.sample_rate = 250.0;
            }
            thread::sleep(Duration::from_millis(20));
        }
    });
    Ok(())
}

pub fn connect(shared: Shared, path: String) -> Result<(), String> {
    if shared.lock().map_err(|e| e.to_string())?.snapshot.recording {
        return Err("Finish recording before changing the device".into());
    }
    // Open successfully before changing application source. Never fall back to demo.
    let mut port = serialport::new(&path, 115200)
        .timeout(Duration::from_millis(200))
        .open()
        .map_err(|e| format!("Could not open {path}: {e}"))?;
    let stop = {
        let mut state = shared.lock().map_err(|e| e.to_string())?;
        state.switch_source("hardware", &path)?;
        state.stop.clone()
    };
    thread::spawn(move || {
        // Many Uno boards reset when serial opens. Keep the UI responsive during boot.
        for _ in 0..20 {
            if stop.load(Ordering::SeqCst) {
                return;
            }
            thread::sleep(Duration::from_millis(100));
        }
        let _ = port.clear(serialport::ClearBuffer::Input);
        if let Err(e) = port.write_all(b"START\n") {
            if let Ok(mut s) = shared.lock() {
                s.disconnect(Some(e.to_string()));
            }
            return;
        }
        let mut reader = BufReader::new(port);
        let mut line = String::new();
        let mut prev: Option<protocol::Sample> = None;
        let mut elapsed_us = 0u64;
        let epoch = now() * 1000;
        let mut malformed = 0;
        while !stop.load(Ordering::SeqCst) {
            match reader.by_ref().take(257).read_line(&mut line) {
                Ok(0) => {}
                Ok(_) => {
                    if line.len() > 256 {
                        line.clear();
                        malformed += 1;
                        continue;
                    }
                    match protocol::parse_sample(&line) {
                        Ok(Some(sample)) => {
                            if let Ok(mut state) = shared.lock() {
                                if !Arc::ptr_eq(&stop, &state.stop) {
                                    break;
                                }
                                if let Some(p) = &prev {
                                    let delta = sample.micros.wrapping_sub(p.micros) as u64;
                                    let jump = sample.sequence.wrapping_sub(p.sequence);
                                    if jump != 1 || !(2000..=8000).contains(&delta) {
                                        state.snapshot.dropped +=
                                            jump.saturating_sub(1).min(10000) as u64;
                                        state.reset_signal();
                                    }
                                    elapsed_us += delta;
                                    if delta > 0 {
                                        state.snapshot.sample_rate = 0.95
                                            * state.snapshot.sample_rate
                                            + 0.05 * (1_000_000.0 / delta as f64);
                                    }
                                }
                                state.ingest(sample.millivolts, epoch + elapsed_us);
                            }
                            prev = Some(sample);
                            malformed = 0;
                        }
                        Ok(None) => {}
                        Err(_) => {
                            malformed += 1;
                        }
                    }
                    line.clear();
                    if malformed > 20 {
                        if let Ok(mut s) = shared.lock() {
                            s.disconnect(Some(
                                "Unrecognized serial data. Flash the Mind-Nav v2 Arduino firmware."
                                    .into(),
                            ));
                        }
                        break;
                    }
                }
                Err(e) if e.kind() == std::io::ErrorKind::TimedOut => {
                    if line.len() > 256 {
                        line.clear();
                    }
                }
                Err(e) => {
                    if let Ok(mut s) = shared.lock() {
                        if Arc::ptr_eq(&stop, &s.stop) {
                            s.disconnect(Some(format!("Device connection lost: {e}")));
                        }
                    }
                    break;
                }
            }
        }
        let _ = reader.get_mut().write_all(b"STOP\n");
    });
    Ok(())
}

pub fn train_session(shared: Shared, session_id: String, name: String) -> Result<Model, String> {
    let (path, config, directory) = {
        let s = shared.lock().map_err(|e| e.to_string())?;
        let path = s.session_path(&session_id)?;
        let session = s
            .sessions
            .iter()
            .find(|s| s.id == session_id)
            .ok_or("Session not found")?;
        (path, session.config.clone(), s.directory.clone())
    };
    let data = dataset::read_file(&path, config).map_err(|e| e.to_string())?;
    let model = model::train(&data, &name, &id(), now(), |p| {
        if let Ok(mut s) = shared.lock() {
            s.training.progress = p;
            s.training.message = if p < 100 {
                format!("Validating whole trials · {} of 5 folds", (p / 15).min(5))
            } else {
                "Saving model".into()
            };
        }
    })
    .map_err(|e| e.to_string())?;
    atomic_json(
        &directory.join("models").join(format!("{}.json", model.id)),
        &model,
    )?;
    let mut s = shared.lock().map_err(|e| e.to_string())?;
    s.models.insert(0, model.clone());
    if let Some(session) = s.sessions.iter_mut().find(|s| s.id == session_id) {
        session.summary = Some(data.summary);
        let copy = session.clone();
        atomic_json(
            &directory
                .join("sessions")
                .join(format!("{}.json", session_id)),
            &copy,
        )?;
    }
    Ok(model)
}

/// Recount flushed rows after a crash; an incomplete final row is excluded.
fn recover_session(directory: &Path, session: &mut Session) {
    let path = directory
        .join("sessions")
        .join(format!("{}.csv", session.id));
    if let Ok(mut reader) = csv::ReaderBuilder::new().flexible(true).from_path(path) {
        let mut trials = std::collections::BTreeMap::new();
        let mut count = 0;
        for row in reader.records().filter_map(Result::ok) {
            if row.len() == 6 && row[0].parse::<f64>().is_ok() && row[1].parse::<f64>().is_ok() {
                count += 1;
                if let (Ok(trial), Ok(label)) = (row[3].parse::<u64>(), row[2].parse::<u8>()) {
                    trials.insert(trial, label);
                }
            }
        }
        session.samples = count;
        session.duration_seconds = count as f64 / session.config.sample_rate as f64;
        session.rest_trials = trials.values().filter(|l| **l == 0).count();
        session.select_trials = trials.values().filter(|l| **l == 1).count();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn records_and_recovers_local_session() {
        let dir = std::env::temp_dir().join(id());
        let mut r = Runtime::new(dir.clone()).unwrap();
        r.switch_source("demo", "Test").unwrap();
        r.begin_recording("Test session".into(), 0).unwrap();
        for i in 0..2500 {
            r.ingest(2500.0 + 10.0 * (i as f64 / 4.0).sin(), 1_000_000 + i * 4000);
        }
        assert!(r.switch_source("hardware", "Test").is_err());
        r.finish_recording(true).unwrap();
        let recovered = Runtime::new(dir.clone()).unwrap();
        assert_eq!(recovered.sessions.len(), 1);
        assert_eq!(recovered.sessions[0].samples, 2500);
        let data = dataset::read_file(
            &recovered.session_path(&recovered.sessions[0].id).unwrap(),
            FilterConfig::default(),
        )
        .unwrap();
        assert_eq!(data.summary.samples, 2500);
        fs::remove_dir_all(dir).unwrap();
    }
}

#[cfg(test)]
mod workflow_tests {
    use super::*;
    fn sample(index: u64) -> f64 {
        let t = index as f64 / 250.0;
        let select = (index / 1250) % 2 == 1;
        let tau = std::f64::consts::TAU;
        2500.0
            + (if select { 4.0 } else { 18.0 }) * (tau * 10.0 * t).sin()
            + (if select { 16.0 } else { 3.0 }) * (tau * 20.0 * t).sin()
            + 3.0 * (tau * 6.0 * t).sin()
    }
    #[test]
    fn recording_training_reload_and_source_gating_work_together() {
        let dir = std::env::temp_dir().join(id());
        let mut r = Runtime::new(dir.clone()).unwrap();
        r.switch_source("demo", "Integration test").unwrap();
        r.begin_recording("Two minute calibration".into(), 2)
            .unwrap();
        for i in 0..30_000 {
            r.ingest(sample(i), 1_000_000 + i * 4000);
        }
        assert!(!r.snapshot.recording);
        assert_eq!(r.sessions[0].samples, 30000);
        let session_id = r.sessions[0].id.clone();
        let shared = Arc::new(Mutex::new(r));
        let m = train_session(shared.clone(), session_id, "Integration model".into()).unwrap();
        assert!(m.metrics.balanced_accuracy > 0.9);
        assert!(m.dataset.rest_windows >= 5);
        assert!(m.dataset.select_windows >= 5);
        let mut r = shared.lock().unwrap();
        r.settings.active_model = Some(m.id.clone());
        r.set_armed(true).unwrap();
        assert!(r.snapshot.armed);
        r.switch_source("hardware", "Unavailable test port")
            .unwrap();
        r.snapshot.quality.usable = true;
        assert!(r.set_armed(true).is_err());
        assert!(!r.snapshot.armed);
        r.disconnect(None);
        drop(r);
        let restored = Runtime::new(dir.clone()).unwrap();
        assert_eq!(restored.models.len(), 1);
        assert_eq!(restored.models[0].id, m.id);
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn crash_recovery_counts_flushed_rows_and_stale_input_disarms() {
        let dir = std::env::temp_dir().join(id());
        {
            let mut r = Runtime::new(dir.clone()).unwrap();
            r.switch_source("demo", "Test").unwrap();
            r.begin_recording("Interrupted".into(), 0).unwrap();
            for i in 0..1000 {
                r.ingest(sample(i), i * 4000);
            }
        }
        let mut restored = Runtime::new(dir.clone()).unwrap();
        assert_eq!(restored.sessions[0].samples, 1000);
        assert!(!restored.sessions[0].complete);
        restored.switch_source("demo", "Test").unwrap();
        restored.snapshot.armed = true;
        restored.last_sample = Instant::now() - Duration::from_secs(4);
        let snapshot = restored.get_snapshot();
        assert!(!snapshot.armed);
        assert!(!snapshot.connected);
        assert!(snapshot.error.is_some());
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn changing_source_after_samples_never_underflows_prediction_clock() {
        let dir = std::env::temp_dir().join(id());
        let mut r = Runtime::new(dir.clone()).unwrap();
        r.switch_source("demo", "Test").unwrap();
        for i in 0..1000 {
            r.ingest(sample(i), i * 4000);
        }
        r.switch_source("demo", "Test again").unwrap();
        r.ingest(2500.0, 1);
        assert_eq!(r.snapshot.sample_count, 1);
        fs::remove_dir_all(dir).unwrap();
    }
}
