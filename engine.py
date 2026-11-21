"""Regras do duelo, em Python puro. Não depende da janela nem do Pygame.

Portado de dist/engine.mjs do pacote original. Coordenadas em pixels e
velocidades em pixels por segundo; x/y do jogador são a posição dos pés.
"""
from dataclasses import dataclass
from math import atan2, ceil, cos, hypot, isfinite, sin, tan


WORLD_WIDTH, WORLD_HEIGHT, FLOOR = 1280, 720, 622


@dataclass(frozen=True)
class Rules:
    lives: int = 3
    max_boss_hp: int = 480
    shot_interval: float = 1 / 12
    shot_speed: float = 1450
    player_speed: float = 310
    gravity: float = 1850
    jump_speed: float = 680
    dash_speed: float = 800
    dash_time: float = .21
    dash_cooldown: float = .55
    hurt_invulnerability: float = 1.8
    transform_time: float = 3.6


RULES = Rules()


def clamp(value, low, high):
    return max(low, min(high, value))


def circle_rect(x, y, radius, box):
    nx = clamp(x, box[0], box[0] + box[2])
    ny = clamp(y, box[1], box[1] + box[3])
    return (x - nx) ** 2 + (y - ny) ** 2 < radius ** 2


def segment_rect(x1, y1, x2, y2, box, radius=0):
    """Colisão contínua: um tiro rápido não atravessa o dragão entre quadros."""
    lo, hi = 0., 1.
    for origin, delta, minimum, maximum in (
        (x1, x2 - x1, box[0] - radius, box[0] + box[2] + radius),
        (y1, y2 - y1, box[1] - radius, box[1] + box[3] + radius),
    ):
        if abs(delta) < 1e-9:
            if origin < minimum or origin > maximum:
                return False
            continue
        a, z = (minimum - origin) / delta, (maximum - origin) / delta
        if a > z:
            a, z = z, a
        lo, hi = max(lo, a), min(hi, z)
        if lo > hi:
            return False
    return True


@dataclass
class Player:
    x: float = 190
    y: float = FLOOR
    vx: float = 0
    vy: float = 0
    hp: int = RULES.lives
    facing: int = 1
    on_ground: bool = True
    crouch: bool = False
    dash: float = 0
    dash_direction: int = 1
    dash_cooldown: float = 0
    invulnerable: float = 0
    shot_cooldown: float = 0
    anim_time: float = 0
    jump_age: float = 0
    land_time: float = 0
    shooting: bool = False
    aim_x: int = 1
    aim_y: int = 0


@dataclass
class Boss:
    hp: float = RULES.max_boss_hp
    max_hp: float = RULES.max_boss_hp
    phase: int = 1
    flash: float = 0
    cast: float = 0
    transform: float = 0
    attack_type: str = ""
    attack_mode: str = ""
    attack_age: float = 0
    charge: float = 0
    mouth_lock: tuple | None = None
    horizontal: dict | None = None
    dip_active: bool = False
    dip_y: float = 0
    dip_from: float = 0
    dip_target: float = 0
    dip_elapsed: float = 0
    dip_duration: float = .3
    pulse: float = 0


class GameModel:
    def __init__(self):
        self.invincible = False
        self.muzzle_provider = None
        self.reset()

    def reset(self):
        self.state, self.previous_state = "title", "playing"
        self.elapsed = self.state_time = self.night = 0.
        self.events, self.shots, self.fire, self.beams = [], [], [], []
        self.scheduled, self.warnings = [], []
        self.pattern_index = self.breath_count = self.horizontal_count = 0
        self.attack_timer = .85
        self.stats = dict(shots=0, hits=0, dashes=0)
        self.previous_input = {}
        self.jump_buffer, self.coyote = 0., .12
        self.dash_requested = False
        self.player, self.boss = Player(), Boss()

    def start(self):
        self.reset()
        self.state = "intro"
        self.event("start")

    def pause(self):
        if self.state in ("playing", "intro", "transform"):
            self.previous_state, self.state = self.state, "paused"
            self.dash_requested = False
            self.jump_buffer = 0
            self.event("pause")

    def resume(self):
        if self.state == "paused":
            self.state, self.previous_input = self.previous_state, {}
            self.event("resume")

    def event(self, name, **data):
        if len(self.events) < 160:
            self.events.append(dict(type=name, **data))

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def snapshot(self):
        p = self.player
        return dict(state=self.state, phase=self.boss.phase, night=self.night,
                    hp=p.hp, bossHp=ceil(self.boss.hp), elapsed=self.elapsed,
                    shots=len(self.shots), fire=len(self.fire), beams=len(self.beams),
                    attackType=self.boss.attack_type or None,
                    player=dict(x=p.x, y=p.y, onGround=p.on_ground, dash=p.dash),
                    warnings=[w["type"] for w in self.warnings], stats=dict(self.stats))

    def force_phase(self, phase):
        """Atalho de teste, não associado a teclas durante a partida."""
        if phase not in (1, 2, 3, 4):
            return
        self.state, self.state_time = "playing", 0
        self.boss.hp = RULES.max_boss_hp * (1, .73, .49, .23)[phase - 1]
        self.boss.phase, self.night = phase, int(phase >= 3)
        self.shots, self.fire, self.beams = [], [], []
        self.scheduled, self.warnings = [], []
        self.pattern_index = self.breath_count = self.horizontal_count = 0
        self._clear_horizontal()
        self.boss.mouth_lock = None
        self.boss.charge = self.boss.cast = 0
        self.boss.attack_type = ""
        self.attack_timer = .85

    def player_box(self):
        p = self.player
        crouch = p.crouch or (p.dash > 0 and p.on_ground)
        return p.x - 16, p.y - (53 if crouch else 99), 32, 47 if crouch else 90

    def boss_offset_y(self):
        b = self.boss
        if b.dip_active:
            return b.dip_y
        return b.mouth_lock[1] - (341 if b.phase < 3 else 439) if b.mouth_lock else sin(self.elapsed * 1.7) * 12

    def boss_box(self):
        b, bob = self.boss, self.boss_offset_y()
        return (1035, 252 + bob, 175, 358) if b.phase < 3 else (991, 203 + bob, 265, 405)

    def mouth(self):
        if self.boss.mouth_lock and not self.boss.dip_active:
            return self.boss.mouth_lock
        bob = self.boss_offset_y()
        return (1059, 341 + bob) if self.boss.phase < 3 else (1090, 439 + bob)

    def _clear_horizontal(self):
        b = self.boss
        b.horizontal, b.dip_active = None, False
        b.dip_y = b.dip_from = b.dip_target = b.dip_elapsed = b.pulse = 0

    def _dip_to(self, mouth_y, duration=.3):
        b, offset = self.boss, self.boss_offset_y()
        b.dip_active, b.dip_from, b.dip_y = True, offset, offset
        b.dip_target = mouth_y - (341 if b.phase < 3 else 439)
        b.dip_elapsed, b.dip_duration, b.mouth_lock = 0, duration, None

    def _update_boss_pose(self, dt):
        b, h = self.boss, self.boss.horizontal
        b.pulse = max(0, b.pulse - dt)
        if h and h['phase'] != 'windup':
            h['elapsed'] += dt
        if (h and h['phase'] == 'firing'
                and not any(s.get('kind') == 'horizontal' or 'pose_y' in s for s in self.scheduled)
                and not any(f['kind'] == 'horizontal' for f in self.fire)):
            h['phase'], h['elapsed'] = 'recover', 0
            self._dip_to((341 if b.phase < 3 else 439) + sin(self.elapsed * 1.7) * 12, .38)
            b.cast = .22
        if h and h['phase'] == 'recover':
            b.dip_target = sin(self.elapsed * 1.7) * 12
        if b.dip_active:
            b.dip_elapsed = min(b.dip_duration, b.dip_elapsed + dt)
            t = b.dip_elapsed / b.dip_duration
            b.dip_y = b.dip_from + (b.dip_target - b.dip_from) * t * t * (3 - 2 * t)
        if h and h['phase'] == 'recover' and b.dip_elapsed >= b.dip_duration:
            b.horizontal, b.dip_active, b.dip_y = None, False, 0

    def step(self, seconds, inputs=None):
        if not isfinite(seconds) or seconds <= 0:
            return
        if self.state in ("paused", "title", "dead", "victory"):
            return
        inputs = inputs or {}
        dt = min(seconds, .1)
        count = max(1, ceil(dt * 120))
        if inputs.get("jump") and not self.previous_input.get("jump"):
            self.jump_buffer = .12
        if inputs.get("dash") and not self.previous_input.get("dash"):
            self.dash_requested = True
        if not inputs.get("jump") and self.previous_input.get("jump") and self.player.vy < -220:
            self.player.vy *= .52
        self.previous_input = dict(inputs)
        for _ in range(count):
            self._tick(dt / count, inputs)

    def _tick(self, dt, inputs):
        if self.state in ("paused", "title", "dead", "victory"):
            return
        self.state_time += dt
        p, b = self.player, self.boss
        for key in ("invulnerable", "dash_cooldown", "shot_cooldown", "land_time"):
            setattr(p, key, max(0, getattr(p, key) - dt))
        p.anim_time += dt
        b.flash, b.cast = max(0, b.flash - dt), max(0, b.cast - dt)
        b.attack_age += dt
        if not any(not w["fired"] for w in self.warnings) and not self.beams and b.cast <= 0:
            b.mouth_lock, b.charge = None, 0
        if self.state == "intro":
            if self.state_time >= 1.7:
                self.state, self.state_time, self.previous_input = "playing", 0, {}
                self.event("ready")
            return
        self.elapsed += dt
        self._update_boss_pose(dt)
        if self.state == "transform":
            b.transform = self.state_time / RULES.transform_time
            self.night = clamp(b.transform, 0, 1)
            if self.state_time >= RULES.transform_time:
                self.state, self.state_time, self.night = "playing", 0, 1
                b.transform, self.attack_timer = 1, 1.
                p.invulnerable = max(p.invulnerable, 1.1)
                self.event("transformed")
            self._move_player(dt, inputs, False)
            return
        self._move_player(dt, inputs, True)
        p.shooting = bool(inputs.get("shoot"))
        if p.shooting and p.shot_cooldown <= 1e-7:
            self._shoot()
            p.shot_cooldown = RULES.shot_interval
        self._update_attacks(dt)
        bb = self.boss_box()
        for shot in self.shots:
            if shot.get("dead"):
                continue
            x, y = shot["x"], shot["y"]
            shot["x"] += shot["vx"] * dt
            shot["y"] += shot["vy"] * dt
            shot["life"] -= dt
            if segment_rect(x, y, shot["x"], shot["y"], bb, shot["r"]):
                shot["dead"] = True
                self.damage_boss(1)
                self.stats["hits"] += 1
                self.event("hit", x=shot["x"], y=shot["y"])
                if self.state != "playing":
                    break
            if shot["life"] < 0 or not -40 <= shot["x"] <= 1320 or not -50 <= shot["y"] <= 760:
                shot["dead"] = True
        self.shots = [s for s in self.shots if not s.get("dead")]
        if self.state != "playing":
            return
        pb = self.player_box()
        for f in self.fire:
            f["age"] += dt
            if f["kind"] == "sine":
                f["base_y"] += f["vy"] * dt
                f["x"] += f["vx"] * dt
                f["y"] = f["base_y"] + sin(f["age"] * f["frequency"]) * f["amplitude"]
            else:
                f["vy"] += f["gravity"] * dt
                f["x"] += f["vx"] * dt
                f["y"] += f["vy"] * dt
            if f["kind"] == "bounce" and f["y"] + f["r"] >= FLOOR:
                if f["bounces"] > 0:
                    f["y"], f["vy"] = FLOOR - f["r"] - 1, -abs(f["vy"]) * .78
                    f["bounces"] -= 1
                    self.event("bounce", x=f["x"], y=f["y"])
                else:
                    f["dead"] = True
            if f["age"] > 9 or not -70 <= f["x"] <= 1400 or not -140 <= f["y"] <= 790:
                f["dead"] = True
            if not f["dead"] and circle_rect(f["x"], f["y"], f["r"] * (.5 if f["kind"] == "giant" else .76), pb):
                f["dead"] = True
                self.hurt_player()
        self.fire = [f for f in self.fire if not f["dead"]]
        for beam in self.beams:
            beam["age"] += dt
            if beam["age"] >= beam["duration"]:
                beam["dead"] = True
                continue
            if beam["age"] < .08 or beam["touched"]:
                continue
            if segment_rect(beam["x"], beam["y"], beam["end_x"], beam["end_y"], pb, beam["half_width"] * .72):
                beam["touched"] = True
                self.hurt_player()
        self.beams = [beam for beam in self.beams if not beam["dead"]]
        if circle_rect(p.x, p.y - 55, 16, bb):
            self.hurt_player()

    def _move_player(self, dt, inputs, can_dash):
        p = self.player
        self.jump_buffer = max(0, self.jump_buffer - dt)
        self.coyote = .11 if p.on_ground else max(0, self.coyote - dt)
        direction = int(bool(inputs.get("right"))) - int(bool(inputs.get("left")))
        p.crouch = bool(inputs.get("down")) and p.on_ground and p.dash <= 0
        if direction and p.dash <= 0:
            p.facing = direction
        p.aim_x = direction if inputs.get("up") else p.facing
        p.aim_y = -1 if inputs.get("up") else 0
        if inputs.get("down") and inputs.get("up"):
            p.aim_x, p.aim_y = p.facing, 0
        if self.dash_requested:
            self.dash_requested = False
            if can_dash and p.dash_cooldown <= 0:
                p.dash, p.dash_cooldown = RULES.dash_time, RULES.dash_cooldown
                p.dash_direction, p.vy = direction or p.facing, 0
                self.stats["dashes"] += 1
                self.event("dash", x=p.x, y=p.y)
        if self.jump_buffer > 0 and self.coyote > 0 and p.dash <= 0:
            p.vy, p.on_ground, p.jump_age = -RULES.jump_speed, False, 0
            self.coyote = self.jump_buffer = 0
            self.event("jump", x=p.x, y=p.y)
        if p.dash > 0:
            p.dash = max(0, p.dash - dt)
            p.vx = p.dash_direction * RULES.dash_speed
        else:
            target = direction * (115 if p.crouch else RULES.player_speed)
            rate = 2700 if direction else 3300
            p.vx += clamp(target - p.vx, -rate * dt, rate * dt)
            p.vy += RULES.gravity * dt
        p.x = clamp(p.x + p.vx * dt, 53, 860 if self.boss.phase >= 3 else 920)
        p.y += p.vy * dt
        if p.y >= FLOOR:
            if not p.on_ground and p.vy > 180:
                p.land_time = .16
                self.event("land", x=p.x, y=FLOOR)
            p.y, p.vy, p.on_ground = FLOOR, 0, True
        else:
            p.on_ground = False
            p.jump_age += dt

    def _shoot(self):
        p = self.player
        norm = hypot(p.aim_x, p.aim_y) or 1
        ax, ay = p.aim_x / norm, p.aim_y / norm
        muzzle = ((p.x + 28 * p.facing, p.y - 141) if ay < -.9 else
                  (p.x + 66 * (-1 if ax < 0 else 1), p.y - (54 if p.crouch else 83)))
        if self.muzzle_provider:
            supplied = self.muzzle_provider()
            if supplied and all(isfinite(n) for n in supplied):
                muzzle = supplied
        self.shots.append(dict(x=muzzle[0], y=muzzle[1], vx=ax * RULES.shot_speed,
                               vy=ay * RULES.shot_speed, r=9, life=1.4, dead=False))
        self.shots = self.shots[-70:]
        self.stats["shots"] += 1
        self.event("shoot", x=muzzle[0], y=muzzle[1], ax=ax, ay=ay)

    def damage_boss(self, amount):
        if self.state != "playing" or not isfinite(amount) or amount <= 0:
            return
        b = self.boss
        b.hp, b.flash = max(0, b.hp - amount), .07
        if b.hp <= 0:
            self.state, self.state_time = "victory", 0
            self.fire, self.beams, self.scheduled, self.warnings, self.shots = [], [], [], [], []
            b.mouth_lock = None
            self._clear_horizontal()
            self.event("victory")
            return
        if b.phase < 3 and b.hp <= b.max_hp * .5:
            b.phase, self.state, self.state_time = 3, "transform", 0
            b.transform = b.cast = b.charge = 0
            b.attack_type, b.mouth_lock = "", None
            self.fire, self.beams, self.shots, self.scheduled, self.warnings = [], [], [], [], []
            self.pattern_index = self.breath_count = self.horizontal_count = 0
            self._clear_horizontal()
            self.event("transform")
            return
        phase = 4 if b.hp <= b.max_hp * .25 else 2 if b.hp <= b.max_hp * .75 else 1
        if phase > b.phase:
            b.phase = phase
            self.attack_timer = max(self.attack_timer, .9)
            self.event("phase", phase=phase)

    def hurt_player(self):
        p = self.player
        if self.state != "playing" or self.invincible or p.invulnerable > 0 or p.dash > 0:
            return False
        p.hp, p.invulnerable, p.vx = max(0, p.hp - 1), RULES.hurt_invulnerability, -p.facing * 110
        self.event("hurt", x=p.x, y=p.y - 60, hp=p.hp)
        if not p.hp:
            self.state, self.state_time = "dead", 0
            self.beams, self.scheduled, self.warnings = [], [], []
            self.boss.mouth_lock = None
            self._clear_horizontal()
            self.event("death")
        return True

    def _update_attacks(self, dt):
        self.attack_timer -= dt
        for warning in self.warnings:
            warning["remaining"] -= dt
            if not warning["fired"]:
                self.boss.charge = clamp(1 - warning["remaining"] / warning["total"], 0, 1)
            if warning["remaining"] <= 0 and not warning["fired"]:
                warning["fired"] = True
                self._release(warning)
        self.warnings = [w for w in self.warnings if w["remaining"] > -.15]
        for scheduled in self.scheduled:
            scheduled["delay"] -= dt
            if scheduled["delay"] <= 0 and not scheduled["fired"]:
                scheduled["fired"] = True
                self._launch(scheduled)
        self.scheduled = [s for s in self.scheduled if not s["fired"]]
        if (self.attack_timer <= 0 and not self.beams and
                not any(f["kind"] == "giant" for f in self.fire) and
                not self.boss.horizontal and
                not any(not w["fired"] for w in self.warnings)):
            self.prepare_attack()

    def prepare_attack(self, forced_type=None):
        phase = self.boss.phase
        sequence = (["horizontal", "giant", "flame", "fan", "horizontal", "aimed", "steps", "sine", "bounce", "burst"] if phase < 3 else
                    ["horizontal", "giant", "flame", "rain", "horizontal", "bounce", "fan", "burst", "sine", "aimed", "steps"])
        kind = forced_type or sequence[self.pattern_index % len(sequence)]
        if not forced_type:
            self.pattern_index += 1
        duration = ((1.1 if phase < 3 else 1.05) if kind == "flame" else
                    (1 if phase < 3 else .9) if kind in ("giant", "horizontal") else
                    (0, .9, .85, .8, .75)[phase])
        if self.boss.horizontal:
            self._clear_horizontal()
        mx, my = self.mouth()
        tx, ty = self.player.x, self.player.y - 58
        w = dict(type=kind, remaining=duration, total=duration, x=mx, y=my,
                 angle=atan2(ty - my, tx - mx), phase=phase, target_x=tx, target_y=ty, fired=False)
        if kind in ("flame", "giant", "rain", "horizontal"):
            self.fire, self.beams, self.scheduled, self.warnings = [], [], [], []
        if kind == "flame":
            w["mode"] = "low" if self.breath_count % 2 == 0 else "high"
            self.breath_count += 1
            w["target_y"] = FLOOR - (18 if w["mode"] == "low" else 165)
            w["angle"] = atan2(w["target_y"] - my, tx - mx)
            w["end_x"], w["end_y"] = 20, my + tan(w["angle"]) * (20 - mx)
            w["half_width"] = 22
            w["guidance"] = "RAJADA BAIXA — PREPARE O PULO" if w["mode"] == "low" else "RAJADA ALTA — FIQUE NO CHÃO"
            self.boss.mouth_lock = mx, my
        elif kind == "giant":
            w["target_y"] = self.player.y - 32
            w["angle"] = atan2(w["target_y"] - my, tx - mx)
            w["guidance"] = "BOLA GIGANTE — PULE OU DESVIE!"
            self.boss.mouth_lock = mx, my
        else:
            self.boss.mouth_lock = None
        if kind == "horizontal":
            first = "low" if (self.horizontal_count % 2 == 0) == (phase < 3) else "high"
            self.horizontal_count += 1
            count, speed = (3 if phase % 2 else 4), (0, 520, 560, 600, 640)[phase]
            rows = []
            for i in range(1 if phase < 3 else 2):
                mode = first if i == 0 else ("low" if first == "high" else "high")
                rows.append(dict(index=i, mode=mode, y=594 if mode == "low" else 538,
                                 start=i * .78, count=count, spacing=.13 if count == 3 else .12, speed=speed))
            w.update(rows=rows, mode=first, lane_y=rows[0]['y'], angle=3.141592653589793)
            w['guidance'] = 'RAJADA ALTA — AGACHE' if first == 'high' else 'RAJADA BAIXA — PULO OU DASH'
            if len(rows) > 1:
                w['guidance'] += ' · DEPOIS BAIXA' if first == 'high' else ' · DEPOIS ALTA'
            self.boss.horizontal = dict(phase='windup', rows=rows, elapsed=0., row_index=0)
            self._dip_to(w['lane_y'], .32)
        if kind == "rain":
            # Math.round do JavaScript: os empates positivos arredondam para cima.
            lane = clamp(int((self.player.x - 65) / 130 + .5), 1, 5)
            w["safe_x"], w["safe_width"] = 65 + lane * 130, 280
            w["lanes"] = [65 + i * 130 for i in range(7) if abs(65 + i * 130 - w["safe_x"]) > 145]
        self.warnings.append(w)
        b = self.boss
        b.cast, b.attack_type, b.attack_mode = duration + .4, kind, w.get("mode", "")
        b.attack_age = b.charge = 0
        self.attack_timer = 2.7 if kind == "rain" else (0, 2.4, 2.2, 2.05, 1.9)[phase]
        self.event("telegraph", attack_type=kind, mode=w.get("mode"))
        return w

    def _release(self, w):
        w["fired"] = True
        phase, kind = w["phase"], w["type"]
        speed = (0, 320, 350, 390, 430)[phase]
        self.boss.charge = self.boss.attack_age = 0

        def schedule(delay, **config):
            self.scheduled.append(dict(delay=delay, phase=phase, fired=False, **config))

        if kind == "horizontal":
            if not self.boss.horizontal:
                self.boss.horizontal = dict(phase='windup', rows=w['rows'], elapsed=0., row_index=0)
                self._dip_to(w['rows'][0]['y'], .01)
            self.boss.horizontal.update(phase='firing', elapsed=0.)
            self.boss.cast = .4
            for row in w['rows']:
                if row['index']:
                    schedule(row['start'] - .34, pose_y=row['y'], row=row['index'])
                for i in range(row['count']):
                    schedule(row['start'] + i * row['spacing'], kind='horizontal', lane_y=row['y'],
                             row=row['index'], mode=row['mode'], vx=-row['speed'], vy=0, r=14)
        elif kind == "flame":
            self.fire, self.scheduled = [], []
            self.beams.append(dict(x=w["x"], y=w["y"], end_x=w["end_x"], end_y=w["end_y"],
                                   angle=w["angle"], age=0., duration=.5, half_width=w["half_width"],
                                   mode=w["mode"], touched=False, dead=False))
            self.boss.cast = .65
        elif kind == "giant":
            self.fire, self.scheduled = [], []
            schedule(0, x=w["x"], y=w["y"], angle=w["angle"], speed=500 if phase < 3 else 580, r=44, kind="giant")
            self.boss.cast = .65
        elif kind == "fan":
            count = (0, 4, 5, 6, 7)[phase]
            for i in range(count):
                schedule(0, angle=w["angle"] + (i - (count - 1) / 2) * .23, speed=speed, r=14 if phase < 3 else 15)
        elif kind in ("aimed", "burst"):
            for i in range((0, 2, 3, 3, 4)[phase]):
                schedule(i * .24, angle=w["angle"], speed=speed, r=14)
        elif kind == "steps":
            for i in range(2 if phase < 3 else 3):
                schedule(i * .32, angle=atan2(FLOOR - (180 if i % 2 else 38) - w["y"], w["target_x"] - w["x"]), speed=speed, r=14)
        elif kind == "sine":
            count = (0, 3, 4, 4, 5)[phase]
            for i in range(count):
                schedule(i * .20, angle=w["angle"] + (i - (count - 1) / 2) * .15, speed=speed,
                         kind="sine", amplitude=(0, 23, 26, 29, 32)[phase], frequency=4.4, r=14)
        elif kind == "bounce":
            for i in range(1 if phase < 3 else 2):
                schedule(i * .34, kind="bounce", vx=-225 if phase < 3 else -240, vy=-145, gravity=440, bounces=1, r=18)
        elif kind == "rain":
            for x in w["lanes"]:
                schedule(0, x=x, y=68, vx=0, vy=240 if phase < 3 else 260, r=14, kind="rain")
        self.event("attack", attack_type=kind, x=w["x"], y=w["y"])

    def _launch(self, scheduled):
        if 'pose_y' in scheduled:
            if self.boss.horizontal:
                self.boss.horizontal['row_index'] = scheduled['row']
                self._dip_to(scheduled['pose_y'], .3)
            return
        if len(self.fire) >= 40:
            return
        s = scheduled
        self.boss.cast = max(self.boss.cast, .3)
        mx, my = self.mouth()
        if s.get('kind') == 'horizontal':
            self.boss.pulse = .09
            self.event('horizontal_shot', x=mx, y=my, mode=s['mode'], row=s['row'])
        angle, speed = s.get("angle", 0), s.get("speed", 0)
        self.fire.append(dict(x=s.get("x", mx), y=s.get("y", my), base_y=s.get("y", my),
                              vx=s.get("vx", cos(angle) * speed), vy=s.get("vy", sin(angle) * speed),
                              r=s.get("r", 16), kind=s.get("kind", "orb"), mode=s.get('mode'), row=s.get('row'), gravity=s.get("gravity", 0),
                              bounces=s.get("bounces", 0), amplitude=s.get("amplitude", 0),
                              frequency=s.get("frequency", 0), age=0., dead=False))
