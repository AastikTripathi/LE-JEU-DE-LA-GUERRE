
# engine.py
from typing import List, Dict, Tuple, Set


class GameEngine:
    def __init__(self):
        self.cols = 25
        self.rows = 20

        # Authentic L-Shaped Mountain Ranges (0-indexed mapping)
        self.mountains = {
            # North Range (Columns 9-12 on Rows 2-8)
            (9, 2), (10, 2), (11, 2), (12, 2),
            (9, 3), (9, 4),
            (9, 6), (9, 7), (9, 8),

            # South Range (Columns 10-15 on Rows 13-17)
            (10, 13), (11, 13), (12, 13), (13, 13), (14, 13), (15, 13),
            (15, 15), (15, 16), (15, 17)
        }

        # Mountain Passes (The functional gaps breaking the L-shapes)
        self.passes = {(9, 5), (15, 14)}

        # Strategic Fortresses (Both pure Forts and Arsenals yield defensive cover bonuses)
        self.fortresses = {
            (7, 1), (12, 8), (20, 7),  # North Forts
            (2, 12), (14, 11), (22, 14),  # South Forts
            (7, 3), (14, 1),  # North Arsenals
            (2, 19), (22, 19)  # South Arsenals
        }

        self.arsenals = {
            "North": {(7, 3), (14, 1)},
            "South": {(2, 19), (22, 19)}
        }

        self.directions = [
            (0, 1), (0, -1), (1, 0), (-1, 0),  # Orthogonal
            (1, 1), (1, -1), (-1, 1), (-1, -1)  # Diagonal
        ]

        # Official Unit Stat Catalog
        self.unit_stats = {
            "infantry": {"speed": 1, "range": 2, "offense": 4, "defense": 6},
            "cavalry": {"speed": 2, "range": 2, "offense": 5, "defense": 5, "charge": 7},
            "artillery": {"speed": 1, "range": 3, "offense": 5, "defense": 8},
            "relay": {"speed": 1, "range": 0, "offense": 0, "defense": 1}
        }

    def get_stats(self, unit_type: str) -> dict:
        u_type = unit_type.lower()
        if "infantry" in u_type: return self.unit_stats["infantry"]
        if "cavalry" in u_type: return self.unit_stats["cavalry"]
        if "artillery" in u_type: return self.unit_stats["artillery"]
        return self.unit_stats["relay"]

    def compute_lines_of_communication(self, units: List[Dict], side: str) -> Set[Tuple[int, int]]:
        opponent_side = "North" if side == "South" else "South"
        enemy_pos = {(u['x'], u['y']) for u in units if u['side'] == opponent_side}
        friendly_pos = {(u['x'], u['y']) for u in units if u['side'] == side}

        # for ax, ay in self.arsenals[side]:
        #     if (ax, ay) in enemy_pos:
        #         return set()  # Total network collapse
        #
        # active_loc_cells = set()
        # enemy_positions = {(u['x'], u['y']) for u in units if u['side'] != side}
        # friendly_relays = {u['id']: (u['x'], u['y']) for u in units if
        #                    u['side'] == side and 'relay' in u['type'].lower()}
        #
        # emitters_queue = list(self.arsenals[side])

        active_loc_cells = set()
        enemy_positions = {(u['x'], u['y']) for u in units if u['side'] != side}
        friendly_relays = {u['id']: (u['x'], u['y']) for u in units if
                           u['side'] == side and 'relay' in u['type'].lower()}

        # MODIFIED: Only queue arsenals that are NOT occupied by the enemy
        emitters_queue = [
            (ax, ay) for ax, ay in self.arsenals[side] if (ax, ay) not in enemy_pos
        ]

        # Authentic Rule: Total collapse ONLY happens if all friendly arsenals are compromised
        if not emitters_queue:
            return set()
        processed_emitters = set(emitters_queue)

        for ax, ay in self.arsenals[opponent_side]:
            if (ax, ay) in friendly_pos and (ax, ay) not in processed_emitters:
                emitters_queue.append((ax, ay))
                processed_emitters.add((ax, ay))

        for ax, ay in emitters_queue:
            active_loc_cells.add((ax, ay))

        while emitters_queue:
            cx, cy = emitters_queue.pop(0)
            for dx, dy in self.directions:
                tx, ty = cx + dx, cy + dy
                while 0 <= tx < self.cols and 0 <= ty < self.rows:
                    if (tx, ty) in self.mountains: break
                    if (tx, ty) in enemy_positions: break

                    active_loc_cells.add((tx, ty))

                    for r_id, (rx, ry) in list(friendly_relays.items()):
                        if tx == rx and ty == ry and (rx, ry) not in processed_emitters:
                            emitters_queue.append((rx, ry))
                            processed_emitters.add((rx, ry))
                    tx += dx
                    ty += dy
        return active_loc_cells

    def get_connected_units(self, units: List[Dict], side: str) -> Set[str]:
        active_loc = self.compute_lines_of_communication(units, side)
        friendly_units = [u for u in units if u['side'] == side]

        connected_ids = set()
        queue = []

        for u in friendly_units:
            if (u['x'], u['y']) in active_loc:
                connected_ids.add(u['id'])
                queue.append(u)

        position_to_unit = {(u['x'], u['y']): u for u in friendly_units}
        while queue:
            current_unit = queue.pop(0)
            cx, cy = current_unit['x'], current_unit['y']
            for dx, dy in self.directions:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in position_to_unit:
                    neighbor = position_to_unit[(nx, ny)]
                    if neighbor['id'] not in connected_ids:
                        connected_ids.add(neighbor['id'])
                        queue.append(neighbor)
        return connected_ids

    # def check_line_of_sight(self, from_x: int, from_y: int, to_x: int, to_y: int, max_range: int,
    #                         units: List[Dict]) -> bool:
    #     dx = to_x - from_x
    #     dy = to_y - from_y
    #
    #     if dx != 0 and dy != 0 and abs(dx) != abs(dy):
    #         return False
    #
    #     steps = max(abs(dx), abs(dy))
    #     if steps > max_range or steps == 0:
    #         return False
    #
    #     step_x = 0 if dx == 0 else dx // abs(dx)
    #     step_y = 0 if dy == 0 else dy // abs(dy)
    #
    #     cx, cy = from_x + step_x, from_y + step_y
    #     for _ in range(steps - 1):
    #         if (cx, cy) in self.mountains:
    #             return False
    #         if any(u['x'] == cx and u['y'] == cy for u in units):
    #             return False
    #         cx += step_x
    #         cy += step_y
    #
    #     return True

    def check_line_of_sight(self, from_x: int, from_y: int, to_x: int, to_y: int, max_range: int,
                            units: List[Dict]) -> bool:
        dx = to_x - from_x
        dy = to_y - from_y

        if dx != 0 and dy != 0 and abs(dx) != abs(dy):
            return False

        steps = max(abs(dx), abs(dy))
        if steps > max_range or steps == 0:
            return False

        step_x = 0 if dx == 0 else dx // abs(dx)
        step_y = 0 if dy == 0 else dy // abs(dy)

        cx, cy = from_x + step_x, from_y + step_y
        for _ in range(steps - 1):
            # Absolute barrier check: Mountains block all combat fire/support lines
            if (cx, cy) in self.mountains:
                return False

            # REMOVED: "if any(u['x'] == cx ...)"
            # Units do not block ballistic lines of fire or communication in the official rules.

            cx += step_x
            cy += step_y

        return True

    def validate_move(self, units: List[Dict], unit_id: str, target_x: int, target_y: int, moved_ids: List[str]) -> \
            Tuple[bool, str]:
        moving_unit = next((u for u in units if u['id'] == unit_id), None)
        if not moving_unit: return False, "Unit missing."
        if unit_id in moved_ids: return False, "This unit has already altered its coordinates this turn."

        connected_units = self.get_connected_units(units, moving_unit['side'])
        if unit_id not in connected_units: return False, "Unit is stranded out of supply and frozen."
        if not (0 <= target_x < self.cols and 0 <= target_y < self.rows): return False, "Out of boundary limits."
        if (target_x, target_y) in self.mountains: return False, "Impassable mountain range."
        if any(u['x'] == target_x and u['y'] == target_y for u in units): return False, "Tile occupied."

        stats = self.get_stats(moving_unit['type'])
        distance = max(abs(target_x - moving_unit['x']), abs(target_y - moving_unit['y']))
        if distance > stats['speed']: return False, "Target exceeds physical unit movement rules."

        return True, "Move approved."

    def calculate_combat(self, units: List[Dict], attacker_side: str, target_x: int, target_y: int) -> Dict:
        target_unit = next((u for u in units if u['x'] == target_x and u['y'] == target_y), None)
        if not target_unit or target_unit['side'] == attacker_side:
            return {"valid": False, "reason": "No valid enemy target located on those coordinates."}

        total_offense = 0
        for u in units:
            if u['side'] == attacker_side:
                stats = self.get_stats(u['type'])
                if self.check_line_of_sight(u['x'], u['y'], target_x, target_y, stats['range'], units):
                    is_adjacent = max(abs(u['x'] - target_x), abs(u['y'] - target_y)) == 1
                    is_fortified = (target_x, target_y) in self.fortresses or (target_x, target_y) in self.passes

                    if "cavalry" in u['type'].lower() and is_adjacent and not is_fortified:
                        total_offense += stats['charge']
                    else:
                        total_offense += stats['offense']

        target_stats = self.get_stats(target_unit['type'])
        total_defense = target_stats['defense']

        if (target_x, target_y) in self.fortresses:
            total_defense += 4
        elif (target_x, target_y) in self.passes:
            total_defense += 2

        for u in units:
            if u['side'] == target_unit['side'] and u['id'] != target_unit['id']:
                stats = self.get_stats(u['type'])
                if self.check_line_of_sight(u['x'], u['y'], target_x, target_y, stats['range'], units):
                    total_defense += stats['defense']

        target_connected = target_unit['id'] in self.get_connected_units(units, target_unit['side'])
        if not target_connected:
            total_defense = max(1, total_defense // 2)

        net_force = total_offense - total_defense

        if net_force >= 2:
            result = "DESTROY"
        elif net_force == 1:
            result = "RETREAT"
        else:
            result = "FAIL"

        return {
            "valid": True, "result": result, "net_force": net_force,
            "offense": total_offense, "defense": total_defense
        }
