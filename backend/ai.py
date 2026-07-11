
# ai.py
import copy
import sys


class WarGameAI:
    def __init__(self, engine, side: str = "South"):
        self.engine = engine
        self.side = side
        self.enemy_side = "North" if side == "South" else "South"

        self.defensive_weight = 0.5
        self._enemy_evaluator = None  # Lazy-init — avoids infinite recursion

        self.unit_values = {
            "artillery": 40,
            "cavalry": 55,
            "relay": 95,
            "infantry": 20,
            "arsenal": 1000
        }
        self.macro_directives = {}
        self.macro_state = "STANDARD"
        self.target_arsenal_coords = None

        # --- NEW DIAGNOSTIC SYSTEM PROPERTIES ---
        self.position_history = {}  # Format: {unit_id: [(x1, y1), (x2, y2), ...]}
        self._distance_cache = {}  # {target_y: {(x, y): distance}}
        self.cluster_turn_cursor = 0

    # def get_path_distance_to_goal(self, x, y, target_y):
    #     """Heuristic: Manhattan distance to the target baseline."""
    #     return abs(target_y - y)

    def _build_distance_map(self, target_y):
        from collections import deque
        dist = {}
        queue = deque()
        for x in range(self.engine.cols):
            if (x, target_y) not in self.engine.mountains:
                dist[(x, target_y)] = 0
                queue.append((x, target_y))
        while queue:
            cx, cy = queue.popleft()
            d = dist[(cx, cy)]
            for dx, dy in self.engine.directions:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.engine.cols and 0 <= ny < self.engine.rows:
                    if (nx, ny) not in self.engine.mountains and (nx, ny) not in dist:
                        dist[(nx, ny)] = d + 1
                        queue.append((nx, ny))
        return dist

    def get_path_distance_to_goal(self, x, y, target_y):
        """Terrain-aware distance to the target baseline, via a precomputed
        static map (mountains never move, so this only needs to be built once
        per target row and reused for the rest of the match)."""
        if target_y not in self._distance_cache:
            self._distance_cache[target_y] = self._build_distance_map(target_y)
        return self._distance_cache[target_y].get((x, y), 30)

    @property
    def enemy_evaluator(self):
        """Lazily constructs a WarGameAI from the enemy's POV for perspective scoring."""
        if self._enemy_evaluator is None:
            self._enemy_evaluator = WarGameAI(self.engine, side=self.enemy_side)
            self._enemy_evaluator.defensive_weight = 0.0
        return self._enemy_evaluator

    def _analyze_theater_clusters(self, units: list) -> dict:
        """Groups units into spatial battalions for macro situational tracking."""
        sides = {"North": [], "South": []}
        for u in units:
            sides[u.get("side")].append(u)

        clusters = {"North": [], "South": []}
        for side in ["North", "South"]:
            unvisited = list(sides[side])
            while unvisited:
                current = unvisited.pop(0)
                cluster = [current]
                added = True
                while added:
                    added = False
                    to_remove = []
                    for cand in unvisited:
                        if any(abs(cand["x"] - c["x"]) + abs(cand["y"] - c["y"]) <= 3 for c in cluster):
                            cluster.append(cand)
                            to_remove.append(cand)
                            added = True
                    # for r in to_remove:
                    #     unvisited.remove(r)
                    unvisited = [cand for cand in unvisited if cand not in to_remove]

                total_strength = sum(self.unit_values.get(u.get("type", "").lower(), 20) for u in cluster)
                cx = sum(u["x"] for u in cluster) / len(cluster)
                cy = sum(u["y"] for u in cluster) / len(cluster)

                clusters[side].append({
                    "units": cluster,
                    "strength": total_strength,
                    "center": (cx, cy)
                })
        return clusters

    def _assign_macro_directives(self, units: list, ai_connected: set, enemy_connected: set):
        """
        DYNAMIC STATE SELECTOR & ARSENAL TARGET EVALUATOR
        Tracks field compositions, handles uncaptured objectives, and triggers
        the sweeping ANNIHILATION_HUNT state when sweeping remaining forces.
        """
        self.macro_directives.clear()
        self.target_arsenal_coords = None

        ai_units = [u for u in units if u.get("side") == self.side]
        enemy_units = [u for u in units if u.get("side") == self.enemy_side]

        ai_count = len(ai_units)
        enemy_count = len(enemy_units)

        if ai_count > enemy_count * 1.2 or enemy_count <= 6:
            self.macro_state = "ANNIHILATION_HUNT"
        elif enemy_count > ai_count * 1.3 and ai_count <= 6:
            self.macro_state = "DESPERATION_CHOKE"
        else:
            self.macro_state = "STANDARD"

        theater = self._analyze_theater_clusters(units)
        enemy_clusters = theater[self.enemy_side]

        open_enemy_arsenals = []
        for ax, ay in self.engine.arsenals[self.enemy_side]:
            is_captured = any(u["x"] == ax and u["y"] == ay and u["side"] == self.side for u in units)
            if not is_captured:
                guard_strength = sum(self.unit_values.get(e["type"].lower(), 20) for e in enemy_units if
                                     abs(e["x"] - ax) + abs(e["y"] - ay) <= 4)
                open_enemy_arsenals.append(((ax, ay), guard_strength))

        if self.macro_state == "DESPERATION_CHOKE" and open_enemy_arsenals:
            open_enemy_arsenals.sort(key=lambda item: item[1])
            self.target_arsenal_coords = open_enemy_arsenals[0][0]

        for unit in units:
            if unit.get("side") != self.side:
                continue

            u_id = unit["id"]
            u_type = unit.get("type", "").lower()
            ux, uy = unit["x"], unit["y"]

            if u_type == "relay":
                self.macro_directives[u_id] = "DYNAMIC_LINK"
                continue

            if self.macro_state == "DESPERATION_CHOKE" and self.target_arsenal_coords:
                self.macro_directives[u_id] = "CHOKE_RUN"
                continue

            if self.macro_state == "ANNIHILATION_HUNT":
                self.macro_directives[u_id] = "HUNTER_SEEKER"
                continue

            heavy_threat_nearby = any(
                ec["strength"] > 120 and (abs(ux - ec["center"][0]) + abs(uy - ec["center"][1]) <= 5) for ec in
                enemy_clusters)
            if heavy_threat_nearby and u_type in ["infantry", "artillery"]:
                self.macro_directives[u_id] = "SHIELD_WALL"
            else:
                self.macro_directives[u_id] = "STANDARD_MARCH"

    def detect_threats(self, units: list) -> float:
        """Tracks direct proximity risks to back-line assets."""
        threat_score = 0.0
        enemy_units = [u for u in units if u.get("side") == self.enemy_side]
        friendly_relays = [u for u in units if u.get("side") == self.side and "relay" in u.get("type", "").lower()]

        for relay in friendly_relays:
            for enemy in enemy_units:
                dist = abs(relay["x"] - enemy["x"]) + abs(relay["y"] - enemy["y"])
                if dist <= 4:
                    threat_score -= (5 - dist) * 180.0

        for ax, ay in self.engine.arsenals[self.side]:
            for enemy in enemy_units:
                dist = abs(enemy["x"] - ax) + abs(enemy["y"] - ay)
                if dist <= 9:
                    threat_score -= (10 - dist) * 130.0

        if friendly_relays:
            connected_now = self.engine.get_connected_units(units, self.side)
            for relay in friendly_relays:
                if relay["id"] not in connected_now:
                    threat_score -= 900.0

        return threat_score

    def _assess_local_threats(self, units, ai_connected):
        """Estimates how exposed each friendly unit is to enemy attack next turn:
        sums enemy offense within move+range reach and compares to the unit's
        effective defense (fortress/pass/support-adjusted). Positive = unit is
        likely to lose a fight if attacked as-is; negative = unit can hold."""
        threats = {}
        enemy_units = [u for u in units if u.get("side") == self.enemy_side]
        ai_units = [u for u in units if u.get("side") == self.side]

        for unit in ai_units:
            u_id = unit["id"]
            ux, uy = unit["x"], unit["y"]
            u_stats = self.engine.get_stats(unit.get("type", ""))
            defense = u_stats["defense"]

            if (ux, uy) in self.engine.fortresses:
                defense += 4
            elif (ux, uy) in self.engine.passes:
                defense += 2

            for a in ai_units:
                if a["id"] == u_id:
                    continue
                a_stats = self.engine.get_stats(a.get("type", ""))
                if self.engine.check_line_of_sight(a["x"], a["y"], ux, uy, a_stats["range"], units):
                    defense += a_stats["defense"]

            if u_id not in ai_connected:
                defense = max(1, defense // 2)

            potential_offense = 0.0
            for enemy in enemy_units:
                e_stats = self.engine.get_stats(enemy.get("type", ""))
                reach = e_stats["speed"] + e_stats["range"]
                dist = abs(enemy["x"] - ux) + abs(enemy["y"] - uy)
                if dist <= reach:
                    is_charge_range = dist <= e_stats["speed"] + 1
                    potential_offense += e_stats.get("charge", e_stats["offense"]) if is_charge_range else e_stats[
                        "offense"]

            threats[u_id] = potential_offense - defense

        return threats

    def _cluster_own_units(self, units):
        """Groups this side's units into spatially local factions so move
        comparisons happen within a faction, not across the whole army."""
        own = [u for u in units if u.get("side") == self.side]
        unvisited = list(own)
        cluster_map = {}
        cid = 0
        while unvisited:
            current = unvisited.pop(0)
            cluster = [current]
            added = True
            while added:
                added = False
                remaining = []
                for cand in unvisited:
                    if any(abs(cand["x"] - c["x"]) + abs(cand["y"] - c["y"]) <= 3 for c in cluster):
                        cluster.append(cand)
                        added = True
                    else:
                        remaining.append(cand)
                unvisited = remaining
            for u in cluster:
                cluster_map[u["id"]] = cid
            cid += 1
        return cluster_map

    def evaluate_board(self, units: list, return_breakdown: bool = False,
                       base_enemy_connected: set = None) -> dict or float:
        base_material = 0.0
        territory_score = 0.0
        role_score = 0.0
        cohesion_score = 0.0
        stacked_attack_pressure = 0.0

        try:
            connected_north = set(self.engine.get_connected_units(units, "North"))
            connected_south = set(self.engine.get_connected_units(units, "South"))
        except Exception:
            connected_north = set()
            connected_south = set()

        ai_connected = connected_south if self.side == "South" else connected_north
        enemy_connected = connected_north if self.side == "South" else connected_south

        target_y = 0 if self.side == "South" else 19
        home_y = 19 if self.side == "South" else 0

        ai_units = [u for u in units if u.get("side") == self.side]
        enemy_units = [u for u in units if u.get("side") == self.enemy_side]

        connected_y_positions = []
        connected_count = 0

        for unit in units:
            u_side = unit.get("side")
            u_type = unit.get("type", "").lower()
            u_id = unit.get("id")
            ux, uy = unit.get("x", 0), unit.get("y", 0)
            is_connected = u_id in (ai_connected if u_side == self.side else enemy_connected)
            base_val = self.unit_values.get(u_type, 20)

            if u_side == self.side:
                base_material += base_val
                if is_connected:
                    connected_count += 1
                    connected_y_positions.append(uy)
                else:
                    cohesion_score -= 15.0
            else:
                base_material -= base_val
                if base_enemy_connected is not None:
                    if (u_id in base_enemy_connected) and not is_connected:
                        territory_score += 200.0
                elif not is_connected:
                    territory_score += 60.0

        territory_score += connected_count * 35.0

        min_global_distance = 99
        for enemy in enemy_units:
            ex, ey = enemy.get("x", 0), enemy.get("y", 0)
            for ally in ai_units:
                ax, ay = ally.get("x", 0), ally.get("y", 0)
                dist = abs(ex - ax) + abs(ey - ay)
                if dist < min_global_distance:
                    min_global_distance = dist

        is_engagement_phase = min_global_distance <= 6
        if is_engagement_phase:
            for enemy in enemy_units:
                ex, ey = enemy.get("x", 0), enemy.get("y", 0)
                converging_friendly_count = 0
                for ally in ai_units:
                    ax, ay = ally.get("x", 0), ally.get("y", 0)
                    if abs(ex - ax) + abs(ey - ay) <= (4 if ally.get("type", "").lower() == "cavalry" else 3):
                        converging_friendly_count += 1
                if converging_friendly_count == 1:
                    stacked_attack_pressure += 10.0
                elif converging_friendly_count == 2:
                    stacked_attack_pressure += 40.0
                elif converging_friendly_count >= 3:
                    stacked_attack_pressure += 80.0

        all_enemy_positions = [(e.get("x", 0), e.get("y", 0)) for e in enemy_units]

        local_threats = self._assess_local_threats(units, ai_connected)
        threatened_units = {uid: val for uid, val in local_threats.items() if val > 0}

        captured_enemy_arsenals = []
        uncaptured_enemy_arsenals = []
        for ax, ay in self.engine.arsenals[self.enemy_side]:
            if any(u["x"] == ax and u["y"] == ay and u["side"] == self.side for u in units):
                captured_enemy_arsenals.append((ax, ay))
            else:
                uncaptured_enemy_arsenals.append((ax, ay))

        for unit in ai_units:
            u_id = unit.get("id")
            u_type = unit.get("type", "").lower()
            ux, uy = unit.get("x", 0), unit.get("y", 0)
            is_connected = u_id in ai_connected
            directive = self.macro_directives.get(u_id, "STANDARD_MARCH")

            # --- REINFORCEMENT: reward standing adjacent to a threatened ally ---
            if threatened_units:
                for t_id, severity in threatened_units.items():
                    if t_id == u_id:
                        continue
                    ally = next((a for a in ai_units if a["id"] == t_id), None)
                    if ally and abs(ux - ally["x"]) + abs(uy - ally["y"]) == 1:
                        role_score += min(severity, 15) * 25.0

            # --- SELF-PRESERVATION: if this unit itself is exposed, favor
            # positions that add friendly support rather than isolation ---
            if u_id in threatened_units:
                nearby_allies = sum(1 for a in ai_units if a["id"] != u_id and
                                    abs(ux - a["x"]) + abs(uy - a["y"]) <= 1)
                role_score += nearby_allies * 60.0
                role_score -= min(threatened_units[u_id], 20) * 20.0

            if u_type == "relay":
                combat_allies = [a for a in ai_units if "relay" not in a.get("type", "").lower()]
                if combat_allies:
                    avg_ax = sum(a["x"] for a in combat_allies) / len(combat_allies)
                    avg_ay = sum(a["y"] for a in combat_allies) / len(combat_allies)
                    role_score += (45 - (abs(ux - avg_ax) + abs(uy - avg_ay))) * 160.0

                if uncaptured_enemy_arsenals:
                    min_dist_a = min(abs(ux - ax) + abs(uy - ay) for ax, ay in uncaptured_enemy_arsenals)
                    role_score += (45 - min_dist_a) * 90.0
                elif all_enemy_positions:
                    min_dist_e = min(abs(ux - ex) + abs(uy - ey) for ex, ey in all_enemy_positions)
                    role_score += (45 - min_dist_e) * 90.0

                if is_connected: role_score += 100.0
                continue

            if uncaptured_enemy_arsenals:
                min_dist_to_uncaptured = min(abs(ux - ax) + abs(uy - ay) for ax, ay in uncaptured_enemy_arsenals)
                role_score += (45 - min_dist_to_uncaptured) * 250.0

            for ax, ay in captured_enemy_arsenals:
                if ux == ax and uy == ay:
                    has_nearby_threat = any(abs(ex - ax) + abs(ey - ay) <= 5 for ex, ey in all_enemy_positions)
                    if has_nearby_threat:
                        role_score += 700.0
                    else:
                        role_score += 250.0

            for enemy in enemy_units:
                ex, ey = enemy.get("x", 0), enemy.get("y", 0)
                e_id = enemy.get("id")
                is_deactivated = e_id not in enemy_connected
                dist_to_enemy = abs(ux - ex) + abs(uy - ey)

                if is_deactivated:
                    role_score += (45 - dist_to_enemy) * 350.0
                else:
                    role_score += (45 - dist_to_enemy) * 150.0

                if dist_to_enemy == 1:
                    role_score += 800.0

            if self.macro_state == "DESPERATION_CHOKE" and self.target_arsenal_coords:
                dist_to_target = abs(ux - self.target_arsenal_coords[0]) + abs(uy - self.target_arsenal_coords[1])
                role_score += (45 - dist_to_target) * 400.0

            if directive == "SHIELD_WALL":
                neighbor_allies = sum(1 for a in ai_units if abs(ux - a["x"]) + abs(uy - a["y"]) == 1)
                role_score += neighbor_allies * 120.0

            dist_to_goal = self.get_path_distance_to_goal(ux, uy, target_y)
            role_score += (20 - dist_to_goal) * 10.0
            if is_connected: role_score += 50.0

        if connected_y_positions and self.macro_state == "STANDARD":
            avg_y = sum(connected_y_positions) / len(connected_y_positions)
            cohesion_score += abs(home_y - avg_y) * 45.0

        if self.macro_state == "ANNIHILATION_HUNT":
            cohesion_score *= 0.1

        threat_score = self.detect_threats(
            units) if self._enemy_evaluator is not None or self.defensive_weight > 0 else 0.0

        total_score = base_material + territory_score + role_score + cohesion_score + stacked_attack_pressure + threat_score

        if return_breakdown:
            return {
                "TOTAL": total_score,
                "Material": base_material,
                "Territory": territory_score,
                "Role_Exec": role_score,
                "Cohesion": cohesion_score,
                "Attack_Press": stacked_attack_pressure,
                "Threat_Def": threat_score
            }
        return total_score

    # --- NEW ANOMALY DETECTION ENGINE ENGINE ---
    def _detect_behavioral_anomaly(self, uid: int) -> str or None:
        """Analyzes spatial updates over turns to isolate loops and deadlocks."""
        history = self.position_history.get(uid, [])
        if len(history) < 4:
            return None

        # 1. Stasis Detection (Unit has stood completely still over 3 full engine turns)
        if len(set(history[-3:])) == 1:
            return "STASIS_FREEZE"

        # 2. 2-Step Oscillation Check (A -> B -> A -> B)
        if history[-4] == history[-2] and history[-3] == history[-1] and history[-4] != history[-3]:
            return "2_STEP_OSCILLATION"

        # 3. 3-Step Oscillation Check (A -> B -> C -> A -> B -> C)
        if len(history) >= 6:
            if history[-6] == history[-3] and history[-5] == history[-2] and history[-4] == history[-1]:
                return "3_STEP_OSCILLATION"

        return None

    def get_all_legal_moves(self, units: list, moved_this_turn: list) -> list:
        legal_actions = []
        ai_units = [u for u in units if u.get("side") == self.side]
        for unit in ai_units:
            if unit["id"] in moved_this_turn:
                continue
            for target in units:
                if target.get("side") == self.enemy_side:
                    combat = self.engine.calculate_combat(units, self.side, target["x"], target["y"])
                    if combat.get("valid"):
                        legal_actions.append(
                            {"action_type": "attack", "unitId": unit["id"], "x": target["x"], "y": target["y"]})
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    tx, ty = unit["x"] + dx, unit["y"] + dy
                    if 0 <= tx < 25 and 0 <= ty < 20:
                        is_valid, _ = self.engine.validate_move(units, unit["id"], tx, ty, moved_this_turn)
                        if is_valid:
                            legal_actions.append({"action_type": "move", "unitId": unit["id"], "x": tx, "y": ty})
        return legal_actions

    def calculate_cohesion_loss(self, units, unit_id, target_x, target_y):
        ghost = copy.deepcopy(units)
        u = next((unit for unit in ghost if unit['id'] == unit_id), None)
        if not u: return 0
        u['x'], u['y'] = target_x, target_y
        before = self.engine.get_connected_units(units, self.side)
        after = self.engine.get_connected_units(ghost, self.side)
        return len(before - after)

    def select_best_action(self, current_state: dict) -> dict:
        units = current_state["units"]
        moved_this_turn = current_state["moved_units_this_turn"]
        attack_executed = current_state["attack_executed_this_turn"]

        try:
            start_north = set(self.engine.get_connected_units(units, "North"))
            start_south = set(self.engine.get_connected_units(units, "South"))
        except:
            start_north = start_south = set()
        base_enemy_connected = start_north if self.side == "South" else start_south
        base_my_connected = start_south if self.side == "South" else start_north

        # ─── ADD THIS LINE TO FIX THE NAMEERROR ───────────────────────────
        target_y = 0 if self.side == "South" else 19
        # ──────────────────────────────────────────────────────────────────

        # --- UPDATE TEMPORAL TRACKER KEYS ---
        for u in units:
            if u.get("side") == self.side:
                uid = u["id"]
                if uid not in self.position_history:
                    self.position_history[uid] = []
                self.position_history[uid].append((u["x"], u["y"]))
                if len(self.position_history[uid]) > 8:
                    self.position_history[uid].pop(0)

        self._assign_macro_directives(units, base_my_connected, base_enemy_connected)

        current_my_score = self.evaluate_board(units, base_enemy_connected=base_enemy_connected)
        if self.defensive_weight > 0:
            current_enemy_score = self.enemy_evaluator.evaluate_board(units, base_enemy_connected=base_my_connected)
            baseline_score = current_my_score - self.defensive_weight * current_enemy_score
        else:
            baseline_score = current_my_score

        if self.macro_state in ["ANNIHILATION_HUNT", "DESPERATION_CHOKE"]:
            best_score = float('-inf')
            best_action = None
        else:
            best_score = baseline_score
            best_action = {"action_type": "end_turn"}

        actions = self.get_all_legal_moves(units, moved_this_turn)
        if not actions:
            return {"action_type": "end_turn"}

        unit_to_cluster = self._cluster_own_units(units)
        actions_by_cluster = {}
        for action in actions:
            cid = unit_to_cluster.get(action["unitId"], -1)
            actions_by_cluster.setdefault(cid, []).append(action)

        cluster_ids = sorted(actions_by_cluster.keys())
        start = self.cluster_turn_cursor % len(cluster_ids)
        ordered_clusters = cluster_ids[start:] + cluster_ids[:start]

        diagnostic_log = {}
        chosen_cluster = ordered_clusters[0]
        actions = actions_by_cluster[chosen_cluster]
        self.cluster_turn_cursor = (self.cluster_turn_cursor + 1) % len(cluster_ids)

        for action in actions:
            temp = copy.deepcopy(units)
            mod = 0.0
            act_uid = action.get("unitId")

            # if action["action_type"] == "attack":
            #     if attack_executed: continue
            #     combat = self.engine.calculate_combat(temp, self.side, action["x"], action["y"])
            #     if combat.get("valid"):
            #         if combat["result"] == "DESTROY":
            #             return action
            #         elif combat["result"] == "RETREAT":
            #             mod += 500.0
            #         target_connected = self.engine.get_connected_units(temp, self.enemy_side)
            #         target_unit = next((u for u in temp if u["x"] == action["x"] and u["y"] == action["y"]), None)
            #         if target_unit and target_unit["id"] not in target_connected:
            #             mod += 800.0

            if action["action_type"] == "attack":
                if attack_executed: continue
                combat = self.engine.calculate_combat(temp, self.side, action["x"], action["y"])
                if combat.get("valid"):
                    if combat["result"] == "DESTROY":
                        mod += 10000.0 + combat["net_force"] * 100.0
                        # Simulate the kill so evaluate_board reflects the
                        # actual post-attack board, not a no-op.
                        temp = [u for u in temp if not (u["x"] == action["x"] and u["y"] == action["y"])]
                    elif combat["result"] == "RETREAT":
                        mod += 300.0 + combat["net_force"] * 100.0
                        target_connected = self.engine.get_connected_units(temp, self.enemy_side)
                        target_unit = next((u for u in temp if u["x"] == action["x"] and u["y"] == action["y"]), None)
                        if target_unit and target_unit["id"] not in target_connected:
                            mod += 800.0
                    else:
                        # FAIL: wastes the turn's one attack action for
                        # nothing — actively discourage it so the AI
                        # only attacks when it expects a real result.
                        mod -= 2000.0

            elif action["action_type"] == "move":
                if (action["x"], action["y"]) in self.engine.arsenals[self.enemy_side]:
                    mod += 5000.0

                for u in temp:
                    if u.get("id") == act_uid:
                        u["x"], u["y"] = action["x"], action["y"]

                try:
                    enemy_connected_after = self.engine.get_connected_units(temp, self.enemy_side)
                    if len(enemy_connected_after) < len(base_enemy_connected):
                        mod += 1500.0
                except:
                    pass

                lost = self.calculate_cohesion_loss(units, act_uid, action["x"], action["y"])
                if lost > 0:
                    cohesion_factor = 30.0 if self.macro_state == "ANNIHILATION_HUNT" else (
                        600.0 if len(units) > 10 else 100.0)

                    if self.macro_state == "ANNIHILATION_HUNT":
                        cohesion_factor = 0.0

                    mod -= (lost * cohesion_factor)

                # unit = next(u for u in units if u['id'] == act_uid)
                unit = next((u for u in units if u['id'] == act_uid), None)
                if not unit:
                    continue
                dist_moved = abs(unit['x'] - action['x']) + abs(unit['y'] - action['y'])
                if dist_moved <= 1:
                    mod += 0.0 if self.macro_state in ["ANNIHILATION_HUNT", "DESPERATION_CHOKE"] else 15.0

            # --- BREAKDOWN INTERCEPTION PIPELINE ---
            # my_breakdown = self.evaluate_board(temp, return_breakdown=True, base_enemy_connected=base_enemy_connected)
            # if self.defensive_weight > 0:
            #     enemy_score = self.enemy_evaluator.evaluate_board(temp, base_enemy_connected=base_my_connected)
            #     score = (my_breakdown["TOTAL"] - self.defensive_weight * enemy_score) + mod
            # else:
            #     score = my_breakdown["TOTAL"] + mod

            my_breakdown = self.evaluate_board(temp, return_breakdown=True, base_enemy_connected=base_enemy_connected)

            # If the base structural move already results in severe regression, skip calculating enemy POV entirely
            if my_breakdown["TOTAL"] + mod < best_score - 500.0:
                continue

            if self.defensive_weight > 0:
                enemy_score = self.enemy_evaluator.evaluate_board(temp, base_enemy_connected=base_my_connected)
                score = (my_breakdown["TOTAL"] - self.defensive_weight * enemy_score) + mod
            else:
                score = my_breakdown["TOTAL"] + mod

            # Capture data context if unit belongs to an active anomaly detection flag
            anomaly_type = self._detect_behavioral_anomaly(act_uid) if act_uid else None
            if anomaly_type:
                if act_uid not in diagnostic_log:
                    diagnostic_log[act_uid] = {"anomaly": anomaly_type, "choices": []}
                diagnostic_log[act_uid]["choices"].append({
                    "action": action,
                    "score": score,
                    "mod_applied": mod,
                    "breakdown": my_breakdown
                })

            if score > best_score:
                best_score = score
                best_action = action

        # --- RUN CONSOLE PRINT INTERCEPT FOR DETECTED ANOMALIES ---
        for uid, data in diagnostic_log.items():
            ref_unit = next(u for u in units if u["id"] == uid)
            print("\n" + "=" * 80, file=sys.stderr)
            print(
                f"⚠️ DIAGNOSTIC ALERT: Unit ID {uid} [{ref_unit['type'].upper()}] at ({ref_unit['x']}, {ref_unit['y']}) is in state: {data['anomaly']}",
                file=sys.stderr)
            print(f"Macro Strategy Context: {self.macro_state}", file=sys.stderr)
            print(f"Historical Positions Tracking Queue: {self.position_history[uid]}", file=sys.stderr)
            print("-" * 80, file=sys.stderr)
            print(
                f"{'PROPOSED TARGET':<18} | {'FINAL SCORE':<12} | {'ROLE EVAL':<10} | {'COHESION':<10} | {'THREATS':<10} | {'MODIFIER':<10}",
                file=sys.stderr)
            print("-" * 80, file=sys.stderr)

            # Sort choices by score descending to see what won versus what lost
            sorted_choices = sorted(data["choices"], key=lambda c: c["score"], reverse=True)
            for choice in sorted_choices:
                act = choice["action"]
                bd = choice["breakdown"]
                tgt = f"{act['action_type'].upper()} -> ({act['x']}, {act['y']})" if act[
                                                                                         'action_type'] != 'end_turn' else "END_TURN"
                print(
                    f"{tgt:<18} | {choice['score']:<12.1f} | {bd['Role_Exec']:<10.1f} | {bd['Cohesion']:<10.1f} | {bd['Threat_Def']:<10.1f} | {choice['mod_applied']:<10.1f}",
                    file=sys.stderr)

            # Print a quick summary of the root cause
            if len(sorted_choices) >= 2:
                top_choice = sorted_choices[0]
                # Look for a choice that moves closer to enemy forces/arsenals
                forward_choices = [c for c in sorted_choices if c['action']['action_type'] == 'move' and
                                   abs(c['action']['y'] - target_y) < abs(ref_unit['y'] - target_y)]

                if forward_choices and top_choice != forward_choices[0]:
                    f_choice = forward_choices[0]
                    print("\n💡 ROOT CAUSE ANALYSIS:", file=sys.stderr)
                    role_delta = f_choice['breakdown']['Role_Exec'] - top_choice['breakdown']['Role_Exec']
                    coh_delta = f_choice['breakdown']['Cohesion'] - top_choice['breakdown']['Cohesion']
                    loss_delta = f_choice['mod_applied'] - top_choice['mod_applied']

                    print(
                        f"   • Forward movement was rejected in favor of {top_choice['action']['action_type'].upper()}.",
                        file=sys.stderr)
                    if coh_delta < 0:
                        print(
                            f"   • Cohesion Deficit: Moving forward would drop Cohesion score by {abs(coh_delta):.1f} points.",
                            file=sys.stderr)
                    if role_delta < 0:
                        print(
                            f"   • Role Penalty: Moving forward would lose out on {abs(role_delta):.1f} objective value points.",
                            file=sys.stderr)
                    if loss_delta < 0:
                        print(
                            f"   • Structural Loss: Move broke lines, triggering a penalty of {abs(loss_delta):.1f} points.",
                            file=sys.stderr)
            print("=" * 80 + "\n", file=sys.stderr)

        return best_action if best_action else {"action_type": "end_turn"}
