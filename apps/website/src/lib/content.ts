export type Block =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[]; ordered?: boolean }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "code"; label: string; code: string }
  | { type: "note"; title: string; text: string; tone: "info" | "warning" }
  | {
      type: "links";
      items: { label: string; href: string; download?: boolean }[];
    }
  | { type: "diagram"; variant: "wiring" | "pipeline" }
  | { type: "platforms" }
  | { type: "image"; src: string; alt: string; caption: string };
export type Section = { id: string; title: string; blocks: Block[] };
export type Chapter = { lead?: string; sections: Section[]; source: string };
const p = (text: string): Block => ({ type: "paragraph", text });
const list = (items: string[], ordered = false): Block => ({
  type: "list",
  items,
  ordered,
});
const table = (headers: string[], rows: string[][]): Block => ({
  type: "table",
  headers,
  rows,
});
const code = (label: string, code: string): Block => ({
  type: "code",
  label,
  code,
});
const note = (
  title: string,
  text: string,
  tone: "info" | "warning" = "info",
): Block => ({ type: "note", title, text, tone });
const links = (
  items: { label: string; href: string; download?: boolean }[],
): Block => ({ type: "links", items });
export const chapters: Record<string, Chapter> = {
  guide: {
    source: "README.md · desktop Help, Recorder, and Model Studio",
    lead: "Start with the desktop app in Demo mode, then move to your acquisition hardware when it is ready. This path covers the complete first-session workflow.",
    sections: [
      {
        id: "before-you-start",
        title: "Before you start",
        blocks: [
          p(
            "Mind-Nav uses a Rust core, a Tauri 2 desktop shell, and a Svelte 5 interface. Recording, model creation, and live inference run on the same computer. The active application does not require Python, a notebook, or a cloud account.",
          ),
          links([
            {
              label: "Check software and hardware requirements",
              href: "#/requirements",
            },
          ]),
          note(
            "Try the workflow without electrodes",
            "Demo mode provides synthetic input for exploring recording, model creation, and practice. Demo results are labeled and cannot be used as evidence of EEG decoding performance.",
          ),
        ],
      },
      {
        id: "install",
        title: "01 / Install and open the desktop app",
        blocks: [
          p(
            "Install Git, stable Rust, Node.js 22.12 or a newer supported LTS, and the Tauri dependencies for your platform. Clone the repository, then run these commands:",
          ),
          code(
            "Terminal · first run",
            "git clone https://github.com/Sakib-Dalal/Mind-Nav.git\ncd Mind-Nav/apps/desktop\nnpm ci\nnpm run tauri dev",
          ),
          p(
            "The first native build can take longer while Rust dependencies compile. Keep the terminal open while using the development app.",
          ),
          note(
            "Website, browser preview, and desktop app",
            "This handbook is documentation. The desktop project’s npm run dev command opens a design preview at localhost:1487. Actual serial access, saved recordings, training, and models require npm run tauri dev or a built desktop application.",
          ),
        ],
      },
      {
        id: "connect",
        title: "02 / Choose your input",
        blocks: [
          list(
            [
              "Open device setup in the desktop app.",
              "Choose Demo mode for a first software walkthrough, or select the Arduino serial port after completing the v2 wiring and firmware steps.",
              "Watch the signal and connection status. Give the filters at least three seconds to settle.",
              "Confirm the source is what you selected. A failed connection never silently changes to Demo mode.",
            ],
            true,
          ),
          links([
            { label: "Hardware connection diagram", href: "#/hardware" },
            { label: "Flash protocol v2", href: "#/firmware" },
          ]),
        ],
      },
      {
        id: "record",
        title: "03 / Make a first recording",
        blocks: [
          p(
            "Open EEG Recorder, name your session, and choose 2 minutes. Start recording. During each five-second REST cue, relax. During SELECT, imagine the same chosen action each time, such as closing a hand; movement is not required.",
          ),
          p(
            "Pause whenever needed, then resume. Finish & save writes the session locally. Aim for at least five clean trials of each intent; rejected windows can reduce the usable data.",
          ),
          links([{ label: "Recording guide", href: "#/recording" }]),
        ],
      },
      {
        id: "train-and-practice",
        title: "04 / Train, review, and practice",
        blocks: [
          list(
            [
              "In Model Studio, choose the saved recording and name the model.",
              "Train the personal model. Review balanced accuracy, SELECT precision/recall, and REST false positives.",
              "Explicitly activate the model. Match its source and filter settings to the current input.",
              "Open Practice and run a separate guided sequence. Practice evaluates trials without selecting keys or adding its data to training.",
            ],
            true,
          ),
          note(
            "A validation score is a starting point",
            "Trial-separated results come from one recording. They do not establish reliability on a different day or for a different person. Do not interpret model scores as calibrated probabilities of intent.",
            "warning",
          ),
          links([
            { label: "Model evaluation", href: "#/models" },
            { label: "Practice guide", href: "#/practice" },
          ]),
        ],
      },
      {
        id: "communicate",
        title: "05 / Explore communication",
        blocks: [
          p(
            "Open Communicate. Try a quick phrase or start the scanning keyboard. Press Enter to choose a highlighted row, then press Enter again to choose a key. A USB assistive switch can be mapped to Enter. Escape pauses the scanner.",
          ),
          p(
            "After checking your model and signal, explicitly enable BCI input for selections inside the app. Use patient view for larger communication targets and adjust the scanning interval in Settings.",
          ),
          note(
            "Local speech only",
            "“I need help” speaks on this computer. It does not contact a caregiver or an emergency service.",
            "warning",
          ),
          links([
            {
              label: "Communication and accessibility",
              href: "#/communication",
            },
          ]),
        ],
      },
    ],
  },
  requirements: {
    source: "README.md · docs/HARDWARE.md · Tauri prerequisites",
    lead: "The software can be explored with Demo mode. Live acquisition adds the BioAmp, ADS1115, Arduino, and a suitably isolated electrode setup.",
    sections: [
      {
        id: "software",
        title: "Software requirements",
        blocks: [
          table(
            ["Requirement", "Version or setup", "Purpose"],
            [
              [
                "Node.js + npm",
                "Node.js 22.12+ or a newer supported LTS",
                "Install and build the Svelte interface",
              ],
              [
                "Rust + Cargo",
                "Stable toolchain",
                "DSP, training, device access, and desktop shell",
              ],
              [
                "Git",
                "Installed and available in your terminal",
                "Get the project source",
              ],
              [
                "Tauri dependencies",
                "Platform-specific build tools and WebView",
                "Build and run the native application",
              ],
              [
                "Arduino IDE or CLI",
                "Arduino AVR Boards / Uno target",
                "Compile and upload acquisition firmware",
              ],
              [
                "Adafruit ADS1X15",
                "2.6.2+ with Adafruit BusIO",
                "ADS1115 continuous conversion and ready signal",
              ],
            ],
          ),
          p(
            "Python, PyTorch, scikit-learn, and Jupyter belong to the legacy research workflow. They are not dependencies of the current desktop application.",
          ),
          links([
            {
              label: "Official Tauri prerequisites",
              href: "https://v2.tauri.app/start/prerequisites/",
            },
            {
              label: "Adafruit ADS1X15 source",
              href: "https://github.com/adafruit/Adafruit_ADS1X15",
            },
          ]),
        ],
      },
      {
        id: "platform",
        title: "Set up your operating system",
        blocks: [{ type: "platforms" }],
      },
      {
        id: "components",
        title: "Hardware checklist",
        blocks: [
          table(
            ["Component", "Quantity", "Role and notes"],
            [
              [
                "Arduino Uno",
                "1",
                "Runs the v2 C++ firmware and sends USB serial samples",
              ],
              [
                "ADS1115 ADC board",
                "1",
                "16-bit ADC; A0 input, I²C address 0x48; ALERT/RDY must be accessible",
              ],
              [
                "BioAmp EXG Pill / existing BioAmp front end",
                "1",
                "Amplifies and physically filters the electrode signal; keep its configuration consistent",
              ],
              [
                "Electrode leads and suitable electrodes",
                "As specified by the acquisition setup",
                "Match the amplifier and supervised recording protocol",
              ],
              [
                "Suitable electrical isolation",
                "Required for a person-connected setup",
                "The sketch and Uno/ADC wiring do not provide isolation",
              ],
              [
                "USB data cable",
                "1",
                "Connects the Uno to the host; a charging-only cable will not work",
              ],
              [
                "Jumper wires and a secure interconnect",
                "As needed",
                "Analog signal, I²C, ready line, appropriate supply, and shared acquisition ground",
              ],
              [
                "Computer with audio output",
                "1",
                "Runs the native app and speaks communication messages",
              ],
              [
                "USB assistive switch",
                "Optional",
                "Configure it to send Enter for scanner selection",
              ],
            ],
          ),
          note(
            "Component specifications still apply",
            "The ADC’s ±6.144 V measurement range does not allow inputs outside its permitted supply/input limits. Verify the exact BioAmp and ADC board supply requirements. The existing Uno arrangement is nominally 5 V.",
            "warning",
          ),
          links([
            { label: "Inspect the v2 pin map", href: "#/hardware/pin-map" },
            {
              label: "TI ADS1115 specifications",
              href: "https://www.ti.com/product/ADS1115",
            },
          ]),
        ],
      },
      {
        id: "release-status",
        title: "Build and platform status",
        blocks: [
          p(
            "The project validation record reports a macOS .app build. Signing, notarization, and Windows/Linux installer packaging still need platform-specific release configuration and validation. No minimum CPU or RAM benchmark is established in the repository.",
          ),
          p(
            "For your first build, use the source workflow. You need internet access to fetch dependencies; the desktop recording and inference workflow itself uses local processing.",
          ),
          links([{ label: "Current validation record", href: "#/validation" }]),
        ],
      },
    ],
  },
  hardware: {
    source: "docs/HARDWARE.md · firmware/arduino/mind_nav/mind_nav.ino",
    lead: "Follow the v2 acquisition chain: BioAmp analog output → ADS1115 → Arduino Uno → USB serial → the desktop app.",
    sections: [
      {
        id: "isolation",
        title: "Before connecting a person",
        blocks: [
          note(
            "This is a logical wiring guide, not an isolation design",
            "The Arduino sketch and the connections below do not provide electrical isolation. Use suitable isolated acquisition hardware and qualified supervision before attaching electrodes. Keep person-connected testing separate from a basic electronics bench test.",
            "warning",
          ),
          p(
            "Treat the BioAmp, ADC, and acquisition controller as one acquisition system whose electrical safety must be assessed. A shared acquisition ground in this diagram is a signal reference, not a claim that a USB-powered system is safe for electrode use.",
          ),
        ],
      },
      {
        id: "wiring",
        title: "The v2 connection diagram",
        blocks: [
          { type: "diagram", variant: "wiring" },
          note(
            "The new wire that matters",
            "ADS1115 ALERT/RDY → Uno D2 is required. Conversion-ready interrupts drive the 250 SPS sampling loop. Without this line, the app receives no samples and shows a timeout.",
          ),
        ],
      },
      {
        id: "pin-map",
        title: "Complete pin reference",
        blocks: [
          table(
            ["From", "To", "Purpose"],
            [
              ["BioAmp OUT", "ADS1115 A0", "Single-channel analog input"],
              ["BioAmp GND", "Shared acquisition GND", "Analog reference"],
              [
                "ADS1115 GND",
                "Uno GND / shared acquisition GND",
                "Common reference for the acquisition electronics",
              ],
              ["ADS1115 SDA", "Uno A4 (SDA)", "I²C data · 400 kHz bus"],
              ["ADS1115 SCL", "Uno A5 (SCL)", "I²C clock"],
              ["ADS1115 ADDR", "GND", "Select I²C address 0x48"],
              [
                "ADS1115 ALERT/RDY",
                "Uno D2",
                "Falling-edge conversion-ready interrupt; INPUT_PULLUP",
              ],
              [
                "ADS1115 VDD / VCC",
                "Appropriate board supply",
                "Nominally 5 V in the existing Uno arrangement; verify board specifications",
              ],
              [
                "BioAmp supply",
                "Appropriate amplifier supply",
                "Verify the exact amplifier board specification",
              ],
              [
                "Uno USB",
                "Computer via approved acquisition arrangement",
                "115200 baud serial; isolation requirements still apply",
              ],
            ],
          ),
          p(
            "A0 here means the ADS1115 input, not Uno A0. The active firmware reads the external ADC. A1, A2, and A3 on the ADS1115 are not sampled by this sketch.",
          ),
        ],
      },
      {
        id: "acquisition-settings",
        title: "Acquisition settings",
        blocks: [
          table(
            ["Setting", "Current value"],
            [
              ["Sampling", "Continuous ADS1115 conversions at nominal 250 SPS"],
              ["ADC gain", "GAIN_TWOTHIRDS · ±6.144 V full scale"],
              ["Software filtering on Arduino", "None; raw ADC mV is streamed"],
              ["I²C / address", "400 kHz / 0x48"],
              ["Serial", "115200 baud"],
              ["Ready interrupt", "Uno D2, FALLING, INPUT_PULLUP"],
            ],
          ),
          p(
            "The BioAmp’s physical analog filter remains in the chain. The previous firmware’s ×2 + 500 display transform and software filters are absent. Record and use a model with the same physical amplifier setup.",
          ),
          note(
            "Read the units correctly",
            "The waveform displays ADC millivolts. Electrode microvolts require a measured amplifier gain and cannot be inferred directly from this waveform.",
          ),
        ],
      },
      {
        id: "electrodes",
        title: "Electrode reference",
        blocks: [
          p(
            "The repository includes an international 10–20 position reference and an older BioAmp illustration. These are orientation material, not a validated montage or a person-connection procedure. Select the actual montage and amplifier configuration with qualified supervision.",
          ),
          {
            type: "image",
            src: "/assets/10-20-system.png",
            alt: "Repository reference image of international 10–20 EEG electrode positions, including Fp1, Fp2, C3, Cz, C4, O1 and O2.",
            caption:
              "Original repository reference · Media/10-20-system.png. Position nomenclature only; not a v2 electrical wiring diagram.",
          },
          links([
            {
              label: "Original BioAmp illustration (legacy wiring)",
              href: "/assets/eeg_placement.png",
            },
          ]),
          p(
            "The older illustration shows a different analog connection and omits the external ADC and ready line. Use the v2 pin reference above for the current acquisition electronics.",
          ),
        ],
      },
      {
        id: "bench-check",
        title: "Bench check before recording",
        blocks: [
          list(
            [
              "With power disconnected, check pin names, supply polarity, ground continuity, and the required ALERT/RDY connection.",
              "Compile and upload the v2 sketch with the correct Uno target and ADS1X15 library.",
              "With no person attached, verify the board’s STATUS response and serial sample format.",
              "Check the measured sample rate and dropped-sample count in the desktop app; validate timing on the real board.",
              "Only proceed to person-connected acquisition with suitable isolation and a supervised setup.",
            ],
            true,
          ),
          links([
            { label: "Continue to firmware setup", href: "#/firmware" },
            {
              label: "Download hardware reference",
              href: "/downloads/HARDWARE.md",
              download: true,
            },
          ]),
        ],
      },
    ],
  },
  firmware: {
    source: "firmware/arduino/mind_nav/mind_nav.ino · docs/HARDWARE.md",
    lead: "The active sketch streams raw ADC millivolts with a sample sequence and device timestamp. It targets the Arduino Uno and ADS1115.",
    sections: [
      {
        id: "flash",
        title: "Compile and upload",
        blocks: [
          list(
            [
              "In Arduino IDE, install Arduino AVR Boards and select Arduino Uno.",
              "Install Adafruit ADS1X15 2.6.2 or newer through Library Manager, including Adafruit BusIO.",
              "Open firmware/arduino/mind_nav/mind_nav.ino. Confirm the ADS1115 wiring, especially ALERT/RDY → D2.",
              "Select the connected board’s serial port, then upload the sketch. Uploading replaces the sketch currently on that board.",
              "Close Serial Monitor before connecting the desktop app so only one process owns the port.",
            ],
            true,
          ),
          links([
            {
              label: "Download the v2 Arduino sketch",
              href: "/downloads/mind_nav.ino",
              download: true,
            },
          ]),
          code(
            "Terminal · compile only, from the repository root",
            "arduino-cli compile --fqbn arduino:avr:uno firmware/arduino/mind_nav",
          ),
          p(
            "Compilation does not flash hardware. Upload from Arduino IDE after selecting the actual port, or use arduino-cli upload with your board’s port. If using the downloaded sketch, keep mind_nav.ino inside a folder named mind_nav.",
          ),
        ],
      },
      {
        id: "protocol",
        title: "Protocol v2",
        blocks: [
          code(
            "Serial · 115200 baud · sample response",
            "# MINDNAV,2,250,mV,RAW\n0,2040050,2499.9375\n1,2044052,2501.4375",
          ),
          table(
            ["Field", "Format", "Meaning"],
            [
              [
                "sequence",
                "Unsigned 32-bit integer",
                "Emitted reading counter; resets on START",
              ],
              [
                "micros",
                "Unsigned 32-bit integer",
                "Device timestamp from micros(); wrap handled by Rust",
              ],
              [
                "raw_adc_millivolts",
                "Finite numeric value",
                "ADS1115 conversion in mV; no display transform",
              ],
            ],
          ),
          p(
            "Lines beginning with # are diagnostics or metadata, not samples. The desktop parser rejects legacy single-value output. Commands must end with a newline.",
          ),
          table(
            ["Command", "Behavior"],
            [
              [
                "START",
                "Reset the emitted sequence and start continuous acquisition",
              ],
              ["STOP", "Stop emitting sample readings"],
              ["STATUS", "Report protocol header and # READY or # STREAMING"],
            ],
          ),
        ],
      },
      {
        id: "timing",
        title: "Timing and interruption handling",
        blocks: [
          p(
            "The ADS1115 conversion-ready line triggers a falling-edge interrupt. The loop reads the latest conversion and prints sequence, micros, and mV. The ADC clock sets the nominal 250 SPS rate; it is not a calibrated guarantee of exact timing.",
          ),
          list([
            "Rust handles 32-bit micros() wrap.",
            "Sequence gaps or intervals outside 2–8 ms reset filters and disarm input.",
            "Sequence numbers count emitted readings. Missed ready interrupts are primarily visible as timestamp gaps.",
            "The app reports a smoothed measured rate and does not resample moderate clock drift.",
            "Three seconds without samples ends the connection and saves an active recording as interrupted.",
          ]),
        ],
      },
      {
        id: "firmware-errors",
        title: "Common firmware symptoms",
        blocks: [
          table(
            ["Symptom", "Check"],
            [
              [
                "# ERROR: ADS1115 not found at 0x48",
                "Power, shared GND, SDA/A4, SCL/A5, and ADDR tied to GND",
              ],
              [
                "# READY but no sample rows",
                "Send START with a newline; check ALERT/RDY → D2",
              ],
              [
                "Only one value on each line",
                "Old firmware is running; upload the v2 sketch",
              ],
              [
                "Serial port busy",
                "Close Serial Monitor and any other serial reader",
              ],
              [
                "Upper signal clips",
                "Verify physical input limits and gain; ±6.144 V does not override supply limits",
              ],
            ],
          ),
          links([{ label: "More troubleshooting", href: "#/troubleshooting" }]),
        ],
      },
    ],
  },
  recording: {
    source: "README.md · desktop Recorder · docs/SIGNAL_PIPELINE.md",
    lead: "A recording pairs the incoming signal with alternating REST and SELECT trials so the model can learn a consistent distinction.",
    sections: [
      {
        id: "prepare",
        title: "Prepare a session",
        blocks: [
          list(
            [
              "Connect the Arduino or deliberately choose Demo mode. Confirm the source label.",
              "Wait at least three seconds for filter settling and check the signal-quality message.",
              "Open EEG Recorder and give the session a recognizable name.",
              "Choose 2, 5, or 15 minutes, or record until you choose to stop. Start with two minutes.",
              "Keep amplifier settings and the chosen mental task consistent across recording and later use.",
            ],
            true,
          ),
          note(
            "Watch quality, not just the waveform",
            "Flat input, clipping, abrupt artifacts, gaps, and disconnects are checked. These gain-dependent heuristics are not electrode impedance measurements and can miss smooth movement artifacts.",
          ),
        ],
      },
      {
        id: "cues",
        title: "Follow the cues",
        blocks: [
          table(
            ["Cue", "Duration", "What to do"],
            [
              ["REST", "5 seconds", "Relax and let your gaze settle"],
              [
                "SELECT",
                "5 seconds",
                "Imagine the same action each time, such as closing a hand; physical movement is not required",
              ],
            ],
          ),
          p(
            "Spoken cues can be turned on in Settings. Pause to rest, then resume when ready. The pipeline excludes startup settling and a 500 ms trial-transition guard from native training windows.",
          ),
          p(
            "Aim for at least five clean trials of each intent. The sample count alone is not enough: quality rejection and short trial segments can leave too few eligible windows.",
          ),
        ],
      },
      {
        id: "finish",
        title: "Save and review",
        blocks: [
          p(
            "Use Finish & save, or let a timed recording finish. The session is stored locally and appears in Sessions and Model Studio. Review its source, duration, and trial counts before training.",
          ),
          p(
            "CSV buffers flush every second and metadata writes atomically. If acquisition is interrupted, the app preserves the recording as interrupted; the last unflushed samples may be lost.",
          ),
          links([
            { label: "Train from your recording", href: "#/models" },
            { label: "Storage and exports", href: "#/data" },
          ]),
        ],
      },
    ],
  },
  models: {
    source: "desktop Model Studio · docs/SIGNAL_PIPELINE.md",
    lead: "Model Studio trains a small, inspectable REST/SELECT classifier on your recording. Evaluation and activation are separate steps.",
    sections: [
      {
        id: "create",
        title: "Create a personal model",
        blocks: [
          list(
            [
              "Choose a saved recording, or import an EEG CSV. Review the source and sample rate.",
              "Use at least five clean trials per class, with enough eligible windows after quality rejection.",
              "Give the model a name and choose Train personal model.",
              "Wait for the local training report, review its metrics, and explicitly activate the model when ready.",
            ],
            true,
          ),
          p(
            "The current classifier is deterministic, class-balanced logistic regression with L2 regularization. It uses 20 spectral and time-domain features. Python weights are not loaded by the native app.",
          ),
        ],
      },
      {
        id: "metrics",
        title: "Read the validation report",
        blocks: [
          table(
            ["Metric", "Interpretation"],
            [
              [
                "Balanced accuracy",
                "Average recall across REST and SELECT, reducing class-imbalance bias",
              ],
              [
                "SELECT precision",
                "Of predicted selections, how many were labeled SELECT",
              ],
              [
                "SELECT recall",
                "Of labeled SELECT windows, how many were detected",
              ],
              [
                "REST false-positive rate",
                "How often labeled REST was predicted as SELECT",
              ],
              [
                "Confusion counts",
                "The raw REST/SELECT correct and incorrect predictions",
              ],
              [
                "Per-fold scores",
                "Variation across the trial-separated validation folds",
              ],
            ],
          ),
          note(
            "Check unwanted selections",
            "A high overall score can coexist with an unacceptable REST false-positive rate. No clinical pass threshold is established for this project. Review the report and run separate practice before enabling BCI input.",
            "warning",
          ),
        ],
      },
      {
        id: "evaluation",
        title: "How validation is separated",
        blocks: [
          p(
            "Five folds assign whole trials chronologically within each class. A trial never appears in both training and validation, and each fold’s scaler is fitted only on its training rows. Out-of-fold predictions produce the report; the final model is then fitted on all eligible data.",
          ),
          p(
            "These are within-recording, trial-separated results. They do not measure generalization to a different person, session, or day. Causal filter history may span adjacent trials. Hyperparameters are fixed.",
          ),
          note(
            "Report threshold and live threshold differ",
            "Validation metrics use a 0.5 threshold. The runtime defaults to 0.8, smooths scores, and applies temporal selection checks. A model score is not a calibrated probability of intent.",
          ),
        ],
      },
      {
        id: "activate",
        title: "Activate with the matching source",
        blocks: [
          table(
            ["Model source", "Use"],
            [
              [
                "Device / v2 raw",
                "Can be used with matching live hardware and filter configuration",
              ],
              ["Demo", "Only for the matching synthetic source"],
              [
                "Legacy import",
                "Comparison only; cannot arm native live input",
              ],
            ],
          ),
          p(
            "The JSON model stores its version, features, sample rate, filter configuration, and source contract. A source or configuration change disarms BCI input. Recheck the signal and settings before explicitly enabling it again.",
          ),
          links([
            { label: "Practice with the model", href: "#/practice" },
            { label: "Legacy import rules", href: "#/data/legacy" },
          ]),
        ],
      },
    ],
  },
  practice: {
    source: "docs/SIGNAL_PIPELINE.md · desktop Practice",
    lead: "Practice evaluates a separate guided sequence. It never arms BCI input, selects keys, or feeds its results back into training.",
    sections: [
      {
        id: "run",
        title: "Run a practice sequence",
        blocks: [
          list(
            [
              "Activate a model and connect its matching input source.",
              "Confirm the model’s filter settings match the runtime and the signal has settled.",
              "Open Practice and begin the guided REST/SELECT sequence.",
              "Follow the same mental task used for training, then review correct and skipped trials plus confusion counts.",
            ],
            true,
          ),
          p(
            "Each five-second trial is scored once from the final second’s scores at the selected threshold. A full second of usable samples is required; otherwise that trial is skipped.",
          ),
        ],
      },
      {
        id: "interpret",
        title: "Interpret the result",
        blocks: [
          p(
            "Skipped trials indicate insufficient usable data. They should not be read as correct predictions. Demo practice is explicitly synthetic. A short successful sequence does not establish reliable communication over a day or across sessions.",
          ),
          list([
            "If REST triggers SELECT, inspect the signal, trial strategy, and model report before enabling BCI input.",
            "If many trials are skipped, resolve acquisition quality or timing issues first.",
            "If conditions changed since training, record a new session under the intended setup.",
          ]),
          links([
            { label: "Understand validation limits", href: "#/validation" },
            { label: "Continue to communication", href: "#/communication" },
          ]),
        ],
      },
    ],
  },
  communication: {
    source:
      "desktop Communicate, Settings, and scanner · docs/SIGNAL_PIPELINE.md",
    lead: "Communicate combines quick phrases, locally spoken messages, and a scanning keyboard. Selections stay within the app.",
    sections: [
      {
        id: "phrases",
        title: "Quick phrases and speech",
        blocks: [
          p(
            "Use quick phrases for yes, no, water, help, discomfort, or thanks. Compose a longer message with the keyboard and speak it through the computer’s audio output. Check that the intended listener can hear the device.",
          ),
          note(
            "Help is spoken locally",
            "The “I need help” phrase does not send an alert, call a caregiver, or contact emergency services.",
            "warning",
          ),
        ],
      },
      {
        id: "scanning",
        title: "Use the row-and-column scanner",
        blocks: [
          list(
            [
              "Start scanning. The highlighted row advances at the configured interval.",
              "Press Enter, use an assistive switch mapped to Enter, or select the highlighted control to choose a row.",
              "The scanner moves through that row’s keys. Select again on the key you want.",
              "After two key cycles without a selection, scanning returns to rows. Use Undo to recover from a mistake.",
              "Escape pauses. The board also contains scannable Pause and Finish actions. A paused scanner can be resumed with another switch or BCI selection.",
            ],
            true,
          ),
          table(
            ["Control", "Action"],
            [
              [
                "Enter / mapped assistive switch",
                "Choose the highlighted row, then the highlighted key",
              ],
              ["Escape", "Pause scanning"],
              ["Undo", "Recover from the previous input"],
              [
                "Scannable Pause",
                "Pause without leaving the communication board",
              ],
              ["Scannable Finish", "Exit the scanning interaction"],
            ],
          ),
        ],
      },
      {
        id: "bci-input",
        title: "Enable BCI selections deliberately",
        blocks: [
          p(
            "After reviewing a matching model and practice results, explicitly enable BCI input. The runtime smooths model scores with EMA α = 0.4 and requires three consecutive qualifying predictions. A 1.5-second cooldown and return below 0.4 are required before another selection.",
          ),
          p(
            "Poor-quality windows reset the intent gate. Source changes, filter changes, timing gaps, or disconnects disarm input. A held intent produces one selection edge rather than repeating continuously.",
          ),
          note(
            "Scope of control",
            "BCI selects within Mind-Nav’s scanning board. It does not inject system-wide keystrokes, control a wheelchair, or operate other applications.",
          ),
        ],
      },
      {
        id: "accessibility",
        title: "Adjust the experience",
        blocks: [
          table(
            ["Setting", "Available behavior"],
            [
              ["Scanning interval", "0.6–5 seconds; default 1.5 seconds"],
              ["Selection threshold", "0.60–0.95; default 0.8"],
              ["Patient view", "Large, focused communication targets"],
              ["Text and appearance", "Larger text, light or dark theme"],
              ["Motion and cues", "Reduced motion and optional spoken cues"],
              [
                "Notch filter",
                "50 Hz, 60 Hz, or Off; must match the active model configuration",
              ],
            ],
          ),
          p(
            "Composed messages survive navigation inside the running app and clear when the app closes. Choose a comfortable scanning pace with the person using the board. Usability with intended users still requires supervised evaluation.",
          ),
        ],
      },
    ],
  },
  pipeline: {
    source: "docs/SIGNAL_PIPELINE.md · mind-nav-core",
    lead: "Training and native inference share the same causal Rust preprocessing and feature extraction. The application does not call a Python inference process or a cloud model.",
    sections: [
      {
        id: "flow",
        title: "The processing flow",
        blocks: [
          { type: "diagram", variant: "pipeline" },
          p(
            "The model stores sample rate, high/low-pass frequencies, notch frequency, source domain, and feature version. This contract keeps eligible training data and live input aligned.",
          ),
        ],
      },
      {
        id: "filters",
        title: "Filtering and quality checks",
        blocks: [
          table(
            ["Stage", "Configuration", "Purpose"],
            [
              [
                "Initial DC offset subtraction",
                "Startup estimate",
                "Reduce filter startup transients",
              ],
              ["High-pass", "Second order, 0.5 Hz", "Attenuate slow drift"],
              [
                "Notch",
                "50 or 60 Hz, Q = 30",
                "Attenuate mains-frequency interference",
              ],
              [
                "Low-pass",
                "Second order, 40 Hz",
                "Attenuate higher-frequency content",
              ],
              [
                "Quality gates",
                "Nonfinite, flat, rail, excursion, and abrupt-change checks",
                "Reject unusable windows and reset intent gating",
              ],
            ],
          ),
          p(
            "Filters use normalized RBJ biquads in transposed direct-form II. The high/low-pass stages are Butterworth. Processing is causal: it uses no future samples, introduces latency, and cannot perfectly separate artifacts from brain activity.",
          ),
          note(
            "Quality heuristics are limited",
            "The thresholds depend on amplifier gain. Smooth movement artifacts may pass and useful signals may be rejected. The quality display is not an impedance measurement or a validated EEG-quality score.",
          ),
        ],
      },
      {
        id: "windows",
        title: "Windows and spectral estimates",
        blocks: [
          list([
            "Native windows contain 500 samples: two seconds at 250 SPS.",
            "Live inference updates around four times per second; native training uses non-overlapping windows.",
            "Training excludes three seconds of startup settling and a 500 ms transition guard.",
            "Labels, explicit trial IDs, and timestamp discontinuities delimit groups.",
            "Welch PSD uses one-second Hann segments, 50% overlap, DC detrending, and one-sided power/Hz normalization.",
          ]),
          table(
            ["Band", "Frequency range"],
            [
              ["Delta", "0.5–4 Hz"],
              ["Theta", "4–8 Hz"],
              ["Alpha", "8–13 Hz"],
              ["Beta", "13–30 Hz"],
              ["Gamma range used here", "30–40 Hz"],
            ],
          ),
        ],
      },
      {
        id: "features",
        title: "The 20-feature model input",
        blocks: [
          p(
            "Feature version 1 combines five log band powers and five relative band powers with ten additional descriptors: log RMS, Hjorth mobility, Hjorth complexity, zero crossings, standardized third and fourth moments, alpha/beta and theta/alpha log ratios, band entropy, and normalized line length.",
          ),
          p(
            "The classifier is class-balanced, L2-regularized logistic regression. Scaling is fitted within each training fold, then the final model is fitted on all eligible data. All model reports and source contracts are serialized in versioned JSON.",
          ),
        ],
      },
      {
        id: "gate",
        title: "From score to selection edge",
        blocks: [
          table(
            ["Check", "Default behavior"],
            [
              ["Smoothing", "Exponential moving average, α = 0.4"],
              [
                "Qualification",
                "Three consecutive predictions at or above the selected threshold",
              ],
              ["Threshold", "0.8 by default; adjustable in the desktop app"],
              ["Cooldown", "1.5 seconds"],
              ["Rearm", "Score must return below 0.4"],
              [
                "Invalid input",
                "Poor quality resets the gate; gaps, disconnects, and source/config changes disarm input",
              ],
            ],
          ),
          p(
            "A held selection intent produces one edge. Two-second windows, causal filters, and temporal gating add latency; this project does not claim a measured end-to-end response-time guarantee.",
          ),
          links([
            {
              label: "Download signal contract",
              href: "/downloads/SIGNAL_PIPELINE.md",
              download: true,
            },
            {
              label: "W3C Audio EQ Cookbook",
              href: "https://www.w3.org/TR/audio-eq-cookbook/",
            },
          ]),
        ],
      },
    ],
  },
  data: {
    source: "README.md · docs/SIGNAL_PIPELINE.md · desktop runtime",
    lead: "Recordings, models, and preferences are local files. Native and legacy data have different source contracts and different live-use permissions.",
    sections: [
      {
        id: "storage",
        title: "Storage, export, and recovery",
        blocks: [
          p(
            "The desktop app uses your operating system’s application data directory for app.mindnav.desktop. Settings shows the exact path. CSV recordings, session metadata, versioned JSON models, and preferences live there.",
          ),
          list([
            "Export individual recordings and models through the native save dialog.",
            "Copy the application data folder for backups.",
            "CSV buffers flush every second; metadata writes atomically.",
            "Interrupted recordings can be recovered, with possible loss of the last unflushed samples.",
            "The app does not encrypt saved files or upload recording data.",
          ]),
          note(
            "Message lifetime differs from session storage",
            "The communication message remains while you navigate inside the app, and is cleared when the app closes.",
          ),
        ],
      },
      {
        id: "native-format",
        title: "Native CSV format",
        blocks: [
          code(
            "CSV · header written by the native recorder",
            "timestamp,raw_mv,label,trial_id,source,sample_rate",
          ),
          table(
            ["Column", "Meaning"],
            [
              ["timestamp", "Acquisition timestamp in seconds"],
              ["raw_mv", "Raw ADC millivolts before Rust software filtering"],
              ["label", "0 = REST; 1 = SELECT"],
              [
                "trial_id",
                "Trial group used to keep evaluation splits separate",
              ],
              ["source", "hardware or demo"],
              ["sample_rate", "Declared nominal sample rate: 250 Hz"],
            ],
          ),
          p(
            "The native CSV is a labeled training recording, not a verbatim copy of the three-field serial stream. Preserve trial IDs, source, and sample-rate metadata during export or external processing.",
          ),
        ],
      },
      {
        id: "import",
        title: "Import a recording",
        blocks: [
          p(
            "Open Model Studio and select Import EEG CSV. Detect timing uses declared native sample_rate metadata first. Without native metadata, it estimates the median rate across 200-sample spans from up to 10,000 legacy rows. Nominal 250 Hz and 256 Hz overrides are also available.",
          ),
          table(
            ["CSV content", "Accepted values"],
            [
              ["Signal column", "raw_mv, Signal_Raw, Signal_mV, or eeg_value"],
              ["REST label", "REST or 0"],
              ["SELECT label", "SELECT, CLICK, 1, or 5"],
              ["Unlabelled data", "-1"],
              ["Detected legacy rate", "Rounded estimate must be 125–1000 Hz"],
            ],
          ),
          p(
            "The importer rejects nonfinite samples, unknown labels, mixed demo/hardware domains, conflicting declared rates, files over 256 MB, and more than five million samples. Training accepts up to 20,000 windows.",
          ),
          note(
            "Detected timing is an estimate",
            "Host timestamp batching and clock changes can distort legacy rate estimates. Detect timing does not calibrate the ADC. Preserve native timing metadata when available.",
          ),
        ],
      },
      {
        id: "legacy",
        title: "Understand legacy compatibility",
        blocks: [
          table(
            ["Artifact", "Current behavior"],
            [
              [
                "Native v2 raw recording",
                "Two-second windows; eligible for a matching live hardware model",
              ],
              [
                "Legacy filtered/scaled CSV",
                "One-second comparison windows; cannot arm native live input",
              ],
              ["Demo recording or model", "Synthetic source only"],
              [
                "Python .joblib / PyTorch .pt weights",
                "Archived; not converted or loaded by the Rust runtime",
              ],
            ],
          ),
          p(
            "Legacy signal values are mapped through (value − 500) / 2 to undo the old display transform. Earlier firmware filtering cannot be undone. One-second comparison windows accommodate the old shorter trials.",
          ),
          p(
            "To use live BCI input, record new v2 raw data and train a new model in Model Studio. Retain original legacy files for comparison rather than overwriting them.",
          ),
        ],
      },
      {
        id: "archive",
        title: "What remains in the research archive",
        blocks: [
          p(
            "legacy/ preserves the original Python EEG recorder, navigation app, Jupyter notebooks, six model architectures and their weights, and the optional MicroPython Pico W Wi-Fi LED experiment. They are outside the active Rust build.",
          ),
          p(
            "Existing recordings remain in Data/ and legacy/Notebook/. The six-model architecture comparison and optional Pico feedback are research references, not current desktop runtime capabilities.",
          ),
          links([
            {
              label: "Inspect the repository",
              href: "https://github.com/Sakib-Dalal/Mind-Nav",
            },
            { label: "Repository layout", href: "#/development/layout" },
          ]),
        ],
      },
    ],
  },
  validation: {
    source: "docs/VALIDATION.md · validation record dated 8 September 2026",
    lead: "The repository records software tests, interface checks, and a legacy-data compatibility run. Physical EEG acquisition and patient usability remain separate validation work.",
    sections: [
      {
        id: "status",
        title: "Research status",
        blocks: [
          note(
            "A working research foundation",
            "Mind-Nav is not a clinically validated assistive device. Its tests do not establish electrical safety, clinical decoding accuracy, or suitability for independent patient use.",
            "warning",
          ),
          p(
            "The current Rust pipeline improves consistency between training and inference, trial separation, and failure handling. The project does not claim improved clinical accuracy over the original six-model research implementation.",
          ),
        ],
      },
      {
        id: "tested",
        title: "What the project has checked",
        blocks: [
          table(
            ["Area", "Recorded verification"],
            [
              [
                "Rust signal core",
                "Filter attenuation, Welch normalization, nonfinite/flat rejection, and protocol rejection",
              ],
              [
                "Models and datasets",
                "Trial-separated training, legacy CSV parsing/timing, model serialization, and source mismatch rejection",
              ],
              [
                "Native runtime",
                "Synthetic end-to-end recording, training/reload, interrupted-session recovery, and stale-input disarming",
              ],
              [
                "Intent and scanner",
                "Held-intent debounce, return-to-rest, row/key selection, missed-cycle recovery, Pause/Finish controls",
              ],
              [
                "Frontend",
                "Type checks, production build, light/dark interface and browser control checks",
              ],
              [
                "macOS packaging",
                "Tauri .app produced; native GUI/device flow not manually completed",
              ],
              [
                "Arduino Uno",
                "Compiled with ADS1X15 2.6.2; 7,864 bytes flash and 489 bytes static RAM; no hardware flashed",
              ],
            ],
          ),
          p(
            "The synthetic native integration test drives the real Rust recorder for two minutes of sample time, writes CSV/JSON, trains a model, reloads it, and checks source gating. It is not a physical EEG test.",
          ),
        ],
      },
      {
        id: "legacy-results",
        title: "Legacy-data compatibility results",
        blocks: [
          p(
            "The Rust training example was run against the unchanged Data/eeg_precision_bci.csv recording. These are historical compatibility results at a 0.5 classification threshold, not current-device or patient performance.",
          ),
          table(
            ["Measure", "Recorded result"],
            [
              ["Parsed samples", "292,734"],
              ["Estimated legacy capture rate", "163 Hz"],
              ["Accepted one-second windows", "1,279"],
              ["REST / SELECT windows", "512 / 767"],
              ["Included trials", "513"],
              ["Five-fold balanced accuracy", "87.07%"],
              ["SELECT precision / recall", "89.88% / 89.18%"],
              ["REST false-positive rate", "15.04%"],
            ],
          ),
          table(
            ["Actual label", "Predicted REST", "Predicted SELECT"],
            [
              ["REST", "435", "77"],
              ["SELECT", "83", "684"],
            ],
          ),
          note(
            "Do not use this as a live-use benchmark",
            "The legacy recording was already filtered, and its host timestamps only estimate capture timing. These results confirm parsing and training. Legacy models cannot arm live v2 input.",
            "warning",
          ),
        ],
      },
      {
        id: "remaining",
        title: "What still needs validation",
        blocks: [
          list([
            "Conversion-ready wiring and measured sample timing on the physical board.",
            "Gain-specific signal-quality thresholds and isolated electrode acquisition.",
            "Latency and false activations across days, sessions, and users.",
            "Native serial hardware, speech playback, and file dialogs on target platforms.",
            "Windows/Linux installers, macOS signing and notarization.",
            "Caregiver and patient workflows with the people who will use the system.",
          ]),
          p(
            "The validation record notes that native macOS UI automation could not be completed because Computer Use permission was unavailable. Browser interface checks do not substitute for the native device workflow.",
          ),
          links([
            {
              label: "Download the full validation record",
              href: "/downloads/VALIDATION.md",
              download: true,
            },
          ]),
        ],
      },
    ],
  },
  troubleshooting: {
    source: "docs/HARDWARE.md · README.md · desktop Help and runtime checks",
    lead: "Start with the source and connection status, then check the signal, data contract, and model. A connection error never silently enables simulation.",
    sections: [
      {
        id: "connection",
        title: "Device and connection problems",
        blocks: [
          table(
            ["Symptom", "What to check"],
            [
              [
                "No serial port appears",
                "Use a USB data cable, check board power and OS device recognition, then refresh device setup",
              ],
              [
                "Port is busy or cannot open",
                "Close Arduino Serial Monitor and other serial readers; check OS serial permissions",
              ],
              [
                "ADS1115 not found",
                "Check supply, GND, SDA → A4, SCL → A5, and ADDR → GND (0x48)",
              ],
              [
                "Device connects but no samples arrive",
                "Verify ALERT/RDY → D2, v2 firmware, and the START command",
              ],
              [
                "Expected v2 firmware / single-value output",
                "Upload the current three-field raw-mV sketch",
              ],
              [
                "Disconnect after three seconds",
                "No samples arrived; inspect USB, power, ready wiring, and serial stream",
              ],
              [
                "Gaps or input disarmed",
                "Check the actual device timestamps and wiring; reconnect, settle, and explicitly enable input again",
              ],
            ],
          ),
          links([
            { label: "Wiring diagram", href: "#/hardware/wiring" },
            { label: "Serial protocol", href: "#/firmware/protocol" },
          ]),
        ],
      },
      {
        id: "signal",
        title: "Signal quality problems",
        blocks: [
          table(
            ["Symptom", "What to check"],
            [
              [
                "Filter settling",
                "Allow at least three seconds of stable samples after startup or a reset",
              ],
              [
                "Flat signal",
                "Check BioAmp output, ADS1115 A0, amplifier configuration, and acquisition connections",
              ],
              [
                "Clipping or very large excursions",
                "Verify gain, supply/input limits, and physical signal path before person-connected use",
              ],
              [
                "50/60 Hz interference",
                "Use the appropriate notch setting; the model configuration must match",
              ],
              [
                "Unexpected units",
                "The display is ADC mV, not calibrated electrode µV",
              ],
              [
                "Movement looks like intent",
                "Review artifact sources and trial behavior; single-channel EEG cannot reliably separate every artifact",
              ],
            ],
          ),
        ],
      },
      {
        id: "training",
        title: "Data and model problems",
        blocks: [
          table(
            ["Symptom", "What to check"],
            [
              [
                "Too few usable trials or windows",
                "Record more balanced REST/SELECT data with at least five clean trials per class",
              ],
              [
                "Import rejected",
                "Check accepted signal columns, label values, finite samples, file limits, and consistent source/rate metadata",
              ],
              [
                "Legacy model cannot arm",
                "Expected behavior: record new v2 raw data and train a native model",
              ],
              [
                "Source or filter mismatch",
                "Match sample rate, filter settings, feature contract, and hardware/demo source",
              ],
              [
                "High reported accuracy but unwanted selections",
                "Review REST false positives, practice on separate trials, and remember the report/runtime thresholds differ",
              ],
              [
                "Practice skips many trials",
                "Each trial needs a full final second of usable samples; resolve quality and timing first",
              ],
            ],
          ),
        ],
      },
      {
        id: "app",
        title: "Application and communication problems",
        blocks: [
          table(
            ["Symptom", "What to check"],
            [
              [
                "Recording or training unavailable in browser",
                "Launch the native app with npm run tauri dev; npm run dev is a design preview",
              ],
              [
                "No speech heard",
                "Check OS volume, output device, and voice support; Linux requires spd-say",
              ],
              [
                "Scanner is paused",
                "Resume with the app control, switch, or eligible BCI selection",
              ],
              [
                "Scanner returns to rows",
                "Expected recovery after two key cycles without a choice; increase the scanning interval if needed",
              ],
              [
                "Saved data location unclear",
                "Open Settings for the exact application data folder",
              ],
              [
                "Build fails on system libraries",
                "Install Tauri platform prerequisites and the project’s Linux serial/speech dependencies",
              ],
            ],
          ),
          links([
            { label: "Platform requirements", href: "#/requirements/platform" },
            { label: "Communication controls", href: "#/communication" },
          ]),
        ],
      },
      {
        id: "report",
        title: "Make an issue reproducible",
        blocks: [
          p(
            "When reporting a problem, include your OS, project version, input source, firmware version, filter settings, the exact error, and steps to reproduce. For timing issues, include measured rate and dropped-sample counts. Review logs or example files for personal recording data before sharing.",
          ),
          links([
            {
              label: "Open the project issue tracker",
              href: "https://github.com/Sakib-Dalal/Mind-Nav/issues",
            },
          ]),
        ],
      },
    ],
  },
  development: {
    source: "README.md · Cargo.toml · desktop and website package scripts",
    lead: "The repository separates the reusable Rust core, native desktop app, Arduino acquisition sketch, Svelte handbook, and original research archive.",
    sections: [
      {
        id: "layout",
        title: "Repository map",
        blocks: [
          code(
            "Repository",
            "Mind-Nav/\n├── apps/\n│   ├── desktop/          Svelte 5 + Tauri 2 desktop application\n│   │   ├── src/          Interface and scanner\n│   │   ├── src-tauri/    Rust runtime, persistence, speech\n│   │   └── static/       Crown identity\n│   └── website/          This Svelte 5 project handbook\n├── crates/\n│   └── mind-nav-core/    DSP, datasets, models, practice, intent gate\n├── firmware/arduino/\n│   └── mind_nav/         v2 acquisition sketch\n├── docs/                Hardware, signal contract, validation\n├── Data/                Existing recordings\n├── Media/               Original diagrams and project images\n└── legacy/              Original Python and Pico W research",
          ),
        ],
      },
      {
        id: "desktop",
        title: "Run and build the desktop app",
        blocks: [
          code(
            "Terminal · from the repository root",
            "cd apps/desktop\nnpm ci\nnpm run tauri dev",
          ),
          code(
            "Terminal · macOS application build, from apps/desktop",
            "npm run tauri -- build --bundles app",
          ),
          p(
            "The macOS application is emitted at target/release/bundle/macos/Mind-Nav.app relative to the repository root. The current release profile uses thin LTO and strips symbols. Signing/notarization and other platform installers require release configuration.",
          ),
          code(
            "Terminal · browser design preview, from apps/desktop",
            "npm run dev",
          ),
          p(
            "The desktop browser preview runs at localhost:1487. It supports interface exploration and an illustrative waveform. The native backend is required for hardware, recordings, saved models, and training.",
          ),
        ],
      },
      {
        id: "checks",
        title: "Project verification commands",
        blocks: [
          code(
            "Terminal · Rust, from the repository root",
            "cargo test --workspace\ncargo clippy --workspace --all-targets -- -D warnings\ncargo fmt --all --check",
          ),
          code(
            "Terminal · desktop frontend",
            "cd apps/desktop\nnpm run check\nnpm test\nnpm run build",
          ),
          code(
            "Terminal · firmware and dataset example, from the repository root",
            "arduino-cli compile --fqbn arduino:avr:uno firmware/arduino/mind_nav\ncargo run -p mind-nav-core --example train_csv -- Data/eeg_precision_bci.csv",
          ),
          p(
            "The CSV example runs a compatibility/training check on the existing recording. Neither an Arduino compile nor a software test performs hardware validation.",
          ),
        ],
      },
      {
        id: "website",
        title: "Run this Svelte handbook",
        blocks: [
          code(
            "Terminal · from the repository root",
            "cd apps/website\nnpm ci\nnpm run dev",
          ),
          p(
            "The handbook runs at localhost:1490. Its content lives in src/lib/content.ts and its navigation in src/lib/navigation.ts. It uses Svelte 5, TypeScript, Vite, locally bundled Manrope, and Lucide icons. It does not connect to EEG hardware or load recording files.",
          ),
          code(
            "Terminal · from apps/website",
            "npm run check\nnpm run build\nnpm run preview",
          ),
          p(
            "The production output is dist/. The preview serves that output at localhost:1491. Fragment-based documentation routes can be hosted as static files without server rewrites. A content section can be linked directly, for example #/hardware/pin-map.",
          ),
        ],
      },
      {
        id: "source-documents",
        title: "Source documents",
        blocks: [
          p(
            "The handbook describes the current local project snapshot. Keep it in sync when firmware, model contracts, or runtime behavior changes. The original technical documents and the complete acquisition sketch are included for reference.",
          ),
          links([
            {
              label: "Hardware reference",
              href: "/downloads/HARDWARE.md",
              download: true,
            },
            {
              label: "Signal pipeline contract",
              href: "/downloads/SIGNAL_PIPELINE.md",
              download: true,
            },
            {
              label: "Validation record",
              href: "/downloads/VALIDATION.md",
              download: true,
            },
            {
              label: "Arduino v2 sketch",
              href: "/downloads/mind_nav.ino",
              download: true,
            },
            {
              label: "GitHub repository",
              href: "https://github.com/Sakib-Dalal/Mind-Nav",
            },
          ]),
        ],
      },
    ],
  },
};
