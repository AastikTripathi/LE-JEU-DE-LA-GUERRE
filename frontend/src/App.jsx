// // src/App.jsx
// import React, { useState, useEffect } from 'react';
// import { COLS, ROWS, GET_TERRAIN } from './constants';
//
// export default function App() {
//   const [units, setUnits] = useState([]);
//   const [turn, setTurn] = useState('North');
//   const [movesLeft, setMovesLeft] = useState(5);
//   const [attackExecuted, setAttackExecuted] = useState(false);
//   const [locCells, setLocCells] = useState({ North: [], South: [] });
//   const [connectedUnitIds, setConnectedUnitIds] = useState([]);
//   const [selectedUnitId, setSelectedUnitId] = useState(null);
//   const [socket, setSocket] = useState(null);
//   const [errorMessage, setErrorMessage] = useState('');
//
//   // Open live network pipeline to Python server
//   useEffect(() => {
//     const ws = new WebSocket('ws://127.0.0.1:8000/ws');
//
//     ws.onopen = () => {
//       console.log("⚡ Connected to Python Rule Engine successfully!");
//     };
//
//     ws.onmessage = (event) => {
//       const data = JSON.parse(event.data);
//       if (data.type === 'error') {
//         setErrorMessage(data.message);
//         setTimeout(() => setErrorMessage(''), 5000); // Flash alert for combat updates or errors
//       } else {
//         // Sync full operational state from Python
//         setUnits(data.units);
//         setTurn(data.turn);
//         setMovesLeft(data.movesLeft);
//         setAttackExecuted(data.attackExecuted);
//         setLocCells(data.linesOfCommunication);
//         setConnectedUnitIds(data.connectedUnitIds);
//       }
//     };
//
//     ws.onerror = (err) => {
//       console.error("❌ WebSocket Error:", err);
//     };
//
//     setSocket(ws);
//     return () => ws.close();
//   }, []);
//
//   const unitPositionsMap = units.reduce((acc, unit) => {
//     acc[`${unit.x},${unit.y}`] = unit;
//     return acc;
//   }, {});
//
//   const handleCellClick = (x, y) => {
//     const clickedUnit = unitPositionsMap[`${x},${y}`];
//
//     if (clickedUnit) {
//       // RULE: If clicking your own unit, select or deselect it
//       if (clickedUnit.side === turn) {
//         setSelectedUnitId(clickedUnit.id === selectedUnitId ? null : clickedUnit.id);
//       }
//       // RULE: If a unit is selected and you click an ENEMY unit, execute an ATTACK command
//       else if (selectedUnitId && socket && socket.readyState === WebSocket.OPEN) {
//         socket.send(JSON.stringify({
//           action: 'attack',
//           x,
//           y
//         }));
//         setSelectedUnitId(null);
//       }
//       return;
//     }
//
//     // RULE: If clicking an empty square and a unit is selected, execute a MOVE command
//     if (selectedUnitId && socket && socket.readyState === WebSocket.OPEN) {
//       socket.send(JSON.stringify({
//         action: 'move',
//         unitId: selectedUnitId,
//         x,
//         y
//       }));
//       setSelectedUnitId(null);
//     } else if (selectedUnitId) {
//       setErrorMessage("Action Denied: No active server link found.");
//       setTimeout(() => setErrorMessage(''), 4000);
//     }
//   };
//
//   // Sends the explicit state clear and passes turn over the socket
//   const handleEndTurn = () => {
//     if (socket && socket.readyState === WebSocket.OPEN) {
//       socket.send(JSON.stringify({ action: 'end_turn' }));
//       setSelectedUnitId(null);
//     }
//   };
//
//   const isCellInLoc = (x, y, side) => {
//     return locCells[side].some(coord => coord[0] === x && coord[1] === y);
//   };
//
//   const cells = [];
//   for (let y = 0; y < ROWS; y++) {
//     for (let x = 0; x < COLS; x++) {
//       cells.push({
//         x, y,
//         terrain: GET_TERRAIN(x, y),
//         occupyingUnit: unitPositionsMap[`${x},${y}`],
//         isNorthLoc: isCellInLoc(x, y, 'North'),
//         isSouthLoc: isCellInLoc(x, y, 'South')
//       });
//     }
//   }
//
//   return (
//     <div style={styles.container}>
//       {/* Upper Control Bar */}
//       <div style={styles.header}>
//         <div>
//           <h1 style={styles.title}>LE JEU DE LA GUERRE</h1>
//           <p style={styles.subtitle}>Guy Debord's Tactical Simulator</p>
//         </div>
//
//         {/* Real-time State Monitors */}
//         <div style={styles.controlPanel}>
//           <div style={{ ...styles.statusBadge, borderColor: turn === 'North' ? '#3b82f6' : '#ef4444' }}>
//             ARMY: <span style={{ color: turn === 'North' ? '#60a5fa' : '#f87171' }}>{turn.toUpperCase()}</span>
//           </div>
//           <div style={styles.metricsBadge}>
//             MOVES REMAINING: <span style={styles.HighlightText}>{movesLeft}/5</span>
//           </div>
//           <div style={styles.metricsBadge}>
//             ATTACK STATUS: <span style={{ color: attackExecuted ? '#ef4444' : '#10b981' }}>{attackExecuted ? "USED" : "AVAILABLE"}</span>
//           </div>
//           <button onClick={handleEndTurn} style={styles.endTurnButton}>
//             END STRATEGY PHASE
//           </button>
//         </div>
//       </div>
//
//       {/* Dynamic System Output Logs */}
//       {errorMessage && (
//         <div style={{
//           ...styles.errorAlert,
//           backgroundColor: errorMessage.includes('Success') || errorMessage.includes('repelled') ? '#064e3b' : '#7f1d1d',
//           borderColor: errorMessage.includes('Success') || errorMessage.includes('repelled') ? '#10b981' : '#f87171'
//         }}>
//           📡 SYSTEM LOG: {errorMessage}
//         </div>
//       )}
//
//       {/* Main Campaign Grid */}
//       <div style={styles.gridContainer}>
//         {cells.map(({ x, y, terrain, occupyingUnit, isNorthLoc, isSouthLoc }) => {
//           const isSelected = occupyingUnit && occupyingUnit.id === selectedUnitId;
//           const isUnitConnected = occupyingUnit && connectedUnitIds.includes(occupyingUnit.id);
//
//           return (
//             <div
//               key={`${x}-${y}`}
//               onClick={() => handleCellClick(x, y)}
//               style={{
//                 ...styles.cell,
//                 backgroundColor: terrain.color,
//                 border: terrain.border || '1px solid #1f2937',
//                 outline: isSelected ? '3px solid #eab308' : 'none',
//                 zIndex: isSelected ? 10 : 1
//               }}
//             >
//               {/* Communication Grid Lines */}
//               {!occupyingUnit && (isNorthLoc || isSouthLoc) && (
//                 <div style={{
//                   ...styles.locDot,
//                   backgroundColor: isNorthLoc && isSouthLoc ? '#a855f7' : isNorthLoc ? '#3b82f6' : '#ef4444'
//                 }} />
//               )}
//
//               {occupyingUnit ? (
//                 <div
//                   style={{
//                     ...styles.unitBadge,
//                     borderColor: occupyingUnit.side === 'North' ? '#3b82f6' : '#ef4444',
//                     color: occupyingUnit.side === 'North' ? '#60a5fa' : '#f87171',
//                     opacity: isUnitConnected ? 1 : 0.3, // Combat unit grid drop if isolated
//                   }}
//                 >
//                   {occupyingUnit.symbol}
//                 </div>
//               ) : (
//                 <span style={styles.terrainLabel}>{terrain.label}</span>
//               )}
//               <span style={styles.coords}>{x},{y}</span>
//             </div>
//           );
//         })}
//       </div>
//     </div>
//   );
// }
//
// const styles = {
//   container: { backgroundColor: '#020617', minHeight: '100vh', color: '#f3f4f6', fontFamily: 'monospace', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px' },
//   header: { width: '100%', maxWidth: '1100px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', borderBottom: '2px solid #334155', paddingBottom: '15px' },
//   title: { fontSize: '22px', letterSpacing: '4px', color: '#f1f5f9', fontWeight: 'bold', margin: 0 },
//   subtitle: { fontSize: '11px', color: '#64748b', margin: '4px 0 0 0', letterSpacing: '1px' },
//   controlPanel: { display: 'flex', gap: '12px', alignItems: 'center' },
//   statusBadge: { backgroundColor: '#0f172a', border: '2px solid', padding: '8px 14px', borderRadius: '4px', fontSize: '13px', fontWeight: 'bold', letterSpacing: '1px' },
//   metricsBadge: { backgroundColor: '#0f172a', border: '1px solid #334155', padding: '8px 14px', borderRadius: '4px', fontSize: '12px', color: '#94a3b8' },
//   HighlightText: { color: '#f59e0b', fontWeight: 'bold' },
//   endTurnButton: { backgroundColor: '#1e293b', border: '1px solid #64748b', color: '#f8fafc', padding: '9px 16px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer', transition: 'all 0.2s', fontFamily: 'monospace' },
//   errorAlert: { width: '100%', maxWidth: '1080px', border: '1px solid', color: '#f8fafc', padding: '12px', borderRadius: '4px', marginBottom: '15px', fontSize: '13px', letterSpacing: '0.5px' },
//   gridContainer: { display: 'grid', gridTemplateColumns: 'repeat(25, minmax(0, 1fr))', gap: '2px', width: '100%', maxWidth: '1100px', backgroundColor: '#0f172a', padding: '10px', borderRadius: '8px', border: '1px solid #1e293b' },
//   cell: { position: 'relative', aspectRatio: '1', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', userSelect: 'none' },
//   unitBadge: { width: '82%', height: '82%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px', border: '2px solid', fontWeight: 'bold', fontSize: '13px', backgroundColor: '#020617', zIndex: 2 },
//   locDot: { position: 'absolute', width: '7px', height: '7px', borderRadius: '50%', zIndex: 1, opacity: 0.8, boxShadow: '0 0 4px currentColor' },
//   terrainLabel: { fontSize: '10px', opacity: 0.25 },
//   coords: { position: 'absolute', bottom: '2px', right: '2px', fontSize: '5px', color: '#334155', opacity: 0.5 }
// };




// src/App.jsx
import React, { useState, useEffect } from 'react';
import { COLS, ROWS, GET_TERRAIN } from './constants';

export default function App() {
  // Lobby / Authentication States
  const [inLobby, setInLobby] = useState(true);
  const [playerName, setPlayerName] = useState('');
  const [roomName, setRoomName] = useState('');
  const [roomPassword, setRoomPassword] = useState('');

  // Game Core States
  const [units, setUnits] = useState([]);
  const [turn, setTurn] = useState('North');
  const [movesLeft, setMovesLeft] = useState(5);
  const [attackExecuted, setAttackExecuted] = useState(false);
  const [locCells, setLocCells] = useState({ North: [], South: [] });
  const [connectedUnitIds, setConnectedUnitIds] = useState([]);
  const [selectedUnitId, setSelectedUnitId] = useState(null);
  const [socket, setSocket] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [canUndo, setCanUndo] = useState(false);
  const [roomUrl, setRoomUrl] = useState('');

  // Auto-detect if a player arrived via a shareable invite link
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sharedRoom = params.get('room');
    if (sharedRoom) {
      setRoomName(sharedRoom);
    }
  }, []);

  const handleConnectToRoom = (e) => {
    e.preventDefault();
    if (!playerName.trim() || !roomName.trim() || !roomPassword.trim()) {
      setErrorMessage("System Failure: Identification fields cannot be blank.");
      return;
    }

    // Append room query parameter into the browser address bar for simple clipboard sharing
    const params = new URLSearchParams(window.location.search);
    params.set('room', roomName.trim());
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
    setRoomUrl(window.location.href);

    // Initialize network handshake containing names/passwords as clean URL query vectors
    const secureWsUrl = `ws://127.0.0.1:8000/ws/${encodeURIComponent(roomName.trim())}?name=${encodeURIComponent(playerName.trim())}&password=${encodeURIComponent(roomPassword.trim())}`;
    const ws = new WebSocket(secureWsUrl);

    ws.onopen = () => {
      console.log(`📡 Operational link established for room: ${roomName}`);
      setInLobby(false);
      setErrorMessage('');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'error') {
        setErrorMessage(data.message);
        // If password authentication fails on initial drop, kick user back to lobby screen
        if (data.message.toLowerCase().includes('password') || data.message.toLowerCase().includes('authentication')) {
          setInLobby(true);
          ws.close();
        } else {
          setTimeout(() => setErrorMessage(''), 4000);
        }
      } else {
        setUnits(data.units);
        setTurn(data.turn);
        setMovesLeft(data.movesLeft);
        setAttackExecuted(data.attackExecuted);
        setLocCells(data.linesOfCommunication);
        setConnectedUnitIds(data.connectedUnitIds);
        setCanUndo(data.canUndo ?? false);
      }
    };

    ws.onerror = (err) => {
      console.error("❌ Link connection error:", err);
      setErrorMessage("Network Failure: Server did not respond to handshake.");
    };

    ws.onclose = () => {
      setInLobby(true);
    };

    setSocket(ws);
  };

  const unitPositionsMap = units.reduce((acc, unit) => {
    acc[`${unit.x},${unit.y}`] = unit;
    return acc;
  }, {});

  const handleCellClick = (x, y) => {
    const clickedUnit = unitPositionsMap[`${x},${y}`];

    if (clickedUnit) {
      if (clickedUnit.side === turn) {
        setSelectedUnitId(clickedUnit.id === selectedUnitId ? null : clickedUnit.id);
      } else if (selectedUnitId && socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'attack', x, y }));
        setSelectedUnitId(null);
      }
      return;
    }

    if (selectedUnitId && socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: 'move', unitId: selectedUnitId, x, y }));
      setSelectedUnitId(null);
    }
  };

  const handleAction = (actionType) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: actionType }));
      setSelectedUnitId(null);
    }
  };

  const isCellInLoc = (x, y, side) => locCells[side]?.some(coord => coord[0] === x && coord[1] === y);

  const cells = [];
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      cells.push({
        x, y,
        terrain: GET_TERRAIN(x, y),
        occupyingUnit: unitPositionsMap[`${x},${y}`],
        isNorthLoc: isCellInLoc(x, y, 'North'),
        isSouthLoc: isCellInLoc(x, y, 'South')
      });
    }
  }

  // LOBBY PHASE RENDERING SCREEN
  if (inLobby) {
    return (
      <div style={styles.container}>
        <div style={styles.lobbyCard}>
          <h1 style={styles.lobbyTitle}>LE JEU DE LA GUERRE</h1>
          <p style={styles.lobbySubtitle}>Secure Network Deployment Terminal</p>

          {errorMessage && <div style={styles.lobbyError}>{errorMessage}</div>}

          <form onSubmit={handleConnectToRoom} style={styles.form}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>TACTICAL CALLSIGN (NAME)</label>
              <input type="text" value={playerName} onChange={(e) => setPlayerName(e.target.value)} placeholder="e.g., Commander_Alpha" style={styles.input} required />
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>THEATER ROOM ID</label>
              <input type="text" value={roomName} onChange={(e) => setRoomName(e.target.value)} placeholder="e.g., sector-7" style={styles.input} required />
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>SECURE ACCESS KEY (PASSWORD)</label>
              <input type="password" value={roomPassword} onChange={(e) => setRoomPassword(e.target.value)} placeholder="••••••••" style={styles.input} required />
            </div>

            <button type="submit" style={styles.lobbyButton}>INITIALIZE SYSTEM CONNECT</button>
          </form>
        </div>
      </div>
    );
  }

  // LIVE CAMPAIGN BOARD RENDERING SCREEN
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>LE JEU DE LA GUERRE</h1>
          <div style={styles.sharePanel}>
            <span style={{ color: '#64748b', fontWeight: 'bold' }}>SHARE DISPATCH LINK:</span>
            <input readOnly value={roomUrl} onClick={(e) => { e.target.select(); document.execCommand('copy'); }} style={styles.linkInput} title="Click to copy link" />
          </div>
        </div>

        <div style={styles.controlPanel}>
          <button onClick={() => handleAction('undo')} disabled={!canUndo} style={{ ...styles.btn, opacity: canUndo ? 1 : 0.3, cursor: canUndo ? 'pointer' : 'not-allowed' }}>
            UNDO
          </button>
          <button onClick={() => handleAction('restart')} style={styles.btn}>
            RESTART MAP
          </button>
          <div style={{ ...styles.statusBadge, borderColor: turn === 'North' ? '#3b82f6' : '#ef4444' }}>
            ARMY: <span style={{ color: turn === 'North' ? '#60a5fa' : '#f87171' }}>{turn.toUpperCase()}</span>
          </div>
          <div style={styles.metricsBadge}>
            MOVES: <span style={styles.HighlightText}>{movesLeft}/5</span>
          </div>
          <div style={styles.metricsBadge}>
            ATTACK: <span style={{ color: attackExecuted ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>{attackExecuted ? "USED" : "READY"}</span>
          </div>
          <button onClick={() => handleAction('end_turn')} style={styles.endTurnButton}>
            END STRATEGY PHASE
          </button>
        </div>
      </div>

      {errorMessage && (
        <div style={{
          ...styles.errorAlert,
          backgroundColor: errorMessage.includes('Success') || errorMessage.includes('eliminated') || errorMessage.includes('repelled') ? '#064e3b' : '#7f1d1d',
          borderColor: errorMessage.includes('Success') || errorMessage.includes('eliminated') || errorMessage.includes('repelled') ? '#10b981' : '#f87171'
        }}>
          📡 SYSTEM LOG: {errorMessage}
        </div>
      )}

      <div style={styles.gridContainer}>
        {cells.map(({ x, y, terrain, occupyingUnit, isNorthLoc, isSouthLoc }) => {
          const isSelected = occupyingUnit && occupyingUnit.id === selectedUnitId;
          const isUnitConnected = occupyingUnit && connectedUnitIds.includes(occupyingUnit.id);

          return (
            <div key={`${x}-${y}`} onClick={() => handleCellClick(x, y)}
              style={{ ...styles.cell, backgroundColor: terrain.color, border: terrain.border || '1px solid #1f2937', outline: isSelected ? '3px solid #eab308' : 'none', zIndex: isSelected ? 10 : 1 }}
            >
              {!occupyingUnit && (isNorthLoc || isSouthLoc) && (
                <div style={{ ...styles.locDot, backgroundColor: isNorthLoc && isSouthLoc ? '#a855f7' : isNorthLoc ? '#3b82f6' : '#ef4444' }} />
              )}

              {occupyingUnit ? (
                <div style={{ ...styles.unitBadge, borderColor: occupyingUnit.side === 'North' ? '#3b82f6' : '#ef4444', color: occupyingUnit.side === 'North' ? '#60a5fa' : '#f87171', opacity: isUnitConnected ? 1 : 0.3 }}>
                  {occupyingUnit.symbol}
                </div>
              ) : (
                <span style={styles.terrainLabel}>{terrain.label}</span>
              )}
              <span style={styles.coords}>{x},{y}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles = {
  container: { backgroundColor: '#020617', minHeight: '100vh', color: '#f3f4f6', fontFamily: 'monospace', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '24px' },
  // Lobby Component Layout Elements
  lobbyCard: { backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', padding: '40px', width: '100%', maxWidth: '480px', marginTop: '80px', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)' },
  lobbyTitle: { fontSize: '24px', letterSpacing: '3px', fontWeight: 'bold', margin: '0 0 8px 0', textAlign: 'center', color: '#f1f5f9' },
  lobbySubtitle: { fontSize: '11px', color: '#64748b', textAlign: 'center', margin: '0 0 24px 0', letterSpacing: '1px' },
  lobbyError: { backgroundColor: '#7f1d1d', border: '1px solid #f87171', color: '#fca5a5', padding: '10px', borderRadius: '4px', fontSize: '12px', marginBottom: '20px', fontFamily: 'monospace' },
  form: { display: 'flex', flexDirection: 'column', gap: '20px' },
  inputGroup: { display: 'flex', flexDirection: 'column', gap: '6px' },
  label: { fontSize: '10px', color: '#94a3b8', letterSpacing: '1px', fontWeight: 'bold' },
  input: { backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#f8fafc', padding: '10px 14px', fontSize: '13px', fontFamily: 'monospace', outline: 'none' },
  lobbyButton: { backgroundColor: '#1e293b', border: '1px solid #475569', color: '#38bdf8', padding: '12px', borderRadius: '4px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer', fontFamily: 'monospace', marginTop: '10px', letterSpacing: '1px' },

  // Game Interface Layout Elements
  header: { width: '100%', maxWidth: '1100px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', borderBottom: '2px solid #334155', paddingBottom: '15px' },
  title: { fontSize: '22px', letterSpacing: '4px', color: '#f1f5f9', fontWeight: 'bold', margin: 0 },
  sharePanel: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px', fontSize: '11px' },
  linkInput: { backgroundColor: '#0f172a', border: '1px solid #334155', color: '#38bdf8', padding: '4px 10px', borderRadius: '4px', width: '340px', fontSize: '11px', fontFamily: 'monospace', cursor: 'pointer', outline: 'none' },
  controlPanel: { display: 'flex', gap: '10px', alignItems: 'center' },
  btn: { backgroundColor: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '9px 14px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'monospace', fontSize: '12px' },
  statusBadge: { backgroundColor: '#0f172a', border: '2px solid', padding: '8px 14px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' },
  metricsBadge: { backgroundColor: '#0f172a', border: '1px solid #334155', padding: '9px 14px', borderRadius: '4px', fontSize: '12px', color: '#94a3b8' },
  HighlightText: { color: '#f59e0b', fontWeight: 'bold' },
  endTurnButton: { backgroundColor: '#1e293b', border: '1px solid #64748b', color: '#f8fafc', padding: '9px 16px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer', fontFamily: 'monospace' },
  errorAlert: { width: '100%', maxWidth: '1080px', border: '1px solid', color: '#f8fafc', padding: '12px', borderRadius: '4px', marginBottom: '15px', fontSize: '13px' },
  gridContainer: { display: 'grid', gridTemplateColumns: 'repeat(25, minmax(0, 1fr))', gap: '2px', width: '100%', maxWidth: '1100px', backgroundColor: '#0f172a', padding: '10px', borderRadius: '8px', border: '1px solid #1e293b' },
  cell: { position: 'relative', aspectRatio: '1', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', userSelect: 'none' },
  unitBadge: { width: '82%', height: '82%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px', border: '2px solid', fontWeight: 'bold', fontSize: '13px', backgroundColor: '#020617', zIndex: 2 },
  locDot: { position: 'absolute', width: '7px', height: '7px', borderRadius: '50%', zIndex: 1, opacity: 0.8, boxShadow: '0 0 4px currentColor' },
  terrainLabel: { fontSize: '10px', opacity: 0.25 },
  coords: { position: 'absolute', bottom: '2px', right: '2px', fontSize: '5px', color: '#334155', opacity: 0.4 }
};