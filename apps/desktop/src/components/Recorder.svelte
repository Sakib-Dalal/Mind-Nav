<script lang="ts">
  import {
    Circle,
    Square,
    Pause,
    Play,
    Usb,
    Activity,
    ShieldCheck,
    Check,
    ArrowRight,
    Volume2,
  } from '@lucide/svelte';
  import { app, action, command, refresh, speak } from '../lib/app.svelte';
  import { duration } from '../lib/types';
  import Waveform from './Waveform.svelte';
  let { connect } = $props<{ connect: () => void }>();
  let name = $state('My connection session'),
    minutes = $state(2),
    lastCue = $state('');
  async function start() {
    await command('start_recording', { name, minutes });
  }
  $effect(() => {
    const cue = app.snapshot.recording && !app.snapshot.paused ? app.snapshot.cue : '';
    if (cue && cue !== lastCue && app.settings.voice_cues)
      action(() => speak(cue === 'REST' ? 'Rest. Take your time.' : 'Imagine your chosen action.'));
    lastCue = cue;
  });
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">CAPTURE A LITTLE POSSIBILITY</div>
    <h1>Find your rhythm.</h1>
    <p>A guided session helps Mind-Nav learn your rest and selection patterns.</p>
  </div>
  <button class="button outlined" onclick={connect}
    ><Usb size={17} />{app.snapshot.connected ? 'Device settings' : 'Connect device'}</button
  >
</div>
<div class="record-layout">
  <div class="record-main">
    <section class="card">
      <div class="card-heading">
        <div>
          <h3>Your live signal</h3>
          <p>{app.snapshot.quality.reason}</p>
        </div>
        <span class="pill" class:success={app.snapshot.connected}
          ><span class="status-dot"></span>{app.snapshot.source === 'demo'
            ? 'Demo signal'
            : app.snapshot.connected
              ? 'Live device'
              : 'Disconnected'}</span
        >
      </div>
      <Waveform />
      <div class="signal-details">
        <span><strong>{Math.round(app.snapshot.sample_rate) || '—'}</strong> Hz measured</span><span
          ><strong>{app.snapshot.dropped}</strong> dropped samples</span
        ><span
          ><strong>{app.snapshot.connected ? app.snapshot.quality.rms.toFixed(1) : '—'}</strong> mV RMS
          at ADC</span
        >
      </div>
    </section>
    <section class:select-cue={app.snapshot.cue === 'SELECT'} class="cue-card">
      <div class="cue-label">
        {app.snapshot.recording
          ? app.snapshot.paused
            ? 'SESSION PAUSED'
            : 'FOLLOW YOUR CUE'
          : 'YOUR GUIDED SESSION'}
      </div>
      <div class="cue-symbol">
        {#if app.snapshot.recording && app.snapshot.cue === 'SELECT'}<Activity
            size={42}
          />{:else}<span class="breathing-circle"></span>{/if}
      </div>
      <h2>
        {app.snapshot.recording
          ? app.snapshot.paused
            ? 'Take a moment.'
            : app.snapshot.cue === 'REST'
              ? 'Rest. Just be.'
              : 'Imagine your action.'
          : 'Get comfortable.'}
      </h2>
      <p>
        {app.snapshot.recording && app.snapshot.cue === 'SELECT'
          ? 'Imagine the same action each time, such as closing a hand. No movement is required.'
          : 'Relax, let your gaze settle, and follow the cues at your own pace.'}
      </p>
      {#if app.snapshot.recording}<div class="cue-progress">
          <div style:width={`${(app.snapshot.cue_remaining / 5) * 100}%`}></div>
        </div>
        <span class="tiny"
          >{app.snapshot.paused
            ? 'Resume whenever you’re ready.'
            : `${Math.ceil(app.snapshot.cue_remaining)} seconds until the next cue`}</span
        >{:else}<span class="pill">5 seconds rest <ArrowRight size={13} /> 5 seconds imagine</span
        >{/if}
    </section>
    <div class="record-dock">
      <div>
        <span
          class:recording-dot={app.snapshot.recording && !app.snapshot.paused}
          class="little-dot"
        ></span><strong>{duration(app.snapshot.elapsed)}</strong><span class="muted"
          >{app.snapshot.recording
            ? app.snapshot.paused
              ? 'Paused'
              : 'Recording'
            : 'Ready to record'}</span
        >
      </div>
      <div class="button-row">
        {#if app.snapshot.recording}<button
            class="button outlined"
            onclick={() => action(() => command('pause_recording'))}
            >{#if app.snapshot.paused}<Play size={17} />Resume{:else}<Pause
                size={17}
              />Pause{/if}</button
          ><button
            class="button primary"
            onclick={() =>
              action(async () => {
                await command('stop_recording');
                await refresh();
              }, 'Session saved on this device.')}><Square size={16} />Finish & save</button
          >{:else}<button
            class="button primary"
            onclick={() => action(start)}
            disabled={!app.snapshot.connected || !name.trim()}
            ><Circle size={16} />Start recording</button
          >{/if}
      </div>
    </div>
  </div>
  <aside class="record-sidebar">
    <section class="card form-card">
      <h3>Make this session yours</h3>
      <label for="session-name">Session name</label><input
        id="session-name"
        bind:value={name}
        maxlength="80"
        disabled={app.snapshot.recording}
      /><label for="session-duration">Recording duration</label><select
        id="session-duration"
        bind:value={minutes}
        disabled={app.snapshot.recording}
        ><option value={2}>2 minutes · First steps</option><option value={5}
          >5 minutes · More practice</option
        ><option value={15}>15 minutes · Extended session</option><option value={0}
          >Until I choose to stop</option
        ></select
      >
      <div class="field-note">
        Aim for at least 5 clean trials of each intent. Start with 2 minutes.
      </div>
      <div class="setting-inline">
        <Volume2 size={18} /><span>Spoken cues</span><span class="pill"
          >{app.settings.voice_cues ? 'On' : 'Off'}</span
        >
      </div>
    </section>
    <section class="card form-card">
      <h3>A cleaner connection</h3>
      <div class="filter-step">
        <span>01</span>
        <div>
          <strong>Steady the baseline</strong><small>0.5 Hz high-pass removes slow drift.</small>
        </div>
      </div>
      <div class="filter-step">
        <span>02</span>
        <div>
          <strong>Reduce power-line noise</strong><small
            >{app.settings.notch
              ? `${app.settings.notch} Hz notch filter`
              : 'Notch filter disabled'}.</small
          >
        </div>
      </div>
      <div class="filter-step">
        <span>03</span>
        <div>
          <strong>Keep useful frequencies</strong><small
            >40 Hz low-pass limits high-frequency noise.</small
          >
        </div>
      </div>
      <div class="filter-step">
        <span><Check size={15} /></span>
        <div>
          <strong>Check every window</strong><small
            >Flag clipping, flat signals, and large artifacts.</small
          >
        </div>
      </div>
    </section>
    <div class="privacy-note">
      <ShieldCheck size={20} /><span
        ><strong>Just you and your device.</strong><small
          >Raw samples stay available for retraining. Nothing is uploaded.</small
        ></span
      >
    </div>
  </aside>
</div>
