<script lang="ts">
  import { Upload, Plus, Search, Download, AudioLines, ArrowRight } from '@lucide/svelte';
  import { app, action, command, refresh, notify } from '../lib/app.svelte';
  import { duration, date, sourceLabel } from '../lib/types';
  let search = $state(''),
    source = $state('all');
  let filtered = $derived(
    app.sessions.filter(
      (s) =>
        s.name.toLowerCase().includes(search.toLowerCase()) &&
        (source === 'all' || s.source === source),
    ),
  );
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">EVERY STEP, KEPT CLOSE</div>
    <h1>Your connection journal.</h1>
    <p>Your recordings, ready to revisit, export, or use in Model Studio.</p>
  </div>
  <button class="button primary" onclick={() => (app.page = 'EEG Recorder')}
    ><Plus size={17} />New session</button
  >
</div>
<section class="card">
  <div class="sessions-toolbar">
    <div class="search-field">
      <Search size={18} /><input
        aria-label="Search sessions"
        placeholder="Find a session…"
        bind:value={search}
      />
    </div>
    <select aria-label="Filter by source" bind:value={source}
      ><option value="all">All sources</option><option value="hardware">Device recordings</option
      ><option value="demo">Demo recordings</option><option value="legacy">Legacy imports</option
      ></select
    ><button class="button outlined" onclick={() => (app.page = 'Model Studio')}
      ><Upload size={16} />Import a recording</button
    >
  </div>
  {#if filtered.length}<div class="table-scroll">
      <table class="sessions-table">
        <thead
          ><tr
            ><th>Session</th><th>Source</th><th>Duration</th><th>Samples</th><th>Status</th><th
              ><span class="sr-only">Actions</span></th
            ></tr
          ></thead
        ><tbody
          >{#each filtered as s}<tr
              ><td
                ><div class="table-session">
                  <span class="icon-tile"><AudioLines size={19} /></span><span
                    ><strong>{s.name}</strong><small>{date(s.created_at)}</small></span
                  >
                </div></td
              ><td><span class="pill">{sourceLabel(s.source)}</span></td><td
                >{duration(s.duration_seconds)}</td
              ><td>{s.samples.toLocaleString()}</td><td>{s.complete ? 'Saved' : 'Interrupted'}</td
              ><td
                ><button
                  class="icon-button"
                  aria-label={`Export ${s.name}`}
                  onclick={() =>
                    action(async () => {
                      const result = await command<string | null>('export_session', {
                        sessionId: s.id,
                      });
                      if (result) notify('Recording exported.');
                    })}><Download size={18} /></button
                ></td
              ></tr
            >{/each}</tbody
        >
      </table>
    </div>
  {:else}<div class="large-empty">
      <div class="empty-illustration"><AudioLines size={40} /></div>
      <h3>
        {search || source !== 'all'
          ? 'No matching sessions.'
          : 'A new chapter starts with a signal.'}
      </h3>
      <p>
        {search || source !== 'all'
          ? 'Try a different name or source.'
          : 'Record your first guided session, or bring an existing EEG recording into Model Studio.'}
      </p>
      <button class="button primary" onclick={() => (app.page = 'EEG Recorder')}
        >Record your first session <ArrowRight size={17} /></button
      >
    </div>{/if}
</section>
<div class="page-footnote">
  <span>CSV exports include raw samples, trial labels, source, and sample rate.</span><span
    class="footnote-right">{app.sessions.length} sessions · stored locally</span
  >
</div>
