
// src/constants.js
export const COLS = 25;
export const ROWS = 20;

export const TERRAIN_MAP = {
  // Authentic L-shaped configuration
  mountains: [
    // North Range
    '9,2', '10,2', '11,2', '12,2',
    '9,3', '9,4',
    '9,6', '9,7', '9,8',
    // South Range
    '10,13', '11,13', '12,13', '13,13', '14,13', '15,13',
    '15,15', '15,16', '15,17'
  ],
  // Pass gaps breaking through the mountain barriers
  passes: ['9,5', '15,14'],
  // Authentic Home Arsenals
  arsenals: ['7,3', '14,1', '2,19', '22,19'],
  // Historical Fortresses
  forts: [
    '7,1', '12,8', '20,7',    // North Fortifications
    '2,12', '14,11', '22,14'  // South Fortifications
  ]
};

export const GET_TERRAIN = (x, y) => {
  const key = `${x},${y}`;
  if (TERRAIN_MAP.mountains.includes(key)) return { type: 'mountain', label: '▲', color: '#4b5563' };
  if (TERRAIN_MAP.passes.includes(key)) return { type: 'pass', label: '⚬', color: '#1f2937', border: '2px dashed #6b7280' };
  if (TERRAIN_MAP.forts.includes(key)) return { type: 'fort', label: '⛊', color: '#b45309' };
  if (TERRAIN_MAP.arsenals.includes(key)) return { type: 'arsenal', label: '★', color: '#111827', border: '2px solid #3b82f6' };
  return { type: 'plain', label: '', color: '#111827' };
};
