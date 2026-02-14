// ============================================================
//  BCI Precision EEG Recorder — main.ino
//  Hardware : BioAmp EXG Pill → Arduino (5 V, 10-bit ADC, A0)
// ============================================================

#define SAMPLE_RATE   256
#define BAUD_RATE     115200
#define INPUT_PIN     A0

#define ADC_REF_MV    5000.0f
#define ADC_MAX       1024.0f
#define DC_OFFSET     500.0f
#define SMOOTH_WIN    8

static float  smoothBuf[SMOOTH_WIN] = {0};
static int    smoothIdx  = 0;
static bool   running    = false;

float EEGFilter(float input);
float NotchFilter50Hz(float input);

void setup() {
  Serial.begin(BAUD_RATE);
  analogReference(DEFAULT);
  for (int i = 0; i < SMOOTH_WIN; i++) smoothBuf[i] = 0.0f;
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if      (cmd == "START") running = true;
    else if (cmd == "STOP")  running = false;
  }

  if (!running) return;

  static unsigned long lastMicros = 0;
  unsigned long nowMicros = micros();
  if (nowMicros - lastMicros < 3906UL) return;
  lastMicros += 3906UL;

  int   raw = analogRead(INPUT_PIN);
  float mV  = ((float)raw - (ADC_MAX * 0.5f)) * (ADC_REF_MV / ADC_MAX);

  float filtered = EEGFilter(mV);
  float notched  = NotchFilter50Hz(filtered);

  smoothBuf[smoothIdx] = notched;
  smoothIdx = (smoothIdx + 1) % SMOOTH_WIN;
  float sum = 0.0f;
  for (int i = 0; i < SMOOTH_WIN; i++) sum += smoothBuf[i];
  float smoothed = sum / (float)SMOOTH_WIN;

  float output = smoothed + DC_OFFSET;
  if (output < 0.0f) output = 0.0f;

  Serial.println(output, 6);
}

float EEGFilter(float input) {
  float output = input;

  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.00537118f)*z1 - 0.28067741f*z2;
    output   = 0.00653475f*x + 0.01306950f*z1 + 0.00653475f*z2;
    z2 = z1; z1 = x; }

  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.22628006f)*z1 - 0.62545541f*z2;
    output   = 1.00000000f*x + 2.00000000f*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.92816562f)*z1 - 0.92972279f*z2;
    output   = 1.00000000f*x + (-2.00000000f)*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  { static float z1 = 0.0f, z2 = 0.0f;
    float x = output - (-1.97280896f)*z1 - 0.97417960f*z2;
    output   = 1.00000000f*x + (-2.00000000f)*z1 + 1.00000000f*z2;
    z2 = z1; z1 = x; }

  return output;
}

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