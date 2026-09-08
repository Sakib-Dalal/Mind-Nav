//! Shared, deterministic signal processing and training. No Python runtime.
pub mod dataset;
pub mod model;
pub mod practice;
pub mod protocol;
pub mod signal;

pub const SAMPLE_RATE: usize = 250;
pub const WINDOW: usize = SAMPLE_RATE * 2;
pub const FEATURE_VERSION: u32 = 1;

#[derive(Debug, thiserror::Error)]
pub enum Error {
    #[error("{0}")]
    Invalid(String),
    #[error(transparent)]
    Io(#[from] std::io::Error),
    #[error(transparent)]
    Csv(#[from] csv::Error),
    #[error(transparent)]
    Json(#[from] serde_json::Error),
}
pub type Result<T> = std::result::Result<T, Error>;
