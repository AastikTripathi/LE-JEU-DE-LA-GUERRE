
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

  // Player Identity States
  const [mySide, setMySide] = useState(null);       // 'North' or 'South' — assigned by server
  const [players, setPlayers] = useState({ North: null, South: null }); // Both player names

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

    const isProd =
    !window.location.hostname.includes("localhost") &&
    !window.location.hostname.includes("127.0.0.1");

    const backendHost = isProd
    ? "le-jeu-de-la-guerre.onrender.com"
    : "127.0.0.1:8000";

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";

    const secureWsUrl =
    `${protocol}://${backendHost}/ws/${encodeURIComponent(roomName.trim())}` +
    `?name=${encodeURIComponent(playerName.trim())}` +
    `&password=${encodeURIComponent(roomPassword.trim())}`;
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
        if (data.message.toLowerCase().includes('password') || data.message.toLowerCase().includes('authentication') || data.message.toLowerCase().includes('full')) {
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
        if (data.yourSide) setMySide(data.yourSide);
        if (data.players) setPlayers(data.players);
      }
    };

    ws.onerror = (err) => {
      console.error("❌ Link connection error:", err);
      setErrorMessage("Network Failure: Server did not respond to handshake.");
    };

    ws.onclose = () => {
      setInLobby(true);
      setMySide(null);
      setPlayers({ North: null, South: null });
    };

    setSocket(ws);
  };

  const unitPositionsMap = units.reduce((acc, unit) => {
    acc[`${unit.x},${unit.y}`] = unit;
    return acc;
  }, {});

  // True when it is this client's turn to act
  const isMyTurn = mySide === turn;

  const handleCellClick = (x, y) => {
    if (!isMyTurn) return; // Silently ignore clicks on opponent's turn

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
    // Restart is allowed by either player; all other actions require it to be your turn
    if (actionType !== 'restart' && !isMyTurn) return;
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

  const opponentSide = mySide === 'North' ? 'South' : 'North';
  const opponentName = players[opponentSide];
  const myName = players[mySide] ?? playerName;

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

        {/* Player identity panel */}
        <div style={styles.identityPanel}>
          {/* Me */}
          <div style={{ ...styles.playerTag, borderColor: mySide === 'North' ? '#3b82f6' : '#ef4444' }}>
            <span style={{ fontSize: '9px', color: '#64748b', letterSpacing: '1px' }}>YOU</span>
            <span style={{ color: mySide === 'North' ? '#60a5fa' : '#f87171', fontWeight: 'bold', fontSize: '13px' }}>
              {myName}
            </span>
            <span style={{ ...styles.sidePip, backgroundColor: mySide === 'North' ? '#3b82f6' : '#ef4444' }}>
              {mySide?.toUpperCase()}
            </span>
          </div>

          <span style={{ color: '#475569', fontSize: '13px', fontWeight: 'bold', alignSelf: 'center' }}>VS</span>

          {/* Opponent */}
          <div style={{ ...styles.playerTag, borderColor: opponentSide === 'North' ? '#3b82f6' : '#ef4444', opacity: opponentName ? 1 : 0.4 }}>
            <span style={{ fontSize: '9px', color: '#64748b', letterSpacing: '1px' }}>OPPONENT</span>
            <span style={{ color: opponentSide === 'North' ? '#60a5fa' : '#f87171', fontWeight: 'bold', fontSize: '13px' }}>
              {opponentName ?? 'Awaiting Commander...'}
            </span>
            <span style={{ ...styles.sidePip, backgroundColor: opponentSide === 'North' ? '#3b82f6' : '#ef4444' }}>
              {opponentSide?.toUpperCase()}
            </span>
          </div>
        </div>

        <div style={styles.controlPanel}>
          <button
            onClick={() => handleAction('undo')}
            disabled={!canUndo || !isMyTurn}
            style={{ ...styles.btn, opacity: (canUndo && isMyTurn) ? 1 : 0.3, cursor: (canUndo && isMyTurn) ? 'pointer' : 'not-allowed' }}
          >
            UNDO
          </button>
          <button onClick={() => handleAction('restart')} style={styles.btn}>
            RESTART MAP
          </button>
          <div style={{ ...styles.statusBadge, borderColor: turn === 'North' ? '#3b82f6' : '#ef4444' }}>
            TURN: <span style={{ color: turn === 'North' ? '#60a5fa' : '#f87171' }}>
              {players[turn] ? players[turn].toUpperCase() : turn.toUpperCase()}
            </span>
          </div>
          <div style={styles.metricsBadge}>
            MOVES: <span style={styles.HighlightText}>{movesLeft}/5</span>
          </div>
          <div style={styles.metricsBadge}>
            ATTACK: <span style={{ color: attackExecuted ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>{attackExecuted ? "USED" : "READY"}</span>
          </div>
          <button
            onClick={() => handleAction('end_turn')}
            disabled={!isMyTurn}
            style={{ ...styles.endTurnButton, opacity: isMyTurn ? 1 : 0.4, cursor: isMyTurn ? 'pointer' : 'not-allowed' }}
          >
            END STRATEGY PHASE
          </button>
        </div>
      </div>

      {/* Turn indicator banner — shown when it's NOT your turn */}
      {!isMyTurn && (
        <div style={styles.waitingBanner}>
          ⏳ AWAITING {players[turn] ? players[turn].toUpperCase() : turn.toUpperCase()}'S STRATEGY PHASE…
        </div>
      )}

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
              style={{ ...styles.cell, backgroundColor: terrain.color, border: terrain.border || '1px solid #1f2937', outline: isSelected ? '3px solid #eab308' : 'none', zIndex: isSelected ? 10 : 1, cursor: isMyTurn ? 'pointer' : 'default' }}
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
  header: { width: '100%', maxWidth: '1100px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '15px', borderBottom: '2px solid #334155', paddingBottom: '15px', gap: '20px', flexWrap: 'wrap' },
  title: { fontSize: '22px', letterSpacing: '4px', color: '#f1f5f9', fontWeight: 'bold', margin: 0 },
  sharePanel: { display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px', fontSize: '11px' },
  linkInput: { backgroundColor: '#0f172a', border: '1px solid #334155', color: '#38bdf8', padding: '4px 10px', borderRadius: '4px', width: '240px', fontSize: '11px', fontFamily: 'monospace', cursor: 'pointer', outline: 'none' },

  // Player identity panel
  identityPanel: { display: 'flex', gap: '12px', alignItems: 'stretch' },
  playerTag: { display: 'flex', flexDirection: 'column', gap: '4px', backgroundColor: '#0f172a', border: '1px solid', borderRadius: '6px', padding: '8px 14px', minWidth: '130px' },
  sidePip: { fontSize: '9px', padding: '2px 6px', borderRadius: '3px', color: '#020617', fontWeight: 'bold', letterSpacing: '1px', alignSelf: 'flex-start' },

  controlPanel: { display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' },
  btn: { backgroundColor: '#0f172a', border: '1px solid #334155', color: '#f8fafc', padding: '9px 14px', borderRadius: '4px', cursor: 'pointer', fontFamily: 'monospace', fontSize: '12px' },
  statusBadge: { backgroundColor: '#0f172a', border: '2px solid', padding: '8px 14px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' },
  metricsBadge: { backgroundColor: '#0f172a', border: '1px solid #334155', padding: '9px 14px', borderRadius: '4px', fontSize: '12px', color: '#94a3b8' },
  HighlightText: { color: '#f59e0b', fontWeight: 'bold' },
  endTurnButton: { backgroundColor: '#1e293b', border: '1px solid #64748b', color: '#f8fafc', padding: '9px 16px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer', fontFamily: 'monospace' },
  errorAlert: { width: '100%', maxWidth: '1080px', border: '1px solid', color: '#f8fafc', padding: '12px', borderRadius: '4px', marginBottom: '15px', fontSize: '13px' },
  waitingBanner: { width: '100%', maxWidth: '1080px', backgroundColor: '#1c1917', border: '1px solid #44403c', color: '#a8a29e', padding: '10px 16px', borderRadius: '4px', marginBottom: '12px', fontSize: '12px', letterSpacing: '1px', textAlign: 'center' },
  gridContainer: { display: 'grid', gridTemplateColumns: 'repeat(25, minmax(0, 1fr))', gap: '2px', width: '100%', maxWidth: '1100px', backgroundColor: '#0f172a', padding: '10px', borderRadius: '8px', border: '1px solid #1e293b' },
  cell: { position: 'relative', aspectRatio: '1', display: 'flex', alignItems: 'center', justifyContent: 'center', userSelect: 'none' },
  unitBadge: { width: '82%', height: '82%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '4px', border: '2px solid', fontWeight: 'bold', fontSize: '13px', backgroundColor: '#020617', zIndex: 2 },
  locDot: { position: 'absolute', width: '7px', height: '7px', borderRadius: '50%', zIndex: 1, opacity: 0.8, boxShadow: '0 0 4px currentColor' },
  terrainLabel: { fontSize: '10px', opacity: 0.25 },
  coords: { position: 'absolute', bottom: '2px', right: '2px', fontSize: '5px', color: '#334155', opacity: 0.4 }
};
