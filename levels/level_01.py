"""Primeira fase pronta: dragão, duas formas, dez ataques e castelo dia/noite."""
from engine import GameModel, RULES
from scene import Scene
from settings import PHYSICS_STEP
from .base import BaseLevel


class Level01(BaseLevel):
    id = 'castelo'
    number = 1
    title = 'A Fornalha do Castelo'
    subtitle = 'Enfrente o Dragão Vermelho'
    available = True

    def __init__(self):
        super().__init__()
        self.model = GameModel()
        self.scene = Scene(self.model)
        self.accumulator = 0.

    @property
    def state(self):
        return self.model.state

    @property
    def elapsed(self):
        return self.model.elapsed

    @property
    def lives(self):
        return self.model.player.hp

    @property
    def max_lives(self):
        return RULES.lives

    @property
    def stats(self):
        return self.model.stats

    @property
    def music_model(self):
        return self.model

    @property
    def hud_title(self):
        return 'CHEFE 01 · O DESPERTAR' if self.model.boss.phase >= 3 else 'CHEFE 01 · DRAGÃO VERMELHO'

    def start(self):
        self.accumulator = 0.
        self.model.invincible = False
        self.model.start()
        self.scene.particles.clear()
        self.scene.shake = self.scene.hurt_flash = 0.

    def pause(self):
        self.model.pause()
        self.accumulator = 0.

    def resume(self):
        self.model.resume()
        self.accumulator = 0.

    def update(self, dt, inputs):
        if self.state in ('intro', 'playing', 'transform'):
            self.accumulator += min(dt, .1)
            while self.accumulator + 1e-12 >= PHYSICS_STEP:
                self.model.step(PHYSICS_STEP, inputs)
                self.accumulator = max(0., self.accumulator - PHYSICS_STEP)
        else:
            self.accumulator = 0.
        events = self.model.drain_events()
        self.scene.process_events(events)
        self.scene.update(dt)
        return events

    def draw(self, target, debug=False):
        self.scene.draw(target, debug)
