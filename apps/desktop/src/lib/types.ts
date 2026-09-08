export type Page =
  | 'Overview'
  | 'Communicate'
  | 'EEG Recorder'
  | 'Model Studio'
  | 'Practice'
  | 'Sessions'
  | 'Settings'
  | 'Help';
export interface Settings {
  theme: 'light' | 'dark';
  large_text: boolean;
  reduced_motion: boolean;
  scan_ms: number;
  threshold: number;
  notch: number;
  voice_cues: boolean;
  name: string;
  active_model: string | null;
}
export interface Config {
  sample_rate: number;
  high_pass: number;
  low_pass: number;
  notch: number;
}
export interface Summary {
  samples: number;
  windows: number;
  window_samples: number;
  rest_windows: number;
  select_windows: number;
  trials: number;
  rejected_windows: number;
  duration_seconds: number;
  source: string;
  name: string;
}
export interface Session {
  id: string;
  name: string;
  created_at: number;
  source: string;
  samples: number;
  duration_seconds: number;
  rest_trials: number;
  select_trials: number;
  complete: boolean;
  imported: boolean;
  config: Config;
  summary: Summary | null;
}
export interface Model {
  id: string;
  name: string;
  created_at: number;
  config: Config;
  dataset: Summary;
  metrics: {
    balanced_accuracy: number;
    precision: number;
    recall: number;
    false_positive_rate: number;
    confusion: number[][];
    folds: number;
    fold_accuracy: number[];
  };
}
export interface Practice {
  running: boolean;
  samples: number;
  trials: number;
  correct: number;
  skipped: number;
  confusion: number[][];
}
export interface Snapshot {
  practice: Practice;
  connected: boolean;
  source: string;
  port: string;
  quality: { usable: boolean; score: number; reason: string; rms: number; peak_to_peak: number };
  waveform: number[];
  bands: number[];
  sample_count: number;
  dropped: number;
  sample_rate: number;
  recording: boolean;
  paused: boolean;
  elapsed: number;
  cue: string;
  cue_remaining: number;
  rest_trials: number;
  select_trials: number;
  probability: number | null;
  armed: boolean;
  selections: number;
  error: string | null;
  training: { running: boolean; progress: number; message: string };
}
export const defaults: Settings = {
  theme: 'light',
  large_text: false,
  reduced_motion: false,
  scan_ms: 1500,
  threshold: 0.8,
  notch: 50,
  voice_cues: true,
  name: 'Explorer',
  active_model: null,
};
export const emptySnapshot: Snapshot = {
  practice: {
    running: false,
    samples: 0,
    trials: 0,
    correct: 0,
    skipped: 0,
    confusion: [
      [0, 0],
      [0, 0],
    ],
  },
  connected: false,
  source: 'disconnected',
  port: '',
  quality: {
    usable: false,
    score: 0,
    reason: 'Connect your device to check the signal',
    rms: 0,
    peak_to_peak: 0,
  },
  waveform: [],
  bands: [0, 0, 0, 0, 0],
  sample_count: 0,
  dropped: 0,
  sample_rate: 0,
  recording: false,
  paused: false,
  elapsed: 0,
  cue: 'REST',
  cue_remaining: 5,
  rest_trials: 0,
  select_trials: 0,
  probability: null,
  armed: false,
  selections: 0,
  error: null,
  training: { running: false, progress: 0, message: 'Ready to train' },
};
export function duration(seconds: number) {
  const s = Math.floor(seconds);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}
export function date(ms: number) {
  return new Date(ms).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}
export function sourceLabel(source: string) {
  return source === 'hardware'
    ? 'Device'
    : source === 'legacy'
      ? 'Legacy import'
      : source === 'demo'
        ? 'Demo'
        : 'Disconnected';
}
