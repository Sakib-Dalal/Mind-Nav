# Acquisition hardware

| Connection | Destination |
|---|---|
| BioAmp OUT | ADS1115 A0 |
| BioAmp GND | Shared acquisition ground |
| ADS1115 SDA / SCL | Uno A4 / A5 |
| ADS1115 ADDR | GND (`0x48`) |
| ADS1115 ALERT/RDY | **Uno D2** — new in v2 |
| ADS1115 supply | Appropriate supply per board specification; nominally 5 V in the existing Uno arrangement |

Use Adafruit ADS1X15 2.6.2+ and its BusIO dependency. The sketch uses continuous 250 SPS conversions and the library’s conversion-ready comparator configuration. D2 uses `INPUT_PULLUP`; missing ALERT/RDY wiring produces no samples and a visible timeout. I²C is 400 kHz, serial is 115200 baud.

`GAIN_TWOTHIRDS` selects ±6.144 V full scale. This avoids clipping the upper part of a nominal 0–5 V amplifier output at the old 4.096 V limit. It does **not** permit exceeding ADC supply/input limits. There is no `* 2 + 500` transform or software filtering in the new firmware. BioAmp’s physical analog filter remains part of the acquisition chain; keep its setup consistent between training and use.

## Protocol v2

```text
# MINDNAV,2,250,mV,RAW
0,2040050,2499.9375
1,2044052,2501.4375
```

Fields are unsigned sample sequence, unsigned `micros()` timestamp, and raw ADC millivolts. Comments start with `#`. Numeric single-value v1 output is rejected. Commands are newline-terminated `START`, `STOP`, and `STATUS`; parsing is bounded and nonblocking.

Rust handles 32-bit timer wrap, resets filters/disarms on sequence gaps or sample intervals outside 2–8 ms, and reports a smoothed measured rate. Three seconds without samples ends the connection and saves an active recording as interrupted. It never silently starts a simulator.

The ADC clock makes 250 SPS nominal. The app retains device timing but does not resample moderate clock drift. Sequence numbers count emitted readings; missed ready interrupts are primarily visible as timestamp gaps. Validate timing on the actual board.

The sketch does not provide electrical isolation. Use suitable isolated acquisition hardware and qualified supervision before attaching electrodes. ADC mV cannot be interpreted as electrode µV until amplifier gain is measured. No board is flashed by the software build.

References: [TI ADS1115 specifications](https://www.ti.com/product/ADS1115), [Adafruit ADS1X15 source](https://github.com/adafruit/Adafruit_ADS1X15).
