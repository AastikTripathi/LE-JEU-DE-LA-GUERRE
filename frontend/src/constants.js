// src/constants.js
export const COLS = 25;
export const ROWS = 20;

export const TERRAIN_MAP = {
  mountains: ['5,9', '6,9', '7,9', '17,10', '18,10', '19,10'],
  passes: ['8,9', '16,10'],
  arsenals: ['12,1', '13,1', '2,18', '22,18'],
  forts: ['4,4', '20,4', '12,15']
};

export const GET_TERRAIN = (x, y) => {
  const key = `${x},${y}`;
  if (TERRAIN_MAP.mountains.includes(key)) return { type: 'mountain', label: '▲', color: '#4b5563' };
  if (TERRAIN_MAP.passes.includes(key)) return { type: 'pass', label: '⚬', color: '#1f2937', border: '2px dashed #6b7280' };
  if (TERRAIN_MAP.forts.includes(key)) return { type: 'fort', label: '⛊', color: '#b45309' };
  if (TERRAIN_MAP.arsenals.includes(key)) return { type: 'arsenal', label: '★', color: '#111827', border: '2px solid #3b82f6' };
  return { type: 'plain', label: '', color: '#111827' };
};