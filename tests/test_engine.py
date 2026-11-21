"""Regressões da conversão e equivalência com o motor JavaScript original."""
import json
from math import hypot, isfinite
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import FLOOR, GameModel, RULES, segment_rect


def playable():
    model = GameModel()
    model.start()
    advance(model, 216)
    return model


def advance(model, frames, inputs=None):
    for _ in range(frames):
        model.step(1 / 120, inputs)


def camel(key):
    parts = key.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def capture(model):
    def pick(obj, keys):
        return {camel(k): obj[k] for k in keys if k in obj}
    p = vars(model.player)
    return dict(snapshot=model.snapshot(),
                player=pick(p, ("vx", "vy", "facing", "on_ground", "crouch", "dash_cooldown", "invulnerable", "shot_cooldown", "aim_x", "aim_y")),
                shots=[pick(s, ("x", "y", "vx", "vy", "r", "life")) for s in model.shots],
                fire=[pick(f, ("x", "y", "vx", "vy", "r", "age", "kind", "base_y", "gravity", "bounces", "amplitude", "frequency")) for f in model.fire],
                beams=[pick(b, ("x", "y", "end_x", "end_y", "age", "duration", "half_width", "mode", "touched")) for b in model.beams],
                warnings=[pick(w, ("type", "remaining", "total", "x", "y", "angle", "target_x", "target_y", "mode", "safe_x", "safe_width", "lanes", "fired", "rows")) for w in model.warnings])


class OriginalEquivalence(unittest.TestCase):
    def assert_nested(self, actual, expected, path="root"):
        if isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected), path)
            for key, value in expected.items():
                self.assert_nested(actual[key], value, f"{path}.{key}")
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected), path)
            for i, (a, e) in enumerate(zip(actual, expected)):
                self.assert_nested(a, e, f"{path}[{i}]")
        elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
            self.assertAlmostEqual(actual, expected, delta=1e-6, msg=path)
        else:
            self.assertEqual(actual, expected, path)

    def test_reference_44_scenarios_146_checkpoints(self):
        """Referência da versão difícil publicada, incluindo rajadas horizontais."""
        cases = json.loads(Path(__file__).with_name("original_cases.json").read_text())
        for case in cases:
            with self.subTest(scenario=case["name"]):
                g = playable()
                g.invincible = True
                for index, (command, expected) in enumerate(zip(case["commands"], case["checks"])):
                    if command.get("phase"):
                        g.force_phase(command["phase"])
                    if command.get("attack"):
                        g.prepare_attack(command["attack"])
                        g.attack_timer = 999
                    if command.get("damage"):
                        g.damage_boss(command["damage"])
                    if command.get("pause"):
                        g.pause()
                    if command.get("resume"):
                        g.resume()
                    advance(g, command.get("frames", 0), command.get("input"))
                    self.assert_nested(capture(g), expected, f"{case['name']}[{index}]")


class CombatTests(unittest.TestCase):
    def test_three_lives_invulnerability_and_death(self):
        g = playable()
        g.attack_timer = 999
        self.assertTrue(g.hurt_player())
        self.assertEqual(g.player.hp, 2)
        self.assertFalse(g.hurt_player())
        for _ in range(2):
            advance(g, 220)
            self.assertTrue(g.hurt_player())
        self.assertEqual(g.state, "dead")
        self.assertEqual(g.player.hp, 0)
        g.start()
        self.assertEqual(g.player.hp, 3)
        self.assertFalse(g.fire)

    def test_dash_protects_and_has_cooldown(self):
        g = playable()
        g.step(1 / 120, dict(dash=True, right=True))
        self.assertGreater(g.player.dash, 0)
        self.assertFalse(g.hurt_player())
        g.step(1 / 120)
        g.step(1 / 120, dict(dash=True))
        self.assertEqual(g.stats["dashes"], 1)
        advance(g, 70)
        g.step(1 / 120, dict(dash=True))
        self.assertEqual(g.stats["dashes"], 2)

    def test_variable_jump_height_and_landing(self):
        hold, tap = playable(), playable()
        hold.invincible = tap.invincible = True
        min_hold = min_tap = FLOOR
        for i in range(160):
            hold.step(1 / 120, dict(jump=i < 100))
            tap.step(1 / 120, dict(jump=i < 7))
            min_hold, min_tap = min(min_hold, hold.player.y), min(min_tap, tap.player.y)
        self.assertLess(min_hold, min_tap - 35)
        self.assertEqual(hold.player.y, FLOOR)
        self.assertEqual(tap.player.y, FLOOR)

    def test_jump_buffer_before_landing(self):
        g = playable()
        g.player.y, g.player.vy, g.player.on_ground, g.coyote = FLOOR - 5, 250, False, 0
        advance(g, 8, dict(jump=True))
        self.assertFalse(g.player.on_ground)
        self.assertLess(g.player.vy, -400)

    def test_twelve_shots_per_second_and_muzzle_origin(self):
        g = playable()
        g.muzzle_provider = lambda: (333, 444)
        g.step(1 / 120, dict(shoot=True))
        self.assertAlmostEqual(g.shots[0]["x"], 333 + 1450 / 120)
        self.assertEqual(g.shots[0]["y"], 444)
        advance(g, 119, dict(shoot=True))
        self.assertEqual(g.stats["shots"], 12)

    def test_continuous_collision_hits_only_once(self):
        g = playable()
        x, y, w, h = g.boss_box()
        self.assertTrue(segment_rect(x - 500, y + 100, x + 500, y + 100, (x, y, w, h), 9))
        g.shots.append(dict(x=x - 500, y=y + 100, vx=180000, vy=0, r=9, life=1))
        g.step(1 / 120)
        g.step(1 / 120)
        self.assertEqual(g.boss.hp, RULES.max_boss_hp - 1)
        self.assertEqual(g.stats["hits"], 1)

    def test_pause_freezes_motion_and_discards_actions(self):
        g = playable()
        advance(g, 12, dict(jump=True))
        before = g.snapshot()
        g.pause()
        advance(g, 240, dict(dash=True, shoot=True))
        after = g.snapshot()
        self.assertEqual(after["player"], before["player"])
        self.assertEqual(after["elapsed"], before["elapsed"])
        self.assertEqual(after["stats"], before["stats"])
        g.resume()
        g.step(1 / 120)
        self.assertEqual(g.stats["dashes"], 0)

    def test_low_flame_hits_stationary_player_once(self):
        g = playable()
        w = g.prepare_attack("flame")
        g.attack_timer = 999
        advance(g, round((w["total"] + .65) * 120))
        self.assertEqual(g.player.hp, 2)
        self.assertFalse(g.beams)

    def test_low_flame_is_evaded_by_jump_or_dash(self):
        for action, early in ((dict(jump=True), .17), (dict(dash=True, right=True), .04)):
            with self.subTest(action=action):
                g = playable()
                w = g.prepare_attack("flame")
                g.attack_timer = 999
                advance(g, round((w["total"] - early) * 120))
                advance(g, 86, action)
                self.assertEqual(g.player.hp, 3)

    def test_high_flame_is_safe_on_ground(self):
        g = playable()
        g.breath_count = 1
        w = g.prepare_attack("flame")
        g.attack_timer = 999
        self.assertEqual(w["mode"], "high")
        advance(g, round((w["total"] + .65) * 120), dict(down=True))
        self.assertEqual(g.player.hp, 3)

    def test_phase_transformation_night_and_victory(self):
        g = playable()
        g.damage_boss(RULES.max_boss_hp * .25 + 1)
        self.assertEqual(g.boss.phase, 2)
        g.damage_boss(RULES.max_boss_hp * .25)
        self.assertEqual(g.state, "transform")
        hp = g.boss.hp
        g.damage_boss(50)
        self.assertEqual(g.boss.hp, hp)
        advance(g, 440)
        self.assertEqual((g.state, g.boss.phase, g.night), ("playing", 3, 1))
        g.damage_boss(RULES.max_boss_hp * .25)
        self.assertEqual(g.boss.phase, 4)
        g.damage_boss(RULES.max_boss_hp)
        self.assertEqual(g.state, "victory")
        self.assertFalse(g.fire or g.beams or g.shots or g.warnings)

    def test_special_attacks_clear_old_hazards(self):
        for attack in ("flame", "giant", "rain"):
            g = playable()
            w = g.prepare_attack("fan")
            g._release(w)
            g._update_attacks(1 / 120)
            self.assertTrue(g.fire)
            g.prepare_attack(attack)
            self.assertFalse(g.fire or g.beams or g.scheduled)
            self.assertEqual(len(g.warnings), 1)

    def test_no_overlap_during_giant_orb(self):
        g = playable()
        g.invincible = True
        w = g.prepare_attack("giant")
        g.attack_timer = 999
        advance(g, round((w["total"] + .1) * 120))
        self.assertEqual(len(g.fire), 1)
        g.attack_timer = 0
        advance(g, 78)
        self.assertEqual(len(g.fire), 1)
        self.assertFalse(g.warnings or g.beams)

    def test_frame_rate_independent_simulation(self):
        results = []
        for hz in (30, 60, 120):
            g = playable()
            g.invincible = True
            for _ in range(hz * 2):
                g.step(1 / hz, dict(right=True, shoot=True))
            results.append(g.snapshot())
        for result in results[1:]:
            self.assertAlmostEqual(result["player"]["x"], results[0]["player"]["x"])
            self.assertEqual(result["stats"], results[0]["stats"])


if __name__ == "__main__":
    unittest.main()
