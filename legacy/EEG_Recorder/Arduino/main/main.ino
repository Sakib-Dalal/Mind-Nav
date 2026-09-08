/*
 * EEG BCI with BioAmp EXG Pill + ADS1115 + Arduino Uno
 * =====================================================
 * Precision EEG acquisition for motor imagery / mental task BCI
 * 
 * HARDWARE WIRING:
 * ----------------
 * BioAmp EXG Pill:
 *   VCC  -> Arduino 5V
 *   GND  -> Arduino GND
 *   OUT  -> ADS1115 A0
 * 
 * ADS1115:
 *   VDD  -> 5V
 *   GND  -> GND
 *   SDA  -> A4 (I2C)
 *   SCL  -> A5 (I2C)
 *   ADDR -> GND (I2C address = 0x48)
 *   A0   -> BioAmp OUT
 * 
 * EEG ELECTRODES (Motor Cortex - C3/C4 montage):
 *   IN+  -> C3 or C4 (motor cortex, hand area)
 *   IN-  -> Mastoid or earlobe (reference)
 *   GND  -> Forehead or other mastoid (ground)
 * 
 * BIOAMP CONFIGURATION (back of board):
 *   Gain: HIGH (for EEG ~10-100 µV signals)
 *   BandPass: ENABLED (0.5-40 Hz onboard filter)
 *   Electrodes: 2-ELECTRODE mode
 * 
 * Library: Adafruit ADS1X15 (install via Library Manager)
 */

#include <Wire.h>
#include <Adafruit_ADS1X15.h>

// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

Adafruit_ADS1115 ads;  // 16-bit ADC

// Sampling rate (Hz) - ADS1115 supports: 8, 16, 32, 64, 128, 250, 475, 860
// For EEG BCI (0.5-40 Hz content), 250-256 Hz is optimal (Nyquist = 125-128 Hz)
#define SAMPLE_RATE       256
#define SAMPLE_PERIOD_US  (1000000UL / SAMPLE_RATE)

// ADS1115 gain: GAIN_ONE = ±4.096V range (0.125 mV/bit)
// BioAmp output swings 0-5V centered at 2.5V, so GAIN_ONE captures full range
#define ADS_GAIN          GAIN_ONE

// Serial communication
#define BAUD_RATE         115200

// ═══════════════════════════════════════════════════════════════════════════
// SIGNAL PROCESSING - EEG FILTERS
// ═══════════════════════════════════════════════════════════════════════════

// High-pass filter (fc = 0.5 Hz) - removes DC drift and slow artifacts
// Using 1st order IIR: y[n] = α*(y[n-1] + x[n] - x[n-1])
// α = RC/(RC+dt), where RC = 1/(2π*fc), dt = 1/fs
float hp_x_prev = 0.0f;
float hp_y_prev = 0.0f;
const float HP_ALPHA = 0.98774f;  // for fc=0.5Hz @ 256Hz

// Low-pass filter (fc = 40 Hz) - removes muscle artifacts and line noise
// Using 1st order IIR: y[n] = y[n-1] + α*(x[n] - y[n-1])
// α = dt/(RC+dt), where RC = 1/(2π*fc)
float lp_y_prev = 0.0f;
const float LP_ALPHA = 0.609f;  // for fc=40Hz @ 256Hz

// Notch filter for 60 Hz powerline interference (optional)
// Simple moving average notch: removes 60Hz and harmonics
#define NOTCH_ENABLE false  // Set true if you have 60Hz noise
#define NOTCH_TAP_60HZ  4   // 256/60 ≈ 4.27 samples per cycle
float notch_buffer[5] = {0};
uint8_t notch_idx = 0;

// ═══════════════════════════════════════════════════════════════════════════
// BASELINE CORRECTION
// ═══════════════════════════════════════════════════════════════════════════
// Adaptive baseline removal (running average over 2 seconds)
#define BASELINE_WINDOW (SAMPLE_RATE * 2)
float baseline_sum = 0.0f;
uint16_t baseline_count = 0;

// ═══════════════════════════════════════════════════════════════════════════
// STATE VARIABLES
// ═══════════════════════════════════════════════════════════════════════════

unsigned long last_sample_us = 0;
bool is_recording = false;
uint32_t sample_counter = 0;

// ═══════════════════════════════════════════════════════════════════════════
// FUNCTION PROTOTYPES
// ═══════════════════════════════════════════════════════════════════════════

float apply_highpass(float x);
float apply_lowpass(float x);
float apply_notch(float x);
void  reset_filters();
void  process_serial_command();

// ═══════════════════════════════════════════════════════════════════════════
// SETUP
// ═══════════════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(BAUD_RATE);
  
  // Wait for serial connection (comment out for standalone operation)
  while (!Serial) {
    delay(10);
  }
  
  // Initialize I2C
  Wire.begin();
  Wire.setClock(400000);  // 400 kHz Fast Mode
  
  // Initialize ADS1115
  if (!ads.begin(0x48)) {
    Serial.println("ERROR: ADS1115 not found! Check wiring:");
    Serial.println("  SDA -> A4, SCL -> A5, ADDR -> GND");
    while (1) {
      delay(1000);
    }
  }
  
  // Configure ADS1115
  ads.setGain(ADS_GAIN);
  ads.setDataRate(RATE_ADS1115_250SPS);  // Closest to 256 Hz
  
  Serial.println("# EEG BCI - BioAmp EXG Pill + ADS1115");
  Serial.println("# Sample Rate: 256 Hz | Resolution: 16-bit | Range: ±4.096V");
  Serial.println("# Filters: HP 0.5Hz, LP 40Hz");
  Serial.println("# Send 'START' to begin recording, 'STOP' to end");
  Serial.println("# Ready. Waiting for START command...");
  
  last_sample_us = micros();
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN LOOP
// ═══════════════════════════════════════════════════════════════════════════

void loop() {
  // Check for serial commands
  process_serial_command();
  
  // Precise timing control
  unsigned long now_us = micros();
  if ((now_us - last_sample_us) < SAMPLE_PERIOD_US) {
    return;  // Not time for next sample yet
  }
  last_sample_us = now_us;
  
  // Only sample if recording is active
  if (!is_recording) {
    return;
  }
  
  // ── Read ADS1115 ───────────────────────────────────────────
  int16_t adc_raw = ads.readADC_SingleEnded(0);  // A0 channel
  
  // Convert to millivolts
  // GAIN_ONE: 1 LSB = 0.125 mV
  float voltage_mv = ads.computeVolts(adc_raw) * 1000.0f;
  
  // ── Apply signal processing pipeline ───────────────────────
  
  // 1. High-pass filter (remove DC and drift)
  float hp_signal = apply_highpass(voltage_mv);
  
  // 2. Low-pass filter (remove muscle artifacts)
  float lp_signal = apply_lowpass(hp_signal);
  
  // 3. Optional 60Hz notch filter
  float filtered_signal = lp_signal;
  if (NOTCH_ENABLE) {
    filtered_signal = apply_notch(lp_signal);
  }
  
  // 4. Baseline correction (adaptive DC removal)
  baseline_sum += filtered_signal;
  baseline_count++;
  if (baseline_count > BASELINE_WINDOW) {
    baseline_sum -= baseline_sum / BASELINE_WINDOW;
    baseline_count = BASELINE_WINDOW;
  }
  float baseline = baseline_sum / max(baseline_count, 1);
  float corrected_signal = filtered_signal - baseline;
  
  // ── Output to serial ───────────────────────────────────────
  // Send ONLY the processed voltage value for Python to parse
  // Scaling to fit typical display range (±500 arbitrary units)
  // Adjust scaling factor based on your signal amplitude
  float output_value = corrected_signal * 2.0f + 500.0f;  
  
  Serial.println(output_value, 4);  // 4 decimal places
  
  sample_counter++;
  
  // ── Timing diagnostics (every 5 seconds) ───────────────────
  if (sample_counter % (SAMPLE_RATE * 5) == 0) {
    // This will appear in Python console but won't interfere with data
    // Comment out if you want clean output
    // Serial.print("# Samples: "); Serial.println(sample_counter);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// FILTER IMPLEMENTATIONS
// ═══════════════════════════════════════════════════════════════════════════

// High-pass filter (1st order IIR, fc = 0.5 Hz)
float apply_highpass(float x) {
  float y = HP_ALPHA * (hp_y_prev + x - hp_x_prev);
  hp_x_prev = x;
  hp_y_prev = y;
  return y;
}

// Low-pass filter (1st order IIR, fc = 40 Hz)
float apply_lowpass(float x) {
  lp_y_prev = lp_y_prev + LP_ALPHA * (x - lp_y_prev);
  return lp_y_prev;
}

// Simple moving average notch filter for 60 Hz
float apply_notch(float x) {
  notch_buffer[notch_idx] = x;
  notch_idx = (notch_idx + 1) % NOTCH_TAP_60HZ;
  
  float sum = 0.0f;
  for (int i = 0; i < NOTCH_TAP_60HZ; i++) {
    sum += notch_buffer[i];
  }
  return sum / NOTCH_TAP_60HZ;
}

// Reset all filter states
void reset_filters() {
  hp_x_prev = 0.0f;
  hp_y_prev = 0.0f;
  lp_y_prev = 0.0f;
  baseline_sum = 0.0f;
  baseline_count = 0;
  
  for (int i = 0; i < NOTCH_TAP_60HZ; i++) {
    notch_buffer[i] = 0.0f;
  }
  notch_idx = 0;
}

// ═══════════════════════════════════════════════════════════════════════════
// SERIAL COMMAND PROCESSING
// ═══════════════════════════════════════════════════════════════════════════

void process_serial_command() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();
    
    if (cmd == "START") {
      is_recording = true;
      sample_counter = 0;
      reset_filters();
      Serial.println("# Recording started");
      
    } else if (cmd == "STOP") {
      is_recording = false;
      Serial.println("# Recording stopped");
      Serial.print("# Total samples: ");
      Serial.println(sample_counter);
      
    } else if (cmd == "STATUS") {
      Serial.print("# Recording: ");
      Serial.println(is_recording ? "YES" : "NO");
      Serial.print("# Samples: ");
      Serial.println(sample_counter);
      
    } else if (cmd == "RESET") {
      reset_filters();
      sample_counter = 0;
      Serial.println("# Filters reset");
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// NOTES FOR OPTIMIZATION
// ═══════════════════════════════════════════════════════════════════════════
/*
 * SIGNAL QUALITY TIPS:
 * 
 * 1. Electrode Placement:
 *    - For motor imagery (hand movement): C3/C4 (10-20 system)
 *    - For relaxation/focus: Fp1/Fp2 (frontal)
 *    - For eye blink: Above/below eye
 * 
 * 2. Reduce Noise:
 *    - Use battery power (USB power bank) instead of wall adapter
 *    - Keep electrode cables short and twisted together
 *    - Apply conductive gel generously
 *    - Clean skin with alcohol wipe before applying electrodes
 * 
 * 3. ADS1115 Settings:
 *    - GAIN_ONE (±4.096V) for BioAmp's 0-5V output range
 *    - 250 SPS is optimal balance of speed and noise rejection
 *    - Differential mode (A0-A1) can be used for even better CMRR
 * 
 * 4. Filter Tuning:
 *    - Increase HP fc to 1-2 Hz for faster baseline stabilization
 *    - Decrease LP fc to 30 Hz if EMG contamination is high
 *    - Enable NOTCH_ENABLE if 60Hz powerline noise is visible
 * 
 * 5. Baseline Drift:
 *    - BASELINE_WINDOW of 2 seconds works for most scenarios
 *    - Increase to 5-10 seconds for very stable recordings
 *    - Decrease to 0.5-1 second for fast-changing signals
 */
