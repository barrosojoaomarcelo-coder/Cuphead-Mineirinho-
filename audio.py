"""Sons sintetizados localmente: não requer arquivos de áudio nem NumPy."""
from array import array
from math import pi, sin

import pygame


class Audio:
    def __init__(self, enabled=True):
        self.available = pygame.mixer.get_init() is not None
        self.enabled = enabled
        self.cache = {}
        self.next_music = 0.
        self.beat = 0
        if self.available:
            pygame.mixer.set_num_channels(24)

    def tone(self, frequency, duration=.08, volume=.03, waveform="triangle", slide=0):
        if not self.available or not self.enabled:
            return
        key = round(frequency, 3), duration, volume, waveform, slide
        if key not in self.cache:
            rate, sample_format, channels = pygame.mixer.get_init()
            samples = array("h")
            phase = 0.
            for i in range(int(rate * duration)):
                t = i / rate
                progress = t / duration
                f = max(30, frequency + slide * progress)
                phase += f / rate
                wave = 4 * abs(phase % 1 - .5) - 1 if waveform == "triangle" else 2 * (phase % 1) - 1
                envelope = min(1, t / .007) * (1 - progress) ** 2
                value = int(wave * envelope * volume * 32767)
                samples.extend([value] * channels)
            self.cache[key] = pygame.mixer.Sound(buffer=samples)
        self.cache[key].play()

    def process(self, events):
        sounds = {
            "shoot": (700, .035, .018, "triangle", -130),
            "jump": (270, .13, .04, "triangle", 360),
            "dash": (200, .1, .027, "saw", -130),
            "hurt": (170, .2, .045, "saw", -100),
            "transform": (70, 1.2, .04, "saw", 60),
            "phase": (150, .25, .03, "triangle", 180),
            "death": (230, .65, .04, "triangle", -180),
            "victory": (520, .6, .04, "triangle", 260),
            "horizontal_shot": (180, .055, .018, "saw", -70),
        }
        for event in events:
            kind = event["type"]
            if kind == "start":
                self.next_music, self.beat = 0, 0
                if self.available:
                    pygame.mixer.stop()
            elif kind in sounds:
                self.tone(*sounds[kind])
            elif kind == "attack":
                flame = event["attack_type"] == "flame"
                self.tone(73 if flame else 95, .5 if flame else .2, .03, "saw", 45)
            elif kind == "telegraph" and event["attack_type"] in ("flame", "giant", "horizontal"):
                self.tone(115, .4, .025, "triangle", -40)
            elif kind == "pause" and self.available:
                pygame.mixer.stop()

    def update(self, dt, model):
        if model.state not in ("intro", "playing", "transform") or not self.enabled:
            return
        self.next_music -= dt
        if self.next_music > 0:
            return
        self.next_music = .21
        night = model.boss.phase >= 3
        base = 130.81 if night else 146.83
        melody = ([0, 3, 7, 10, 7, 3, 2, 5, 9, 12, 9, 5, 0, 3, 7, 2] if night else
                  [0, 4, 7, 12, 11, 7, 4, 2, 0, 4, 9, 12, 9, 4, 2, 7])
        if self.beat % 2 == 0:
            self.tone(base * (.5 if self.beat % 4 == 0 else .75), .14, .022)
        self.tone(base * 2 * 2 ** (melody[self.beat % 16] / 12), .13 if self.beat % 2 else .18, .014)
        self.beat += 1
