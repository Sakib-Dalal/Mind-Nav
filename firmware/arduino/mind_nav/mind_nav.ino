/* Mind-Nav acquisition firmware v2 — Arduino Uno + ADS1115 + BioAmp.
 * ADS1115 A0 <- BioAmp OUT; SDA=A4, SCL=A5, GND shared.
 * ADS1115 ALERT/RDY -> Uno D2 (conversion-ready input with pull-up).
 * Install Adafruit ADS1X15. The app does all software filtering in Rust.
 * Output: sequence,micros,raw_adc_millivolts at nominal 250 SPS.
 * Commands: START, STOP, STATUS. All diagnostics begin with #.
 * ADC millivolts are not electrode microvolts: BioAmp gain is not calibrated.
 * Use medically suitable isolation before connecting electrodes to a person.
 */
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <string.h>

Adafruit_ADS1115 ads;
constexpr uint8_t READY_PIN = 2;
volatile bool conversionReady = false;
bool streaming = false;
uint32_t sequence = 0;
char commandBuffer[24];
uint8_t commandLength = 0;

void readyISR() { conversionReady = true; }
void status() {
  Serial.println(F("# MINDNAV,2,250,mV,RAW"));
  Serial.println(streaming ? F("# STREAMING") : F("# READY"));
}
void handleCommand() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      commandBuffer[commandLength] = 0;
      if (strcmp(commandBuffer, "START") == 0) {
        sequence = 0;
        conversionReady = false;
        streaming = true;
        // Adafruit configures comparator thresholds for conversion-ready pulses.
        ads.startADCReading(ADS1X15_REG_CONFIG_MUX_SINGLE_0, true);
        status();
      } else if (strcmp(commandBuffer, "STOP") == 0) {
        streaming = false;
        status();
      } else if (strcmp(commandBuffer, "STATUS") == 0) {
        status();
      } else {
        Serial.println(F("# Unknown command"));
      }
      commandLength = 0;
    } else if (commandLength < sizeof(commandBuffer) - 1) {
      commandBuffer[commandLength++] = c;
    } else {
      commandLength = 0;
    }
  }
}
void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);
  pinMode(READY_PIN, INPUT_PULLUP);
  if (!ads.begin(0x48)) {
    Serial.println(F("# ERROR: ADS1115 not found at 0x48"));
    while (true) delay(1000);
  }
  // +/-6.144 V range avoids clipping a 0–5 V amplifier at 4.096 V.
  // Analog input must still remain within the ADC supply rails.
  ads.setGain(GAIN_TWOTHIRDS);
  ads.setDataRate(RATE_ADS1115_250SPS);
  attachInterrupt(digitalPinToInterrupt(READY_PIN), readyISR, FALLING);
  status();
}
void loop() {
  handleCommand();
  if (!streaming || !conversionReady) return;
  noInterrupts();
  conversionReady = false;
  interrupts();
  const uint32_t stamp = micros();
  const int16_t raw = ads.getLastConversionResults();
  const float millivolts = ads.computeVolts(raw) * 1000.0f;
  Serial.print(sequence++);
  Serial.print(',');
  Serial.print(stamp);
  Serial.print(',');
  Serial.println(millivolts, 4);
}
