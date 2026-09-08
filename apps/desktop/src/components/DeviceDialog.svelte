<script lang="ts">
  import { onMount } from 'svelte';
  import { X, Usb, RefreshCw, FlaskConical, ArrowRight, CheckCircle2 } from '@lucide/svelte';
  import { app, command, action, startDemo, disconnect } from '../lib/app.svelte';
  let { onclose } = $props<{ onclose: () => void }>();
  let ports = $state<string[]>([]),
    selected = $state(''),
    loading = $state(false),
    modal: HTMLDialogElement;
  async function scan() {
    loading = true;
    try {
      ports = await command<string[]>('list_ports');
      selected = ports[0] || '';
    } finally {
      loading = false;
    }
  }
  onMount(() => {
    modal.showModal();
    if (app.native) action(scan);
  });
  async function connect() {
    loading = true;
    try {
      await command('connect_device', { port: selected });
      onclose();
    } finally {
      loading = false;
    }
  }
</script>

<dialog bind:this={modal!} {onclose} class="device-dialog" aria-labelledby="device-title">
  <div class="dialog-heading">
    <span class="icon-tile"><Usb size={23} /></span><button
      class="icon-button"
      onclick={onclose}
      aria-label="Close device setup"><X size={20} /></button
    >
  </div>
  <h2 id="device-title">Let’s get connected.</h2>
  <p class="muted">Choose your EEG device, or explore Mind-Nav with a sample signal.</p>
  <div class="setup-note">
    <CheckCircle2 size={18} /><span
      >Arduino + ADS1115 · USB serial · 250 Hz<br /><small
        >Requires the included v2 Arduino firmware.</small
      ></span
    >
  </div>
  <label for="serial-port">EEG device</label>
  <div class="input-row">
    <select id="serial-port" bind:value={selected} disabled={!app.native || loading}
      ><option value=""
        >{app.native ? 'Select a serial port' : 'Available in the desktop app'}</option
      >{#each ports as port}<option value={port}>{port}</option>{/each}</select
    ><button
      class="icon-button outlined"
      onclick={() => action(scan)}
      disabled={!app.native || loading}
      aria-label="Refresh serial ports"><RefreshCw size={18} /></button
    >
  </div>
  <button
    class="button primary full"
    disabled={!selected || loading}
    onclick={() => action(connect)}
    >{loading ? 'Connecting…' : 'Connect device'}<ArrowRight size={17} /></button
  >
  {#if app.snapshot.connected}<button
      class="button full"
      onclick={() =>
        action(async () => {
          await disconnect();
          onclose();
        })}>Disconnect current source</button
    >{/if}
  <div class="divider-label">OR EXPLORE FIRST</div>
  <button
    class="demo-choice"
    onclick={() =>
      action(async () => {
        await startDemo();
        onclose();
      })}
    disabled={app.snapshot.recording}
    ><FlaskConical size={22} /><span
      ><strong>Try demo mode</strong><small
        >No headset needed. Clearly labeled simulated data.</small
      ></span
    ><ArrowRight size={18} /></button
  >
  <p class="tiny muted">Your recordings stay on this device. No account or cloud required.</p>
</dialog>
