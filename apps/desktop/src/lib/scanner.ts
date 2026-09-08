/** Row-column scanning shared by switch and BCI input. No signal logic in the UI. */
export interface Scan {
  phase: 'rows' | 'keys';
  row: number;
  column: number;
  cycles: number;
  running: boolean;
}
export const initialScan = (): Scan => ({
  phase: 'rows',
  row: 0,
  column: 0,
  cycles: 0,
  running: false,
});
export function tick(s: Scan, rows: string[][]): Scan {
  if (!s.running || !rows.length) return s;
  if (s.phase === 'rows') return { ...s, row: (s.row + 1) % rows.length };
  const column = (s.column + 1) % rows[s.row].length,
    cycles = s.cycles + (column === 0 ? 1 : 0);
  return cycles >= 2 ? { ...initialScan(), running: true } : { ...s, column, cycles };
}
export function select(s: Scan, rows: string[][]): { scan: Scan; value?: string } {
  if (!s.running) return { scan: { ...initialScan(), running: true } };
  if (s.phase === 'rows') return { scan: { ...s, phase: 'keys', column: 0, cycles: 0 } };
  return { scan: { ...initialScan(), running: true }, value: rows[s.row]?.[s.column] };
}
