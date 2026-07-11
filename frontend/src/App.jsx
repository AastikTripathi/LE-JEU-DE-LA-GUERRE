


// src/App.jsx
import React, { useState, useEffect, useRef } from 'react';
import { COLS, ROWS, GET_TERRAIN } from './constants';
import { INITIAL_UNITS } from './initialUnits';

// Combat Profiles for Tactical Telemetry
const UNIT_PROFILES = {
  artillery: { attack: 40, defense: 20, label: "Artillery", tip: "Heavy assault multiplier." },
  cavalry: { attack: 25, defense: 25, label: "Cavalry", tip: "High mobility flanker." },
  infantry: { attack: 20, defense: 40, label: "Infantry", tip: "Defensive anchor on active LoC." },
  relay: { attack: 5, defense: 15, label: "Relay", tip: "Maintains network links." },
  arsenal: { attack: 0, defense: 500, label: "Arsenal", tip: "Primary command objective." }
};

export default function App() {
  // Game Mode Configuration State
  const [gameMode, setGameMode] = useState('single');

  // Lobby / Authentication States
  const [inLobby, setInLobby] = useState(true);
  const [playerName, setPlayerName] = useState('');
  const [roomName, setRoomName] = useState('');
  const [roomPassword, setRoomPassword] = useState('');

  // Game Core States
  const [units, setUnits] = useState(INITIAL_UNITS);
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

  // Telemetry, Animations & Graveyard State Tracking
  const [hoveredCell, setHoveredCell] = useState(null);
  const [xKeyHeld, setXKeyHeld] = useState(false);
  const [multiSelectedIds, setMultiSelectedIds] = useState([]);
  const [tracers, setTracers] = useState([]);          // moving projectile dots
  const [killFlash, setKillFlash] = useState(null);    // {x,y} of tile to flash red on kill
  const [graveyardTiles, setGraveyardTiles] = useState({}); // Tracks layout keys: {"x,y": count}
  const [showRules, setShowRules] = useState(false);   // info panel toggle
  const gridRef = useRef(null);
  const prevUnitsRef = useRef(INITIAL_UNITS);

  // Player Identity States
  const [mySide, setMySide] = useState(null);
  const [players, setPlayers] = useState({ North: null, South: null });
  const [winner, setWinner] = useState(null); // 'North', 'South', or null

  // Dynamically inject structural layout rules and transient projectile animations
  useEffect(() => {
    const styleSheet = document.createElement("style");
    styleSheet.innerText = `
      /* Projectile dot travelling across the grid */
      @keyframes projectileTravel {
        0%   { transform: translate(var(--px0), var(--py0)); opacity: 1; }
        85%  { opacity: 1; }
        100% { transform: translate(var(--px1), var(--py1)); opacity: 0; }
      }
      .projectile-dot {
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
        z-index: 200;
        animation: projectileTravel var(--dur) ease-in forwards;
        left: 0; top: 0;
      }

      /* Red kill-flash bloom on target tile */
      @keyframes killBloom {
        0%   { opacity: 0.9; transform: scale(0.5); }
        60%  { opacity: 0.7; transform: scale(1.4); }
        100% { opacity: 0;   transform: scale(2); }
      }
      .kill-flash {
        position: absolute; inset: 0;
        background: radial-gradient(circle, #ef444480 0%, transparent 70%);
        border-radius: 3px;
        pointer-events: none;
        z-index: 150;
        animation: killBloom 0.55s ease-out forwards;
      }

      /* Skull pulsing on graveyard tile */
      @keyframes skullPulse {
        0%, 100% { opacity: 0.55; transform: translate(-50%,-50%) scale(1); }
        50%       { opacity: 0.85; transform: translate(-50%,-50%) scale(1.15); }
      }
      .skull-marker {
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%,-50%);
        font-size: 14px;
        z-index: 3;
        pointer-events: none;
        animation: skullPulse 2.2s ease-in-out infinite;
        filter: grayscale(30%);
      }
    `;
    document.head.appendChild(styleSheet);
    return () => styleSheet.remove();
  }, []);

  // Track 'X' key down-states for group stack operations
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key.toLowerCase() === 'x') setXKeyHeld(true);
    };
    const handleKeyUp = (e) => {
      if (e.key.toLowerCase() === 'x') setXKeyHeld(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Intercept unit diffs → animated projectile + kill flash + skull graveyard
  useEffect(() => {
    if (inLobby || !gridRef.current) {
      prevUnitsRef.current = units;
      return;
    }

    const prevMap = prevUnitsRef.current.reduce((acc, u) => ({ ...acc, [u.id]: u }), {});
    const currentMap = units.reduce((acc, u) => ({ ...acc, [u.id]: u }), {});

    let deadUnit = null;
    for (const id in prevMap) {
      if (!currentMap[id]) { deadUnit = prevMap[id]; break; }
    }

    if (deadUnit) {
      // 1. Mark graveyard tile with skull
      const tileKey = `${deadUnit.x},${deadUnit.y}`;
      setGraveyardTiles(prev => ({ ...prev, [tileKey]: (prev[tileKey] || 0) + 1 }));

      // 2. Kill-flash on target tile
      setKillFlash({ x: deadUnit.x, y: deadUnit.y });
      setTimeout(() => setKillFlash(null), 600);

      // 3. Animated projectile dot from nearest attacker to target
      const attackerSide = deadUnit.side === 'North' ? 'South' : 'North';
      const potentialAttackers = prevUnitsRef.current.filter(u => u.side === attackerSide);

      let closestAttacker = null;
      let closestDist = Infinity;
      potentialAttackers.forEach(attacker => {
        const unitType = attacker.type.toLowerCase();
        const maxRange = unitType === 'artillery' ? 3 : 1;
        const dx = Math.abs(deadUnit.x - attacker.x);
        const dy = Math.abs(deadUnit.y - attacker.y);
        const dist = Math.hypot(dx, dy);
        if (dx <= maxRange && dy <= maxRange && dist < closestDist) {
          closestDist = dist;
          closestAttacker = attacker;
        }
      });

      if (closestAttacker) {
        const startCell = gridRef.current.querySelector(`[data-coord="${closestAttacker.x},${closestAttacker.y}"]`);
        const endCell   = gridRef.current.querySelector(`[data-coord="${deadUnit.x},${deadUnit.y}"]`);

        if (startCell && endCell) {
          const gridRect  = gridRef.current.getBoundingClientRect();
          const startRect = startCell.getBoundingClientRect();
          const endRect   = endCell.getBoundingClientRect();

          const x1 = startRect.left + startRect.width  / 2 - gridRect.left;
          const y1 = startRect.top  + startRect.height / 2 - gridRect.top;
          const x2 = endRect.left   + endRect.width    / 2 - gridRect.left;
          const y2 = endRect.top    + endRect.height   / 2 - gridRect.top;

          const unitType = closestAttacker.type.toLowerCase();
          // Faster for cavalry, medium for infantry, slow arc for artillery
          const dur = unitType === 'cavalry' ? '0.25s' : unitType === 'artillery' ? '0.6s' : '0.35s';
          const color = unitType === 'artillery' ? '#f59e0b'   // amber shell
                      : unitType === 'cavalry'   ? '#06b6d4'   // cyan streak
                      : '#ef4444';                              // red infantry round
          const size = unitType === 'artillery' ? 10 : 7;

          const traceId = Math.random().toString(36).substring(2, 9);
          setTracers(prev => [...prev, { id: traceId, x1, y1, x2, y2, dur, color, size }]);
          const clearMs = unitType === 'artillery' ? 650 : unitType === 'cavalry' ? 300 : 400;
          setTimeout(() => setTracers(prev => prev.filter(t => t.id !== traceId)), clearMs);
        }
      }
    }
    prevUnitsRef.current = units;
  }, [units, inLobby]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sharedRoom = params.get('room');
    if (sharedRoom) {
      setRoomName(sharedRoom);
      setGameMode('multi');
    }
  }, []);

  const handleConnectToRoom = (e) => {
    e.preventDefault();
    if (!playerName.trim()) {
      setErrorMessage("System Failure: Identification callsign cannot be blank.");
      return;
    }

    const isSandbox = gameMode === 'single' || gameMode === 'ai_vs_ai';
    const finalRoom = isSandbox ? `sandbox-${Date.now()}` : roomName.trim();
    const finalPassword = isSandbox ? 'local-ai' : roomPassword.trim();

    if (gameMode === 'multi' && (!roomName.trim() || !roomPassword.trim())) {
      setErrorMessage("System Failure: Network matches require an active Room ID and Password.");
      return;
    }

    if (gameMode === 'multi') {
      const params = new URLSearchParams(window.location.search);
      params.set('room', finalRoom);
      window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
      setRoomUrl(window.location.href);
    }

    const isProd = !window.location.hostname.includes("localhost") && !window.location.hostname.includes("127.0.0.1");
    const backendHost = isProd ? "le-jeu-de-la-guerre.onrender.com" : "127.0.0.1:8000";
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";

    const secureWsUrl = `${protocol}://${backendHost}/ws/${encodeURIComponent(finalRoom)}?name=${encodeURIComponent(playerName.trim())}&password=${encodeURIComponent(finalPassword)}&vs_ai=${gameMode === 'single'}&ai_vs_ai=${gameMode === 'ai_vs_ai'}`;
    const ws = new WebSocket(secureWsUrl);

    ws.onopen = () => {
      setInLobby(false);
      setErrorMessage('');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);


      // --- DEBUG INTERCEPTOR ---
      console.log("📥 [WS INCOMING] Units count in update:", data.units?.length);
      if (data.units) {
        // Find which units were present before but missing now
        const prevIds = units.map(u => u.id);
        const nextIds = data.units.map(u => u.id);
        const vanished = units.filter(u => !nextIds.includes(u.id));

        if (vanished.length > 0) {
          console.error("💀 [DEBUG] Units vanished during sync:", vanished);
        }
      }

      if (data.type === 'error') {
        setErrorMessage(data.message);
        if (data.message.toLowerCase().includes('password') || data.message.toLowerCase().includes('authentication') || data.message.toLowerCase().includes('full')) {
          setInLobby(true);
          ws.close();
        } else {
          setTimeout(() => setErrorMessage(''), 4000);
        }
      } else {
        setUnits(data.units || []);
        setTurn(data.turn);
        setMovesLeft(data.movesLeft ?? 5);
        setAttackExecuted(data.attackExecuted ?? false);
        setLocCells(data.linesOfCommunication || { North: [], South: [] });
        setConnectedUnitIds(data.connectedUnitIds || []);
        setCanUndo(data.canUndo ?? false);

        if (data.yourSide) setMySide(data.yourSide);
        if (data.players) setPlayers(data.players);
        if (data.winner !== undefined) setWinner(data.winner);
      }
    };

    ws.onerror = () => setErrorMessage("Network Failure: Server did not respond to handshake.");
    ws.onclose = () => {
      setInLobby(true);
      setMySide(null);
      setPlayers({ North: null, South: null });
      setWinner(null);
    };

    setSocket(ws);
  };

  const unitPositionsMap = units.reduce((acc, unit) => {
    acc[`${unit.x},${unit.y}`] = unit;
    return acc;
  }, {});

  const isMyTurn = mySide === turn;

  const handleCellClick = (x, y) => {
    if (!isMyTurn) return;
    const clickedUnit = unitPositionsMap[`${x},${y}`];

    if (clickedUnit) {
      if (clickedUnit.side === turn) {
        if (xKeyHeld) {
          setMultiSelectedIds(prev =>
            prev.includes(clickedUnit.id) ? prev.filter(id => id !== clickedUnit.id) : [...prev, clickedUnit.id]
          );
        } else {
          setSelectedUnitId(clickedUnit.id === selectedUnitId ? null : clickedUnit.id);
          setMultiSelectedIds(clickedUnit.id === selectedUnitId ? [] : [clickedUnit.id]);
        }
      } else if ((selectedUnitId || multiSelectedIds.length > 0) && socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ action: 'attack', x, y }));
        setSelectedUnitId(null);
        setMultiSelectedIds([]);
      }
      return;
    }

    if (selectedUnitId && socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: 'move', unitId: selectedUnitId, x, y }));
      setSelectedUnitId(null);
      setMultiSelectedIds([]);
    }
  };

  const handleAction = (actionType) => {
    if (actionType !== 'restart' && !isMyTurn) return;
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: actionType }));
      setSelectedUnitId(null);
      setMultiSelectedIds([]);
      if (actionType === 'restart') {
        setGraveyardTiles({});
        setWinner(null);
      }
    }
  };

  const isCellInLoc = (x, y, side) => {
    const coords = locCells[side] || [];
    return coords.some(coord => coord[0] === x && coord[1] === y);
  };

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

  const getStackOrientation = () => {
    const activeAttackers = units.filter(u => multiSelectedIds.includes(u.id));
    if (activeAttackers.length < 2) return null;

    const sorted = [...activeAttackers].sort((a, b) => a.x !== b.x ? a.x - b.x : a.y - b.y);
    const dx = sorted[1].x - sorted[0].x;
    const dy = sorted[1].y - sorted[0].y;

    if (Math.abs(dx) > 1 || Math.abs(dy) > 1 || (dx === 0 && dy === 0)) return null;

    for (let i = 1; i < sorted.length; i++) {
      if ((sorted[i].x - sorted[i-1].x) !== dx || (sorted[i].y - sorted[i-1].y) !== dy) {
        return null;
      }
    }
    return { stepX: dx, stepY: dy, sorted };
  };

  const stackOrientation = getStackOrientation();

  const isEnemyInAttackRange = (cellX, cellY) => {
    const targetUnit = unitPositionsMap[`${cellX},${cellY}`];
    if (!targetUnit || targetUnit.side === turn) return false;

    if (stackOrientation) {
      const { stepX, stepY, sorted } = stackOrientation;
      const first = sorted[0];
      const crossProduct = (cellY - first.y) * stepX - (cellX - first.x) * stepY;
      return crossProduct === 0;
    } else if (selectedUnitId) {
      const origin = units.find(u => u.id === selectedUnitId);
      if (!origin) return false;

      // Cut-off pieces have their effective attack power drops to 0 and cannot attack
      const originConnected = connectedUnitIds.includes(origin.id);
      if (!originConnected) return false;

      const maxRange = origin.type?.toLowerCase() === 'artillery' ? 3 : 1;
      return Math.abs(cellX - origin.x) <= maxRange && Math.abs(cellY - origin.y) <= maxRange;
    }
    return false;
  };

  const getUnitLiveStats = (unit) => {
    if (!unit) return null;
    const base = UNIT_PROFILES[unit.type.toLowerCase()] || { attack: 10, defense: 10, label: "Asset" };
    const isConnected = connectedUnitIds.includes(unit.id);

    // Penalize cut-off units: 0 Attack power and halved operational defense profile
    return {
      ...base,
      attack: isConnected ? base.attack : 0,
      currentDefense: isConnected ? base.defense : Math.round(base.defense * 0.5),
      isConnected
    };
  };

  // Sidebar Scoreboard calculations tracking baseline configuration arrays
  const northActive = units.filter(u => u.side === 'North').length;
  const southActive = units.filter(u => u.side === 'South').length;
  const northDead = INITIAL_UNITS.filter(u => u.side === 'North').length - northActive;
  const southDead = INITIAL_UNITS.filter(u => u.side === 'South').length - southActive;

  const activeAttackers = units.filter(u => multiSelectedIds.includes(u.id));
  const totalAttackPower = activeAttackers.reduce((sum, u) => {
    const stats = getUnitLiveStats(u);
    return sum + (stats?.attack || 0);
  }, 0);

  const hoveredUnit = hoveredCell ? unitPositionsMap[`${hoveredCell.x},${hoveredCell.y}`] : null;
  const hoveredStats = getUnitLiveStats(hoveredUnit);

  if (inLobby) {
    return (
      <div style={styles.container}>
        <div style={styles.lobbyCard}>
          <h1 style={styles.lobbyTitle}>LE JEU DE LA GUERRE</h1>
          <p style={styles.lobbySubtitle}>Select Game Mode</p>

          <div style={styles.toggleContainer}>
            <button type="button" onClick={() => setGameMode('single')} style={{...styles.toggleBtn, backgroundColor: gameMode === 'single' ? '#1e293b' : 'transparent', color: gameMode === 'single' ? '#38bdf8' : '#64748b'}}>SINGLE PLAYER</button>
            <button type="button" onClick={() => setGameMode('multi')} style={{...styles.toggleBtn, backgroundColor: gameMode === 'multi' ? '#1e293b' : 'transparent', color: gameMode === 'multi' ? '#38bdf8' : '#64748b'}}>MULTIPLAYER</button>
            <button type="button" onClick={() => setGameMode('ai_vs_ai')} style={{...styles.toggleBtn, backgroundColor: gameMode === 'ai_vs_ai' ? '#1e293b' : 'transparent', color: gameMode === 'ai_vs_ai' ? '#38bdf8' : '#64748b'}}>AI VS AI</button>
          </div>

          {errorMessage && <div style={styles.lobbyError}>{errorMessage}</div>}

          <form onSubmit={handleConnectToRoom} style={styles.form}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>TACTICAL CALLSIGN</label>
              <input type="text" value={playerName} onChange={(e) => setPlayerName(e.target.value)} placeholder="Commander" style={styles.input} required />
            </div>
            {gameMode === 'multi' && (
              <>
                <div style={styles.inputGroup}>
                  <label style={styles.label}>THEATER ROOM ID</label>
                  <input type="text" value={roomName} onChange={(e) => setRoomName(e.target.value)} placeholder="sector-7" style={styles.input} required />
                </div>
                <div style={styles.inputGroup}>
                  <label style={styles.label}>ACCESS KEY</label>
                  <input type="password" value={roomPassword} onChange={(e) => setRoomPassword(e.target.value)} placeholder="••••••••" style={styles.input} required />
                </div>
              </>
            )}
            <button type="submit" style={styles.lobbyButton}>LAUNCH OPERATIONS</button>
          </form>
        </div>
      </div>
    );
  }

  const isSinglePlayer = gameMode === 'single';
  const isAiVsAi = gameMode === 'ai_vs_ai';

  const activeMySide = mySide || (players.South === playerName ? 'South' : 'North');
  const opponentSide = activeMySide === 'North' ? 'South' : 'North';

  const myName = isAiVsAi ? "🤖 AI_NORTH" : (players[activeMySide] ?? playerName);
  const opponentName = isAiVsAi ? "🤖 AI_SOUTH" : (players[opponentSide] ?? (isSinglePlayer ? '🤖 CPU_TACTICIAN' : 'Awaiting Commander...'));

  // WIN SCREEN OVERLAY
  if (winner) {
    const winnerName = players[winner] ?? (winner === 'South' && isSinglePlayer ? '🤖 CPU_TACTICIAN' : winner);
    const isMyWin = winner === activeMySide;
    const winColor = winner === 'North' ? '#3b82f6' : '#ef4444';
    const winGlow = winner === 'North' ? 'rgba(59,130,246,0.4)' : 'rgba(239,68,68,0.4)';

    return (
      <div style={{ ...styles.container, justifyContent: 'center', minHeight: '100vh' }}>
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '24px',
          padding: '60px 40px', backgroundColor: '#0f172a',
          border: `2px solid ${winColor}`, borderRadius: '12px',
          boxShadow: `0 0 60px ${winGlow}, 0 0 120px ${winGlow}`,
          maxWidth: '520px', width: '100%', textAlign: 'center'
        }}>
          <div style={{ fontSize: '52px', marginBottom: '4px' }}>
            {isMyWin ? '🏆' : '💀'}
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', letterSpacing: '3px', fontWeight: 'bold' }}>
            CAMPAIGN CONCLUDED
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', letterSpacing: '4px', color: winColor, textShadow: `0 0 20px ${winColor}` }}>
            {winner.toUpperCase()} VICTORIOUS
          </div>
          <div style={{ fontSize: '14px', color: '#94a3b8' }}>
            Commander <span style={{ color: winColor, fontWeight: 'bold' }}>{winnerName}</span> has won the battle
          </div>

          <div style={{ display: 'flex', gap: '24px', marginTop: '8px', fontSize: '12px', color: '#64748b' }}>
            <div>
              <div style={{ color: '#60a5fa', fontWeight: 'bold', marginBottom: '2px' }}>NORTH</div>
              <div>Active: {units.filter(u => u.side === 'North').length}</div>
              <div style={{ color: '#ef4444' }}>Lost: {INITIAL_UNITS.filter(u => u.side === 'North').length - units.filter(u => u.side === 'North').length}</div>
            </div>
            <div style={{ width: '1px', backgroundColor: '#334155' }} />
            <div>
              <div style={{ color: '#f87171', fontWeight: 'bold', marginBottom: '2px' }}>SOUTH</div>
              <div>Active: {units.filter(u => u.side === 'South').length}</div>
              <div style={{ color: '#ef4444' }}>Lost: {INITIAL_UNITS.filter(u => u.side === 'South').length - units.filter(u => u.side === 'South').length}</div>
            </div>
          </div>

          <button
            onClick={() => handleAction('restart')}
            style={{ marginTop: '8px', backgroundColor: winColor, border: 'none', color: '#020617', padding: '12px 32px', borderRadius: '6px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer', letterSpacing: '2px', fontFamily: 'monospace' }}
          >
            ⚔ DEPLOY AGAIN
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* HEADER PANELS - Structurally height locked to stop layout shifting */}
      <div style={styles.header}>
        <div style={styles.headerTitleSection}>
          <h1 style={styles.title}>LE JEU DE LA GUERRE</h1>
          {gameMode === 'multi' && (
            <div style={styles.sharePanel}>
              <span style={{ color: '#64748b' }}>DISPATCH LINK:</span>
              <input readOnly value={roomUrl} onClick={(e) => { e.target.select(); document.execCommand('copy'); }} style={styles.linkInput} />
            </div>
          )}
        </div>

        <div style={styles.identityPanel}>
          <div style={{ ...styles.playerTag, borderColor: activeMySide === 'North' ? '#3b82f6' : '#ef4444' }}>
            <span style={{ fontSize: '9px', color: '#64748b' }}>YOU</span>
            <span style={{ color: activeMySide === 'North' ? '#60a5fa' : '#f87171', fontWeight: 'bold', fontSize: '13px' }}>{myName}</span>
          </div>
          <span style={{ color: '#475569', fontSize: '12px', alignSelf: 'center' }}>VS</span>
          <div style={{ ...styles.playerTag, borderColor: opponentSide === 'North' ? '#3b82f6' : '#ef4444' }}>
            <span style={{ fontSize: '9px', color: '#64748b' }}>OPPONENT</span>
            <span style={{ color: opponentSide === 'North' ? '#60a5fa' : '#f87171', fontWeight: 'bold', fontSize: '13px' }}>{opponentName}</span>
          </div>
        </div>

        <div style={styles.controlPanel}>
          <button onClick={() => handleAction('undo')} disabled={!canUndo || !isMyTurn} style={{ ...styles.fixedBtn, opacity: (canUndo && isMyTurn) ? 1 : 0.3 }}>UNDO</button>
          <button onClick={() => handleAction('restart')} style={styles.fixedBtn}>RESTART</button>
          <div style={{ ...styles.statusBadge, borderColor: turn === 'North' ? '#3b82f6' : '#ef4444' }}>
            TURN: <span style={{ color: turn === 'North' ? '#60a5fa' : '#f87171' }}>{players[turn] ? players[turn].toUpperCase() : turn.toUpperCase()}</span>
          </div>
          <div style={styles.metricsBadge}>MOVES: <span style={styles.HighlightText}>{movesLeft}/5</span></div>
          <div style={styles.metricsBadge}>
            ATTACK: <span style={{ color: attackExecuted ? '#ef4444' : '#10b981', fontWeight: 'bold' }}>{attackExecuted ? "USED" : "READY"}</span>
          </div>
          <button onClick={() => handleAction('end_turn')} disabled={!isMyTurn} style={{ ...styles.endTurnButton, opacity: isMyTurn ? 1 : 0.4 }}>END TURN</button>
        </div>
      </div>

      {isAiVsAi ? (
        <div style={styles.waitingBanner}>🛰️ SIMULATION ACTIVE: OBSERVING {turn.toUpperCase()} TACTICAL MATRIX...</div>
      ) : (
        !isMyTurn && <div style={styles.waitingBanner}>{isSinglePlayer ? "🤖 AI CALCULATING ASSAULT VECTORS..." : `⏳ AWAITING OPPONENT...`}</div>
      )}
      {errorMessage && <div style={{...styles.errorAlert, backgroundColor: errorMessage.includes('Success') || errorMessage.includes('eliminated') || errorMessage.includes('repelled') ? '#064e3b' : '#7f1d1d', borderColor: errorMessage.includes('Success') || errorMessage.includes('eliminated') || errorMessage.includes('repelled') ? '#10b981' : '#f87171'}}>📡 SYSTEM LOG: {errorMessage}</div>}

      {/* TWO-COLUMN SIDEBAR INTERFACE WRAPPER */}
      <div style={styles.workspaceLayout}>

        {/* SIDEBAR STATUS REPORT PANEL */}
        <div style={styles.sidebarPanel}>
          <div style={{ fontWeight: 'bold', color: '#38bdf8', fontSize: '12px', marginBottom: '10px', letterSpacing: '1px' }}>📊 BATTLEFIELD REPORT</div>
          <div style={styles.sidebarDivider} />

          <div style={styles.factionStatsBlock}>
            <div style={{ color: '#60a5fa', fontWeight: 'bold', fontSize: '11px', marginBottom: '4px' }}>🔴 NORTH FORCES</div>
            <div style={styles.statRow}><span style={styles.statLabel}>ACTIVE:</span><span style={{ color: '#f8fafc', fontWeight: 'bold' }}>{northActive}</span></div>
            <div style={styles.statRow}><span style={styles.statLabel}>CASUALTIES:</span><span style={{ color: '#ef4444' }}>💀 {northDead}</span></div>
          </div>

          <div style={{ ...styles.sidebarDivider, margin: '14px 0' }} />

          <div style={styles.factionStatsBlock}>
            <div style={{ color: '#f87171', fontWeight: 'bold', fontSize: '11px', marginBottom: '4px' }}>🔵 SOUTH FORCES</div>
            <div style={styles.statRow}><span style={styles.statLabel}>ACTIVE:</span><span style={{ color: '#f8fafc', fontWeight: 'bold' }}>{southActive}</span></div>
            <div style={styles.statRow}><span style={styles.statLabel}>CASUALTIES:</span><span style={{ color: '#ef4444' }}>💀 {southDead}</span></div>
          </div>

          <div style={{ ...styles.sidebarDivider, margin: '14px 0' }} />

          {/* ── RULES / INTEL TOGGLE ── */}
          <button
            onClick={() => setShowRules(r => !r)}
            style={{ width: '100%', background: showRules ? '#1e3a5f' : '#0f172a', border: '1px solid #334155', color: '#38bdf8', padding: '5px 8px', borderRadius: '4px', fontSize: '10px', cursor: 'pointer', fontFamily: 'monospace', letterSpacing: '1px', marginBottom: '8px' }}
          >
            {showRules ? '▲ HIDE FIELD MANUAL' : '▼ FIELD MANUAL'}
          </button>

          {showRules && (
            <div style={{ fontSize: '9px', color: '#94a3b8', lineHeight: '1.7' }}>
              <div style={{ color: '#f59e0b', fontWeight: 'bold', marginBottom: '3px' }}>UNIT PROFILES</div>
              {[
                { sym: 'I', label: 'Infantry',  atk: 20, def: 40, rng: '1', color: '#60a5fa' },
                { sym: 'C', label: 'Cavalry',   atk: 25, def: 25, rng: '1', color: '#34d399' },
                { sym: 'A', label: 'Artillery', atk: 40, def: 20, rng: '3', color: '#f59e0b' },
                { sym: 'R', label: 'Relay',     atk: 5,  def: 15, rng: '—', color: '#a78bfa' },
              ].map(u => (
                <div key={u.sym} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '2px', marginBottom: '2px' }}>
                  <span style={{ color: u.color, fontWeight: 'bold', minWidth: '16px' }}>[{u.sym}]</span>
                  <span style={{ color: '#cbd5e1', flex: 1, marginLeft: '4px' }}>{u.label}</span>
                  <span>ATK <span style={{ color: '#f87171' }}>{u.atk}</span></span>
                  <span style={{ marginLeft: '4px' }}>DEF <span style={{ color: '#34d399' }}>{u.def}</span></span>
                  <span style={{ marginLeft: '4px' }}>RNG <span style={{ color: '#f59e0b' }}>{u.rng}</span></span>
                </div>
              ))}

              <div style={{ color: '#f59e0b', fontWeight: 'bold', marginTop: '6px', marginBottom: '3px' }}>STACKING (X + click)</div>
              <div style={{ color: '#cbd5e1' }}>Line up 2+ units in a row → attack from the <em>entire line</em>. Combined ATK = sum of all stacked units. Range extends along the stack axis.</div>

              <div style={{ color: '#f59e0b', fontWeight: 'bold', marginTop: '6px', marginBottom: '3px' }}>COMBAT RESULTS</div>
              <div>✅ <span style={{ color: '#10b981' }}>DESTROY</span> — combined ATK {'>'} DEF</div>
              <div>↩ <span style={{ color: '#f59e0b' }}>RETREAT</span> — ATK ≈ DEF (push back)</div>
              <div>✗ <span style={{ color: '#ef4444' }}>FAIL</span>   — ATK {'<'} DEF</div>

              <div style={{ color: '#f59e0b', fontWeight: 'bold', marginTop: '6px', marginBottom: '3px' }}>LINES OF COMM (LoC)</div>
              <div style={{ color: '#cbd5e1' }}>Units <em>off</em> LoC are cut off: ATK→0, DEF halved (💀 easy targets). Relays extend your LoC grid. Enemy on your Arsenal = total LoC collapse.</div>

              <div style={{ color: '#f59e0b', fontWeight: 'bold', marginTop: '6px', marginBottom: '3px' }}>WIN CONDITIONS</div>
              <div>⚔ Annihilate all enemy units</div>
              <div>🏛 Occupy <em>both</em> enemy arsenals</div>
            </div>
          )}

          {!showRules && (
            <div style={{ fontSize: '9px', color: '#475569', lineHeight: '1.3' }}>
              Objective: Sever enemy networks and target communication structures. Cut-off entities suffer extreme defensive penalties.
            </div>
          )}
        </div>

        {/* INTERACTIVE WAR MAP GRID */}
        <div ref={gridRef} style={styles.gridContainer}>

          {/* Animated projectile dots */}
          {tracers.map(t => (
            <div
              key={t.id}
              className="projectile-dot"
              style={{
                width: `${t.size}px`,
                height: `${t.size}px`,
                backgroundColor: t.color,
                boxShadow: `0 0 8px ${t.color}, 0 0 3px #fff`,
                '--px0': `${t.x1}px`,
                '--py0': `${t.y1}px`,
                '--px1': `${t.x2}px`,
                '--py1': `${t.y2}px`,
                '--dur': t.dur
              }}
            />
          ))}

          {cells.map(({ x, y, terrain, occupyingUnit, isNorthLoc, isSouthLoc }) => {
            const isSelected = occupyingUnit && occupyingUnit.id === selectedUnitId;
            const isMultiSelected = occupyingUnit && multiSelectedIds.includes(occupyingUnit.id);
            const isUnitConnected = occupyingUnit && connectedUnitIds.includes(occupyingUnit.id);
            const inRange = isEnemyInAttackRange(x, y);
            const tileKey = `${x},${y}`;
            const hasResidue = graveyardTiles[tileKey] > 0;
            const isFlashing = killFlash && killFlash.x === x && killFlash.y === y;

            let stackOutline = 'none';
            if (isSelected) stackOutline = '3px solid #eab308';
            else if (isMultiSelected) {
              stackOutline = stackOrientation ? '3px solid #06b6d4' : '2px dashed #64748b';
            }

            return (
              <div
                key={`${x}-${y}`}
                data-coord={tileKey}
                onClick={() => handleCellClick(x, y)}
                onMouseEnter={() => setHoveredCell({ x, y })}
                onMouseLeave={() => setHoveredCell(null)}
                style={{
                  ...styles.cell,
                  backgroundColor: inRange ? 'rgba(220, 38, 38, 0.45)' : terrain.color,
                  border: inRange ? '1px solid #ef4444' : (terrain.border || '1px solid #1f2937'),
                  outline: stackOutline,
                  boxShadow: inRange ? 'inset 0 0 10px rgba(239, 68, 68, 0.4)' : 'none',
                  zIndex: (isSelected || isMultiSelected) ? 10 : 1,
                  cursor: isMyTurn ? 'pointer' : 'default'
                }}
              >
                {/* Kill flash bloom */}
                {isFlashing && <div className="kill-flash" />}

                {/* Skull on graveyard tile (behind live unit if reoccupied) */}
                {hasResidue && <span className="skull-marker">💀</span>}

                {!occupyingUnit && (isNorthLoc || isSouthLoc) && (
                  <div style={{ ...styles.locDot, backgroundColor: isNorthLoc && isSouthLoc ? '#a855f7' : isNorthLoc ? '#3b82f6' : '#ef4444' }} />
                )}

                {occupyingUnit ? (
                  <div style={{
                    ...styles.unitBadge,
                    borderColor: occupyingUnit.side === 'North' ? '#3b82f6' : '#ef4444',
                    color: occupyingUnit.side === 'North' ? '#60a5fa' : '#f87171',
                    opacity: isUnitConnected ? 1 : 0.4
                  }}>
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

      {/* FLOATING HUD OVERLAY PANEL */}
      <div style={styles.floatingHud}>
        <div style={{ fontWeight: 'bold', color: '#38bdf8', marginBottom: '4px', fontSize: '10px' }}>🛰️ RADAR INTEL</div>

        {activeAttackers.length > 0 && (
          <div style={{ borderBottom: '1px solid #334155', paddingBottom: '4px', marginBottom: '4px' }}>
            <span style={{ color: '#64748b' }}>STACK ATK:</span> <span style={{ color: '#06b6d4', fontWeight: 'bold' }}>{totalAttackPower}</span>
            {stackOrientation && <span style={{ color: '#10b981', fontSize: '8px', marginLeft: '6px' }}>[LOCKED LINK]</span>}
          </div>
        )}

        {hoveredUnit ? (
          <div>
            <div style={{ color: hoveredUnit.side === 'North' ? '#60a5fa' : '#f87171', fontWeight: 'bold' }}>
              {hoveredStats.label} [{hoveredUnit.symbol}]
            </div>
            <div style={{ fontSize: '9px', color: '#94a3b8' }}>
              ATK: <span style={{ color: '#f8fafc', marginRight: '6px' }}>{hoveredStats.attack}</span>
              DEF: <span style={{ color: '#f8fafc' }}>{hoveredStats.currentDefense}</span>
              <div style={{ color: hoveredStats.isConnected ? '#38bdf8' : '#ef4444', marginTop: '1px' }}>
                ({hoveredStats.isConnected ? "Linked Network" : "MUTED / CUT-OFF"})
              </div>
            </div>
            {totalAttackPower > 0 && hoveredUnit.side !== turn && (
              <div style={{ marginTop: '2px', color: totalAttackPower > hoveredStats.currentDefense ? '#10b981' : '#f59e0b', fontWeight: 'bold', fontSize: '9px' }}>
                {totalAttackPower > hoveredStats.currentDefense ? "✓ BREACH CONFIRMED" : "✗ REPELLED"}
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: '#475569', fontStyle: 'italic' }}>Radar idle.</div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: { backgroundColor: '#020617', minHeight: '100vh', color: '#f3f4f6', fontFamily: 'monospace', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px' },
  lobbyCard: { backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '30px', width: '100%', maxWidth: '400px', marginTop: '100px' },
  lobbyTitle: { fontSize: '20px', letterSpacing: '2px', textAlign: 'center', margin: '0 0 4px 0', color: '#ffffff' },
  lobbySubtitle: { fontSize: '10px', color: '#ffffff', textAlign: 'center', margin: '0 0 16px 0' },
  toggleContainer: { display: 'flex', backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', padding: '2px', marginBottom: '16px' },
  toggleBtn: { flex: 1, border: 'none', padding: '8px', fontSize: '10px', fontFamily: 'monospace', borderRadius: '3px', cursor: 'pointer' },
  lobbyError: { backgroundColor: '#7f1d1d', color: '#fca5a5', padding: '8px', borderRadius: '4px', fontSize: '11px', marginBottom: '12px' },
  form: { display: 'flex', flexDirection: 'column', gap: '14px' },
  inputGroup: { display: 'flex', flexDirection: 'column', gap: '4px' },
  label: { fontSize: '9px', color: '#94a3b8', fontWeight: 'bold' },
  input: { backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '4px', color: '#f8fafc', padding: '8px 12px', fontSize: '12px', fontFamily: 'monospace', outline: 'none' },
  lobbyButton: { backgroundColor: '#1e293b', border: '1px solid #475569', color: '#38bdf8', padding: '10px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold', cursor: 'pointer' },

  // Hard height thresholds to lock UI jumping
  header: { width: '100%', maxWidth: '1280px', height: '62px', minHeight: '62px', maxHeight: '62px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', borderBottom: '1px solid #334155', paddingBottom: '12px', gap: '12px', boxSizing: 'border-box' },
  headerTitleSection: { display: 'flex', flexDirection: 'column' },
  title: { fontSize: '18px', letterSpacing: '2px', color: '#f1f5f9', margin: 0, lineHeight: '1' },
  sharePanel: { display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px', fontSize: '10px' },
  linkInput: { backgroundColor: '#0f172a', border: '1px solid #334155', color: '#38bdf8', padding: '2px 6px', borderRadius: '4px', width: '150px', fontSize: '10px', outline: 'none' },
  identityPanel: { display: 'flex', gap: '8px', alignItems: 'center' },
  playerTag: { display: 'flex', flexDirection: 'column', backgroundColor: '#0f172a', border: '1px solid', borderRadius: '4px', padding: '4px 10px', minWidth: '100px', height: '38px', boxSizing: 'border-box', justifyContent: 'center' },
  controlPanel: { display: 'flex', gap: '8px', alignItems: 'center' },

  // Fixed button formatting dimensions
  fixedBtn: { backgroundColor: '#0f172a', border: '1px solid #334155', color: '#f8fafc', width: '80px', height: '34px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' },
  statusBadge: { backgroundColor: '#0f172a', border: '1px solid', width: '150px', height: '34px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box', whiteSpace: 'nowrap' },
  metricsBadge: { backgroundColor: '#0f172a', border: '1px solid #334155', width: '110px', height: '34px', borderRadius: '4px', fontSize: '11px', color: '#94a3b8', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box', whiteSpace: 'nowrap' },
  HighlightText: { color: '#f59e0b', fontWeight: 'bold' },
  endTurnButton: { backgroundColor: '#1e293b', border: '1px solid #64748b', color: '#f8fafc', width: '95px', height: '34px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' },

  errorAlert: { width: '100%', maxWidth: '1280px', border: '1px solid', color: '#f8fafc', padding: '8px 12px', borderRadius: '4px', marginBottom: '10px', fontSize: '12px', boxSizing: 'border-box' },
  waitingBanner: { width: '100%', maxWidth: '1280px', backgroundColor: '#1c1917', border: '1px solid #44403c', color: '#a8a29e', padding: '6px', borderRadius: '4px', marginBottom: '10px', fontSize: '11px', textAlign: 'center', boxSizing: 'border-box' },

  // Split view design linking grid layout and sidebar status tracking
  workspaceLayout: { display: 'flex', width: '100%', maxWidth: '1280px', gap: '16px', alignItems: 'flex-start' },
  sidebarPanel: { width: '240px', minWidth: '240px', backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px', boxSizing: 'border-box' },
  sidebarDivider: { height: '1px', backgroundColor: '#334155', width: '100%', margin: '8px 0' },
  factionStatsBlock: { display: 'flex', flexDirection: 'column' },
  statRow: { display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginTop: '4px' },
  statLabel: { color: '#64748b' },

  gridContainer: { position: 'relative', flexGrow: 1, display: 'grid', gridTemplateColumns: 'repeat(25, minmax(0, 1fr))', gap: '2px', backgroundColor: '#0f172a', padding: '8px', borderRadius: '6px', border: '1px solid #1e293b' },
  cell: { position: 'relative', aspectRatio: '1', display: 'flex', alignItems: 'center', justifyContent: 'center', userSelect: 'none', transition: 'background-color 0.15s ease' },
  unitBadge: { width: '80%', height: '80%', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '3px', border: '2px solid', fontWeight: 'bold', fontSize: '12px', backgroundColor: '#020617', zIndex: 2 },
  locDot: { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '6px', height: '6px', borderRadius: '50%', zIndex: 1, opacity: 0.8 },
  terrainLabel: { fontSize: '9px', opacity: 0.2 },
  coords: { position: 'absolute', bottom: '1px', right: '1px', fontSize: '4px', color: '#334155', opacity: 0.3 },

  floatingHud: { position: 'fixed', bottom: '16px', right: '16px', backgroundColor: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(6px)', border: '1px solid #334155', borderRadius: '6px', padding: '10px', width: '180px', fontSize: '10px', zIndex: 100, boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }
};
