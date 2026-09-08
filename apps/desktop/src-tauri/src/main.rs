#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod runtime;
mod speech;
use runtime::{Runtime, Session, Settings, Shared};
use serde::Serialize;
use std::{
    fs,
    sync::{Arc, Mutex},
};
use tauri::{Manager, State};

#[derive(Serialize)]
struct Bootstrap {
    settings: Settings,
    sessions: Vec<Session>,
    models: Vec<mind_nav_core::model::Model>,
    data_directory: String,
}
#[tauri::command]
fn bootstrap(state: State<Shared>) -> Result<Bootstrap, String> {
    let s = state.lock().map_err(|e| e.to_string())?;
    Ok(Bootstrap {
        settings: s.settings.clone(),
        sessions: s.sessions.clone(),
        models: s.models.clone(),
        data_directory: s.directory.to_string_lossy().into(),
    })
}
#[tauri::command]
fn snapshot(state: State<Shared>) -> Result<runtime::Snapshot, String> {
    Ok(state.lock().map_err(|e| e.to_string())?.get_snapshot())
}
#[tauri::command]
fn list_ports() -> Result<Vec<String>, String> {
    serialport::available_ports()
        .map(|ports| ports.into_iter().map(|p| p.port_name).collect())
        .map_err(|e| e.to_string())
}
#[tauri::command]
fn start_demo(state: State<Shared>) -> Result<(), String> {
    runtime::demo(state.inner().clone())
}
#[tauri::command]
async fn connect_device(state: State<'_, Shared>, port: String) -> Result<(), String> {
    let shared = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || runtime::connect(shared, port))
        .await
        .map_err(|e| e.to_string())?
}
#[tauri::command]
fn disconnect_device(state: State<Shared>) -> Result<(), String> {
    state.lock().map_err(|e| e.to_string())?.disconnect(None);
    Ok(())
}
#[tauri::command]
fn start_recording(state: State<Shared>, name: String, minutes: u32) -> Result<(), String> {
    state
        .lock()
        .map_err(|e| e.to_string())?
        .begin_recording(name, minutes)
}
#[tauri::command]
fn pause_recording(state: State<Shared>) -> Result<(), String> {
    let mut s = state.lock().map_err(|e| e.to_string())?;
    if !s.snapshot.recording {
        return Err("No recording is running".into());
    }
    s.snapshot.paused = !s.snapshot.paused;
    Ok(())
}
#[tauri::command]
fn stop_recording(state: State<Shared>) -> Result<(), String> {
    state
        .lock()
        .map_err(|e| e.to_string())?
        .finish_recording(true)
}
#[tauri::command]
fn save_settings(state: State<Shared>, settings: Settings) -> Result<(), String> {
    settings.validate()?;
    let mut s = state.lock().map_err(|e| e.to_string())?;
    if settings.notch != s.settings.notch && s.snapshot.recording {
        return Err("Finish recording before changing the filter".into());
    }
    runtime::atomic_json(&s.directory.join("settings.json"), &settings)?;
    let changed = settings.notch != s.settings.notch
        || settings.active_model != s.settings.active_model
        || settings.threshold != s.settings.threshold;
    s.settings = settings;
    if changed {
        s.reset_signal();
    }
    Ok(())
}
#[tauri::command]
fn arm_input(state: State<Shared>, armed: bool) -> Result<(), String> {
    state.lock().map_err(|e| e.to_string())?.set_armed(armed)
}
#[tauri::command]
fn start_practice(state: State<Shared>) -> Result<(), String> {
    let mut s = state.lock().map_err(|e| e.to_string())?;
    if s.snapshot.recording {
        return Err("Finish recording before practice".into());
    }
    if !s.snapshot.connected || !s.snapshot.quality.usable || s.snapshot.probability.is_none() {
        return Err(
            "Practice needs a steady signal and an active model trained on this source and filters"
                .into(),
        );
    }
    s.snapshot.armed = false;
    s.snapshot.practice.start();
    Ok(())
}
#[tauri::command]
fn stop_practice(state: State<Shared>) -> Result<(), String> {
    state
        .lock()
        .map_err(|e| e.to_string())?
        .snapshot
        .practice
        .running = false;
    Ok(())
}
#[tauri::command]
async fn import_session(
    state: State<'_, Shared>,
    sample_rate: usize,
) -> Result<Option<Session>, String> {
    let Some(file) = rfd::AsyncFileDialog::new()
        .add_filter("EEG recording", &["csv"])
        .pick_file()
        .await
    else {
        return Ok(None);
    };
    let path = file.path().to_path_buf();
    let shared = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || {
        let (directory, mut config) = {
            let s = shared.lock().map_err(|e| e.to_string())?;
            (s.directory.clone(), s.config())
        };
        config.sample_rate = if sample_rate == 0 {
            mind_nav_core::dataset::detect_sample_rate(&path).map_err(|e| e.to_string())?
        } else {
            sample_rate
        };
        let data =
            mind_nav_core::dataset::read_file(&path, config.clone()).map_err(|e| e.to_string())?;
        let session = Session {
            id: runtime::id(),
            name: path
                .file_stem()
                .unwrap_or_default()
                .to_string_lossy()
                .into(),
            created_at: runtime::now(),
            source: data.summary.source.clone(),
            samples: data.summary.samples,
            duration_seconds: data.summary.duration_seconds,
            rest_trials: 0,
            select_trials: 0,
            complete: true,
            imported: true,
            config,
            summary: Some(data.summary),
        };
        fs::copy(
            path,
            directory
                .join("sessions")
                .join(format!("{}.csv", session.id)),
        )
        .map_err(|e| e.to_string())?;
        runtime::atomic_json(
            &directory
                .join("sessions")
                .join(format!("{}.json", session.id)),
            &session,
        )?;
        shared
            .lock()
            .map_err(|e| e.to_string())?
            .sessions
            .insert(0, session.clone());
        Ok(Some(session))
    })
    .await
    .map_err(|e| e.to_string())?
}
#[tauri::command]
async fn train_model(
    state: State<'_, Shared>,
    session_id: String,
    name: String,
) -> Result<mind_nav_core::model::Model, String> {
    let shared = state.inner().clone();
    {
        let mut s = shared.lock().map_err(|e| e.to_string())?;
        if s.training.running {
            return Err("Training is already in progress".into());
        }
        s.training = runtime::Training {
            running: true,
            progress: 0,
            message: "Preparing clean training windows".into(),
        };
    }
    let result = tauri::async_runtime::spawn_blocking({
        let shared = shared.clone();
        move || runtime::train_session(shared, session_id, name)
    })
    .await
    .map_err(|e| e.to_string())
    .and_then(|r| r);
    if let Ok(mut s) = shared.lock() {
        s.training.running = false;
        s.training.message = match &result {
            Ok(_) => "Model saved. Review validation before activating.".into(),
            Err(e) => e.clone(),
        };
    }
    result
}
#[tauri::command]
async fn export_session(
    state: State<'_, Shared>,
    session_id: String,
) -> Result<Option<String>, String> {
    let path = state
        .lock()
        .map_err(|e| e.to_string())?
        .session_path(&session_id)?;
    let Some(file) = rfd::AsyncFileDialog::new()
        .set_file_name("mind-nav-session.csv")
        .add_filter("CSV", &["csv"])
        .save_file()
        .await
    else {
        return Ok(None);
    };
    fs::copy(path, file.path()).map_err(|e| e.to_string())?;
    Ok(Some(file.path().to_string_lossy().into()))
}
#[tauri::command]
async fn export_model(
    state: State<'_, Shared>,
    model_id: String,
) -> Result<Option<String>, String> {
    let model = state
        .lock()
        .map_err(|e| e.to_string())?
        .models
        .iter()
        .find(|m| m.id == model_id)
        .cloned()
        .ok_or("Model not found")?;
    let Some(file) = rfd::AsyncFileDialog::new()
        .set_file_name("mind-nav-model.json")
        .add_filter("Mind-Nav model", &["json"])
        .save_file()
        .await
    else {
        return Ok(None);
    };
    runtime::atomic_json(file.path(), &model)?;
    Ok(Some(file.path().to_string_lossy().into()))
}
#[tauri::command]
async fn speak(state: State<'_, speech::Speech>, text: String) -> Result<(), String> {
    let speech = state.inner().clone();
    tauri::async_runtime::spawn_blocking(move || speech.say(&text))
        .await
        .map_err(|e| e.to_string())?
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            app.manage(speech::Speech::default());
            let directory = app.path().app_data_dir()?;
            app.manage(Arc::new(Mutex::new(
                Runtime::new(directory).map_err(std::io::Error::other)?,
            )));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            bootstrap,
            snapshot,
            list_ports,
            start_demo,
            connect_device,
            disconnect_device,
            start_recording,
            pause_recording,
            stop_recording,
            save_settings,
            arm_input,
            import_session,
            train_model,
            export_session,
            export_model,
            speak,
            start_practice,
            stop_practice
        ])
        .build(tauri::generate_context!())
        .expect("Unable to start Mind-Nav")
        .run(|handle, event| {
            if let tauri::RunEvent::Exit = event {
                handle.state::<speech::Speech>().stop();
                if let Ok(mut s) = handle.state::<Shared>().lock() {
                    s.disconnect(None);
                }
            }
        });
}
