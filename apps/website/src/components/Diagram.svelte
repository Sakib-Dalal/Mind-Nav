<script lang="ts">
  import {
    ArrowDown,
    ArrowRight,
    Download,
    Cable,
    Activity,
    SlidersHorizontal,
    Grid2X2,
    BrainCircuit,
    MousePointer2,
  } from "@lucide/svelte";
  import wiringSvg from "../assets/wiring-v2.svg?raw";
  let { variant } = $props<{ variant: "wiring" | "pipeline" }>();
  let focus = $state("all");
  const wires = [
    {
      id: "all",
      label: "All connections",
      color: "#233d4d",
      text: "Select a connection group to trace its wires. The pin table below is the text alternative to this diagram.",
    },
    {
      id: "analog",
      label: "Analog",
      color: "#ca6a2e",
      text: "BioAmp OUT → ADS1115 A0. This is the amplifier output in the raw-ADC path; Uno A0 is not used.",
    },
    {
      id: "i2c",
      label: "I²C",
      color: "#4977ad",
      text: "ADS1115 SDA → Uno A4 and SCL → Uno A5. The bus runs at 400 kHz; ADDR tied to ground selects 0x48.",
    },
    {
      id: "ready",
      label: "Ready · v2",
      color: "#db7124",
      text: "ADS1115 ALERT/RDY → Uno D2. This required falling-edge interrupt drives acquisition; D2 uses INPUT_PULLUP.",
    },
    {
      id: "ground",
      label: "Ground",
      color: "#668878",
      text: "BioAmp GND, ADS1115 GND, Uno GND, and ADS1115 ADDR share the acquisition reference. This does not provide isolation.",
    },
    {
      id: "supply",
      label: "Supply",
      color: "#b85c64",
      text: "The existing Uno arrangement is nominally 5 V. Verify each board’s supply specification and input limits. This is not an isolation design.",
    },
  ];
  const activeWire = $derived(wires.find((w) => w.id === focus)!);
  const stages = [
    {
      icon: Cable,
      title: "Acquire",
      value: "250 SPS",
      text: "Sequence + timestamp + raw ADC mV",
      detail: "USB serial · 115200 baud",
    },
    {
      icon: SlidersHorizontal,
      title: "Filter",
      value: "0.5–40 Hz",
      text: "High-pass → notch → low-pass",
      detail: "One causal pipeline in Rust",
    },
    {
      icon: Activity,
      title: "Check",
      value: "Quality gates",
      text: "Reject flat, clipped, or invalid input",
      detail: "Settle · gap checks · transition guard",
    },
    {
      icon: Grid2X2,
      title: "Extract",
      value: "20 features",
      text: "Two-second windows + Welch PSD",
      detail: "Spectral and time-domain descriptors",
    },
    {
      icon: BrainCircuit,
      title: "Classify",
      value: "REST / SELECT",
      text: "Personal logistic regression model",
      detail: "Matching source + preprocessing contract",
    },
    {
      icon: MousePointer2,
      title: "Select",
      value: "One edge",
      text: "Smooth → qualify → cooldown → rearm",
      detail: "Select within the communication board",
    },
  ];
</script>

{#if variant === "wiring"}
  <div class="wiring-panel">
    <div class="diagram-toolbar">
      <div><Cable size={17} /><strong>Connection explorer</strong></div>
      <a href="/assets/wiring-v2.svg" download="mind-nav-wiring-v2.svg"
        ><Download size={15} /><span>Download SVG</span></a
      >
    </div>
    <div
      class="wire-controls"
      role="group"
      aria-label="Highlight connection group"
    >
      {#each wires as wire}<button
          aria-pressed={focus === wire.id}
          class:selected={focus === wire.id}
          onclick={() => (focus = wire.id)}
          ><span style:background={wire.color}></span>{wire.label}</button
        >{/each}
    </div>
    <!-- Keyboard focus lets users scroll overflowing content. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="wiring-canvas"
      data-focus={focus}
      tabindex="0"
      role="region"
      aria-label="Scrollable logical wiring diagram"
    >
      {@html wiringSvg}
    </div>
    <div class="wire-description" aria-live="polite">
      <span style:background={activeWire.color}></span>
      <p>{activeWire.text}</p>
    </div>
  </div>
{:else}
  <div
    class="pipeline-diagram"
    aria-label="Six-stage native signal processing flow"
  >
    {#each stages as stage, i}<div class="pipeline-stage">
        <div class="pipeline-node">
          <stage.icon size={23} /><span>0{i + 1}</span>
        </div>
        <div>
          <div class="pipeline-title">
            <h3>{stage.title}</h3>
            <span>{stage.value}</span>
          </div>
          <p>{stage.text}</p>
          <small>{stage.detail}</small>
        </div>
        {#if i < stages.length - 1}<ArrowDown
            class="pipeline-arrow"
            size={18}
          />{/if}
      </div>{/each}
  </div>
{/if}
