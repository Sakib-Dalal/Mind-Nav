<script lang="ts">
  import { app } from '../lib/app.svelte';
  let { compact = false } = $props<{ compact?: boolean }>();
  let data = $derived(app.snapshot.waveform);
  let extent = $derived(Math.max(30, ...data.map(Math.abs)) * 1.2);
  let path = $derived(
    data.length
      ? data
          .map(
            (y, i) =>
              `${i === 0 ? 'M' : 'L'}${((i / (data.length - 1)) * 900).toFixed(2)},${(90 - (y / extent) * 65).toFixed(2)}`,
          )
          .join(' ')
      : 'M0,90 L900,90',
  );
</script>

<div class:compact class="wave-wrap">
  <div class="wave-axis">
    <span>+{Math.round(extent)}</span><span>0</span><span>−{Math.round(extent)}</span>
  </div>
  <svg
    class="wave"
    viewBox="0 0 900 180"
    preserveAspectRatio="none"
    role="img"
    aria-label={app.snapshot.connected
      ? 'Live filtered EEG waveform, ADC millivolts'
      : 'EEG waveform waiting for a connection'}
  >
    <defs
      ><pattern
        id={compact ? 'grid-small' : 'grid'}
        width="75"
        height="45"
        patternUnits="userSpaceOnUse"
        ><path
          d="M 75 0 L 0 0 0 45"
          fill="none"
          stroke="currentColor"
          stroke-width="0.7"
        /></pattern
      ></defs
    >
    <rect
      width="900"
      height="180"
      fill={`url(#${compact ? 'grid-small' : 'grid'})`}
      class="wave-grid"
    />
    <path
      d={path}
      fill="none"
      stroke="var(--wave-color)"
      stroke-width="1.7"
      vector-effect="non-scaling-stroke"
    />
  </svg>
  {#if !data.length}<div class="wave-empty">
      Your signal will appear here<span>Connect an EEG device or try demo mode</span>
    </div>{/if}
</div>
<div class="wave-bottom">
  <span>ADC mV <span class="muted">· CH 01</span></span><span>−2.0 s</span><span>−1.0 s</span><span
    >Now</span
  >
</div>
