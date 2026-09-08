import { describe, it, expect } from 'vitest';
import { initialScan, select, tick } from './scanner';
const rows = [
  ['Yes', 'No'],
  ['Help', 'Water'],
  ['Undo', 'Pause', 'Finish'],
];
describe('one-switch scanning', () => {
  it('selects a row and a key, then returns to rows', () => {
    let s = select(initialScan(), rows).scan;
    s = tick(s, rows);
    expect(s.row).toBe(1);
    s = select(s, rows).scan;
    expect(s.phase).toBe('keys');
    s = tick(s, rows);
    const result = select(s, rows);
    expect(result.value).toBe('Water');
    expect(result.scan.phase).toBe('rows');
  });
  it('recovers after two missed key cycles', () => {
    let s = select(select(initialScan(), rows).scan, rows).scan;
    for (let i = 0; i < 4; i++) s = tick(s, rows);
    expect(s.phase).toBe('rows');
    expect(s.row).toBe(0);
  });
  it('does not advance while paused and can resume with the same switch', () => {
    let s = initialScan();
    expect(tick(s, rows)).toEqual(s);
    s = select(s, rows).scan;
    expect(s.running).toBe(true);
  });
  it('exposes finish and pause to users who cannot move', () => {
    let s = { ...initialScan(), running: true, row: 2 };
    s = select(s, rows).scan;
    s = tick(s, rows);
    expect(select(s, rows).value).toBe('Pause');
    s = tick(s, rows);
    expect(select(s, rows).value).toBe('Finish');
  });
});
