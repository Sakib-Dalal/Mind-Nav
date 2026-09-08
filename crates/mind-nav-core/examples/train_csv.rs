//! Inspect/train an EEG CSV without a GUI. All data remains local.
use mind_nav_core::{dataset, model, signal::FilterConfig};
use std::path::Path;
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    let path = args.get(1).ok_or(
        "Usage: cargo run -p mind-nav-core --example train_csv -- RECORDING.csv [250|256]",
    )?;
    let sample_rate = args.get(2).map(|s| s.parse()).transpose()?.unwrap_or(0);
    let sample_rate = if sample_rate == 0 {
        dataset::detect_sample_rate(Path::new(path))?
    } else {
        sample_rate
    };
    println!("Capture rate: {sample_rate} Hz");
    let dataset = dataset::read_file(
        Path::new(path),
        FilterConfig {
            sample_rate,
            ..Default::default()
        },
    )?;
    println!("{}", serde_json::to_string_pretty(&dataset.summary)?);
    let model = model::train(&dataset, "CLI validation", "cli", 0, |_| {})?;
    println!("{}", serde_json::to_string_pretty(&model.metrics)?);
    Ok(())
}
