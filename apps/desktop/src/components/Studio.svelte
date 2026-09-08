<script lang="ts">
  import {
    BrainCircuit,
    Upload,
    ArrowRight,
    Check,
    Download,
    Plus,
    ShieldCheck,
    FlaskConical,
  } from '@lucide/svelte';
  import { app, action, command, refresh, save, notify } from '../lib/app.svelte';
  import { sourceLabel, date } from '../lib/types';
  import type { Model } from '../lib/types';
  let sessionId = $state(''),
    name = $state('My intention model'),
    sampleRate = $state(0),
    training = $state(false),
    selected = $state<Model | null>(null);
  let dataset = $derived(app.sessions.find((s) => s.id === sessionId));
  let result = $derived(selected || app.models[0]);
  async function train() {
    training = true;
    try {
      selected = await command<Model>('train_model', { sessionId, name });
      await refresh();
      notify('Your model is ready to review.');
    } finally {
      training = false;
    }
  }
  async function importData() {
    const imported = await command<{ id: string } | null>('import_session', { sampleRate });
    if (imported) {
      await refresh();
      sessionId = imported.id;
      notify('Recording imported. Review its source and sample rate before training.');
    }
  }
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">PERSONAL TO YOUR PATTERNS</div>
    <h1>A model, made for you.</h1>
    <p>Turn your recordings into a personal intention model. All on this device.</p>
  </div>
  <button class="button outlined" onclick={() => (app.page = 'EEG Recorder')}
    ><Plus size={17} />New recording</button
  >
</div>
<div class="studio-layout">
  <section class="card training-card">
    <div class="card-heading">
      <div>
        <h3>Create a personal model</h3>
        <p>One guided workflow. No notebook needed.</p>
      </div>
      <span class="icon-tile"><BrainCircuit size={23} /></span>
    </div>
    <div class="form-section">
      <div class="section-number">1</div>
      <div>
        <h4>Choose your recording</h4>
        <p>Use a session with at least 5 clean trials of each intent.</p>
        <label for="training-session" class="sr-only">Training recording</label><select
          id="training-session"
          bind:value={sessionId}
          disabled={training}
          ><option value="">Select a saved session</option>{#each app.sessions as s}<option
              value={s.id}>{s.name} · {sourceLabel(s.source)}</option
            >{/each}</select
        >
        <div class="import-row">
          <button class="text-button" onclick={() => action(importData)} disabled={training}
            ><Upload size={16} />Import EEG CSV</button
          ><label class="inline-label" for="sample-rate"
            >Import rate<select id="sample-rate" bind:value={sampleRate}
              ><option value={0}>Detect timing</option>
              <option value={250}>250 Hz</option><option value={256}>256 Hz (legacy)</option
              ></select
            ></label
          >
        </div>
        {#if dataset}<div class="dataset-summary">
            <span class="pill">{sourceLabel(dataset.source)}</span><strong
              >{dataset.samples.toLocaleString()} samples</strong
            ><small
              >{dataset.config.sample_rate} Hz · {dataset.summary
                ? `${dataset.summary.windows} usable windows · ${dataset.summary.rejected_windows} rejected`
                : 'Quality checks run during training'}</small
            >
          </div>{/if}
        {#if dataset?.source === 'legacy'}<p class="notice">
            Legacy recordings were already filtered and scaled by the old firmware. These models are
            for comparison; record with v2 firmware to use live BCI input.
          </p>{/if}
      </div>
    </div>
    <div class="form-section">
      <div class="section-number">2</div>
      <div>
        <h4>Give it a name</h4>
        <p>Something you’ll recognize next time.</p>
        <label for="model-name" class="sr-only">Model name</label><input
          id="model-name"
          bind:value={name}
          maxlength="80"
          disabled={training}
        />
      </div>
    </div>
    <div class="form-section">
      <div class="section-number">3</div>
      <div>
        <h4>Train, then check</h4>
        <p>Mind-Nav learns REST and SELECT patterns, then tests on separate trials.</p>
        <div class="training-method">
          <Check size={16} />20 signal features<Check size={16} />5 trial-separated folds
        </div>
        <div class="training-method">
          <Check size={16} />Balanced learning<Check size={16} />Regularized classifier
        </div>
      </div>
    </div>
    {#if training || app.snapshot.training.running}<div class="training-progress" role="status">
        <strong>{app.snapshot.training.message}</strong><progress
          max="100"
          value={app.snapshot.training.progress}
        ></progress><small
          >{app.snapshot.training.progress}% · You can keep using the workspace.</small
        >
      </div>{/if}
    <button
      class="button primary full"
      disabled={!sessionId || !name.trim() || training || app.snapshot.training.running}
      onclick={() => action(train)}
      ><BrainCircuit size={18} />{training
        ? 'Learning your patterns…'
        : 'Train personal model'}<ArrowRight size={17} /></button
    >
  </section>
  <div class="studio-right">
    {#if result}<section class="card model-report">
        <div class="card-heading">
          <div>
            <div class="eyebrow">VALIDATION REPORT</div>
            <h3>{result.name}</h3>
          </div>
          <span class="pill">{sourceLabel(result.dataset.source)}</span>
        </div>
        <div class="accuracy-value">
          {(result.metrics.balanced_accuracy * 100).toFixed(1)}<span>%</span>
        </div>
        <div class="muted">Balanced cross-validation accuracy</div>
        <div class="fold-bars" aria-label="Accuracy by validation fold">
          {#each result.metrics.fold_accuracy as score, i}<div>
              <span>{Math.round(score * 100)}%</span>
              <div style:height={`${Math.max(5, score * 70)}px`}></div>
              <small>Fold {i + 1}</small>
            </div>{/each}
        </div>
        <div class="metrics-row">
          <div>
            <strong>{Math.round(result.metrics.precision * 100)}%</strong><small
              >Select precision</small
            >
          </div>
          <div>
            <strong>{Math.round(result.metrics.recall * 100)}%</strong><small>Select recall</small>
          </div>
          <div>
            <strong>{Math.round(result.metrics.false_positive_rate * 100)}%</strong><small
              >False positive rate</small
            >
          </div>
        </div>
        <details>
          <summary>See validation counts</summary>
          <table class="confusion">
            <caption>Actual rows / predicted columns · threshold 50%</caption><thead
              ><tr><th>Intent</th><th>Rest</th><th>Select</th></tr></thead
            ><tbody
              ><tr
                ><th>Rest</th><td>{result.metrics.confusion[0][0]}</td><td
                  >{result.metrics.confusion[0][1]}</td
                ></tr
              ><tr
                ><th>Select</th><td>{result.metrics.confusion[1][0]}</td><td
                  >{result.metrics.confusion[1][1]}</td
                ></tr
              ></tbody
            >
          </table>
        </details>
        <p class="field-note">
          Validation uses held-out trials from this recording. It does not establish performance on
          a new day or with a new person.
        </p>
        <div class="button-row">
          <button
            class="button primary"
            disabled={app.settings.active_model === result.id || result.dataset.source === 'legacy'}
            onclick={() =>
              action(() => save({ active_model: result.id }), 'Personal model activated.')}
            ><Check size={17} />{app.settings.active_model === result.id
              ? 'Active model'
              : 'Use this model'}</button
          ><button
            class="icon-button outlined"
            onclick={() =>
              action(async () => {
                const path = await command<string | null>('export_model', { modelId: result!.id });
                if (path) notify('Model exported.');
              })}
            aria-label="Export model"><Download size={18} /></button
          >
        </div>
      </section>
    {:else}<section class="card model-placeholder">
        <div class="model-orbit"><BrainCircuit size={49} /></div>
        <span class="eyebrow">YOUR NEXT CONNECTION</span>
        <h3>A little practice.<br />A more personal experience.</h3>
        <p>
          Choose a recording and train your first model. Its validation report will appear here.
        </p>
        <div class="pill">Private by design <ShieldCheck size={14} /></div>
      </section>{/if}
    <div class="model-note">
      <ShieldCheck size={20} />
      <div>
        <strong>Clear results, thoughtful controls.</strong>
        <p>
          Models only work with the signal source and filters they were trained on. Demo models stay
          in demo mode.
        </p>
      </div>
    </div>
  </div>
</div>
<section class="card model-library">
  <div class="card-heading">
    <h3>Your model library <span class="subtle-tag">{app.models.length}</span></h3>
    <span class="tiny muted">Saved on this device</span>
  </div>
  {#if app.models.length}{#each app.models as m}<button
        class="model-row"
        onclick={() => (selected = m)}
        ><span class="icon-tile"><BrainCircuit size={20} /></span><span
          ><strong>{m.name}</strong><small
            >{date(m.created_at)} · {sourceLabel(m.dataset.source)} · {m.dataset.windows} windows</small
          ></span
        ><strong>{Math.round(m.metrics.balanced_accuracy * 100)}%</strong><span
          class="pill"
          class:success={m.id === app.settings.active_model}
          >{m.id === app.settings.active_model ? 'Active' : 'View report'}</span
        ></button
      >{/each}{:else}<div class="empty-text">
      Your personal models will be saved here, ready for your next session.
    </div>{/if}
</section>
