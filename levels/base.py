"""Contrato simples entre uma fase e os menus. Novas fases não precisam de boss."""
from abc import ABC, abstractmethod


class BaseLevel(ABC):
    id = 'base'
    number = 0
    title = 'Nova fase'
    subtitle = 'Descrição da fase'
    available = True
    music_model = None  # Opcional: objeto esperado pelo sintetizador de áudio.

    def __init__(self):
        self._state = 'title'
        self._elapsed = 0.
        self._lives = 3
        self._stats = dict(shots=0, hits=0, dashes=0)

    @property
    def state(self):
        return self._state

    @property
    def elapsed(self):
        return self._elapsed

    @property
    def lives(self):
        return self._lives

    @property
    def max_lives(self):
        return 3

    @property
    def stats(self):
        return self._stats

    @property
    def hud_title(self):
        return f'FASE {self.number:02} · {self.title.upper()}'

    def start(self):
        """Reiniciar também chama start; zere aqui todo estado da sua fase."""
        self._state, self._elapsed, self._lives = 'playing', 0., self.max_lives
        self._stats = dict(shots=0, hits=0, dashes=0)

    def pause(self):
        if self.state == 'playing':
            self._state = 'paused'

    def resume(self):
        if self.state == 'paused':
            self._state = 'playing'

    @abstractmethod
    def update(self, dt, inputs):
        """Recebe segundos e ações (left/right/jump/shoot/etc.). Retorne eventos []."""

    @abstractmethod
    def draw(self, target, debug=False):
        """Desenhe numa pygame.Surface de 1280×720. A aplicação desenha o HUD."""
