# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import copy
from engine import GameEngine
import asyncio  # Needed for step-by-step delay pacing
from ai import WarGameAI

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = GameEngine()

# In-memory storage tracking independent active rooms
rooms = {}


def get_initial_state():
    return {
        "units": [
            # === NORTH FORCES (17 Units Total) ===
            {"id": "n-inf-1", "side": "North", "type": "Infantry", "symbol": "I", "x": 4, "y": 4},
            {"id": "n-inf-2", "side": "North", "type": "Infantry", "symbol": "I", "x": 6, "y": 4},
            {"id": "n-inf-3", "side": "North", "type": "Infantry", "symbol": "I", "x": 8, "y": 4},
            {"id": "n-inf-4", "side": "North", "type": "Infantry", "symbol": "I", "x": 10, "y": 4},
            {"id": "n-inf-5", "side": "North", "type": "Infantry", "symbol": "I", "x": 12, "y": 4},
            {"id": "n-inf-6", "side": "North", "type": "Infantry", "symbol": "I", "x": 14, "y": 4},
            {"id": "n-inf-7", "side": "North", "type": "Infantry", "symbol": "I", "x": 16, "y": 4},
            {"id": "n-inf-8", "side": "North", "type": "Infantry", "symbol": "I", "x": 18, "y": 4},
            {"id": "n-inf-9", "side": "North", "type": "Infantry", "symbol": "I", "x": 20, "y": 4},

            {"id": "n-cav-1", "side": "North", "type": "Cavalry", "symbol": "C", "x": 3, "y": 3},
            {"id": "n-cav-2", "side": "North", "type": "Cavalry", "symbol": "C", "x": 7, "y": 3},
            {"id": "n-cav-3", "side": "North", "type": "Cavalry", "symbol": "C", "x": 17, "y": 3},
            {"id": "n-cav-4", "side": "North", "type": "Cavalry", "symbol": "C", "x": 21, "y": 3},

            {"id": "n-art-1", "side": "North", "type": "Artillery", "symbol": "A", "x": 11, "y": 2},
            {"id": "n-art-2", "side": "North", "type": "Artillery", "symbol": "A", "x": 13, "y": 2},

            # FIXED: y coordinates changed from 1 to 0
            {"id": "n-rel-1", "side": "North", "type": "Relay", "symbol": "R", "x": 10, "y": 0},
            {"id": "n-rel-2", "side": "North", "type": "Relay", "symbol": "R", "x": 14, "y": 0},

            # === SOUTH FORCES (17 Units Total) ===
            {"id": "s-inf-1", "side": "South", "type": "Infantry", "symbol": "I", "x": 4, "y": 15},
            {"id": "s-inf-2", "side": "South", "type": "Infantry", "symbol": "I", "x": 6, "y": 15},
            {"id": "s-inf-3", "side": "South", "type": "Infantry", "symbol": "I", "x": 8, "y": 15},
            {"id": "s-inf-4", "side": "South", "type": "Infantry", "symbol": "I", "x": 10, "y": 15},
            {"id": "s-inf-5", "side": "South", "type": "Infantry", "symbol": "I", "x": 12, "y": 15},
            {"id": "s-inf-6", "side": "South", "type": "Infantry", "symbol": "I", "x": 14, "y": 15},
            {"id": "s-inf-7", "side": "South", "type": "Infantry", "symbol": "I", "x": 16, "y": 15},
            {"id": "s-inf-8", "side": "South", "type": "Infantry", "symbol": "I", "x": 18, "y": 15},
            {"id": "s-inf-9", "side": "South", "type": "Infantry", "symbol": "I", "x": 20, "y": 15},

            {"id": "s-cav-1", "side": "South", "type": "Cavalry", "symbol": "C", "x": 3, "y": 16},
            {"id": "s-cav-2", "side": "South", "type": "Cavalry", "symbol": "C", "x": 7, "y": 16},
            {"id": "s-cav-3", "side": "South", "type": "Cavalry", "symbol": "C", "x": 17, "y": 16},
            {"id": "s-cav-4", "side": "South", "type": "Cavalry", "symbol": "C", "x": 21, "y": 16},

            {"id": "s-art-1", "side": "South", "type": "Artillery", "symbol": "A", "x": 11, "y": 17},
            {"id": "s-art-2", "side": "South", "type": "Artillery", "symbol": "A", "x": 13, "y": 17},

            # FIXED: y coordinates changed from 18 to 19
            {"id": "s-rel-1", "side": "South", "type": "Relay", "symbol": "R", "x": 10, "y": 19},
            {"id": "s-rel-2", "side": "South", "type": "Relay", "symbol": "R", "x": 14, "y": 19}
        ],
        "turn": "North",
        "moves_left": 5,
        "moved_units_this_turn": [],
        "attack_executed_this_turn": False,
        "last_combat": None
    }


def check_win_condition(units: list) -> str | None:
    """
    Returns 'North', 'South', or None.
    Win conditions:
      1. Annihilation  — eliminate all enemy units.
      2. Full Capture  — occupy BOTH enemy arsenal tiles simultaneously.
         (Capturing one arsenal collapses enemy LoC and extends yours — but
          you still need to hold both to claim total victory or destroy the remnants.)
    """
    north_units = [u for u in units if u["side"] == "North"]
    south_units = [u for u in units if u["side"] == "South"]

    if not north_units:
        return "South"
    if not south_units:
        return "North"

    north_pos = {(u["x"], u["y"]) for u in north_units}
    south_pos = {(u["x"], u["y"]) for u in south_units}

    # Arsenal tile coordinates
    north_arsenals = {(12, 1), (13, 1)}
    south_arsenals = {(2, 18), (22, 18)}

    # Full capture: you must occupy ALL enemy arsenal tiles at once
    if north_arsenals.issubset(south_pos):   # South holds both North arsenals
        return "South"
    if south_arsenals.issubset(north_pos):   # North holds both South arsenals
        return "North"

    # Deactivation win condition: if one side has active (connected) units but the other side
    # has 0 active units (all cut off/deactivated), the active side wins.
    try:
        connected_north = engine.get_connected_units(units, "North")
        connected_south = engine.get_connected_units(units, "South")
        if north_units and not connected_north and connected_south:
            return "South"
        if south_units and not connected_south and connected_north:
            return "North"
    except Exception:
        pass

    return None


# def initialize_room(room_id: str, vs_ai: bool = False):
#     if room_id not in rooms:
#         rooms[room_id] = {
#             "state": get_initial_state(),
#             "history": [],       # Stack to track turn snapshots for undo commands
#             "connections": [],   # List of {"ws": WebSocket, "name": str, "side": str|None}
#             "password": None,
#             "vs_ai": vs_ai       # Explicit mode flag stored directly in the room dict
#         }


def initialize_room(room_id: str, vs_ai: bool = False, ai_vs_ai: bool = False):
    if room_id not in rooms:
        rooms[room_id] = {
            "state": get_initial_state(),
            "history": [],
            "connections": [],
            "password": None,
            "vs_ai": vs_ai,
            "ai_vs_ai": ai_vs_ai, # Track if both sides are automated
            "sim_running": False  # Flag to prevent spawning duplicate task threads
        }


async def broadcast_room_state(room_id: str):
    room = rooms.get(room_id)
    if not room:
        return

    st = room["state"]
    n_loc = [[x, y] for x, y in engine.compute_lines_of_communication(st["units"], "North")]
    s_loc = [[x, y] for x, y in engine.compute_lines_of_communication(st["units"], "South")]
    connected = list(engine.get_connected_units(st["units"], "North")) + list(
        engine.get_connected_units(st["units"], "South"))

    # Build a name → side map to send to all clients
    players = {"North": None, "South": None}
    for conn in room["connections"]:
        if conn["side"] in ("North", "South"):
            players[conn["side"]] = conn["name"]

    winner = check_win_condition(st["units"])

    payload = {
        "units": st["units"],
        "turn": st["turn"],
        "movesLeft": st["moves_left"],
        "attackExecuted": st["attack_executed_this_turn"],
        "movedUnitsThisTurn": st["moved_units_this_turn"],
        "linesOfCommunication": {"North": n_loc, "South": s_loc},
        "connectedUnitIds": connected,
        "canUndo": len(room["history"]) > 0,
        "players": players,
        "winner": winner,
        "lastCombat": st.get("last_combat"),
    }

    for conn in room["connections"]:
        try:
            # Each client also learns their own assigned side
            personal_payload = {**payload, "yourSide": conn["side"]}
            await conn["ws"].send_json(personal_payload)
        except Exception:
            pass


def save_state_to_history(room_id: str):
    """Deep-copies current game state into the undo stack before an action alters it."""
    room = rooms[room_id]
    # Keep up to last 10 snapshots to avoid memory bloat
    if len(room["history"]) >= 10:
        room["history"].pop(0)
    room["history"].append(copy.deepcopy(room["state"]))


async def run_ai_simulation(room_id: str):
    """Automated background task running both AI agents at maximum velocity."""
    try:
        while True:
            room = rooms.get(room_id)
            if not room or not room.get("ai_vs_ai", False) or not room["connections"]:
                break

            st = room["state"]
            current_side = st["turn"]
            ai_agent = WarGameAI(engine, side=current_side)

            # Process actions rapidly
            while st["turn"] == current_side and st["moves_left"] > 0:
                # Scaled down to 50ms for ultra-rapid visual automation updates
                if check_win_condition(st["units"]):
                    return

                await asyncio.sleep(0.05)

                room = rooms.get(room_id)
                if not room or not room.get("ai_vs_ai", False) or not room["connections"]:
                    return

                st = room["state"]
                best_act = ai_agent.select_best_action(st)

                if best_act["action_type"] == "end_turn":
                    break

                if best_act["action_type"] == "move":
                    for u in st["units"]:
                        if u["id"] == best_act["unitId"]:
                            u["x"], u["y"] = best_act["x"], best_act["y"]
                    st["moves_left"] -= 1
                    st["moved_units_this_turn"].append(best_act["unitId"])

                # elif best_act["action_type"] == "attack":
                #     combat = engine.calculate_combat(st["units"], current_side, best_act["x"], best_act["y"])
                #     if combat.get("valid") and combat["result"] == "DESTROY":
                #         tx, ty = best_act["x"], best_act["y"]
                #         st["units"] = [u for u in st["units"] if not (u["x"] == tx and u["y"] == ty)]
                #     st["attack_executed_this_turn"] = True

                elif best_act["action_type"] == "attack":
                    tx, ty = best_act["x"], best_act["y"]
                    mover = next((u for u in st["units"] if u["id"] == best_act["unitId"]), None)
                    combat = engine.calculate_combat(st["units"], current_side, tx, ty)
                    if combat.get("valid"):
                        if combat["result"] == "DESTROY":
                            st["units"] = [u for u in st["units"] if not (u["x"] == tx and u["y"] == ty)]
                        st["last_combat"] = {
                            "attackerX": mover["x"] if mover else tx,
                            "attackerY": mover["y"] if mover else ty,
                            "targetX": tx, "targetY": ty, "result": combat["result"]
                        }
                    st["attack_executed_this_turn"] = True

                await broadcast_room_state(room_id)

            # Hand over active control matrix directly to opposing instance
            room["history"].clear()
            st["turn"] = "South" if current_side == "North" else "North"
            st["moves_left"] = 5
            st["moved_units_this_turn"] = []
            st["attack_executed_this_turn"] = False
            st["last_combat"] = None
            await broadcast_room_state(room_id)

            # Brief micro-cooldown before next AI takes over
            await asyncio.sleep(0.05)
    finally:
        room = rooms.get(room_id)
        if room:
            room["sim_running"] = False


# @app.websocket("/ws/{room_id}")
# async def websocket_endpoint(websocket: WebSocket, room_id: str):
#     name = websocket.query_params.get("name", "Unknown")
#     password = websocket.query_params.get("password", "")
#     # Parse the boolean flag passed from the frontend toggle
#     vs_ai = websocket.query_params.get("vs_ai", "false").lower() == "true"
#
#     await websocket.accept()
#     initialize_room(room_id, vs_ai=vs_ai)
#
#     room = rooms[room_id]
#
#     # --- INSERT THIS PRECISE BLOCK HERE ---
#     # If this is a single-player match, forcefully evict any ghost connections from a previous refresh
#     if room.get("vs_ai", False):
#         room["connections"] = []
    # --------------------------------------

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    name = websocket.query_params.get("name", "Unknown")
    password = websocket.query_params.get("password", "")
    vs_ai = websocket.query_params.get("vs_ai", "false").lower() == "true"
    ai_vs_ai = websocket.query_params.get("ai_vs_ai", "false").lower() == "true"

    await websocket.accept()
    initialize_room(room_id, vs_ai=vs_ai, ai_vs_ai=ai_vs_ai)

    room = rooms[room_id]

    # Forcefully evict ghost entries if running an automated or solo testing sandbox
    if room.get("vs_ai", False) or room.get("ai_vs_ai", False):
        room["connections"] = []



    # --- Password check ---
    # The first player to connect sets the room password; subsequent players must match it.
    if room["password"] is None:
        room["password"] = password
    elif room["password"] != password:
        await websocket.send_json({"type": "error", "message": "Authentication failed: incorrect password."})
        await websocket.close()
        return


    existing_conn = next((c for c in room["connections"] if c["name"] == name), None)

    if existing_conn:
        # Inherit your original side assignment and remove the stale ghost connection
        assigned_side = existing_conn["side"]
        room["connections"].remove(existing_conn)
        try:
            await existing_conn["ws"].close()
        except Exception:
            pass
    else:
        # Standard side assignment for a brand new player joining
        taken_sides = {conn["side"] for conn in room["connections"] if conn["side"] is not None}

        if "North" not in taken_sides:
            assigned_side = "North"
        elif "South" not in taken_sides:
            assigned_side = "South"
        else:
            # Room is full — reject the 3rd+ connection
            await websocket.send_json({
                "type": "error",
                "message": "Room is full. This battle already has two commanders."
            })
            await websocket.close()
            return

    # conn_entry = {"ws": websocket, "name": name, "side": assigned_side}
    # room["connections"].append(conn_entry)
    #
    # # Broadcast updated state so the new player immediately learns their side
    # await broadcast_room_state(room_id)

    conn_entry = {"ws": websocket, "name": name, "side": assigned_side if not room.get("ai_vs_ai") else "Observer"}
    room["connections"].append(conn_entry)

    await broadcast_room_state(room_id)

    # Fire up the automated sandbox task if it isn't running yet
    if room.get("ai_vs_ai", False) and not room.get("sim_running", False):
        room["sim_running"] = True
        asyncio.create_task(run_ai_simulation(room_id))

    try:
        while True:
            data = await websocket.receive_json()
            st = room["state"]
            action = data.get("action")

            # --- Turn Authorization ---
            # Only the player whose side matches the current turn may act.
            # Exceptions: restart is always allowed by either player.
            if action != "restart" and conn_entry["side"] != st["turn"]:
                await websocket.send_json({
                    "type": "error",
                    "message": f"It is {st['turn']}'s turn. Wait for your opponent."
                })
                continue

            # Freeze all actions (except restart) once the game has a winner
            if action != "restart" and check_win_condition(st["units"]):
                await websocket.send_json({"type": "error", "message": "The battle is over. Restart to play again."})
                continue

            if action == "move":
                if st["moves_left"] <= 0:
                    await websocket.send_json({"type": "error", "message": "No moves remaining."})
                    continue

                unit_id = data.get("unitId")
                tx, ty = data.get("x"), data.get("y")

                is_valid, reason = engine.validate_move(st["units"], unit_id, tx, ty, st["moved_units_this_turn"])
                if is_valid:
                    save_state_to_history(room_id)  # Log history frame
                    print(f"[MOVE] Success: ID={unit_id} to ({tx},{ty}) in room={room_id}. History size now: {len(room['history'])}")
                    for u in st["units"]:
                        if u["id"] == unit_id:
                            u["x"], u["y"] = tx, ty
                    st["moves_left"] -= 1
                    st["moved_units_this_turn"].append(unit_id)
                    await broadcast_room_state(room_id)
                else:
                    print(f"[MOVE] Refused: ID={unit_id} to ({tx},{ty}) in room={room_id} because: {reason}")
                    await websocket.send_json({"type": "error", "message": reason})

            elif action == "attack":
                if st["attack_executed_this_turn"]:
                    await websocket.send_json({"type": "error", "message": "Attack action limit reached."})
                    continue

                tx, ty = data.get("x"), data.get("y")
                combat = engine.calculate_combat(st["units"], st["turn"], tx, ty)

                if combat.get("valid"):
                    save_state_to_history(room_id)  # Log history frame
                    res = combat["result"]
                    attacker_unit = next((u for u in st["units"] if u["side"] == st["turn"] and
                                          abs(u["x"] - tx) <= 3 and abs(u["y"] - ty) <= 3), None)
                    print(f"[ATTACK] Success: target=({tx},{ty}) result={res} in room={room_id}. History size now: {len(room['history'])}")
                    if res == "DESTROY":
                        st["units"] = [u for u in st["units"] if not (u["x"] == tx and u["y"] == ty)]
                        msg = "Strike Success! Unit eliminated."
                    else:
                        msg = "Attack repelled."

                    st["last_combat"] = {
                        "attackerX": attacker_unit["x"] if attacker_unit else tx,
                        "attackerY": attacker_unit["y"] if attacker_unit else ty,
                        "targetX": tx, "targetY": ty, "result": res
                    }
                    st["attack_executed_this_turn"] = True
                    await broadcast_room_state(room_id)
                else:
                    print(f"[ATTACK] Refused: target=({tx},{ty}) in room={room_id} because: {combat.get('reason')}")
                    await websocket.send_json({"type": "error", "message": combat.get("reason", "Invalid attack target.")})

            elif action == "undo":
                if room["history"]:
                    old_state = room["history"].pop()
                    print(f"[UNDO] Restoring state in room={room_id}. History size remaining: {len(room['history'])}")
                    room["state"] = old_state
                    await broadcast_room_state(room_id)
                else:
                    print(f"[UNDO] Refused in room={room_id}: history is empty")
                    await websocket.send_json({"type": "error", "message": "Nothing left to undo."})

            elif action == "restart":
                room["history"].clear()
                room["state"] = get_initial_state()
                await broadcast_room_state(room_id)

            # elif action == "end_turn":
            #     room["history"].clear()  # Wipe undo stack when turn officially locks down
            #     next_side = "South" if st["turn"] == "North" else "North"
            #     st["turn"] = next_side
            #     st["moves_left"] = 5
            #     st["moved_units_this_turn"] = []
            #     st["attack_executed_this_turn"] = False
            #     await broadcast_room_state(room_id)

            elif action == "end_turn":
                room["history"].clear()  # Wipe undo stack when turn officially locks down
                next_side = "South" if st["turn"] == "North" else "North"
                st["turn"] = next_side
                st["moves_left"] = 5
                st["moved_units_this_turn"] = []
                st["attack_executed_this_turn"] = False
                st["last_combat"] = None

                # Broadcast the shift to South's turn immediately
                await broadcast_room_state(room_id)

                # --- INTERCEPT FOR AI MATCH PLAY ---
                # Trigger automation if the next turn belongs to South and the room name flags an AI setup
                # if st["turn"] == "South" and "ai" in room_id.lower():
                #     ai_agent = WarGameAI(engine, side="South")
                if st["turn"] == "South" and room.get("vs_ai", False):
                    ai_agent = WarGameAI(engine, side="South")

                    # AI processes tactical actions step by step until its strategic points deplete
                    while st["turn"] == "South" and st["moves_left"] > 0:
                        # 800ms delay gives human players visual cues of enemy pieces sliding
                        await asyncio.sleep(0.8)

                        best_act = ai_agent.select_best_action(st)

                        if best_act["action_type"] == "end_turn":
                            break

                        if best_act["action_type"] == "move":
                            for u in st["units"]:
                                if u["id"] == best_act["unitId"]:
                                    u["x"], u["y"] = best_act["x"], best_act["y"]
                            st["moves_left"] -= 1
                            st["moved_units_this_turn"].append(best_act["unitId"])

                        # elif best_act["action_type"] == "attack":
                        #     combat = engine.calculate_combat(st["units"], "South", best_act["x"], best_act["y"])
                        #     if combat.get("valid") and combat["result"] == "DESTROY":
                        #         tx, ty = best_act["x"], best_act["y"]
                        #         st["units"] = [u for u in st["units"] if not (u["x"] == tx and u["y"] == ty)]
                        #     st["attack_executed_this_turn"] = True

                        elif best_act["action_type"] == "attack":
                            tx, ty = best_act["x"], best_act["y"]
                            mover = next((u for u in st["units"] if u["id"] == best_act["unitId"]), None)
                            combat = engine.calculate_combat(st["units"], "South", tx, ty)
                            if combat.get("valid"):
                                if combat["result"] == "DESTROY":
                                    st["units"] = [u for u in st["units"] if not (u["x"] == tx and u["y"] == ty)]
                                st["last_combat"] = {
                                    "attackerX": mover["x"] if mover else tx,
                                    "attackerY": mover["y"] if mover else ty,
                                    "targetX": tx, "targetY": ty, "result": combat["result"]
                                }
                            st["attack_executed_this_turn"] = True

                        # Sync intermediate update out to the active websocket connection
                        await broadcast_room_state(room_id)

                    # Return control seamlessly back to the human player (North)
                    st["turn"] = "North"
                    st["moves_left"] = 5
                    st["moved_units_this_turn"] = []
                    st["attack_executed_this_turn"] = False
                    st["last_combat"] = None
                    await broadcast_room_state(room_id)

    except WebSocketDisconnect:
        room["connections"].remove(conn_entry)
        if not room["connections"]:
            del rooms[room_id]  # Clean up memory if empty
        else:
            # Notify remaining player that their opponent disconnected
            for remaining in room["connections"]:
                try:
                    await remaining["ws"].send_json({
                        "type": "error",
                        "message": f"Opponent '{name}' has disconnected."
                    })
                except Exception:
                    pass


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port
    )
