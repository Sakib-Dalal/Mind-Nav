<script lang="ts">
  import {
    ArrowUpRight,
    ArrowRight,
    Activity,
    BrainCircuit,
    Clock3,
    MousePointer2,
    Play,
    Plus,
    ShieldCheck,
    ChevronRight,
    AudioLines,
    Check,
    FlaskConical,
  } from '@lucide/svelte';
  import { app, action, startDemo } from '../lib/app.svelte';
  import { duration, date, sourceLabel } from '../lib/types';
  import Crown from './Crown.svelte';
  import Waveform from './Waveform.svelte';
  let { connect } = $props<{ connect: () => void }>();
  let model = $derived(app.models.find((m) => m.id === app.settings.active_model));
  const bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma'];
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">YOUR PERSONAL WORKSPACE</div>
    <h1>A little thought.<br class="mobile-break" /> A world of possibility.</h1>
    <p>Everything you need to connect, communicate, and move forward.</p>
  </div>
  <button class="button outlined" onclick={connect}><Plus size={17} /> Connect device</button>
</div>
<section class="welcome-card">
  <div class="welcome-content">
    <span class="pill hero-pill"><span class="status-dot"></span> BUILT AROUND YOU</span>
    <h2>Your voice.<br />Your pace. Your way.</h2>
    <p>Turn intention into connection.<br />Let’s make your next conversation possible.</p>
    <div class="button-row">
      <button class="button primary" onclick={() => (app.page = 'Communicate')}
        >Start communicating <ArrowUpRight size={18} /></button
      ><button class="hero-link" onclick={() => (app.page = 'Help')}
        >Take a quick tour <ArrowRight size={16} /></button
      >
    </div>
  </div>
  <div class="hero-art" aria-hidden="true">
    <div class="orbit orbit-one"></div>
    <div class="orbit orbit-two"></div>
    <div class="orbit orbit-three"></div>
    <div class="orbit orbit-four"></div>
    <div class="orb orb-one"></div>
    <div class="orb orb-two"></div>
    <div class="orb orb-three"></div>
    <div class="crown-sphere"><Crown size={114} /></div>
    <div class="floating-label thought"><span class="thought-dot"></span>A thought</div>
    <div class="floating-label possibility"><Check size={14} /> A possibility</div>
    <span class="star star-one">✳</span><span class="star star-two">+</span>
  </div>
  <span class="hero-index">MIND-NAV / MADE FOR POSSIBILITY</span>
</section>
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-label"><span>Signal status</span><Activity size={18} /></div>
    <strong
      >{app.snapshot.connected
        ? app.snapshot.quality.usable
          ? 'Signal ready'
          : 'Settling…'
        : 'Not connected'}<span class:green={app.snapshot.quality.usable} class="little-dot"
      ></span></strong
    ><span
      >{app.snapshot.connected
        ? `${app.snapshot.source === 'demo' ? 'Demo signal' : 'Single channel'} · ${Math.round(app.snapshot.sample_rate)} Hz`
        : 'Your device is one step away'}</span
    >
  </div>
  <button class="stat-card" onclick={() => (app.page = 'Model Studio')}
    ><div class="stat-label"><span>Active model</span><BrainCircuit size={18} /></div>
    <strong class="truncate">{model?.name || 'Make it personal'}</strong><span
      >{model
        ? `${Math.round(model.metrics.balanced_accuracy * 100)}% balanced CV accuracy`
        : 'Create a model that learns from you'}<ArrowUpRight size={14} /></span
    ></button
  >
  <button class="stat-card" onclick={() => (app.page = 'Sessions')}
    ><div class="stat-label"><span>Time connected</span><Clock3 size={18} /></div>
    <strong
      >{duration(
        app.sessions.reduce((sum, s) => sum + s.duration_seconds, 0) + app.snapshot.elapsed,
      )}<small>min : sec</small></strong
    ><span
      >{app.sessions.length} saved {app.sessions.length === 1 ? 'session' : 'sessions'} on this device</span
    ></button
  >
  <button class="stat-card" onclick={() => (app.page = 'Communicate')}
    ><div class="stat-label"><span>Your input</span><MousePointer2 size={18} /></div>
    <strong>{app.snapshot.armed ? 'Brain signal' : 'Switch & scan'}</strong><span
      >{app.snapshot.armed
        ? 'Personal model is listening'
        : 'Simple, one-switch communication'}<ArrowUpRight size={14} /></span
    ></button
  >
</div>
<div class="overview-grid">
  <section class="card signal-card">
    <div class="card-heading">
      <div>
        <h3>Meet your signal <span class="subtle-tag">EEG</span></h3>
        <p>A small window into your connection.</p>
      </div>
      <span class="pill" class:success={app.snapshot.connected}
        ><span class="status-dot"></span>{app.snapshot.connected
          ? app.snapshot.source === 'demo'
            ? 'Demo signal'
            : 'Live signal'
          : 'Offline'}</span
      >
    </div>
    <Waveform />
    <div class="signal-footer">
      <div class="filter-label">
        <span class="status-dot green"></span>0.5–40 Hz bandpass<span class="dot-separator">·</span
        >{app.settings.notch ? `${app.settings.notch} Hz notch` : 'Notch off'}
      </div>
      <button class="text-button" onclick={() => (app.page = 'EEG Recorder')}
        >Open recorder <ArrowUpRight size={15} /></button
      >
    </div>
  </section>
  <section class="card next-card">
    <div class="card-heading">
      <div>
        <div class="eyebrow">ONE STEP AT A TIME</div>
        <h3>Your path to connection</h3>
      </div>
      <span class="small-crown"><Crown size={24} /></span>
    </div>
    {#each [{ n: '01', title: 'Find your signal', text: 'Connect your device and get comfortable.', done: app.snapshot.connected, page: 'device' }, { n: '02', title: 'Make it yours', text: 'Record a session. Create your personal model.', done: app.models.length > 0, page: 'Model Studio' }, { n: '03', title: 'Say what’s on your mind', text: 'A word, a request, a little hello.', done: false, page: 'Communicate' }] as step}<button
        class="step"
        onclick={() =>
          step.page === 'device'
            ? connect()
            : (app.page = step.page as 'Model Studio' | 'Communicate')}
        ><span class:done={step.done} class="step-number"
          >{#if step.done}<Check size={16} />{:else}{step.n}{/if}</span
        ><span><strong>{step.title}</strong><small>{step.text}</small></span><ChevronRight
          size={17}
        /></button
      >{/each}
    <div class="gentle-note">No rush. Every small step counts.</div>
  </section>
</div>
<div class="overview-bottom">
  <section class="card sessions-preview">
    <div class="card-heading">
      <h3>Your recent sessions</h3>
      <button class="text-button" onclick={() => (app.page = 'Sessions')}
        >View all <ArrowRight size={15} /></button
      >
    </div>
    {#if app.sessions.length}{#each app.sessions.slice(0, 2) as session}<button
          class="session-mini"
          onclick={() => (app.page = 'Sessions')}
          ><span class="icon-tile"><AudioLines size={20} /></span><span
            ><strong>{session.name}</strong><small
              >{date(session.created_at)} · {sourceLabel(session.source)}</small
            ></span
          ><span>{duration(session.duration_seconds)}</span><ChevronRight size={17} /></button
        >{/each}{:else}<div class="empty-inline">
        <span class="icon-tile neutral"><AudioLines size={24} /></span>
        <div>
          <strong>A fresh start, full of possibilities.</strong>
          <p>Your first recording will feel right at home here.</p>
        </div>
        <button class="button outlined small" onclick={() => (app.page = 'EEG Recorder')}
          >Record a session <Plus size={15} /></button
        >
      </div>{/if}
  </section>
  <button class="demo-card" onclick={() => action(startDemo)} disabled={app.snapshot.recording}
    ><span class="icon-tile"><FlaskConical size={22} /></span>
    <div>
      <h3>A little curious?</h3>
      <p>Explore with a demo signal.<br />No headset needed.</p>
    </div>
    <ArrowUpRight size={23} /></button
  >
</div>
<div class="page-footnote">
  <ShieldCheck size={15} /><span>On your device. In your control.</span><span class="footnote-right"
    >Designed for independence, one intention at a time.</span
  >
</div>
