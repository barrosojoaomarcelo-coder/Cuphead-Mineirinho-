"""Desenho da arena e das animações com as artes originais do jogo."""
import json
from math import atan2, cos, exp, hypot, pi, sin
from pathlib import Path

import pygame

from engine import FLOOR, RULES, clamp


ROOT = Path(__file__).resolve().parent
PLAYER_SIZE = 174
INK, CREAM, GOLD = "#38201e", "#fff0bd", "#f9bc62"


def player_pose(player):
    """Escolhe ação e quadro; o mesmo cálculo também posiciona o tiro no dedo."""
    p = player
    if p.dash > 0:
        return "06_dash", 1 if p.dash > .09 else 2
    if p.shooting and p.aim_y < 0:
        return ("09_atirar_diagonal" if p.aim_x else "05_atirar_cima"), int(p.anim_time * 19) % 4
    if p.crouch:
        return ("08_pular_atirar", 1) if p.shooting else ("06_dash", 2)
    if not p.on_ground:
        frame = 2 if p.jump_age < .09 else 3 if p.vy < -200 else 4 if abs(p.vy) <= 200 else 5
        return ("08_pular_atirar" if p.shooting else "03_pulo"), frame
    if p.land_time > 0:
        return ("08_pular_atirar" if p.shooting else "03_pulo"), 6 if p.land_time > .08 else 7
    if abs(p.vx) > 38:
        return ("07_correr_atirar" if p.shooting else "02_corrida"), int(p.anim_time * 14) % 8
    if p.shooting:
        return "04_atirar_frente", int(p.anim_time * 19) % 4
    t = p.anim_time % 3.3
    return "01_parado", 0 if t < 2.75 else 1 if t < 2.9 else 2 if t < 3.05 else 3


class Scene:
    def __init__(self, model):
        self.model = model
        self.manifest = json.loads((ROOT / "assets/manifest.json").read_text(encoding="utf-8"))
        self.fonts = {}
        self.player_frames, self.boss_frames = {}, {}
        self.images = {}
        self.time = 0.
        self.entered_at = 0.
        self.last_state = ""
        self.particles = []
        self.shake = self.hurt_flash = 0.
        for action, spec in self.manifest["player"]["actions"].items():
            self.player_frames[action] = self.load_sheet(spec, PLAYER_SIZE)
        for form, spec in self.manifest["dragon"].items():
            self.boss_frames[form] = self.load_sheet(spec, 442)
        for name, url in self.manifest["background"].items():
            self.images[name] = pygame.image.load(str(ROOT / url)).convert()
        bread = pygame.image.load(str(ROOT / self.manifest["bread"]["url"])).convert_alpha()
        self.bread = pygame.transform.smoothscale(bread, (22, 22))
        self.model.muzzle_provider = self.actual_muzzle
        self.vignette = pygame.Surface((1280, 720), pygame.SRCALPHA)
        # Bordas suaves, calculadas uma vez, em vez de a cada quadro.
        for i in range(40):
            pygame.draw.rect(self.vignette, (28, 13, 16, int(28 * (1 - i / 40))),
                             (i * 3, i * 2, 1280 - i * 6, 720 - i * 4), 3)

    def font(self, size, serif=False):
        key = size, serif
        if key not in self.fonts:
            family = ("georgia", "dejavuserif", "serif") if serif else ("arial", "dejavusans", "sans")
            self.fonts[key] = pygame.font.SysFont(family, size, bold=True)
        return self.fonts[key]

    def text(self, target, text, pos, size=22, color=CREAM, center=False, serif=False, outline=False):
        font = self.font(size, serif)
        label = font.render(text, True, color)
        rect = label.get_rect(center=pos) if center else label.get_rect(topleft=pos)
        if outline:
            shadow = font.render(text, True, INK)
            for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2), (-3, 0), (3, 0), (0, -3), (0, 3)):
                target.blit(shadow, rect.move(dx, dy))
        target.blit(label, rect)
        return rect

    def load_sheet(self, spec, size):
        sheet = pygame.image.load(str(ROOT / spec["url"])).convert_alpha()
        cell = spec.get("cell", 256)
        frames = []
        for i in range(spec["count"]):
            source = sheet.subsurface((i % spec["cols"] * cell, i // spec["cols"] * cell, cell, cell))
            frame = pygame.transform.smoothscale(source, (size, size))
            frames.append((frame, pygame.transform.flip(frame, True, False)))
        return frames

    def actual_muzzle(self):
        action, frame = player_pose(self.model.player)
        muzzle = self.manifest["player"]["actions"][action]["muzzles"][frame]
        if muzzle is None:
            return None
        p = self.model.player
        px, py = self.manifest["player"]["pivot"]
        scale = PLAYER_SIZE / self.manifest["player"]["cell"]
        squash = .78 if p.crouch and p.on_ground else 1
        return p.x + (muzzle[0] - px) * scale * p.facing, p.y + (muzzle[1] - py) * scale * squash

    def emit(self, x, y, count, color):
        for i in range(count):
            if len(self.particles) >= 170:
                break
            angle = i / count * pi * 2 + sin(self.time * 19 + i) * .5
            speed = 40 + (i * 37) % 110
            life = .3 + (i % 5) * .08
            self.particles.append(dict(x=x, y=y, vx=cos(angle) * speed,
                                       vy=sin(angle) * speed - 30, life=life, maximum=life,
                                       r=3 + i % 5, color=color))

    def process_events(self, events):
        for event in events:
            kind = event["type"]
            if kind == "start":
                self.particles.clear()
                self.shake = self.hurt_flash = 0
            if kind in ("shoot", "hit", "jump", "land", "dash", "hurt"):
                count = {"shoot": 2, "hit": 3, "jump": 6, "land": 7, "dash": 9, "hurt": 13}[kind]
                self.emit(event["x"], event["y"], count, "#fff2bc" if kind in ("shoot", "hit", "hurt") else "#ddcba7")
            if kind == "hurt":
                self.shake, self.hurt_flash = .26, .12
            if kind == 'horizontal_shot':
                self.emit(event['x'], event['y'], 2, '#ffce79')
            if kind == "transform":
                self.shake = .4
            if kind == "victory":
                for i in range(8):
                    self.emit(850 + i * 36, 270 + (i % 3) * 45, 12, (GOLD, CREAM, "#e76240")[i % 3])

    def update(self, dt):
        if self.model.state != "paused":
            self.time += dt
            self.shake, self.hurt_flash = max(0, self.shake - dt), max(0, self.hurt_flash - dt)
            for p in self.particles:
                p["life"] -= dt
                p["x"], p["y"] = p["x"] + p["vx"] * dt, p["y"] + p["vy"] * dt
                p["vy"] += 30 * dt
            self.particles = [p for p in self.particles if p["life"] > 0]
        if self.model.state != self.last_state:
            self.last_state, self.entered_at = self.model.state, self.time

    def draw_background(self, target):
        m = self.model
        target.blit(self.images["day"], (0, 0))
        if m.night > 0:
            self.images["night"].set_alpha(round(255 * m.night))
            target.blit(self.images["night"], (0, 0))
        target.blit(self.vignette, (0, 0))

    def draw(self, target, hitboxes=False):
        m = self.model
        self.draw_background(target)
        self.draw_boss(target)
        self.draw_warnings(target)
        self.draw_player(target)
        for shot in m.shots:
            bread = pygame.transform.rotate(self.bread, -(1.4 - shot["life"]) * 14 * 180 / pi)
            target.blit(bread, bread.get_rect(center=(shot["x"], shot["y"])))
        for beam in m.beams:
            self.draw_beam(target, beam)
        for fire in m.fire:
            self.draw_fire(target, fire)
        for p in self.particles:
            color = pygame.Color(p["color"])
            radius = max(1, int(p["r"] * p["life"] / p["maximum"]))
            pygame.draw.circle(target, color, (p["x"], p["y"]), radius)
        if m.state == "intro":
            self.banner(target, "VAI COMEÇAR!", "DRAGÃO VERMELHO · PRIMEIRO ATO",
                        min(1, m.state_time * 3, max(0, (1.7 - m.state_time) * 3)))
        if m.state == "transform" and .2 < m.boss.transform < .8:
            self.banner(target, "O DESPERTAR", "A NOITE CHEGOU AO CASTELO",
                        sin((m.boss.transform - .2) / .6 * pi))
        if self.hurt_flash > 0:
            flash = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            flash.fill((255, 237, 197, int(self.hurt_flash * 190)))
            target.blit(flash, (0, 0))
        if hitboxes:
            pygame.draw.rect(target, "cyan", pygame.Rect(m.player_box()), 2)
            pygame.draw.rect(target, "magenta", pygame.Rect(m.boss_box()), 2)
            for fire in m.fire:
                pygame.draw.circle(target, "cyan", (fire["x"], fire["y"]), int(fire["r"] * (.5 if fire["kind"] == "giant" else .76)), 1)

    def banner(self, target, title, subtitle, alpha=1):
        layer = pygame.Surface((1280, 720), pygame.SRCALPHA)
        self.text(layer, title, (640, 285), 65, center=True, serif=True, outline=True)
        self.text(layer, subtitle, (640, 340), 20, center=True, outline=True)
        layer.set_alpha(int(clamp(alpha, 0, 1) * 255))
        target.blit(layer, (0, 0))

    def draw_boss(self, target):
        m, b = self.model, self.model.boss
        transforming = m.state == "transform"
        form = "head" if b.phase >= 3 else "base"
        if transforming and b.transform < .52:
            form = "base"
        warning = next((w for w in m.warnings if not w["fired"] and w["remaining"] > 0), None)
        if m.beams:
            frame = 6
        elif warning:
            frame = 4 if warning["remaining"] / warning["total"] > .42 else 5
        elif b.cast > 0:
            frame = 6 if b.cast > .1 else 7
        else:
            frame = int(self.time * (7 if form == "base" else 5)) % 4
        if b.horizontal and b.horizontal['phase'] == 'firing':
            frame = 6 if b.pulse > .025 else 7
        image = self.boss_frames[form][frame][0]
        alpha = max(0, 1 - (self.time - self.entered_at) / 2) if m.state == "victory" else 1
        scale = 1
        if transforming:
            alpha *= (1 - clamp(b.transform / .55, 0, 1) if form == "base" else
                      clamp((b.transform - .48) / .3, 0, 1))
            if form == "base":
                scale = 1 + b.transform * .35
        stretch_x = stretch_y = 1
        if warning and warning["type"] in ("giant", "flame"):
            charge = clamp(1 - warning["remaining"] / warning["total"], 0, 1)
            stretch_x += charge * .045 + sin(self.time * 12) * charge * .006
            stretch_y += charge * .012
        if m.beams:
            stretch_x, stretch_y = .977 + sin(self.time * 29) * .006, 1.025
        elif not warning and b.cast > 0 and b.attack_type == "giant":
            recoil = exp(-b.attack_age * 9)
            stretch_x, stretch_y = 1 - recoil * .065, 1 + recoil * .025
        image = pygame.transform.smoothscale(image, (int(442 * scale * stretch_x), int(442 * scale * stretch_y)))
        if b.flash > 0:
            image.fill((70, 60, 45, 0), special_flags=pygame.BLEND_RGBA_ADD)
        image.set_alpha(int(alpha * 255))
        bob = m.boss_offset_y()
        x, y = (858 if form == "base" else 902), (181 if form == "base" else 158) + bob
        target.blit(image, image.get_rect(center=(x + 221, y + 221)))
        if b.cast > 0 or transforming:
            mx, my = m.mouth()
            glow = pygame.Surface((140, 140), pygame.SRCALPHA)
            for radius in range(55, 2, -4):
                pygame.draw.circle(glow, (255, 145 + radius, 55, 6), (70, 70), radius)
            target.blit(glow, (mx - 70, my - 70))
        if warning and warning["type"] == "giant":
            mx, my = m.mouth()
            charge = clamp(1 - warning["remaining"] / warning["total"], 0, 1)
            self.draw_orb(target, mx, my, 8 + charge * 33, warning["angle"], True, True)
        if b.horizontal and b.horizontal['phase'] == 'firing' and b.pulse > .025:
            mx, my = m.mouth()
            pygame.draw.polygon(target, '#ffc85c', [(mx+3,my-9), (mx-17,my-13), (mx-31,my), (mx-17,my+12), (mx+3,my+8)])
        if b.dip_active:
            # O corpo fica atrás do piso enquanto o dragão abaixa a cabeça.
            old_clip = target.get_clip()
            target.set_clip(pygame.Rect(830, FLOOR, 450, 720-FLOOR).clip(old_clip))
            self.draw_background(target)
            target.set_clip(old_clip)

    def draw_player(self, target):
        p = self.model.player
        action, frame = player_pose(p)
        image = self.player_frames[action][frame][int(p.facing < 0)]
        squash = .78 if p.crouch and p.on_ground else 1
        if squash != 1:
            image = pygame.transform.smoothscale(image, (PLAYER_SIZE, round(PLAYER_SIZE * squash)))
        scale = PLAYER_SIZE / self.manifest["player"]["cell"]
        px, py = self.manifest["player"]["pivot"]
        shadow = pygame.Surface((90, 16), pygame.SRCALPHA)
        width = 84 if p.on_ground else int(clamp(84 - (FLOOR - p.y) * .1, 36, 84))
        pygame.draw.ellipse(shadow, (20, 13, 20, 56), (45 - width // 2, 3, width, 10))
        target.blit(shadow, (p.x - 45, FLOOR - 5))
        if p.invulnerable > 0 and int(self.time * 16) % 2 == 0 or self.model.state == "dead":
            image = image.copy()
            image.set_alpha(98 if self.model.state != "dead" else 122)
        left = p.x - (px * scale if p.facing > 0 else PLAYER_SIZE - px * scale)
        target.blit(image, (left, p.y - py * scale * squash))
        if p.dash_cooldown > 0:
            progress = 1 - p.dash_cooldown / RULES.dash_cooldown
            pygame.draw.arc(target, CREAM, (p.x - 10, p.y + 5, 20, 20), pi / 2 - pi * 2 * progress, pi / 2, 3)

    @staticmethod
    def dashed_line(target, color, start, end, width=2, dash=12, gap=10):
        a, b = pygame.Vector2(start), pygame.Vector2(end)
        direction = b - a
        length = direction.length()
        if not length:
            return
        direction /= length
        for distance in range(0, int(length), dash + gap):
            pygame.draw.line(target, color, a + direction * distance, a + direction * min(distance + dash, length), width)

    def draw_warnings(self, target):
        for w in self.model.warnings:
            if w["fired"]:
                continue
            layer = pygame.Surface((1280, 720), pygame.SRCALPHA)
            strength = clamp(1 - w["remaining"] / w["total"], 0, 1)
            color = (255, 205, 87, int((.35 + strength * .45) * 255))
            start = w["x"], w["y"]
            if w["type"] == "rain":
                for x in w["lanes"]:
                    self.dashed_line(layer, color, (x, 55), (x, FLOOR - 5))
                    pygame.draw.polygon(layer, color, [(x - 7, 70), (x + 7, 70), (x, 83)])
                pygame.draw.rect(layer, (212, 219, 176, 50), (w["safe_x"] - w["safe_width"] / 2, FLOOR - 5, w["safe_width"], 9))
            elif w["type"] == "horizontal":
                for row in w['rows']:
                    lane_color = (255, 190, 85, 205 if row['index'] == 0 else 100)
                    self.dashed_line(layer, lane_color, (self.model.mouth()[0], row['y']), (35, row['y']), 3)
                    pygame.draw.polygon(layer, lane_color, [(35,row['y']), (50,row['y']-7), (50,row['y']+7)])
            elif w["type"] == "flame":
                end = w["end_x"], w["end_y"]
                pygame.draw.line(layer, (255, 158, 55, int(28 + strength * 30)), start, end, w["half_width"] * 2)
                self.dashed_line(layer, color, start, end, 3, 15, 11)
            elif w["type"] == "giant":
                end = w["x"] + cos(w["angle"]) * 1200, w["y"] + sin(w["angle"]) * 1200
                self.dashed_line(layer, color, start, end)
            else:
                for angle in (w["angle"] - .12, w["angle"] + .12):
                    self.dashed_line(layer, color, start, (w["x"] + cos(angle) * 200, w["y"] + sin(angle) * 200))
            target.blit(layer, (0, 0))
            if w.get("guidance"):
                jump_now = w["type"] == "flame" and w["mode"] == "low" and w["remaining"] < .2
                text = "PULE AGORA!" if jump_now else w["guidance"]
                self.text(target, text, (600, 100), 29 if jump_now else 22, center=True, outline=True)
        h = self.model.boss.horizontal
        if h and h['phase'] == 'firing' and len(h['rows']) > 1 and .3 < h['elapsed'] < h['rows'][1]['start']:
            row = h['rows'][1]
            self.dashed_line(target, '#dcb46c', (self.model.mouth()[0],row['y']), (40,row['y']))
            self.text(target, 'DEPOIS: AGACHE' if row['mode']=='high' else 'DEPOIS: PULO OU DASH', (600,100), 22, center=True, outline=True)

    def draw_orb(self, target, x, y, radius, angle, giant=False, charging=False):
        radius = max(1, radius)
        center = pygame.Vector2(x, y)
        direction = pygame.Vector2(cos(angle), sin(angle))
        normal = pygame.Vector2(-direction.y, direction.x)
        tail = radius * 2.7 if giant else radius + 25
        if not charging:
            points = [center + normal * radius * .65,
                      center - direction * tail - normal * radius * .25,
                      center - direction * tail * .6,
                      center - direction * tail * .9 + normal * radius * .7,
                      center - normal * radius * .75]
            pygame.draw.polygon(target, "#351b20", points)
            pygame.draw.polygon(target, "#ef6327", [center + (p - center) * .9 for p in points])
        edge = []
        for i in range(40):
            a = i / 40 * pi * 2
            r = radius * (1 + sin(a * 7 + self.time * 13) * .045)
            edge.append((x + cos(a) * r, y + sin(a) * r))
        pygame.draw.polygon(target, "#351b20", edge)
        pygame.draw.circle(target, "#f68a2c", (x, y), max(1, int(radius - 3)))
        pygame.draw.circle(target, "#ffcc55", (x, y), max(1, int(radius * .72)))
        pygame.draw.circle(target, "#fff0b5", (x + radius * .16, y - radius * .07), max(1, int(radius * .4)))

    def draw_fire(self, target, fire):
        self.draw_orb(target, fire["x"], fire["y"], fire["r"], atan2(fire["vy"], fire["vx"]), fire["kind"] == "giant")

    def draw_beam(self, target, beam):
        start = pygame.Vector2(beam["x"], beam["y"])
        delta = pygame.Vector2(beam["end_x"], beam["end_y"]) - start
        length = delta.length()
        if not length:
            return
        direction = delta / length
        normal = pygame.Vector2(-direction.y, direction.x)
        extent = length * clamp(beam["age"] / .075, 0, 1)
        closing = clamp((beam["duration"] - beam["age"]) / .09, 0, 1)
        for factor, color in ((1.12, "#32191c"), (1, "#ed6629"), (.66, "#ffbb43"), (.29, "#fff0ae")):
            top, bottom = [], []
            for i in range(26):
                t = i / 25
                width = (8 + beam["half_width"] * 1.1 * t) * factor * closing
                wiggle = sin(t * 29 - self.time * 25) * width * .17
                center = start + direction * (t * extent)
                top.append(center + normal * (-width + wiggle))
                bottom.append(center + normal * (width + sin(t * 31 - self.time * 22 + 1) * width * .17))
            pygame.draw.polygon(target, color, [start, *top, start + direction * (extent + 12 * factor), *reversed(bottom)])
