"""Modelo executável para sua próxima fase. Não altera o dragão nem o menu.

Copie este arquivo, renomeie a classe e registre-a em levels/__init__.py.
O exemplo só move um boneco até a porta: substitua-o por sua própria fase.
"""
import pygame
from .base import BaseLevel


class TemplateLevel(BaseLevel):
    id = 'modelo'
    number = 0
    title = 'Modelo de fase'
    subtitle = 'Substitua cenário, obstáculos e inimigos aqui'
    available = False

    def __init__(self):
        super().__init__()
        self.font = pygame.font.SysFont('arial', 25, bold=True)
        self.start()

    def start(self):
        super().start()
        self.pos = pygame.Vector2(140, 610)
        self.velocity_y = 0.
        self.previous_jump = False

    def update(self, dt, inputs):
        if self.state != 'playing':
            return []
        dt = min(dt, .1)
        self._elapsed += dt
        direction = int(bool(inputs.get('right'))) - int(bool(inputs.get('left')))
        self.pos.x = max(30, min(1240, self.pos.x + direction * 310 * dt))
        jump = bool(inputs.get('jump'))
        if jump and not self.previous_jump and self.pos.y >= 610:
            self.velocity_y = -650
        self.previous_jump = jump
        self.velocity_y += 1850 * dt
        self.pos.y = min(610, self.pos.y + self.velocity_y * dt)
        if self.pos.y >= 610:
            self.velocity_y = 0
        if self.pos.x >= 1160:
            self._state = 'victory'
            return [dict(type='victory')]
        return []

    def draw(self, target, debug=False):
        target.fill('#a5c0bd')
        pygame.draw.rect(target, '#6c8a59', (0, 610, 1280, 110))
        pygame.draw.line(target, '#38201e', (0, 610), (1280, 610), 6)
        pygame.draw.rect(target, '#f4cd78', (1140, 520, 90, 90), border_radius=8)
        pygame.draw.rect(target, '#38201e', (1140, 520, 90, 90), 5, border_radius=8)
        player = pygame.Rect(round(self.pos.x)-20, round(self.pos.y)-68, 40, 68)
        pygame.draw.rect(target, '#613f87', player, border_radius=10)
        pygame.draw.circle(target, '#f5c59d', (round(self.pos.x), round(self.pos.y)-72), 22)
        for i, text in enumerate((self.title, 'MODELO DE DESENVOLVIMENTO', 'A/D move · Espaço pula · Chegue à porta para testar a vitória')):
            image = self.font.render(text, True, '#38201e')
            target.blit(image, image.get_rect(center=(640, 180 + i*45)))
        if debug:
            pygame.draw.rect(target, 'cyan', player, 2)
