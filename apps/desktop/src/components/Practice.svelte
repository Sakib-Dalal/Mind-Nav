<script lang="ts">
  import { Play, Square, BrainCircuit, Activity, ShieldCheck, ArrowRight } from '@lucide/svelte';
  import { app, action, command } from '../lib/app.svelte';
  import { duration } from '../lib/types';
  let practice = $derived(app.snapshot.practice);
  let cue = $derived(Math.floor(practice.samples / 1250) % 2 === 0 ? 'REST' : 'SELECT');
  let model = $derived(app.models.find((m) => m.id === app.settings.active_model));
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">A LITTLE PRACTICE, MORE CONFIDENCE</div>
    <h1>Get to know your connection.</h1>
    <p>Try a two-minute guided check before using your personal model to communicate.</p>
  </div>
  <button class="button outlined" onclick={() => (app.page = 'Model Studio')}
    ><BrainCircuit size={17} />Choose a model</button
  >
</div>
<div class="practice-intro">
  <ShieldCheck size={19} /><span
    >Practice observes predictions without selecting keys. Results stay separate from model
    training.</span
  >
</div>
<div class="practice-grid">
  <section class:select-cue={cue === 'SELECT' && practice.running} class="cue-card">
    <div class="cue-label">{practice.running ? 'YOUR CUE' : 'READY TO PRACTICE'}</div>
    <div class="cue-symbol"><Activity size={39} /></div>
    <h2>
      {practice.running
        ? cue === 'REST'
          ? 'Rest. Just be.'
          : 'Imagine your action.'
        : 'Let’s find your pace.'}
    </h2>
    <p>
      {practice.running
        ? 'Follow the cue. Each trial lasts five seconds.'
        : 'Activate your model and connect the same signal source to begin.'}
    </p>
    <span class="pill"
      >{practice.running
        ? `${5 - Math.floor((practice.samples % 1250) / 250)} seconds until next cue`
        : 'REST → SELECT · 24 trials'}</span
    >
  </section>
  <section class="card prediction-card">
    <div class="eyebrow">YOUR MODEL IS LISTENING</div>
    <span class="icon-tile"><BrainCircuit size={26} /></span>
    <h2>
      {app.snapshot.probability === null
        ? 'Waiting for a model'
        : app.snapshot.probability >= app.settings.threshold
          ? 'Select detected'
          : 'Rest detected'}
    </h2>
    <p>{model?.name || 'Choose a model in Model Studio'}</p>
    <div class="probability-track">
      <div style:width={`${(app.snapshot.probability || 0) * 100}%`}></div>
      <span style:left={`${app.settings.threshold * 100}%`}></span>
    </div>
    <div class="range-labels">
      <span
        >Select score: {app.snapshot.probability === null
          ? '—'
          : `${Math.round(app.snapshot.probability * 100)}%`}</span
      ><span>Threshold: {Math.round(app.settings.threshold * 100)}%</span>
    </div>
    <div class="field-note">{app.snapshot.quality.reason}</div>
  </section>
</div>
<div class="record-dock">
  <div><strong>{duration(practice.samples / 250)}</strong><span class="muted">of 02:00</span></div>
  {#if practice.running}<button
      class="button outlined"
      onclick={() => action(() => command('stop_practice'))}
      ><Square size={16} />Finish practice</button
    >{:else}<button
      class="button primary"
      disabled={app.snapshot.probability === null || app.snapshot.recording}
      onclick={() => action(() => command('start_practice'))}
      ><Play size={17} />Start practice</button
    >{/if}
</div>
<section class="card practice-results">
  <div class="card-heading">
    <h3>Your live practice results</h3>
    <span class="pill"
      >{app.snapshot.source === 'demo' ? 'Demo · simulated signal' : 'Current session only'}</span
    >
  </div>
  <div class="practice-metrics">
    <div>
      <strong
        >{practice.trials
          ? `${Math.round((practice.correct / practice.trials) * 100)}%`
          : '—'}</strong
      ><span>Trials matched</span>
    </div>
    <div><strong>{practice.trials}</strong><span>Usable trials</span></div>
    <div><strong>{practice.skipped}</strong><span>Skipped for signal quality</span></div>
    <div><strong>{practice.confusion[0][1]}</strong><span>False selections during rest</span></div>
  </div>
  <p>
    One prediction is scored per trial using its final second. A poor signal skips the trial. These
    results describe this practice session; they do not measure clinical reliability.
  </p>
</section>
