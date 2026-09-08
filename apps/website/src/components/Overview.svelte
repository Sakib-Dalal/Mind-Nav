<script lang="ts">
  import {
    ArrowUpRight,
    ArrowRight,
    AudioLines,
    BrainCircuit,
    MessageCircle,
    Cable,
    Rocket,
    ListChecks,
    LockKeyhole,
    SlidersHorizontal,
    FlaskConical,
  } from "@lucide/svelte";
</script>

<div class="eyebrow">
  <span class="orange-dash"></span> THE MIND-NAV HANDBOOK
</div>
<section class="intro-hero" aria-labelledby="intro-heading">
  <div class="hero-copy">
    <h1 id="intro-heading">
      A little thought.<br /><span>A new connection.</span>
    </h1>
    <p>
      Build, understand, and use Mind-Nav. Your complete guide to an EEG
      workspace for personal models and accessible communication.
    </p>
    <a class="button primary" href="#/guide"
      >Start with the guide <ArrowRight size={17} /></a
    >
    <div class="hero-caption">
      <span class="small-dot"></span> Research project
      <span class="caption-divider">/</span> Version 0.2.0
    </div>
  </div>
  <div
    class="signal-map"
    aria-label="System overview: EEG acquisition feeds a personal model, then the communication board"
  >
    <div class="map-heading">
      <span class="tiny-label">FROM SIGNAL TO SELECTION</span><span
        class="map-dots">•••</span
      >
    </div>
    <div class="map-row">
      <span class="map-icon"><AudioLines size={25} /></span>
      <div>
        <strong>Capture a signal</strong><span>BioAmp → ADS1115 → Arduino</span>
      </div>
      <span class="map-index">01</span>
    </div>
    <div class="map-connector">
      <span></span><small>250 samples / second</small>
    </div>
    <div class="map-row">
      <span class="map-icon"><BrainCircuit size={25} /></span>
      <div>
        <strong>Learn your patterns</strong><span
          >REST + SELECT · personal model</span
        >
      </div>
      <span class="map-index">02</span>
    </div>
    <div class="map-connector">
      <span></span><small>Local processing + intent checks</small>
    </div>
    <div class="map-row output">
      <span class="map-icon"><MessageCircle size={25} /></span>
      <div>
        <strong>Make a selection</strong><span
          >Scan a keyboard. Speak a message.</span
        >
      </div>
      <ArrowUpRight size={22} />
    </div>
    <div class="map-footer">
      <LockKeyhole size={13} /> Recording and inference stay on your device
    </div>
  </div>
</section>
<div class="spec-strip">
  <div><strong>01</strong><span>EEG channel</span></div>
  <div>
    <strong>250 <small>SPS</small></strong><span>Nominal acquisition</span>
  </div>
  <div><strong>20</strong><span>Signal features</span></div>
  <div>
    <strong>100% <small>local</small></strong><span>Desktop processing</span>
  </div>
</div>
<section class="home-section" id="start-here">
  <div class="section-top">
    <div>
      <div class="eyebrow">YOUR NEXT STEP</div>
      <h2>A place for every part of the build.</h2>
    </div>
    <span class="section-index">01 — 03</span>
  </div>
  <div class="start-cards">
    {#each [{ icon: Rocket, number: "01", title: "Take your first steps", text: "Install the app and try a guided session. Demo mode works without hardware.", href: "guide", label: "Quick start guide" }, { icon: Cable, number: "02", title: "Connect the hardware", text: "Follow the signal chain, inspect each wire, and check the v2 pin connections.", href: "hardware", label: "Explore the diagrams" }, { icon: ListChecks, number: "03", title: "Get everything ready", text: "Find the components, dependencies, and setup notes for your operating system.", href: "requirements", label: "View requirements" }] as card}
      <a class="start-card" href={`#/${card.href}`}
        ><div class="card-top">
          <card.icon size={23} strokeWidth={1.6} /><span>{card.number}</span>
        </div>
        <h3>{card.title}</h3>
        <p>{card.text}</p>
        <div class="card-link">{card.label}<ArrowUpRight size={17} /></div></a
      >
    {/each}
  </div>
</section>
<section class="home-section" id="workflow">
  <div class="section-top">
    <div>
      <div class="eyebrow">ONE CONNECTED WORKFLOW</div>
      <h2>From your first recording to your first words.</h2>
    </div>
  </div>
  <div class="workflow-list">
    {#each [{ n: "01", title: "Connect", text: "Choose a serial device or explicitly start Demo mode.", href: "hardware" }, { n: "02", title: "Record", text: "Alternate five-second REST and SELECT cues.", href: "recording" }, { n: "03", title: "Create", text: "Train locally and review trial-separated validation.", href: "models" }, { n: "04", title: "Practice", text: "Evaluate a separate guided sequence without selecting keys.", href: "practice" }, { n: "05", title: "Communicate", text: "Use quick phrases or the row-and-column scanning keyboard.", href: "communication" }] as step}
      <a href={`#/${step.href}`}
        ><span class="step-num">{step.n}</span><strong>{step.title}</strong>
        <p>{step.text}</p>
        <ArrowUpRight size={16} /></a
      >
    {/each}
  </div>
</section>
<section class="principles" id="about">
  <div>
    <LockKeyhole size={22} />
    <h3>On your device</h3>
    <p>
      CSV recordings, portable JSON models, and preferences stay local. No cloud
      inference.
    </p>
  </div>
  <div>
    <SlidersHorizontal size={22} />
    <h3>At your pace</h3>
    <p>
      Adjust scanning, text size, spoken cues, and selection thresholds in the
      desktop app.
    </p>
  </div>
  <div>
    <FlaskConical size={22} />
    <h3>Built for research</h3>
    <p>
      A working foundation with explicit validation limits and an inspectable
      Rust pipeline.
    </p>
  </div>
</section>
<div class="research-note">
  <FlaskConical size={20} />
  <div>
    <strong>Know what this project can—and cannot—do.</strong>
    <p>
      Mind-Nav is a research foundation, not a clinically validated assistive
      device. Use suitable isolated acquisition hardware before connecting
      electrodes to a person. <a href="#/validation"
        >Read the validation notes <ArrowUpRight size={13} /></a
      >
    </p>
  </div>
</div>
