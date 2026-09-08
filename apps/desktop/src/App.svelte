<script lang="ts">
  import { onMount } from 'svelte';
  import {
    House,
    MessageCircle,
    AudioLines,
    BrainCircuit,
    FolderClock,
    Settings2,
    HelpCircle,
    ChevronDown,
    ChevronRight,
    ShieldCheck,
    Usb,
    ArrowUpRight,
    Sun,
    Moon,
    X,
    CheckCircle2,
    AlertCircle,
    PanelLeftClose,
    FlaskConical,
  } from '@lucide/svelte';
  import { app, initialize, action, save } from './lib/app.svelte';
  import type { Page } from './lib/types';
  import Practice from './components/Practice.svelte';
  import Crown from './components/Crown.svelte';
  import Overview from './components/Overview.svelte';
  import Communicate from './components/Communicate.svelte';
  import Recorder from './components/Recorder.svelte';
  import Studio from './components/Studio.svelte';
  import Sessions from './components/Sessions.svelte';
  import Preferences from './components/Settings.svelte';
  import Help from './components/Help.svelte';
  import DeviceDialog from './components/DeviceDialog.svelte';
  let deviceOpen = $state(false);
  const nav = [
    { name: 'Overview', icon: House },
    { name: 'Communicate', icon: MessageCircle },
    { name: 'EEG Recorder', icon: AudioLines },
    { name: 'Model Studio', icon: BrainCircuit },
    { name: 'Practice', icon: CheckCircle2 },
    { name: 'Sessions', icon: FolderClock },
  ];
  onMount(initialize);
  $effect(() => {
    document.documentElement.dataset.theme = app.settings.theme;
    document.documentElement.classList.toggle('large-text', app.settings.large_text);
    document.documentElement.classList.toggle('reduce-motion', app.settings.reduced_motion);
    document.title = `${app.page} · Mind-Nav`;
  });
</script>

<a class="skip-link" href="#main">Skip to content</a>
<div class:patient-mode={app.patient} class="app-shell">
  {#if !app.patient}<aside class="sidebar">
      <button class="brand" onclick={() => (app.page = 'Overview')} aria-label="Mind-Nav home"
        ><span class="brand-mark"><Crown size={37} /></span><span
          >mind<span class="brand-dash">–</span>nav<span class="brand-caption"
            >MADE FOR POSSIBILITY</span
          ></span
        ></button
      >
      <div class="workspace-switch">
        <span class="workspace-avatar">{app.settings.name.slice(0, 1).toUpperCase()}</span><span
          ><strong>{app.settings.name}’s space</strong><small>Personal workspace</small></span
        ><span class="local-indicator" title="Local workspace"><ShieldCheck size={15} /></span>
      </div>
      <div class="nav-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        {#each nav as item}<button
            class:active={app.page === item.name}
            aria-label={item.name}
            aria-current={app.page === item.name ? 'page' : undefined}
            onclick={() => (app.page = item.name as Page)}
            ><item.icon size={20} strokeWidth={1.7} /><span>{item.name}</span
            >{#if item.name === 'EEG Recorder' && app.snapshot.recording}<span
                class="record-indicator"
              ></span>{:else if item.name === 'Communicate'}<span class="nav-shortcut">↗</span
              >{/if}</button
          >{/each}
      </nav>
      <div class="sidebar-bottom">
        <button class="device-card" onclick={() => (deviceOpen = true)}
          ><span class="device-card-top"
            ><span class="icon-tile"><Usb size={19} /></span><span
              class="status-dot"
              class:green={app.snapshot.connected}
            ></span></span
          ><strong
            >{app.snapshot.connected
              ? app.snapshot.source === 'demo'
                ? 'Exploring demo mode'
                : 'Your device is connected'
              : 'A connection starts here.'}</strong
          ><span
            >{app.snapshot.connected
              ? 'Your next step is full of possibility.'
              : 'Let’s find your signal, together.'}</span
          ><span class="device-card-action"
            >{app.snapshot.connected ? 'Manage connection' : 'Set up your device'}<ArrowUpRight
              size={16}
            /></span
          ></button
        >
        <nav aria-label="Preferences and help">
          <button
            class:active={app.page === 'Settings'}
            aria-label="Settings"
            aria-current={app.page === 'Settings' ? 'page' : undefined}
            onclick={() => (app.page = 'Settings')}
            ><Settings2 size={20} strokeWidth={1.7} /><span>Settings</span></button
          ><button
            class:active={app.page === 'Help'}
            aria-label="A little guidance"
            aria-current={app.page === 'Help' ? 'page' : undefined}
            onclick={() => (app.page = 'Help')}
            ><HelpCircle size={20} strokeWidth={1.7} /><span>A little guidance</span></button
          >
        </nav>
        <div class="sidebar-footer">
          <span class="status-dot green"></span>LOCAL FIRST<span>v0.2</span>
        </div>
      </div>
    </aside>{/if}
  <div class="main-shell">
    <header class="topbar">
      <div class="breadcrumb">
        {#if app.patient}<span class="patient-brand"><Crown size={26} />mind–nav</span>{:else}<span
            >My workspace</span
          ><ChevronRight size={13} /><strong>{app.page}</strong>{/if}
      </div>
      <div class="topbar-right">
        {#if !app.native}<span class="preview-badge">Design preview</span>{/if}<span
          class="privacy-label"><ShieldCheck size={15} />Local & private</span
        ><span class="topbar-divider"></span><button
          class="icon-button theme-toggle"
          onclick={() =>
            action(() => save({ theme: app.settings.theme === 'light' ? 'dark' : 'light' }))}
          aria-label={app.settings.theme === 'light'
            ? 'Switch to dark theme'
            : 'Switch to light theme'}
          >{#if app.settings.theme === 'light'}<Moon size={18} />{:else}<Sun
              size={18}
            />{/if}</button
        ><button
          class="profile-button"
          aria-label="Open personal settings"
          onclick={() => {
            app.patient = false;
            app.page = 'Settings';
          }}>{app.settings.name.slice(0, 1).toUpperCase()}</button
        >
      </div>
    </header>
    {#if app.snapshot.recording && app.page !== 'EEG Recorder'}<button
        class="recording-banner"
        onclick={() => (app.page = 'EEG Recorder')}
        ><span class="recording-dot little-dot"></span>{app.snapshot.paused
          ? 'Recording paused'
          : 'Recording in progress'}<span>Return to recorder <ArrowUpRight size={14} /></span
        ></button
      >{/if}
    {#if app.snapshot.source === 'demo' && app.page !== 'Overview'}<div class="demo-banner">
        <FlaskConical size={15} />Demo mode · {app.native
          ? 'Simulated data is kept separate from device recordings.'
          : 'Illustrative browser preview. Recording and model training run in the desktop app.'}
      </div>{/if}
    <main id="main" tabindex="-1">
      {#if app.page === 'Overview'}<Overview
          connect={() => (deviceOpen = true)}
        />{:else if app.page === 'Communicate'}<Communicate
        />{:else if app.page === 'EEG Recorder'}<Recorder
          connect={() => (deviceOpen = true)}
        />{:else if app.page === 'Model Studio'}<Studio
        />{:else if app.page === 'Practice'}<Practice />{:else if app.page === 'Sessions'}<Sessions
        />{:else if app.page === 'Settings'}<Preferences />{:else}<Help />{/if}
    </main>
  </div>
</div>
{#if deviceOpen}<DeviceDialog onclose={() => (deviceOpen = false)} />{/if}
{#if app.toast}<div
    class:error={app.toastError}
    class="toast"
    role={app.toastError ? 'alert' : 'status'}
  >
    {#if app.toastError}<AlertCircle size={20} />{:else}<CheckCircle2 size={20} />{/if}<span
      >{app.toast}</span
    ><button class="icon-button" onclick={() => (app.toast = '')} aria-label="Dismiss notification"
      ><X size={17} /></button
    >
  </div>{/if}
