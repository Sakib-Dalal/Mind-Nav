#include <Adafruit_ADS1X15.h>

#define SAMPLE_RATE 256
#define BAUD_RATE 115200
#define DC_OFFSET 500.00000000 

Adafruit_ADS1115 ads;

// Ultra-precision conversion factor for ADS1115
// GAIN_ONE: 4.096V range / 32768 levels = 0.125 mV exactly
const double voltsPerBit = 0.12500000; 

// Moving Average Buffer for secondary smoothing
const int smoothWindow = 10;
double buffer[smoothWindow];
int bufferIdx = 0;
bool running = false;

void setup() {
  Serial.begin(BAUD_RATE);
  if (!ads.begin()) while (1);

  ads.setGain(GAIN_ONE);
  ads.setDataRate(RATE_ADS1115_860SPS); // Max hardware sampling speed
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    if (cmd == "START") running = true;
  }

  if (!running) return;

  static unsigned long lastMicros = 0;
  unsigned long currentMicros = micros();

  // Precise 256Hz timing (3906.25 microseconds)
  if (currentMicros - lastMicros >= 3906) {
    lastMicros = currentMicros;

    int16_t raw_adc = ads.readADC_SingleEnded(0);
    double milliVolts = (double)raw_adc * voltsPerBit;

    // Filter Chain using double-precision math
    double filtered = EEGFilter(milliVolts);
    double notched = NotchFilter50Hz(filtered);
    
    // Smoothing Buffer
    buffer[bufferIdx] = notched + DC_OFFSET;
    bufferIdx = (bufferIdx + 1) % smoothWindow;
    
    double smoothSum = 0;
    for(int i=0; i<smoothWindow; i++) smoothSum += buffer[i];
    double finalSignal = smoothSum / (double)smoothWindow;
    
    if (finalSignal < 0) finalSignal = 0.00000000;

    // Output with 8 decimal places for maximum BCI feature extraction
    Serial.println(finalSignal, 8); 
  }
}

// Notch and Bandpass filters optimized for 256Hz
double NotchFilter50Hz(double input) {
  static double x1, x2, y1, y2;
  double a0 = 1.0, a1 = -0.654, a2 = 1.0;
  double b1 = -0.638, b2 = 0.952;
  double output = a0*input + a1*x1 + a2*x2 - b1*y1 - b2*y2;
  x2 = x1; x1 = input; y2 = y1; y1 = output;
  return output;
}

double EEGFilter(double input) {
  double output = input;
  { static double z1, z2; double x = output - -0.95391350*z1 - 0.25311356*z2;
    output = 0.00735282*x + 0.01470564*z1 + 0.00735282*z2; z2 = z1; z1 = x; }
  { static double z1, z2; double x = output - -1.20596630*z1 - 0.60558332*z2;
    output = 1.00000000*x + 2.00000000*z1 + 1.00000000*z2; z2 = z1; z1 = x; }
  { static double z1, z2; double x = output - -1.97690645*z1 - 0.97706395*z2;
    output = 1.00000000*x + -2.00000000*z1 + 1.00000000*z2; z2 = z1; z1 = x; }
  { static double z1, z2; double x = output - -1.99071687*z1 - 0.99086813*z2;
    output = 1.00000000*x + -2.00000000*z1 + 1.00000000*z2; z2 = z1; z1 = x; }
  return output;
}