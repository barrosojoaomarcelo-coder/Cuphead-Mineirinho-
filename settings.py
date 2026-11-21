"""Configurações da janela e teclas. A dificuldade do dragão fica em engine.py."""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent
TITLE = 'Mineirinho — A Fornalha do Castelo'
WIDTH, HEIGHT = 1280, 720
WINDOW_SIZE = (1152, 648)
FPS = 60
PHYSICS_STEP = 1 / 120
ACTION_KEYS = {
    pygame.K_LEFT:'left', pygame.K_a:'left', pygame.K_RIGHT:'right', pygame.K_d:'right',
    pygame.K_UP:'up', pygame.K_w:'up', pygame.K_DOWN:'down', pygame.K_s:'down',
    pygame.K_SPACE:'jump', pygame.K_z:'jump', pygame.K_j:'shoot', pygame.K_x:'shoot',
    pygame.K_LSHIFT:'dash', pygame.K_RSHIFT:'dash', pygame.K_k:'dash',
}
