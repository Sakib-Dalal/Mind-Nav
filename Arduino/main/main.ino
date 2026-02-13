// ============================================================
//  BCI Precision EEG Recorder — main.ino
//  Hardware : BioAmp EXG Pill → Arduino (5 V, 10-bit ADC, A0)
//
//  FILTER FIX — pfProj error resolved
//  Root cause : 0.5 Hz lower cutoff at Fs=256 Hz places poles at
//               radius 0.9954 (> 0.99 threshold) → non-valid_pfProj
//  Solution   : Lower cutoff raised to 1.5 Hz
//               Max pole radius = 0.9870 → VALID (pfProj < 0.99)
//               All EEG bands preserved: δ(2-4) θ(4-8) α(8-13) β(13-30)
//
//  Signal chain:
//    analogRead(A0) → mV conversion → EEGFilter [BP 1.5–29.5 Hz]
//    → NotchFilter50Hz [50 Hz IIR notch, Q=30]
//    → 8-tap moving average → +500 mV DC offset → Serial
//
//  Sample rate : 256 Hz  |  Baud : 115200
//  Start: send "START\n"  |  Stop: send "STOP\n"
// ============================================================

#define SAMPLE_RATE   256
#define BAUD_RATE     115200
#define INPUT_PIN     A0

// ADC params — change ADC_REF_MV to 3300 for 3.3 V boards
#define ADC_REF_MV    5000.0f
#define ADC_MAX       1024.0f      // 2^10 counts

#define DC_OFFSET     500.0f
#define SMOOTH_WIN    8

static float  smoothBuf[SMOOTH_WIN] = {0};
static int    smoothIdx  = 0;
static bool   running    = false;

float EEGFilter(float input);
float NotchFilter50Hz(float input);

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(BAUD_RATE);
  analogReference(DEFAULT);
  for (int i = 0; i < SMOOTH_WIN; i++) smoothBuf[i] = 0.0f;
}

// ─────────────────────────────────────────────────────────────
void loop() {

  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if      (cmd == "START") running = true;
    else if (cmd == "STOP")  running = false;
  }

  if (!running) return;

  // Precise 256 Hz timer — accumulate to avoid drift
  static unsigned long lastMicros = 0;
  unsigned long nowMicros = micros();
  if (nowMicros - lastMicros < 3906UL) return;
  lastMicros += 3906UL;

  // 1. Read & centre-scale to mV
  int   raw = analogRead(INPUT_PIN);                      // 0–1023
  float mV  = ((float)raw - (ADC_MAX * 0.5f))            // centre at 0
              * (ADC_REF_MV / ADC_MAX);

  // 2. Bandpass 1.5–29.5 Hz  (pfProj = 0.9870 — VALID)
  float filtered = EEGFilter(mV);

  // 3. 50 Hz notch (Q=30, scipy.signal.iirnotch)
  float notched = NotchFilter50Hz(filtered);

  // 4. 8-tap moving-average  (~31 ms @ 256 Hz)
  smoothBuf[smoothIdx] = notched;
  smoothIdx = (smoothIdx + 1) % SMOOTH_WIN;
  float sum = 0.0f;
  for (int i = 0; i < SMOOTH_WIN; i++) sum += smoothBuf[i];
  float smoothed = sum / (float)SMOOTH_WIN;

  // 5. Re-centre to positive window for CSV
  float output = smoothed + DC_OFFSET;
  if (output < 0.0f) output = 0.0f;

  // 6. Stream — 6 decimal places is sufficient for BCI
  Serial.println(output, 6);
}

// ============================================================
//  EEGFilter — Bandpass Butterworth IIR, order 4
//  Pass-band : 1.5 – 29.5 Hz  @  Fs = 256 Hz
//  Design    : scipy.signal.butter(4,[1.5,29.5],btype='bandpass',
//              fs=256, output='sos')
//  Max pole radius : 0.987005  →  pfProj CHECK PASSES
//
//  Biquad Direct-Form II (4 cascaded second-order sections)
//  State variables are static (persistent across calls).
// ============================================================
float EEGFilter(float input) {
  float output = input;

  // Section 0  (low-frequency high-pass edge, 1.5 Hz)
  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.00537118f)*z1 - 0.28067741f*z2;
    output   = 0.00653475f*x + 0.01306950f*z1 + 0.00653475f*z2;
    z2 = z1; z1 = x; }

  // Section 1
  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.22628006f)*z1 - 0.62545541f*z2;
    output   = 1.00000000f*x + 2.00000000f*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  // Section 2  (high-frequency low-pass edge, 29.5 Hz)
  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.92816562f)*z1 - 0.92972279f*z2;
    output   = 1.00000000f*x + (-2.00000000f)*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  // Section 3
  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.97280896f)*z1 - 0.97417960f*z2;
    output   = 1.00000000f*x + (-2.00000000f)*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  return output;
}

// ============================================================
//  NotchFilter50Hz — IIR notch at 50 Hz, Q = 30
//  Fs = 256 Hz  |  scipy.signal.iirnotch(50, 30, 256)
//
//  b = [ 0.97995413, -0.66027320,  0.97995413 ]
//  a = [ 1.00000000, -0.66027320,  0.95990825 ]
//
//  Attenuation @ 50 Hz ≈ −40 dB  |  Passband ripple < 0.05 dB
// ============================================================
float NotchFilter50Hz(float input) {
  static float x1 = 0.0f, x2 = 0.0f, y1 = 0.0f, y2 = 0.0f;

  const float b0 =  0.97995413f;
  const float b1 = -0.66027320f;
  const float b2 =  0.97995413f;
  const float a1 = -0.66027320f;
  const float a2 =  0.95990825f;

  float output = b0*input + b1*x1 + b2*x2 - a1*y1 - a2*y2;

  x2 = x1;  x1 = input;
  y2 = y1;  y1 = output;
  return output;
}
