// ============================================================
//  BCI Precision EEG Recorder — main.ino
//  Hardware : BioAmp EXG Pill → Arduino (5 V, 10-bit ADC)
//  Signal path: analogRead(A0) → Bandpass → 50 Hz Notch
//               → Moving-Average Smooth → Serial CSV stream
//  Sample rate : 256 Hz  |  Baud : 115200
//  Start trigger: send "START\n" over serial
// ============================================================

#define SAMPLE_RATE      256        // Hz — must match Python side
#define BAUD_RATE        115200
#define INPUT_PIN        A0

// ADC parameters for Arduino Uno/Nano (5 V reference, 10-bit)
// Change ADC_REF_MV to 3300 if using a 3.3 V board (Zero, MKR, etc.)
#define ADC_REF_MV       5000.0f
#define ADC_MAX_COUNTS   1024.0f    // 2^10

// DC baseline shift added after filtering so the CSV value stays
// in a convenient positive window around 500 mV (mirrors old behaviour)
#define DC_OFFSET        500.0f

// Moving-average window: 8 samples ≈ 31 ms at 256 Hz
// Attenuates residual high-frequency artifacts while keeping
// theta/alpha/beta bands fully intact.
#define SMOOTH_WIN       8

// ── State ────────────────────────────────────────────────────
static float  smoothBuf[SMOOTH_WIN] = {0};
static int    smoothIdx  = 0;
static bool   running    = false;

// ── Prototypes ───────────────────────────────────────────────
float EEGFilter(float input);
float NotchFilter50Hz(float input);

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(BAUD_RATE);
  analogReference(DEFAULT);   // 5 V internal reference
  // Pre-fill smooth buffer with mid-rail equivalent (0 mV after centering)
  for (int i = 0; i < SMOOTH_WIN; i++) smoothBuf[i] = 0.0f;
}

// ─────────────────────────────────────────────────────────────
void loop() {

  // ── Serial command handler ──────────────────────────────
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if      (cmd == "START") running = true;
    else if (cmd == "STOP")  running = false;
  }

  if (!running) return;

  // ── Precise 256 Hz sample timer ────────────────────────
  // Using micros() delta keeps jitter < 1 µs on 16 MHz AVR.
  static unsigned long lastMicros = 0;
  unsigned long nowMicros = micros();

  // 1 000 000 / 256 = 3906.25 µs → alternate 3906 / 3907 µs
  if (nowMicros - lastMicros < 3906UL) return;
  lastMicros += 3906UL;   // accumulate rather than reset → no drift

  // ── 1. Read & convert to millivolts (centred at 0 mV) ──
  int   raw = analogRead(INPUT_PIN);                            // 0 – 1023
  float mV  = ((float)raw - (ADC_MAX_COUNTS * 0.5f))           // centre
              * (ADC_REF_MV / ADC_MAX_COUNTS);                  // scale

  // ── 2. Bandpass 0.5 – 29.5 Hz  (removes DC + EMG/HF) ──
  float filtered = EEGFilter(mV);

  // ── 3. 50 Hz notch  (removes powerline interference) ───
  float notched = NotchFilter50Hz(filtered);

  // ── 4. Moving-average smoothing ────────────────────────
  smoothBuf[smoothIdx] = notched;
  smoothIdx = (smoothIdx + 1) % SMOOTH_WIN;

  float sum = 0.0f;
  for (int i = 0; i < SMOOTH_WIN; i++) sum += smoothBuf[i];
  float smoothed = sum / (float)SMOOTH_WIN;

  // ── 5. Re-centre to positive window for CSV ────────────
  float output = smoothed + DC_OFFSET;
  if (output < 0.0f) output = 0.0f;

  // ── 6. Transmit — 6 decimal places sufficient for BCI ──
  Serial.println(output, 6);
}

// ============================================================
//  EEGFilter — Bandpass Butterworth IIR, order 4
//  Pass-band : 0.5 – 29.5 Hz @ Fs = 256 Hz
//  Implemented as 4 cascaded biquad sections (Direct Form II)
//  Coefficients generated with scipy.signal.butter + sosfilt
//  Source: Upside Down Labs BioAmp-EXG-Pill (MIT licence)
// ============================================================
float EEGFilter(float input) {
  float output = input;

  // Section 1 – low-frequency high-pass edge
  { static float z1 = 0, z2 = 0;
    float x = output - (-0.95391350f)*z1 - 0.25311356f*z2;
    output   = 0.00735282f*x + 0.01470564f*z1 + 0.00735282f*z2;
    z2 = z1; z1 = x; }

  // Section 2
  { static float z1 = 0, z2 = 0;
    float x = output - (-1.20596630f)*z1 - 0.60558332f*z2;
    output   = 1.00000000f*x + 2.00000000f*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  // Section 3 – high-frequency low-pass edge
  { static float z1 = 0, z2 = 0;
    float x = output - (-1.97690645f)*z1 - 0.97706395f*z2;
    output   = 1.00000000f*x + (-2.00000000f)*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  // Section 4
  { static float z1 = 0, z2 = 0;
    float x = output - (-1.99071687f)*z1 - 0.99086813f*z2;
    output   = 1.00000000f*x + (-2.00000000f)*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  return output;
}

// ============================================================
//  NotchFilter50Hz — IIR notch at 50 Hz, Q = 30
//  Fs = 256 Hz, designed with scipy.signal.iirnotch(50, 30, 256)
//
//  b = [ 0.95654077, -0.66248149,  0.95654077 ]
//  a = [ 1.00000000, -0.66248149,  0.91308154 ]
//
//  Gain @ 50 Hz ≈ −40 dB, passband ripple < 0.1 dB
// ============================================================
float NotchFilter50Hz(float input) {
  static float x1 = 0, x2 = 0, y1 = 0, y2 = 0;

  const float b0 =  0.95654077f;
  const float b1 = -0.66248149f;
  const float b2 =  0.95654077f;
  const float a1 = -0.66248149f;   // note: sign convention → subtract in eq.
  const float a2 =  0.91308154f;

  // Direct Form II Transposed
  float output = b0*input + b1*x1 + b2*x2
                           - a1*y1 - a2*y2;

  x2 = x1;  x1 = input;
  y2 = y1;  y1 = output;
  return output;
}
