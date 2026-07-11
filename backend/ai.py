
# ai.py
import copy


class WarGameAI:
    def __init__(self, engine, side: str = "South"):
        self.engine = engine
        self.side = side
        self.enemy_side = "North" if side == "South" else "South"

        # Option B: Controls how much we subtract the enemy's perspective score.
        # 0.0 = pure offence (ignore what enemy wants), 1.0 = play purely to deny enemy goals.
        self.defensive_weight = 0.5
        self._enemy_evaluator = None  # Lazy-init — avoids infinite recursion at construction

        self.unit_values = {
            "artillery": 40,
            "cavalry": 55,
            "relay": 95,
            "infantry": 20,
            "arsenal": 1000
        }

    def get_path_distance_to_goal(self, x, y, target_y):
        """Heuristic: Manhattan distance to the target baseline."""
        return abs(target_y - y)

    @property
    def enemy_evaluator(self):
        """Option B — Lazily constructs a WarGameAI from the enemy's POV for perspective scoring."""
        if self._enemy_evaluator is None:
            self._enemy_evaluator = WarGameAI(self.engine, side=self.enemy_side)
            self._enemy_evaluator.defensive_weight = 0.0  # Enemy evaluator should not recurse
        return self._enemy_evaluator

    def detect_threats(self, units: list) -> float:
        """
        Option C — Explicit threat detection.
        Scans the board for dangerous enemy positions and returns a negative penalty score.
        This runs on the SIMULATED board after a candidate move, so moves that eliminate
        threats naturally score higher than moves that leave threats in place.
        """
        threat_score = 0.0
        enemy_units = [u for u in units if u.get("side") == self.enemy_side]

        # --- Threat 1: Enemy near our Relay units ---
        # Relays are the nervous system. An enemy within 4 tiles is an active danger.
        friendly_relays = [
            u for u in units
            if u.get("side") == self.side and "relay" in u.get("type", "").lower()
        ]
        for relay in friendly_relays:
            for enemy in enemy_units:
                dist = abs(relay["x"] - enemy["x"]) + abs(relay["y"] - enemy["y"])
                if dist <= 4:
                    # Exponential danger — being 1 tile away is far worse than 4
                    threat_score -= (5 - dist) * 180.0

        # --- Threat 2: Enemy closing on our home arsenals ---
        # An enemy near the arsenal is an existential threat.
        for ax, ay in self.engine.arsenals[self.side]:
            for enemy in enemy_units:
                dist = abs(enemy["x"] - ax) + abs(enemy["y"] - ay)
                if dist <= 9:
                    threat_score -= (10 - dist) * 130.0

        # --- Threat 3: Any friendly Relay that is ALREADY cut off ---
        # A severed relay is a strategic catastrophe — scream loudly about it.
        if friendly_relays:
            connected_now = self.engine.get_connected_units(units, self.side)
            for relay in friendly_relays:
                if relay["id"] not in connected_now:
                    threat_score -= 900.0  # Red alarm: relay is dark

        return threat_score

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

        ai_coords = []
        connected_y_positions = []
        relay_positions = []
        connected_count = 0

        # Phase 1: Material and Geography
        for unit in units:
            u_side = unit.get("side")
            u_type = unit.get("type", "").lower()
            u_id = unit.get("id")
            ux, uy = unit.get("x", 0), unit.get("y", 0)
            is_connected = u_id in (ai_connected if u_side == self.side else enemy_connected)
            base_val = self.unit_values.get(u_type, 20)

            if u_side == self.side:
                base_material += base_val
                ai_coords.append((ux, uy))
                if is_connected:
                    connected_count += 1
                    connected_y_positions.append(uy)
                    if u_type == "relay":
                        relay_positions.append((ux, uy))
                else:
                    cohesion_score -= 15.0
            else:
                base_material -= base_val
                if base_enemy_connected is not None:
                    was_connected_at_start = u_id in base_enemy_connected
                    if was_connected_at_start and not is_connected:
                        territory_score += 200.0
                elif not is_connected:
                    territory_score += 60.0

        territory_score += connected_count * 35.0

        # Phase 2: Engagement Proximity
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
                    a_type = ally.get("type", "").lower()
                    manhattan_dist = abs(ex - ax) + abs(ey - ay)
                    max_prep = 4 if a_type == "cavalry" else 3
                    if manhattan_dist <= max_prep:
                        converging_friendly_count += 1
                if converging_friendly_count == 1:
                    stacked_attack_pressure += 10.0
                elif converging_friendly_count == 2:
                    stacked_attack_pressure += 40.0
                elif converging_friendly_count >= 3:
                    stacked_attack_pressure += 80.0

        # Phase 3: Role-Specific Performance & Pathfinding
        # Phase 3: Role-Specific Performance & Pathfinding
        isolated_enemies = [(e.get("x", 0), e.get("y", 0)) for e in enemy_units if
                                e.get("id") not in enemy_connected]

        for unit in ai_units:
            u_type = unit.get("type", "").lower()
            ux, uy = unit.get("x", 0), unit.get("y", 0)
            u_id = unit.get("id")
            is_connected = u_id in ai_connected

            # 1. Pathfinding to baseline
            dist_to_goal = self.get_path_distance_to_goal(ux, uy, target_y)
            role_score += (20 - dist_to_goal) * 20.0
            if is_connected: role_score += 50.0

            # 2. Arsenal Capture Incentive (Annihilation Logic)
            for ax, ay in self.engine.arsenals[self.enemy_side]:
                dist_to_arsenal = abs(ux - ax) + abs(uy - ay)
                if dist_to_arsenal < 8:
                    role_score += (10 - dist_to_arsenal) * 100.0

            # 3. Aggressive Hunting (Using the isolated_enemies variable)
            if isolated_enemies:
                min_dist_to_iso = min([abs(ux - ex) + abs(uy - ey) for ex, ey in isolated_enemies])
                # The closer we are to a stranded enemy, the higher the score
                if min_dist_to_iso <= 5:
                    role_score += (10 - min_dist_to_iso) * 50.0

            # 4. Relay Coverage Expansion
            if u_type == "relay" and is_connected:
                coverage_gain = 0
                for dx, dy in self.engine.directions:
                    tx, ty = ux + dx, uy + dy
                    if 0 <= tx < self.engine.cols and 0 <= ty < self.engine.rows:
                        if (tx, ty) not in self.engine.mountains: coverage_gain += 1
                role_score += (coverage_gain * 25.0)

        # Phase 4: Cohesion
        if connected_y_positions:
            avg_y = sum(connected_y_positions) / len(connected_y_positions)
            cohesion_score += abs(home_y - avg_y) * 45.0

        # Phase 5: Explicit Threat Detection (Option C)
        # Only run threat detection on the primary evaluator — not when the enemy_evaluator
        # calls this recursively, to avoid infinite loops and double-counting.
        threat_score = self.detect_threats(units) if self._enemy_evaluator is not None or self.defensive_weight > 0 else 0.0

        total_score = base_material + territory_score + role_score + cohesion_score + stacked_attack_pressure + threat_score

        if return_breakdown:
            return {
                "TOTAL": total_score,
                "Macro State": "ENGAGEMENT COMBAT" if is_engagement_phase else "MANEUVER / MARCH",
                "Material Balance": base_material,
                "Territory/LOC Size": territory_score,
                "Role Execution Performance": role_score,
                "Swarm Cohesion & Spacing": cohesion_score,
                "Stacked Attack Pressure": stacked_attack_pressure,
                "Threat Defence Score": threat_score
            }
        return total_score

    def get_all_legal_moves(self, units: list, moved_this_turn: list) -> list:
        legal_actions = []
        ai_units = [u for u in units if u.get("side") == self.side]
        for unit in ai_units:
            for target in units:
                if target.get("side") == self.enemy_side:
                    combat = self.engine.calculate_combat(units, self.side, target["x"], target["y"])
                    if combat.get("valid"):
                        legal_actions.append({"action_type": "attack", "x": target["x"], "y": target["y"]})
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
        u = next(unit for unit in ghost if unit['id'] == unit_id)
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
        # base_my_connected is passed to the enemy evaluator so it knows which of OUR units
        # were connected at the start of the turn (its 'base_enemy_connected').
        base_my_connected = start_south if self.side == "South" else start_north

        actions = self.get_all_legal_moves(units, moved_this_turn)
        if not actions: return {"action_type": "end_turn"}

        best_action, best_score = None, float('-inf')

        for action in actions:
            temp = copy.deepcopy(units)
            mod = 0.0

            # --- 1. KILL OVERRIDE: Prioritize destruction above all ---
            if action["action_type"] == "attack":
                if attack_executed: continue
                combat = self.engine.calculate_combat(temp, self.side, action["x"], action["y"])
                if combat.get("valid"):
                    if combat["result"] == "DESTROY":
                        return action  # IMMEDIATELY execute any action that results in a kill
                    elif combat["result"] == "RETREAT":
                        mod += 500.0

                    # --- FINISH THEM: Heavy bonus for attacking cut-off (isolated) enemies ---
                    # Even a failed attack on an isolated unit is strategically correct —
                    # it weakens them further and prevents regrouping.
                    target_connected = self.engine.get_connected_units(temp, self.enemy_side)
                    target_unit = next(
                        (u for u in temp if u["x"] == action["x"] and u["y"] == action["y"]), None
                    )
                    if target_unit and target_unit["id"] not in target_connected:
                        mod += 800.0  # Aggressively pursue stragglers

            elif action["action_type"] == "move":
                # Check for cohesion loss
                lost = self.calculate_cohesion_loss(units, action["unitId"], action["x"], action["y"])
                if lost > 0: mod -= (lost * 600.0)

                # --- 2. STABILITY BONUS: Prevents Relay Oscillation ---
                unit = next(u for u in units if u['id'] == action["unitId"])
                dist_moved = abs(unit['x'] - action['x']) + abs(unit['y'] - action['y'])
                if dist_moved <= 1:
                    mod += 10.0

                for u in temp:
                    if u.get("id") == action["unitId"]: u["x"], u["y"] = action["x"], action["y"]

            # --- 3. PRIMARY SCORE: How good is this position for us? ---
            my_score = self.evaluate_board(temp, base_enemy_connected=base_enemy_connected)

            # --- Option B: PERSPECTIVE SCORING ---
            # Also evaluate how good this SAME board state is for the enemy.
            # A great move isn't just one that helps us — it's one that also denies the enemy their goals.
            # We subtract a fraction (defensive_weight) of the enemy's score from ours.
            # This makes the AI naturally block, protect, and counter-position.
            if self.defensive_weight > 0:
                enemy_score = self.enemy_evaluator.evaluate_board(
                    temp, base_enemy_connected=base_my_connected
                )
                score = (my_score - self.defensive_weight * enemy_score) + mod
            else:
                score = my_score + mod

            if score > best_score:
                best_score = score
                best_action = action

        return best_action if best_action else {"action_type": "end_turn"}
