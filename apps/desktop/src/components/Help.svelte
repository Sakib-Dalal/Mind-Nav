<script lang="ts">
  import {
    ArrowRight,
    Usb,
    AudioLines,
    BrainCircuit,
    MessageCircle,
    Keyboard,
    ShieldCheck,
  } from '@lucide/svelte';
  import { app } from '../lib/app.svelte';
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">LET’S START TOGETHER</div>
    <h1>Small steps. New possibilities.</h1>
    <p>A quick guide for you and the person helping you get set up.</p>
  </div>
</div>
<div class="help-grid">
  {#each [{ icon: Usb, n: '01', title: 'Connect & settle in', text: 'Connect the Arduino with the included v2 firmware. Choose its USB port, then allow the signal to settle. Demo mode lets you explore without a headset.', page: 'EEG Recorder' }, { icon: AudioLines, n: '02', title: 'Record your patterns', text: 'Start a two-minute guided session. Rest during REST. During SELECT, imagine the same action each time. No body movement is required.', page: 'EEG Recorder' }, { icon: BrainCircuit, n: '03', title: 'Create your personal model', text: 'Choose a recording in Model Studio. Review validation, including false positives. Activate the model, then practice with the same source and filters.', page: 'Model Studio' }, { icon: MessageCircle, n: '04', title: 'Make yourself heard', text: 'Open Communicate. Use quick phrases or the keyboard. A switch mapped to Enter selects a highlighted row, then a key. Patient view keeps communication front and center.', page: 'Communicate' }] as item}<button
      class="card help-card"
      onclick={() => (app.page = item.page as 'Communicate' | 'EEG Recorder' | 'Model Studio')}
      ><div>
        <span class="icon-tile"><item.icon size={24} /></span><span class="eyebrow">{item.n}</span>
      </div>
      <h3>{item.title}</h3>
      <p>{item.text}</p>
      <span class="text-button">Let’s try it <ArrowRight size={16} /></span></button
    >{/each}
</div>
<section class="card help-detail">
  <h3>Good to know</h3>
  <details open>
    <summary>How does scanning work?</summary>
    <p>
      Start scanning, then press Enter or the Select highlighted button when the row you want is
      highlighted. Select again on your key. A USB assistive switch can send Enter. After two key
      cycles without a choice, the scanner returns to rows. Escape pauses. “Pause” can be resumed
      with another switch or BCI selection.
    </p>
  </details>
  <details>
    <summary>What if the signal is interrupted?</summary>
    <p>
      BCI selections stop when a window fails signal checks. A device disconnect or three seconds
      without samples disarms input and saves the current recording as interrupted. Reconnect, check
      the signal, and explicitly enable BCI input again.
    </p>
  </details>
  <details>
    <summary>Can I use my existing recordings and models?</summary>
    <p>
      Import CSV recordings in Model Studio. Choose their actual sample rate; the old nominal 256 Hz
      rate may differ from capture timing. Legacy 0/1 and 0/5 labels are supported. Old Python
      .joblib and .pt files stay in the research archive; create new Rust models here. Legacy
      filtered recordings are for model comparison, while live input requires new v2 raw recordings.
    </p>
  </details>
  <details>
    <summary>Where is my data saved?</summary>
    <p>
      The desktop app saves CSV recordings and JSON models in its local application data folder,
      shown in Settings. Export individual recordings or models to a location you choose. Copy that
      folder for backups. Interrupted recordings retain their CSV data even if metadata is
      incomplete.
    </p>
  </details>
  <details>
    <summary>Is Mind-Nav ready for independent patient use?</summary>
    <p>
      This is a research product foundation. The software’s filters and tests do not establish
      clinical accuracy or electrical safety. Hardware and communication reliability still need
      supervised validation for each person. Use properly isolated EEG acquisition hardware. “I need
      help” speaks locally and is not an emergency alert service.
    </p>
  </details>
</section>
