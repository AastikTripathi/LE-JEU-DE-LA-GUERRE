# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import copy
from engine import GameEngine

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
            # --- NORTH FORCES ---
            {"id": "n-inf-1", "side": "North", "type": "Infantry", "symbol": "I", "x": 10, "y": 3},
            {"id": "n-inf-2", "side": "North", "type": "Infantry", "symbol": "I", "x": 11, "y": 3},
            {"id": "n-inf-3", "side": "North", "type": "Infantry", "symbol": "I", "x": 12, "y": 3},
            {"id": "n-cav-1", "side": "North", "type": "Cavalry", "symbol": "C", "x": 9, "y": 2},
            {"id": "n-art-1", "side": "North", "type": "Artillery", "symbol": "A", "x": 12, "y": 2},
            {"id": "n-rel-1", "side": "North", "type": "Relay", "symbol": "R", "x": 13, "y": 2},
            # --- SOUTH FORCES ---
            {"id": "s-inf-1", "side": "South", "type": "Infantry", "symbol": "I", "x": 11, "y": 16},
            {"id": "s-inf-2", "side": "South", "type": "Infantry", "symbol": "I", "x": 12, "y": 16},
            {"id": "s-inf-3", "side": "South", "type": "Infantry", "symbol": "I", "x": 13, "y": 16},
            {"id": "s-cav-1", "side": "South", "type": "Cavalry", "symbol": "C", "x": 10, "y": 17},
            {"id": "s-art-1", "side": "South", "type": "Artillery", "symbol": "A", "x": 12, "y": 17},
            {"id": "s-rel-1", "side": "South", "type": "Relay", "symbol": "R", "x": 11, "y": 18},
        ],
        "turn": "North",
        "moves_left": 5,
        "moved_units_this_turn": [],
        "attack_executed_this_turn": False
    }


def initialize_room(room_id: str):
    if room_id not in rooms:
        rooms[room_id] = {
            "state": get_initial_state(),
            "history": [],  # Stack to track turn snapshots for undo commands
            "connections": []
        }


async def broadcast_room_state(room_id: str):
    room = rooms.get(room_id)
    if not room: return

    st = room["state"]
    n_loc = [[x, y] for x, y in engine.compute_lines_of_communication(st["units"], "North")]
    s_loc = [[x, y] for x, y in engine.compute_lines_of_communication(st["units"], "South")]
    connected = list(engine.get_connected_units(st["units"], "North")) + list(
        engine.get_connected_units(st["units"], "South"))

    payload = {
        "units": st["units"],
        "turn": st["turn"],
        "movesLeft": st["moves_left"],
        "attackExecuted": st["attack_executed_this_turn"],
        "linesOfCommunication": {"North": n_loc, "South": s_loc},
        "connectedUnitIds": connected,
        "canUndo": len(room["history"]) > 0
    }

    for conn in room["connections"]:
        try:
            await conn.send_json(payload)
        except:
            pass


def save_state_to_history(room_id: str):
    """Deep-copies current game state into the undo stack before an action alters it."""
    room = rooms[room_id]
    # Keep up to last 10 snapshots to avoid memory bloat
    if len(room["history"]) >= 10:
        room["history"].pop(0)
    room["history"].append(copy.deepcopy(room["state"]))


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    initialize_room(room_id)
    rooms[room_id]["connections"].append(websocket)

    await broadcast_room_state(room_id)

    try:
        while True:
            data = await websocket.receive_json()
            room = rooms[room_id]
            st = room["state"]
            action = data.get("action")

            if action == "move":
                if st["moves_left"] <= 0:
                    await websocket.send_json({"type": "error", "message": "No moves remaining."})
                    continue

                unit_id = data.get("unitId")
                tx, ty = data.get("x"), data.get("y")

                is_valid, reason = engine.validate_move(st["units"], unit_id, tx, ty, st["moved_units_this_turn"])
                if is_valid:
                    save_state_to_history(room_id)  # Log history frame
                    for u in st["units"]:
                        if u["id"] == unit_id:
                            u["x"], u["y"] = tx, ty
                    st["moves_left"] -= 1
                    st["moved_units_this_turn"].append(unit_id)
                    await broadcast_room_state(room_id)
                else:
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
                    if res == "DESTROY":
                        st["units"] = [u for u in st["units"] if not (u["x"] == tx and u["y"] == ty)]
                        msg = "Strike Success! Unit eliminated."
                    else:
                        msg = "Attack repelled."

                    st["attack_executed_this_turn"] = True
                    await broadcast_room_state(room_id)
                    await websocket.send_json({"type": "error", "message": msg})
                else:
                    await websocket.send_json({"type": "error", "message": combat["reason"]})

            elif action == "undo":
                if room["history"]:
                    room["state"] = room["history"].pop()  # Pop last state snapshot
                    await broadcast_room_state(room_id)
                else:
                    await websocket.send_json({"type": "error", "message": "Nothing left to undo."})

            elif action == "restart":
                room["history"].clear()
                room["state"] = get_initial_state()
                await broadcast_room_state(room_id)

            elif action == "end_turn":
                room["history"].clear()  # Wipe undo stack when turn officially locks down
                next_side = "South" if st["turn"] == "North" else "North"
                st["turn"] = next_side
                st["moves_left"] = 5
                st["moved_units_this_turn"] = []
                st["attack_executed_this_turn"] = False
                await broadcast_room_state(room_id)

    except WebSocketDisconnect:
        rooms[room_id]["connections"].remove(websocket)
        if not rooms[room_id]["connections"]:
            del rooms[room_id]  # Clean up memory if empty


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port
    )
