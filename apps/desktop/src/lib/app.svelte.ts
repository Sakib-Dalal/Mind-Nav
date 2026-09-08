import { invoke, isTauri } from '@tauri-apps/api/core';
import { defaults, emptySnapshot } from './types';
import type { Settings, Snapshot, Session, Model, Page } from './types';
export const app = $state({
  page: 'Overview' as Page,
  settings: { ...defaults },
  snapshot: { ...emptySnapshot },
  sessions: [] as Session[],
  models: [] as Model[],
  native: isTauri(),
  ready: false,
  busy: false,
  toast: '',
  toastError: false,
  patient: false,
  directory: '',
});
let toastTimer: ReturnType<typeof setTimeout>;
export function notify(message: string, error = false) {
  app.toast = message;
  app.toastError = error;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (app.toast = ''), 6500);
}
export async function command<T = void>(name: string, args?: Record<string, unknown>): Promise<T> {
  if (!app.native)
    throw new Error(
      'Open the desktop app for recording, device access, and Rust model training. Run npm run tauri dev.',
    );
  return invoke<T>(name, args);
}
export async function action(fn: () => Promise<unknown>, success?: string) {
  try {
    await fn();
    if (success) notify(success);
  } catch (e) {
    notify(String(e).replace(/^Error: /, ''), true);
  }
}
export async function refresh() {
  if (app.native) {
    const data = await command<{
      settings: Settings;
      sessions: Session[];
      models: Model[];
      data_directory: string;
    }>('bootstrap');
    Object.assign(app, {
      settings: data.settings,
      sessions: data.sessions,
      models: data.models,
      directory: data.data_directory,
    });
  }
}
export async function save(patch: Partial<Settings>) {
  const next = { ...app.settings, ...patch };
  if (app.native) await command('save_settings', { settings: next });
  else localStorage.setItem('mindnav-preferences', JSON.stringify(next));
  app.settings = next;
}
export async function startDemo() {
  if (app.native) await command('start_demo');
  else {
    app.snapshot = {
      ...emptySnapshot,
      connected: true,
      source: 'demo',
      port: 'Browser design preview',
      quality: {
        usable: true,
        score: 96,
        reason: 'Illustrative signal · desktop app runs Rust processing',
        rms: 14,
        peak_to_peak: 55,
      },
      sample_rate: 250,
    };
  }
  notify(
    app.native
      ? 'Demo signal started. Recordings will be labeled Demo.'
      : 'Exploring an illustrative preview. Native recording and training are available in the desktop app.',
  );
}
export async function disconnect() {
  if (app.native) await command('disconnect_device');
  else app.snapshot = { ...emptySnapshot };
}
export async function speak(text: string) {
  if (app.native) await command('speak', { text });
  else if ('speechSynthesis' in window) {
    speechSynthesis.cancel();
    speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  } else throw new Error('Speech is not available on this device.');
}
export function initialize() {
  let stopped = false,
    pending = false,
    lastError = '';
  action(async () => {
    if (app.native) await refresh();
    else {
      try {
        const saved = JSON.parse(localStorage.getItem('mindnav-preferences') || '{}');
        app.settings = { ...defaults, ...saved };
      } catch {
        /* Use defaults for damaged preferences. */
      }
    }
    app.ready = true;
  });
  const interval = setInterval(async () => {
    if (stopped || pending) return;
    pending = true;
    try {
      if (app.native) {
        const before = app.snapshot.recording;
        app.snapshot = await command<Snapshot>('snapshot');
        if (before && !app.snapshot.recording) await refresh();
        if (app.snapshot.error && app.snapshot.error !== lastError) {
          lastError = app.snapshot.error;
          notify(lastError, true);
        }
      } else if (app.snapshot.connected) {
        const t = performance.now() / 1000;
        app.snapshot.waveform = Array.from({ length: 500 }, (_, i) => {
          const x = t + i / 250;
          return (
            17 * Math.sin(x * 63) +
            5 * Math.sin(x * 126) +
            3 * Math.sin(x * 37) +
            2 * Math.sin(x * 213)
          );
        });
        app.snapshot.sample_count += 50;
        app.snapshot.bands = [2, 8, 66, 19, 5];
      }
    } catch (e) {
      if (!stopped) {
        app.snapshot.armed = false;
        app.snapshot.connected = false;
        app.snapshot.quality.usable = false;
        notify(`Desktop connection interrupted: ${e}`, true);
      }
    } finally {
      pending = false;
    }
  }, 200);
  return () => {
    stopped = true;
    clearInterval(interval);
    clearTimeout(toastTimer);
  };
}

export const composer = $state({
  text: '',
  history: [] as string[],
  board: 'phrases' as 'phrases' | 'keyboard',
});
