
# # ai.py
# import copy
#
#
# class WarGameAI:
#     def __init__(self, engine, side: str = "South"):
#         self.engine = engine
#         self.side = side
#         self.enemy_side = "North" if side == "South" else "South"
#
#         # Structural assets values
#         self.unit_values = {
#             "artillery": 40,
#             "cavalry": 25,
#             "relay": 50,  # High strategic value
#             "infantry": 20,
#             "arsenal": 1000
#         }
#
#     def evaluate_board(self, units: list, return_breakdown: bool = False) -> dict or float:
#         # Component tracking initialization
#         base_material = 0.0
#         territory_score = 0.0
#         role_score = 0.0
#         cohesion_score = 0.0
#
#         try:
#             connected_north = set(self.engine.get_connected_units(units, "North"))
#             connected_south = set(self.engine.get_connected_units(units, "South"))
#         except Exception:
#             connected_north = set()
#             connected_south = set()
#
#         ai_connected = connected_south if self.side == "South" else connected_north
#         enemy_connected = connected_north if self.side == "South" else connected_south
#
#         target_y = 0 if self.side == "South" else 19
#         home_y = 19 if self.side == "South" else 0
#
#         ai_coords = []
#         connected_y_positions = []
#         relay_positions = []
#         connected_count = 0
#
#         # Phase 1: Material and Basic Geography
#         for unit in units:
#             u_side = unit.get("side")
#             u_type = unit.get("type", "").lower()
#             u_id = unit.get("id")
#             ux, uy = unit.get("x", 0), unit.get("y", 0)
#             is_connected = u_id in (ai_connected if u_side == self.side else enemy_connected)
#             base_val = self.unit_values.get(u_type, 20)
#
#             if u_side == self.side:
#                 base_material += base_val
#                 ai_coords.append((ux, uy))
#
#                 if is_connected:
#                     connected_count += 1
#                     connected_y_positions.append(uy)
#                     if u_type == "relay":
#                         relay_positions.append((ux, uy))
#                 else:
#                     # Isolated units severely penalize the operational state
#                     cohesion_score -= 100.0
#             else:
#                 base_material -= base_val
#                 if not is_connected:
#                     territory_score += 50.0  # Strategic value for cutting enemy network
#
#         # Phase 2: Territory Generation Metric (The Core Network Goal)
#         # The AI is heavily rewarded for expanding the total headcount of safely supplied pieces.
#         territory_score += connected_count * 40.0
#
#         # Phase 3: Role-Specific Performance Calculations
#         for unit in [u for u in units if u.get("side") == self.side]:
#             u_type = unit.get("type", "").lower()
#             ux, uy = unit.get("x", 0), unit.get("y", 0)
#             u_id = unit.get("id")
#             is_connected = u_id in ai_connected
#             y_dist = abs(uy - target_y)
#
#             # --- THE RELAY ARCHITECT ---
#             if u_type == "relay":
#                 if is_connected:
#                     # Relays want to advance to push the network depth, but care most about coverage breadth
#                     role_score += (20 - y_dist) * 15.0
#
#                     # Security Check: Relays need combat units nearby. Penalize if totally isolated out front.
#                     min_guard_dist = min([abs(ux - cx) + abs(uy - cy) for cx, cy in ai_coords if (cx, cy) != (ux, uy)],
#                                          default=99)
#                     if min_guard_dist > 3:
#                         role_score -= 50.0  # Vulnerability penalty
#                 else:
#                     role_score -= 200.0  # An offline relay is catastrophic
#
#             # --- THE INFANTRY / ARTILLERY PHALANX ---
#             elif u_type in ["infantry", "artillery"]:
#                 if is_connected:
#                     # Natural pressure to march forward inside the network
#                     role_score += (20 - y_dist) * 5.0
#
#                     # Escort Duty: Reward them for staying relatively close to active relays to screen them
#                     if relay_positions:
#                         min_relay_dist = min([abs(ux - rx) + abs(uy - ry) for rx, ry in relay_positions])
#                         if min_relay_dist <= 2:
#                             role_score += 25.0  # Screen asset bonus
#
#             # --- THE CAVALRY STRIKER ---
#             elif u_type == "cavalry":
#                 if is_connected:
#                     # High progressive forward intent
#                     role_score += (20 - y_dist) * 12.0
#                 else:
#                     role_score -= 150.0  # Massive penalty if it over-extends out of the network zone
#
#         # Phase 4: Swarm Cohesion and Formation
#         if connected_y_positions:
#             avg_y = sum(connected_y_positions) / len(connected_y_positions)
#             cohesion_score += abs(home_y - avg_y) * 30.0  # Pulls the whole army mass forward
#
#             # Keep the operational line from over-stretching
#             span = max(connected_y_positions) - min(connected_y_positions)
#             if span > 4:
#                 cohesion_score -= (span - 4) * 25.0
#
#         # Combat Line Anti-Congestion Mesh
#         for i in range(len(ai_coords)):
#             for j in range(i + 1, len(ai_coords)):
#                 dist = abs(ai_coords[i][0] - ai_coords[j][0]) + abs(ai_coords[i][1] - ai_coords[j][1])
#                 if dist <= 1:
#                     cohesion_score -= 20.0  # Anti-clumping
#                 elif dist == 2:
#                     cohesion_score += 12.0  # Beautiful phalanx grid alignment reward
#
#         total_score = base_material + territory_score + role_score + cohesion_score
#
#         if return_breakdown:
#             return {
#                 "TOTAL": total_score,
#                 "Material Balance": base_material,
#                 "Territory/LOC Size": territory_score,
#                 "Role Execution Performance": role_score,
#                 "Swarm Cohesion & Spacing": cohesion_score
#             }
#
#         return total_score
#
#     def get_all_legal_moves(self, units: list, moved_this_turn: list) -> list:
#         legal_actions = []
#         ai_units = [u for u in units if u.get("side") == self.side]
#
#         for unit in ai_units:
#             for target in units:
#                 if target.get("side") == self.enemy_side:
#                     combat_check = self.engine.calculate_combat(units, self.side, target["x"], target["y"])
#                     if combat_check.get("valid"):
#                         legal_actions.append({
#                             "action_type": "attack",
#                             "x": target["x"],
#                             "y": target["y"]
#                         })
#
#             for dx in range(-3, 4):
#                 for dy in range(-3, 4):
#                     tx, ty = unit["x"] + dx, unit["y"] + dy
#                     if 0 <= tx < 25 and 0 <= ty < 20:
#                         is_valid, _ = self.engine.validate_move(units, unit["id"], tx, ty, moved_this_turn)
#                         if is_valid:
#                             legal_actions.append({
#                                 "action_type": "move",
#                                 "unitId": unit["id"],
#                                 "x": tx,
#                                 "y": ty
#                             })
#         return legal_actions
#
#     def select_best_action(self, current_state: dict) -> dict:
#         units = current_state["units"]
#         moved_this_turn = current_state["moved_units_this_turn"]
#         attack_executed = current_state["attack_executed_this_turn"]
#
#         print("\n=== 🤖 AI DECISION CYCLE START ===")
#         actions = self.get_all_legal_moves(units, moved_this_turn)
#         print(f"🤖 AI DEBUG: Total raw legal actions generated: {len(actions)}")
#
#         if not actions:
#             print("=== 🤖 AI DECISION CYCLE END ===\n")
#             return {"action_type": "end_turn"}
#
#         best_action = None
#         best_score = float('-inf')
#
#         for action in actions:
#             if action["action_type"] == "attack" and attack_executed:
#                 continue
#
#             temp_units = copy.deepcopy(units)
#             if action["action_type"] == "move":
#                 for u in temp_units:
#                     if u.get("id") == action["unitId"]:
#                         u["x"], u["y"] = action["x"], action["y"]
#             elif action["action_type"] == "attack":
#                 combat = self.engine.calculate_combat(temp_units, self.side, action["x"], action["y"])
#                 if combat.get("valid") and combat.get("result") == "DESTROY":
#                     temp_units = [u for u in temp_units if not (u["x"] == action["x"] and u["y"] == action["y"])]
#
#             score = self.evaluate_board(temp_units)
#             if action["action_type"] == "attack":
#                 score += 40.0
#
#             if score > best_score:
#                 best_score = score
#                 best_action = action
#
#         # Recalculate Winning Itemized Receipt for debugging logs
#         if best_action and best_score > float('-inf'):
#             winning_units = copy.deepcopy(units)
#             if best_action["action_type"] == "move":
#                 for u in winning_units:
#                     if u.get("id") == best_action["unitId"]:
#                         u["x"], u["y"] = best_action["x"], best_action["y"]
#
#             receipt = self.evaluate_board(winning_units, return_breakdown=True)
#
#             print("\n📊 AI WINNING ACTION SCORE RECEIPT:")
#             print(f"   Action: {best_action}")
#             print(f"   ↳ 🟩 Total Evaluated Fitness Score: {receipt['TOTAL']}")
#             print(f"   ↳ 🪙 Material Balance Components:  {receipt['Material Balance']}")
#             print(f"   ↳ 🗺️ Territory & LOC Network Size: {receipt['Territory/LOC Size']}")
#             print(f"   ↳ 🎭 Role Execution Performance:   {receipt['Role Execution Performance']}")
#             print(f"   ↳ 🧲 Swarm Cohesion & Mesh Spacing:{receipt['Swarm Cohesion & Spacing']}")
#
#         print("=== 🤖 AI DECISION CYCLE END ===\n")
#         return best_action if (best_action and best_score > float('-inf')) else {"action_type": "end_turn"}

#
# # ai.py
# import copy
#
#
# class WarGameAI:
#     def __init__(self, engine, side: str = "South"):
#         self.engine = engine
#         self.side = side
#         self.enemy_side = "North" if side == "South" else "South"
#
#         self.unit_values = {
#             "artillery": 40,
#             "cavalry": 25,
#             "relay": 50,
#             "infantry": 20,
#             "arsenal": 1000
#         }
#
#     def evaluate_board(self, units: list, return_breakdown: bool = False) -> dict or float:
#         base_material = 0.0
#         territory_score = 0.0
#         role_score = 0.0
#         cohesion_score = 0.0
#         stacked_attack_pressure = 0.0
#
#         try:
#             connected_north = set(self.engine.get_connected_units(units, "North"))
#             connected_south = set(self.engine.get_connected_units(units, "South"))
#         except Exception:
#             connected_north = set()
#             connected_south = set()
#
#         ai_connected = connected_south if self.side == "South" else connected_north
#         enemy_connected = connected_north if self.side == "South" else connected_south
#
#         target_y = 0 if self.side == "South" else 19
#         home_y = 19 if self.side == "South" else 0
#
#         ai_units = [u for u in units if u.get("side") == self.side]
#         enemy_units = [u for u in units if u.get("side") == self.enemy_side]
#
#         ai_coords = []
#         connected_y_positions = []
#         relay_positions = []
#         connected_count = 0
#
#         # Phase 1: Material and Basic Geography
#         for unit in units:
#             u_side = unit.get("side")
#             u_type = unit.get("type", "").lower()
#             u_id = unit.get("id")
#             ux, uy = unit.get("x", 0), unit.get("y", 0)
#             is_connected = u_id in (ai_connected if u_side == self.side else enemy_connected)
#             base_val = self.unit_values.get(u_type, 20)
#
#             if u_side == self.side:
#                 base_material += base_val
#                 ai_coords.append((ux, uy))
#
#                 if is_connected:
#                     connected_count += 1
#                     connected_y_positions.append(uy)
#                     if u_type == "relay":
#                         relay_positions.append((ux, uy))
#                 else:
#                     cohesion_score -= 100.0
#             else:
#                 base_material -= base_val
#                 if not is_connected:
#                     territory_score += 50.0
#
#         territory_score += connected_count * 40.0
#
#         # Phase 2: Engagement Proximity Trigger & Threat Field
#         min_global_distance = 99
#         for enemy in enemy_units:
#             ex, ey = enemy.get("x", 0), enemy.get("y", 0)
#             for ally in ai_units:
#                 ax, ay = ally.get("x", 0), ally.get("y", 0)
#                 dist = abs(ex - ax) + abs(ey - ay)
#                 if dist < min_global_distance:
#                     min_global_distance = dist
#
#         is_engagement_phase = min_global_distance <= 6
#
#         if is_engagement_phase:
#             for enemy in enemy_units:
#                 ex, ey = enemy.get("x", 0), enemy.get("y", 0)
#                 converging_friendly_count = 0
#
#                 for ally in ai_units:
#                     ax, ay = ally.get("x", 0), ally.get("y", 0)
#                     a_type = ally.get("type", "").lower()
#                     manhattan_dist = abs(ex - ax) + abs(ey - ay)
#
#                     max_preparation_reach = 4 if a_type == "cavalry" else 3
#                     if manhattan_dist <= max_preparation_reach:
#                         converging_friendly_count += 1
#
#                 if converging_friendly_count == 1:
#                     stacked_attack_pressure += 10.0
#                 elif converging_friendly_count == 2:
#                     stacked_attack_pressure += 85.0  # Increased weight to favor coordination setups
#                 elif converging_friendly_count >= 3:
#                     stacked_attack_pressure += 220.0  # Dominant reward for a complete trap mesh
#
#         # Phase 3: Role-Specific Performance Calculations
#         for unit in ai_units:
#             u_type = unit.get("type", "").lower()
#             ux, uy = unit.get("x", 0), unit.get("y", 0)
#             u_id = unit.get("id")
#             is_connected = u_id in ai_connected
#             y_dist = abs(uy - target_y)
#
#             if u_type == "relay":
#                 if is_connected:
#                     role_score += (20 - y_dist) * 15.0
#                     min_guard_dist = min([abs(ux - cx) + abs(uy - cy) for cx, cy in ai_coords if (cx, cy) != (ux, uy)],
#                                          default=99)
#                     if min_guard_dist > 3:
#                         role_score -= 50.0
#                 else:
#                     role_score -= 200.0
#
#             elif u_type in ["infantry", "artillery"]:
#                 if is_connected:
#                     role_score += (20 - y_dist) * 6.0
#                     if relay_positions:
#                         min_relay_dist = min([abs(ux - rx) + abs(uy - ry) for rx, ry in relay_positions])
#                         if min_relay_dist <= 2:
#                             role_score += 25.0
#
#             elif u_type == "cavalry":
#                 if is_connected:
#                     role_score += (20 - y_dist) * 12.0
#                 else:
#                     role_score -= 150.0
#
#         # Phase 4: Swarm Cohesion and Formation
#         if connected_y_positions:
#             avg_y = sum(connected_y_positions) / len(connected_y_positions)
#             cohesion_score += abs(home_y - avg_y) * 30.0
#
#             span = max(connected_y_positions) - min(connected_y_positions)
#             if span > 4:
#                 cohesion_score -= (span - 4) * 25.0
#
#         for i in range(len(ai_coords)):
#             for j in range(i + 1, len(ai_coords)):
#                 dist = abs(ai_coords[i][0] - ai_coords[j][0]) + abs(ai_coords[i][1] - ai_coords[j][1])
#                 if dist <= 1:
#                     cohesion_score -= 20.0
#                 elif dist == 2:
#                     cohesion_score += 12.0
#
#         total_score = base_material + territory_score + role_score + cohesion_score + stacked_attack_pressure
#
#         if return_breakdown:
#             return {
#                 "TOTAL": total_score,
#                 "Macro State": "ENGAGEMENT COMBAT" if is_engagement_phase else "MANEUVER / MARCH",
#                 "Material Balance": base_material,
#                 "Territory/LOC Size": territory_score,
#                 "Role Execution Performance": role_score,
#                 "Swarm Cohesion & Spacing": cohesion_score,
#                 "Stacked Attack Pressure": stacked_attack_pressure
#             }
#
#         return total_score
#
#     def get_all_legal_moves(self, units: list, moved_this_turn: list) -> list:
#         legal_actions = []
#         ai_units = [u for u in units if u.get("side") == self.side]
#
#         for unit in ai_units:
#             for target in units:
#                 if target.get("side") == self.enemy_side:
#                     combat_check = self.engine.calculate_combat(units, self.side, target["x"], target["y"])
#                     if combat_check.get("valid"):
#                         legal_actions.append({
#                             "action_type": "attack",
#                             "x": target["x"],
#                             "y": target["y"]
#                         })
#
#             for dx in range(-3, 4):
#                 for dy in range(-3, 4):
#                     tx, ty = unit["x"] + dx, unit["y"] + dy
#                     if 0 <= tx < 25 and 0 <= ty < 20:
#                         is_valid, _ = self.engine.validate_move(units, unit["id"], tx, ty, moved_this_turn)
#                         if is_valid:
#                             legal_actions.append({
#                                 "action_type": "move",
#                                 "unitId": unit["id"],
#                                 "x": tx,
#                                 "y": ty
#                             })
#         return legal_actions
#
#     def select_best_action(self, current_state: dict) -> dict:
#         units = current_state["units"]
#         moved_this_turn = current_state["moved_units_this_turn"]
#         attack_executed = current_state["attack_executed_this_turn"]
#
#         # Detect total tactical actions taken this turn cycle
#         current_move_count = len(moved_this_turn)
#
#         print("\n=== 🤖 AI DECISION CYCLE START ===")
#         print(f"🤖 AI COMBAT STATUS: Move Progress: {current_move_count}/5 | Attack Phase Spent: {attack_executed}")
#
#         actions = self.get_all_legal_moves(units, moved_this_turn)
#         if not actions:
#             print("=== 🤖 AI DECISION CYCLE END ===\n")
#             return {"action_type": "end_turn"}
#
#         best_action = None
#         best_score = float('-inf')
#         combat_log_details = ""
#
#         for action in actions:
#             temp_units = copy.deepcopy(units)
#             action_score_modifier = 0.0
#
#             if action["action_type"] == "attack":
#                 # STRATEGY DISCIPLINE GATE: Do not attack prematurely if we still have available movement budget
#                 if attack_executed or current_move_count < 4:
#                     continue
#
#                 combat = self.engine.calculate_combat(temp_units, self.side, action["x"], action["y"])
#                 combat_result = combat.get("result", "NONE")
#
#                 if combat.get("valid"):
#                     if combat_result == "DESTROY":
#                         # High fidelity clean kill execution incentive
#                         action_score_modifier += 150.0
#                         temp_units = [u for u in temp_units if not (u["x"] == action["x"] and u["y"] == action["y"])]
#                     elif combat_result == "RETREAT":
#                         # Value structural dislocation of enemy units
#                         action_score_modifier += 75.0
#                         # Optional: Adjust enemy position in temp_units if engine gives retreat coords
#                     else:
#                         # Stalemate or minor bounce has lower priority than clean positioning
#                         action_score_modifier -= 30.0
#
#             elif action["action_type"] == "move":
#                 for u in temp_units:
#                     if u.get("id") == action["unitId"]:
#                         u["x"], u["y"] = action["x"], action["y"]
#
#             score = self.evaluate_board(temp_units) + action_score_modifier
#
#             if score > best_score:
#                 best_score = score
#                 best_action = action
#                 if action["action_type"] == "attack":
#                     combat_log_details = f"Target Coordinate: ({action['x']}, {action['y']}) | Engine Assessment: {combat.get('result', 'UNKNOWN')}"
#
#         if best_action and best_score > float('-inf'):
#             winning_units = copy.deepcopy(units)
#             if best_action["action_type"] == "move":
#                 for u in winning_units:
#                     if u.get("id") == best_action["unitId"]:
#                         u["x"], u["y"] = best_action["x"], best_action["y"]
#
#             receipt = self.evaluate_board(winning_units, return_breakdown=True)
#
#             print("\n📊 AI WINNING ACTION SCORE RECEIPT:")
#             print(f"   Action Selected: {best_action}")
#             if best_action["action_type"] == "attack":
#                 print(f"   ⚔️ COMBAT ENGAGEMENT REPORT: {combat_log_details}")
#             print(f"   ↳ 🌐 Current Mode:                 {receipt['Macro State']} 📍")
#             print(f"   ↳ 🟩 Total Evaluated Fitness Score: {receipt['TOTAL']}")
#             print(f"   ↳ 🪙 Material Balance Components:  {receipt['Material Balance']}")
#             print(f"   ↳ 🗺️ Territory & LOC Network Size: {receipt['Territory/LOC Size']}")
#             print(f"   ↳ 🎭 Role Execution Performance:   {receipt['Role Execution Performance']}")
#             print(f"   ↳ 🧲 Swarm Cohesion & Mesh Spacing:{receipt['Swarm Cohesion & Spacing']}")
#             print(f"   ↳ 💥 STACKED ATTACK FORCE PRESSURE: {receipt['Stacked Attack Pressure']}")
#
#         print("=== 🤖 AI DECISION CYCLE END ===\n")
#         return best_action if (best_action and best_score > float('-inf')) else {"action_type": "end_turn"}
#
# # ai.py
# import copy
#
#
# class WarGameAI:
#     def __init__(self, engine, side: str = "South"):
#         self.engine = engine
#         self.side = side
#         self.enemy_side = "North" if side == "South" else "South"
#
#         self.unit_values = {
#             "artillery": 40,
#             "cavalry": 25,
#             "relay": 65,  # Increased strategic weight to protect orchestrators
#             "infantry": 20,
#             "arsenal": 1000
#         }
#
#     def evaluate_board(self, units: list, return_breakdown: bool = False,
#                        base_enemy_connected: set = None) -> dict or float:
#         base_material = 0.0
#         territory_score = 0.0
#         role_score = 0.0
#         cohesion_score = 0.0
#         stacked_attack_pressure = 0.0
#
#         try:
#             connected_north = set(self.engine.get_connected_units(units, "North"))
#             connected_south = set(self.engine.get_connected_units(units, "South"))
#         except Exception:
#             connected_north = set()
#             connected_south = set()
#
#         ai_connected = connected_south if self.side == "South" else connected_north
#         enemy_connected = connected_north if self.side == "South" else connected_south
#
#         target_y = 0 if self.side == "South" else 19
#         home_y = 19 if self.side == "South" else 0
#
#         ai_units = [u for u in units if u.get("side") == self.side]
#         enemy_units = [u for u in units if u.get("side") == self.enemy_side]
#
#         ai_coords = []
#         connected_y_positions = []
#         relay_positions = []
#         connected_count = 0
#
#         # Phase 1: Material and Basic Geography
#         for unit in units:
#             u_side = unit.get("side")
#             u_type = unit.get("type", "").lower()
#             u_id = unit.get("id")
#             ux, uy = unit.get("x", 0), unit.get("y", 0)
#             is_connected = u_id in (ai_connected if u_side == self.side else enemy_connected)
#             base_val = self.unit_values.get(u_type, 20)
#
#             if u_side == self.side:
#                 base_material += base_val
#                 ai_coords.append((ux, uy))
#
#                 if is_connected:
#                     connected_count += 1
#                     connected_y_positions.append(uy)
#                     if u_type == "relay":
#                         relay_positions.append((ux, uy))
#                 else:
#                     # Drastically lowered punitive damage to allow experimental maneuvering steps
#                     cohesion_score -= 40.0
#             else:
#                 base_material -= base_val
#                 # Only reward NEW cut-offs achieved during this active decision turn
#                 if base_enemy_connected is not None:
#                     was_connected_at_start = u_id in base_enemy_connected
#                     if was_connected_at_start and not is_connected:
#                         territory_score += 200.0  # Strong event bounty for severing a line
#                 else:
#                     if not is_connected:
#                         territory_score += 60.0  # Fallback original valuation
#
#         # Scale network territory reward exponentially by progression depth
#         territory_score += connected_count * 35.0
#
#         # Phase 2: Engagement Proximity Trigger & Threat Field
#         min_global_distance = 99
#         for enemy in enemy_units:
#             ex, ey = enemy.get("x", 0), enemy.get("y", 0)
#             for ally in ai_units:
#                 ax, ay = ally.get("x", 0), ally.get("y", 0)
#                 dist = abs(ex - ax) + abs(ey - ay)
#                 if dist < min_global_distance:
#                     min_global_distance = dist
#
#         is_engagement_phase = min_global_distance <= 6
#
#         if is_engagement_phase:
#             for enemy in enemy_units:
#                 ex, ey = enemy.get("x", 0), enemy.get("y", 0)
#                 converging_friendly_count = 0
#
#                 for ally in ai_units:
#                     ax, ay = ally.get("x", 0), ally.get("y", 0)
#                     a_type = ally.get("type", "").lower()
#                     manhattan_dist = abs(ex - ax) + abs(ey - ay)
#
#                     max_preparation_reach = 4 if a_type == "cavalry" else 3
#                     if manhattan_dist <= max_preparation_reach:
#                         converging_friendly_count += 1
#
#                 if converging_friendly_count == 1:
#                     stacked_attack_pressure += 10.0
#                 elif converging_friendly_count == 2:
#                     stacked_attack_pressure += 40.0
#                 elif converging_friendly_count >= 3:
#                     stacked_attack_pressure += 80.0
#
#         # Phase 3: Role-Specific Performance Calculations & Global Awareness Gradients
#         # MODIFIED: Extract global list of stranded/isolated components to build tracking paths
#         isolated_enemies = [(e.get("x", 0), e.get("y", 0)) for e in enemy_units if e.get("id") not in enemy_connected]
#         isolated_allies = [(a.get("x", 0), a.get("y", 0)) for a in ai_units if a.get("id") not in ai_connected]
#
#         for unit in ai_units:
#             u_type = unit.get("type", "").lower()
#             ux, uy = unit.get("x", 0), unit.get("y", 0)
#             u_id = unit.get("id")
#             is_connected = u_id in ai_connected
#             y_dist = abs(uy - target_y)
#
#             if u_type == "relay":
#                 if is_connected:
#                     # EXISTING: Encourage forward exploration
#                     role_score += (20 - y_dist) * 35.0
#
#                     # --- NEW: CONNECTIVITY EXPANSION INCENTIVE ---
#                     # Simulate the network coverage if this relay were at the current position
#                     # We count how many tiles this specific relay 'unlocks'
#                     coverage_gain = 0
#                     for dx, dy in self.engine.directions:
#                         # Simple look-ahead to see if we expand into empty, non-mountain space
#                         tx, ty = ux + dx, uy + dy
#                         if 0 <= tx < self.engine.cols and 0 <= ty < self.engine.rows:
#                             if (tx, ty) not in self.engine.mountains:
#                                 coverage_gain += 1
#
#                     # Reward the relay for 'anchoring' into open terrain
#                     role_score += (coverage_gain * 25.0)
#                     # ----------------------------------------------
#
#             elif u_type in ["infantry", "artillery"]:
#                 if is_connected:
#                     role_score += (20 - y_dist) * 10.0
#                     if relay_positions:
#                         min_relay_dist = min([abs(ux - rx) + abs(uy - ry) for rx, ry in relay_positions])
#                         # Give combat units a strong incentive to rally and stream through relay anchors
#                         if min_relay_dist <= 3:
#                             role_score += 40.0
#
#                     # MODIFIED: Clear hunting vector. If an enemy is stray and isolated, chase them down
#                     if isolated_enemies:
#                         min_dist_to_iso_enemy = min([abs(ux - ex) + abs(uy - ey) for ex, ey in isolated_enemies])
#                         role_score += (25 - min_dist_to_iso_enemy) * 10.0
#                 else:
#                     # MODIFIED: Provide a steep rescue gradient field so stuck pieces walk back to the safety mesh
#                     if relay_positions:
#                         min_relay_dist = min([abs(ux - rx) + abs(uy - ry) for rx, ry in relay_positions])
#                         role_score += (25 - min_relay_dist) * 15.0
#                     elif ai_coords:
#                         min_ally_dist = min(
#                             [abs(ux - cx) + abs(uy - cy) for cx, cy in ai_coords if (cx, cy) != (ux, uy)], default=0)
#                         role_score += (25 - min_ally_dist) * 8.0
#
#             elif u_type == "cavalry":
#                 if is_connected:
#                     role_score += (20 - y_dist) * 18.0
#
#                     # MODIFIED: Cavalry hunts down vulnerable isolated elements with high priority
#                     if isolated_enemies:
#                         min_dist_to_iso_enemy = min([abs(ux - ex) + abs(uy - ey) for ex, ey in isolated_enemies])
#                         role_score += (25 - min_dist_to_iso_enemy) * 15.0
#                 else:
#                     role_score -= 75.0
#                     if relay_positions:
#                         min_relay_dist = min([abs(ux - rx) + abs(uy - ry) for rx, ry in relay_positions])
#                         role_score += (25 - min_relay_dist) * 15.0
#
#         # Phase 4: Swarm Cohesion and Formation
#         if connected_y_positions:
#             avg_y = sum(connected_y_positions) / len(connected_y_positions)
#             cohesion_score += abs(home_y - avg_y) * 45.0  # Reward whole-army downward/upward advance
#
#         for i in range(len(ai_coords)):
#             for j in range(i + 1, len(ai_coords)):
#                 dist = abs(ai_coords[i][0] - ai_coords[j][0]) + abs(ai_coords[i][1] - ai_coords[j][1])
#                 if dist <= 1:
#                     cohesion_score -= 10.0  # Light penalty for bunching up on top of each other
#                 elif dist == 2:
#                     cohesion_score += 15.0  # Spacing bonus to optimize network coverage
#
#         total_score = base_material + territory_score + role_score + cohesion_score + stacked_attack_pressure
#
#         if return_breakdown:
#             return {
#                 "TOTAL": total_score,
#                 "Macro State": "ENGAGEMENT COMBAT" if is_engagement_phase else "MANEUVER / MARCH",
#                 "Material Balance": base_material,
#                 "Territory/LOC Size": territory_score,
#                 "Role Execution Performance": role_score,
#                 "Swarm Cohesion & Spacing": cohesion_score,
#                 "Stacked Attack Pressure": stacked_attack_pressure
#             }
#
#         return total_score
#
#     def get_all_legal_moves(self, units: list, moved_this_turn: list) -> list:
#         legal_actions = []
#         ai_units = [u for u in units if u.get("side") == self.side]
#
#         for unit in ai_units:
#             for target in units:
#                 if target.get("side") == self.enemy_side:
#                     combat_check = self.engine.calculate_combat(units, self.side, target["x"], target["y"])
#                     if combat_check.get("valid"):
#                         legal_actions.append({
#                             "action_type": "attack",
#                             "x": target["x"],
#                             "y": target["y"]
#                         })
#
#             for dx in range(-3, 4):
#                 for dy in range(-3, 4):
#                     tx, ty = unit["x"] + dx, unit["y"] + dy
#                     if 0 <= tx < 25 and 0 <= ty < 20:
#                         is_valid, _ = self.engine.validate_move(units, unit["id"], tx, ty, moved_this_turn)
#                         if is_valid:
#                             legal_actions.append({
#                                 "action_type": "move",
#                                 "unitId": unit["id"],
#                                 "x": tx,
#                                 "y": ty
#                             })
#         return legal_actions
#
#     def calculate_cohesion_loss(self, units, unit_id, target_x, target_y):
#         # Create a "Ghost State" of the board
#         ghost_units = copy.deepcopy(units)
#         unit = next(u for u in ghost_units if u['id'] == unit_id)
#         unit['x'], unit['y'] = target_x, target_y
#
#         # Calculate how many units were connected before, and how many after
#         before_connected = self.engine.get_connected_units(units, unit['side'])
#         after_connected = self.engine.get_connected_units(ghost_units, unit['side'])
#
#         # Returns the number of units that will be stranded by this move
#         return len(before_connected) - len(after_connected)
#
#     def select_best_action(self, current_state: dict) -> dict:
#         units = current_state["units"]
#         moved_this_turn = current_state["moved_units_this_turn"]
#         attack_executed = current_state["attack_executed_this_turn"]
#
#         current_move_count = len(moved_this_turn)
#
#         print("\n=== 🤖 AI DECISION CYCLE START ===")
#         print(f"🤖 AI COMBAT STATUS: Move Progress: {current_move_count}/5 | Attack Phase Spent: {attack_executed}")
#
#         try:
#             start_north = set(self.engine.get_connected_units(units, "North"))
#             start_south = set(self.engine.get_connected_units(units, "South"))
#         except Exception:
#             start_north = set()
#             start_south = set()
#         base_enemy_connected = start_north if self.side == "South" else start_south
#
#         actions = self.get_all_legal_moves(units, moved_this_turn)
#         if not actions:
#             print("=== 🤖 AI DECISION CYCLE END ===\n")
#             return {"action_type": "end_turn"}
#
#         best_action = None
#         best_score = float('-inf')
#         combat_log_details = ""
#
#         for action in actions:
#             temp_units = copy.deepcopy(units)
#             action_score_modifier = 0.0
#
#             if action["action_type"] == "attack":
#                 if attack_executed:
#                     continue
#
#                 combat = self.engine.calculate_combat(temp_units, self.side, action["x"], action["y"])
#                 combat_result = combat.get("result", "NONE")
#
#                 if combat.get("valid"):
#                     if combat_result == "DESTROY":
#                         action_score_modifier += 1200.0
#                         temp_units = [u for u in temp_units if not (u["x"] == action["x"] and u["y"] == action["y"])]
#                     elif combat_result == "RETREAT":
#                         action_score_modifier += 500.0
#                     else:
#                         action_score_modifier -= 20.0
#
#
#             elif action["action_type"] == "move":
#
#                 # --- NEW INTELLIGENCE: COHESION PENALTY ---
#
#                 lost_units = self.calculate_cohesion_loss(units, action["unitId"], action["x"], action["y"])
#
#                 if lost_units > 0:
#                     action_score_modifier -= (lost_units * 600.0)  # Penalty for breaking chains
#
#                 for u in temp_units:
#
#                     if u.get("id") == action["unitId"]:
#                         u["x"], u["y"] = action["x"], action["y"]
#
#             score = self.evaluate_board(temp_units, base_enemy_connected=base_enemy_connected) + action_score_modifier
#
#             if score > best_score:
#                 best_score = score
#                 best_action = action
#                 if action["action_type"] == "attack":
#                     combat_log_details = f"Target Coordinate: ({action['x']}, {action['y']}) | Engine Assessment: {combat.get('result', 'UNKNOWN')}"
#
#         if best_action and best_score > float('-inf'):
#             winning_units = copy.deepcopy(units)
#             if best_action["action_type"] == "move":
#                 for u in winning_units:
#                     if u.get("id") == best_action["unitId"]:
#                         u["x"], u["y"] = best_action["x"], best_action["y"]
#
#             receipt = self.evaluate_board(winning_units, return_breakdown=True,
#                                           base_enemy_connected=base_enemy_connected)
#
#             print("\n📊 AI WINNING ACTION SCORE RECEIPT:")
#             print(f"   Action Selected: {best_action}")
#             if best_action["action_type"] == "attack":
#                 print(f"   ⚔️ COMBAT ENGAGEMENT REPORT: {combat_log_details}")
#             print(f"   ↳ 🌐 Current Mode:                 {receipt['Macro State']} 📍")
#             print(f"   ↳ 🟩 Total Evaluated Fitness Score: {receipt['TOTAL']}")
#             print(f"   ↳ 🪙 Material Balance Components:  {receipt['Material Balance']}")
#             print(f"   ↳ 🗺️ Territory & LOC Network Size: {receipt['Territory/LOC Size']}")
#             print(f"   ↳ 🎭 Role Execution Performance:   {receipt['Role Execution Performance']}")
#             print(f"   ↳ 🧲 Swarm Cohesion & Mesh Spacing:{receipt['Swarm Cohesion & Spacing']}")
#             print(f"   ↳ 💥 STACKED ATTACK FORCE PRESSURE: {receipt['Stacked Attack Pressure']}")
#
#         print("=== 🤖 AI DECISION CYCLE END ===\n")
#         return best_action if (best_action and best_score > float('-inf')) else {"action_type": "end_turn"}


# ai.py
import copy


class WarGameAI:
    def __init__(self, engine, side: str = "South"):
        self.engine = engine
        self.side = side
        self.enemy_side = "North" if side == "South" else "South"

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

        total_score = base_material + territory_score + role_score + cohesion_score + stacked_attack_pressure

        if return_breakdown:
            return {
                "TOTAL": total_score,
                "Macro State": "ENGAGEMENT COMBAT" if is_engagement_phase else "MANEUVER / MARCH",
                "Material Balance": base_material,
                "Territory/LOC Size": territory_score,
                "Role Execution Performance": role_score,
                "Swarm Cohesion & Spacing": cohesion_score,
                "Stacked Attack Pressure": stacked_attack_pressure
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

            elif action["action_type"] == "move":
                # Check for cohesion loss
                lost = self.calculate_cohesion_loss(units, action["unitId"], action["x"], action["y"])
                if lost > 0: mod -= (lost * 600.0)

                # --- 2. STABILITY BONUS: Prevents Relay Oscillation ---
                # A small bonus for staying still or moving only 1 tile
                # helps break ties between two equal-scoring tiles.
                unit = next(u for u in units if u['id'] == action["unitId"])
                dist_moved = abs(unit['x'] - action['x']) + abs(unit['y'] - action['y'])
                if dist_moved <= 1:
                    mod += 10.0

                for u in temp:
                    if u.get("id") == action["unitId"]: u["x"], u["y"] = action["x"], action["y"]

            score = self.evaluate_board(temp, base_enemy_connected=base_enemy_connected) + mod

            if score > best_score:
                best_score, best_score_action = score, action
                best_action = best_score_action

        return best_action if best_action else {"action_type": "end_turn"}