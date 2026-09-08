use crate::{Error, Result};

#[derive(Debug, PartialEq)]
pub struct Sample {
    pub sequence: u32,
    pub micros: u32,
    pub millivolts: f64,
}

/// Firmware v2: sequence,microseconds,ADC millivolts. Comments start with #.
pub fn parse_sample(line: &str) -> Result<Option<Sample>> {
    let s = line.trim();
    if s.is_empty() || s.starts_with('#') {
        return Ok(None);
    }
    let columns: Vec<_> = s.split(',').collect();
    let invalid = || Error::Invalid("Expected v2 firmware: sequence,micros,millivolts".into());
    if columns.len() != 3 {
        return Err(invalid());
    }
    let sample = Sample {
        sequence: columns[0].parse().map_err(|_| invalid())?,
        micros: columns[1].parse().map_err(|_| invalid())?,
        millivolts: columns[2].parse().map_err(|_| invalid())?,
    };
    if !sample.millivolts.is_finite() || !(0.0..=6144.0).contains(&sample.millivolts) {
        return Err(invalid());
    }
    Ok(Some(sample))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn handles_protocol_and_rejects_legacy_or_nan() {
        assert_eq!(parse_sample("# MINDNAV,2,250,mV").unwrap(), None);
        assert_eq!(
            parse_sample("42,168000,2500.125\r\n")
                .unwrap()
                .unwrap()
                .sequence,
            42
        );
        assert!(parse_sample("500.000").is_err());
        assert!(parse_sample("1,4,NaN").is_err());
    }
}
