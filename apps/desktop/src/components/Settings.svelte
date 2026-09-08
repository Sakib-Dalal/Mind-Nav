<script lang="ts">
  import {
    Sun,
    Moon,
    Type,
    Volume2,
    Accessibility,
    Activity,
    ShieldCheck,
    Check,
  } from '@lucide/svelte';
  import { app, save, action, notify } from '../lib/app.svelte';
  import type { Settings } from '../lib/types';
  let name = $state(app.settings.name);
  const update = (patch: Partial<Settings>) => action(() => save(patch));
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">COMFORT COMES FIRST</div>
    <h1>A space that feels like you.</h1>
    <p>Small adjustments can make a world of difference.</p>
  </div>
  <span class="pill success"><Check size={14} />Changes save automatically</span>
</div>
<div class="settings-grid">
  <section class="card settings-card">
    <div class="card-heading"><h3><Sun size={20} />Appearance</h3></div>
    <p class="muted">Choose a calmer canvas for your day.</p>
    <div class="theme-options">
      <button
        class:chosen={app.settings.theme === 'light'}
        onclick={() => update({ theme: 'light' })}
        aria-pressed={app.settings.theme === 'light'}
        ><div class="theme-preview light-preview">
          <i></i>
          <div><span></span><span></span></div>
        </div>
        <span
          ><Sun size={16} />Light{#if app.settings.theme === 'light'}<Check size={16} />{/if}</span
        ></button
      ><button
        class:chosen={app.settings.theme === 'dark'}
        onclick={() => update({ theme: 'dark' })}
        aria-pressed={app.settings.theme === 'dark'}
        ><div class="theme-preview dark-preview">
          <i></i>
          <div><span></span><span></span></div>
        </div>
        <span
          ><Moon size={16} />Dark{#if app.settings.theme === 'dark'}<Check size={16} />{/if}</span
        ></button
      >
    </div>
    <div class="preference-row">
      <div>
        <strong>Larger text</strong>
        <p>More room for easier reading.</p>
      </div>
      <button
        class="switch"
        class:on={app.settings.large_text}
        role="switch"
        aria-checked={app.settings.large_text}
        aria-label="Larger text"
        onclick={() => update({ large_text: !app.settings.large_text })}><span></span></button
      >
    </div>
    <div class="preference-row">
      <div>
        <strong>Reduce motion</strong>
        <p>Keep transitions still and gentle.</p>
      </div>
      <button
        class="switch"
        class:on={app.settings.reduced_motion}
        role="switch"
        aria-checked={app.settings.reduced_motion}
        aria-label="Reduce motion"
        onclick={() => update({ reduced_motion: !app.settings.reduced_motion })}
        ><span></span></button
      >
    </div>
  </section>
  <section class="card settings-card">
    <div class="card-heading"><h3><Accessibility size={20} />Your pace</h3></div>
    <label for="scan-speed"
      >Scanning speed <strong>{(app.settings.scan_ms / 1000).toFixed(1)} seconds</strong></label
    ><input
      id="scan-speed"
      type="range"
      min="600"
      max="5000"
      step="100"
      value={app.settings.scan_ms}
      onchange={(e) => update({ scan_ms: Number(e.currentTarget.value) })}
    />
    <div class="range-labels"><span>Faster · 0.6 s</span><span>More time · 5 s</span></div>
    <p class="field-note">
      Each row and key stays highlighted for this long. Two missed key cycles return to row
      scanning.
    </p>
    <div class="preference-row">
      <div>
        <strong>Spoken cues & phrases</strong>
        <p>Hear recording prompts and quick phrases.</p>
      </div>
      <button
        class="switch"
        class:on={app.settings.voice_cues}
        role="switch"
        aria-checked={app.settings.voice_cues}
        aria-label="Spoken cues and phrases"
        onclick={() => update({ voice_cues: !app.settings.voice_cues })}><span></span></button
      >
    </div>
    <div class="field-note">
      A switch mapped to Enter selects the highlighted item. Escape pauses scanning. Patient view
      enlarges the communication board.
    </div>
  </section>
  <section class="card settings-card">
    <div class="card-heading"><h3><Activity size={20} />Signal & selections</h3></div>
    <label for="notch">Power-line filter</label><select
      id="notch"
      value={app.settings.notch}
      disabled={app.snapshot.recording}
      onchange={(e) => update({ notch: Number(e.currentTarget.value) })}
      ><option value="50">50 Hz · India, Europe & most regions</option><option value="60"
        >60 Hz · North America & some regions</option
      ><option value="0">Off</option></select
    >
    <p class="field-note">
      Changing filters requires a matching model before BCI input can resume.
    </p>
    <label for="threshold"
      >Selection threshold <strong>{Math.round(app.settings.threshold * 100)}%</strong></label
    ><input
      id="threshold"
      type="range"
      min="60"
      max="95"
      step="1"
      value={app.settings.threshold * 100}
      onchange={(e) => update({ threshold: Number(e.currentTarget.value) / 100 })}
    />
    <p class="field-note">
      Raise this if selections happen too easily. A selection needs three stable predictions, a
      1.5-second cooldown, and a return to rest.
    </p>
  </section>
  <section class="card settings-card">
    <div class="card-heading"><h3><ShieldCheck size={20} />Your workspace</h3></div>
    <label for="display-name">What should we call you?</label>
    <form
      class="input-row"
      onsubmit={(e) => {
        e.preventDefault();
        action(() => save({ name: name.trim() }), 'Your name has been saved.');
      }}
    >
      <input id="display-name" bind:value={name} maxlength="60" required /><button
        class="button outlined"
        type="submit">Save</button
      >
    </form>
    <div class="local-data-note">
      <ShieldCheck size={26} />
      <h4>Private is the starting point.</h4>
      <p>Recordings and models live on this device. No accounts, telemetry, or cloud uploads.</p>
      <small
        >{app.directory ||
          'The desktop app uses your operating system’s application data folder.'}</small
      >
    </div>
  </section>
</div>
