//! One native utterance at a time; text is passed as data, never shell code.
use std::{
    process::{Child, Command},
    sync::{Arc, Mutex},
};
#[derive(Clone, Default)]
pub struct Speech(Arc<Mutex<Option<Child>>>);
impl Speech {
    pub fn stop(&self) {
        if let Ok(mut slot) = self.0.lock() {
            if let Some(mut child) = slot.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
    pub fn say(&self, text: &str) -> Result<(), String> {
        if text.trim().is_empty() || text.chars().count() > 2000 {
            return Err("Speech needs 1–2000 characters".into());
        }
        let mut slot = self.0.lock().map_err(|e| e.to_string())?;
        if let Some(mut child) = slot.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        #[cfg(target_os = "macos")]
        let child = Command::new("say").arg("--").arg(text).spawn();
        #[cfg(target_os = "linux")]
        let child = Command::new("spd-say")
            .args(["--wait", "--"])
            .arg(text)
            .spawn();
        #[cfg(target_os="windows")]
        let child=Command::new("powershell").args(["-NoProfile","-NonInteractive","-Command","Add-Type -AssemblyName System.Speech; $speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speaker.Speak([Console]::In.ReadToEnd())"]).stdin(std::process::Stdio::piped()).spawn().and_then(|mut child|{use std::io::Write;child.stdin.take().ok_or_else(||std::io::Error::other("No speech input"))?.write_all(text.as_bytes())?;Ok(child)});
        *slot = Some(child.map_err(|e| format!("Speech could not start: {e}"))?);
        Ok(())
    }
}
