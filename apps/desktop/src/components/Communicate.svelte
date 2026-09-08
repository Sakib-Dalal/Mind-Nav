<script lang="ts">
  import { onMount } from 'svelte';
  import {
    Play,
    Pause,
    Volume2,
    Undo2,
    Delete,
    ArrowLeft,
    Heart,
    GlassWater,
    HandHeart,
    Check,
    Minus,
    MessageCircle,
    Keyboard,
    Maximize2,
    BrainCircuit,
    MousePointer2,
  } from '@lucide/svelte';
  import { app, action, command, speak, notify, composer } from '../lib/app.svelte';
  import { initialScan, tick, select } from '../lib/scanner';
  let scan = $state(initialScan()),
    lastSelections = app.snapshot.selections;
  let boardElement = $state<HTMLDivElement>();
  const phrases = [
    { key: 'Yes', icon: Check, tone: 'sage', text: 'Yes' },
    { key: 'No', icon: Minus, tone: 'blue', text: 'No' },
    {
      key: 'Water, please',
      icon: GlassWater,
      tone: 'blue',
      text: 'I would like some water, please.',
    },
    { key: 'I need help', icon: HandHeart, tone: 'peach', text: 'I need some help, please.' },
    {
      key: 'I’m uncomfortable',
      icon: Heart,
      tone: 'rose',
      text: 'I am uncomfortable. Please help me adjust.',
    },
    { key: 'Thank you', icon: MessageCircle, tone: 'sage', text: 'Thank you.' },
  ];
  let rows = $derived(
    composer.board === 'phrases'
      ? [
          phrases.slice(0, 3).map((p) => p.key),
          phrases.slice(3).map((p) => p.key),
          ['Keyboard', 'Speak', 'Undo', 'Pause', 'Finish'],
        ]
      : [
          'QWERTYUIOP'.split(''),
          'ASDFGHJKL'.split(''),
          'ZXCVBNM'.split(''),
          ['Space', 'Delete', 'Speak', 'Phrases', 'Undo', 'Pause', 'Finish'],
        ],
  );
  function change(value: string) {
    composer.history = [...composer.history.slice(-49), composer.text];
    composer.text = value.slice(0, 2000);
  }
  function choose(value: string) {
    if (value === 'Keyboard' || value === 'Phrases') {
      composer.board = value === 'Keyboard' ? 'keyboard' : 'phrases';
      scan = { ...initialScan(), running: scan.running };
    } else if (value === 'Speak') {
      if (composer.text.trim()) action(() => speak(composer.text));
      else notify('Choose a phrase or type a message first.');
    } else if (value === 'Undo') {
      const previous = composer.history.at(-1);
      if (previous !== undefined) {
        composer.text = previous;
        composer.history = composer.history.slice(0, -1);
      }
    } else if (value === 'Delete') change(Array.from(composer.text).slice(0, -1).join(''));
    else if (value === 'Space') change(composer.text + ' ');
    else if (value === 'Pause') scan = { ...scan, running: false };
    else if (value === 'Finish') {
      scan = initialScan();
      app.patient = false;
      app.page = 'Overview';
      if (app.snapshot.armed) action(() => command('arm_input', { armed: false }));
    } else if (composer.board === 'phrases') {
      const phrase = phrases.find((p) => p.key === value);
      if (phrase) {
        change(phrase.text);
        if (app.settings.voice_cues) action(() => speak(phrase.text));
      }
    } else change(composer.text + value.toLowerCase());
  }
  function input() {
    const result = select(scan, rows);
    scan = result.scan;
    if (result.value) choose(result.value);
  }
  function key(event: KeyboardEvent) {
    if (event.repeat) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      scan = { ...scan, running: false };
      if (app.snapshot.armed) action(() => command('arm_input', { armed: false }));
      return;
    }
    const el = event.target as HTMLElement;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)) return;
    if (event.key === 'Enter' && (scan.running || app.patient || el.tagName !== 'BUTTON')) {
      event.preventDefault();
      input();
    }
  }

  onMount(() => {
    window.addEventListener('keydown', key);
    return () => {
      window.removeEventListener('keydown', key);
      if (app.snapshot.armed) action(() => command('arm_input', { armed: false }));
    };
  });
  $effect(() => {
    if (!scan.running) return;
    const current = scan;
    const options = rows;
    const timer = setTimeout(() => (scan = tick(current, options)), app.settings.scan_ms);
    return () => clearTimeout(timer);
  });
  $effect(() => {
    if (scan.running) {
      boardElement?.querySelectorAll<HTMLElement>('.scan-row')[scan.row]?.scrollIntoView({
        block: 'nearest',
        behavior: 'instant',
      });
    }
  });
  $effect(() => {
    if (app.snapshot.selections > lastSelections) {
      lastSelections = app.snapshot.selections;
      if (app.snapshot.armed && app.page === 'Communicate') input();
    } else if (app.snapshot.selections < lastSelections) lastSelections = app.snapshot.selections;
  });
  const active = (r: number, c: number) =>
    scan.running && scan.row === r && (scan.phase === 'rows' || scan.column === c);
</script>

<div class="page-heading">
  <div>
    <div class="eyebrow">A SPACE FOR YOUR VOICE</div>
    <h1>Say it your way.</h1>
    <p>Choose a phrase or take your time with a message.</p>
  </div>
  <button class="button outlined" onclick={() => (app.patient = !app.patient)}
    >{#if app.patient}<ArrowLeft size={18} />Caregiver workspace{:else}<Maximize2
        size={18}
      />Patient view{/if}</button
  >
</div>
<section class="message-output card">
  <div class="message-label">
    <span>YOUR MESSAGE</span><span>{composer.text.length} / 2000</span>
  </div>
  <div class="composed-message" aria-live="polite" aria-atomic="true">
    {composer.text || 'A hello is a lovely place to start.'}
  </div>
  <div class="message-actions">
    <button class="button primary" onclick={() => choose('Speak')} disabled={!composer.text}
      ><Volume2 size={19} />Speak message</button
    ><button
      class="button outlined"
      onclick={() => choose('Undo')}
      disabled={!composer.history.length}><Undo2 size={17} />Undo</button
    ><span class="muted tiny"
      >{app.settings.voice_cues
        ? 'Quick phrases are spoken when selected.'
        : 'Select a phrase, then choose Speak.'}</span
    >
  </div>
</section>
<div class="board-toolbar">
  <div class="segmented">
    <button
      class:chosen={composer.board === 'phrases'}
      aria-pressed={composer.board === 'phrases'}
      onclick={() => choose('Phrases')}><MessageCircle size={17} />Quick phrases</button
    ><button
      class:chosen={composer.board === 'keyboard'}
      aria-pressed={composer.board === 'keyboard'}
      onclick={() => choose('Keyboard')}><Keyboard size={17} />Keyboard</button
    >
  </div>
  <span class="muted tiny"
    >{scan.running
      ? `Scanning ${scan.phase === 'rows' ? 'rows' : 'keys'} · ${app.settings.scan_ms / 1000}s per step`
      : 'Ready when you are'}</span
  >
</div>
<div
  bind:this={boardElement}
  class="communication-board"
  aria-label={composer.board === 'phrases' ? 'Quick phrases' : 'Scanning keyboard'}
>
  {#each rows as row, r}<div
      class:keyboard-row={composer.board === 'keyboard'}
      class:controls-row={r === rows.length - 1}
      class:scanned-row={scan.running && scan.phase === 'rows' && scan.row === r}
      class="scan-row"
    >
      {#each row as value, c}{@const phrase = phrases.find((p) => p.key === value)}<button
          class:scan-active={active(r, c)}
          class:phrase-tile={composer.board === 'phrases' && r < 2}
          class:key-tile={composer.board === 'keyboard' && r < rows.length - 1}
          class:scan-control={r === rows.length - 1}
          class={`board-key ${phrase?.tone || ''}`}
          onclick={() => choose(value)}
          aria-label={value === 'Delete' ? 'Delete last character' : value}
        >
          {#if phrase && composer.board === 'phrases'}<span class="phrase-icon"
              ><phrase.icon size={29} /></span
            ><span>{value}</span>{:else if value === 'Delete'}<Delete
              size={22}
            />{:else}{value}{/if}
          {#if active(r, c) && scan.phase === 'keys'}<span class="select-marker" aria-hidden="true"
              >●</span
            >{/if}</button
        >{/each}
    </div>{/each}
</div>
<section class="scan-dock">
  <div class="scan-status-icon"><MousePointer2 size={24} /></div>
  <div>
    <strong>{scan.running ? 'Your scanner is moving.' : 'Your pace. You’re in control.'}</strong>
    <p>
      {app.snapshot.armed
        ? 'Use your trained intention to select the highlighted row, then a key.'
        : 'Press Enter or your connected switch to select a row, then a key.'}
    </p>
  </div>
  <button class="button outlined" onclick={() => (scan = { ...scan, running: !scan.running })}
    >{#if scan.running}<Pause size={17} />Pause scan{:else}<Play size={17} />Start scanning{/if}</button
  ><button class="button primary" onclick={input}
    >{scan.running ? 'Select highlighted' : 'Start with switch'}</button
  >
</section>
{#if !app.patient}<section class="card input-settings">
    <div>
      <BrainCircuit size={22} />
      <div>
        <h3>Use your brain signal</h3>
        <p>Activate a personal model and connect its matching signal source.</p>
      </div>
    </div>
    <button
      class="button outlined"
      disabled={!app.snapshot.connected && !app.snapshot.armed}
      onclick={() =>
        action(async () => {
          await command('arm_input', { armed: !app.snapshot.armed });
        })}>{app.snapshot.armed ? 'Pause BCI input' : 'Enable BCI input'}</button
    >
  </section>{/if}
<div class="page-footnote">
  <span>Escape pauses scanning and BCI input.</span><span class="footnote-right"
    >“I need help” speaks on this device; it does not contact anyone.</span
  >
</div>
