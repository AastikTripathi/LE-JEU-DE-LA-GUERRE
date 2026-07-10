// src/initialUnits.js
// Must exactly mirror the unit list in server.py get_initial_state()
export const INITIAL_UNITS = [
  // === NORTH FORCES (17 Units) ===
  { id: 'n-inf-1', side: 'North', type: 'Infantry', symbol: 'I', x: 4,  y: 4 },
  { id: 'n-inf-2', side: 'North', type: 'Infantry', symbol: 'I', x: 6,  y: 4 },
  { id: 'n-inf-3', side: 'North', type: 'Infantry', symbol: 'I', x: 8,  y: 4 },
  { id: 'n-inf-4', side: 'North', type: 'Infantry', symbol: 'I', x: 10, y: 4 },
  { id: 'n-inf-5', side: 'North', type: 'Infantry', symbol: 'I', x: 12, y: 4 },
  { id: 'n-inf-6', side: 'North', type: 'Infantry', symbol: 'I', x: 14, y: 4 },
  { id: 'n-inf-7', side: 'North', type: 'Infantry', symbol: 'I', x: 16, y: 4 },
  { id: 'n-inf-8', side: 'North', type: 'Infantry', symbol: 'I', x: 18, y: 4 },
  { id: 'n-inf-9', side: 'North', type: 'Infantry', symbol: 'I', x: 20, y: 4 },

  { id: 'n-cav-1', side: 'North', type: 'Cavalry',  symbol: 'C', x: 3,  y: 3 },
  { id: 'n-cav-2', side: 'North', type: 'Cavalry',  symbol: 'C', x: 7,  y: 3 },
  { id: 'n-cav-3', side: 'North', type: 'Cavalry',  symbol: 'C', x: 17, y: 3 },
  { id: 'n-cav-4', side: 'North', type: 'Cavalry',  symbol: 'C', x: 21, y: 3 },

  { id: 'n-art-1', side: 'North', type: 'Artillery', symbol: 'A', x: 11, y: 2 },
  { id: 'n-art-2', side: 'North', type: 'Artillery', symbol: 'A', x: 13, y: 2 },

  { id: 'n-rel-1', side: 'North', type: 'Relay', symbol: 'R', x: 10, y: 1 },
  { id: 'n-rel-2', side: 'North', type: 'Relay', symbol: 'R', x: 14, y: 1 },

  // === SOUTH FORCES (17 Units) ===
  { id: 's-inf-1', side: 'South', type: 'Infantry', symbol: 'I', x: 4,  y: 15 },
  { id: 's-inf-2', side: 'South', type: 'Infantry', symbol: 'I', x: 6,  y: 15 },
  { id: 's-inf-3', side: 'South', type: 'Infantry', symbol: 'I', x: 8,  y: 15 },
  { id: 's-inf-4', side: 'South', type: 'Infantry', symbol: 'I', x: 10, y: 15 },
  { id: 's-inf-5', side: 'South', type: 'Infantry', symbol: 'I', x: 12, y: 15 },
  { id: 's-inf-6', side: 'South', type: 'Infantry', symbol: 'I', x: 14, y: 15 },
  { id: 's-inf-7', side: 'South', type: 'Infantry', symbol: 'I', x: 16, y: 15 },
  { id: 's-inf-8', side: 'South', type: 'Infantry', symbol: 'I', x: 18, y: 15 },
  { id: 's-inf-9', side: 'South', type: 'Infantry', symbol: 'I', x: 20, y: 15 },

  { id: 's-cav-1', side: 'South', type: 'Cavalry',  symbol: 'C', x: 3,  y: 16 },
  { id: 's-cav-2', side: 'South', type: 'Cavalry',  symbol: 'C', x: 7,  y: 16 },
  { id: 's-cav-3', side: 'South', type: 'Cavalry',  symbol: 'C', x: 17, y: 16 },
  { id: 's-cav-4', side: 'South', type: 'Cavalry',  symbol: 'C', x: 21, y: 16 },

  { id: 's-art-1', side: 'South', type: 'Artillery', symbol: 'A', x: 11, y: 17 },
  { id: 's-art-2', side: 'South', type: 'Artillery', symbol: 'A', x: 13, y: 17 },

  { id: 's-rel-1', side: 'South', type: 'Relay', symbol: 'R', x: 10, y: 18 },
  { id: 's-rel-2', side: 'South', type: 'Relay', symbol: 'R', x: 14, y: 18 },
];