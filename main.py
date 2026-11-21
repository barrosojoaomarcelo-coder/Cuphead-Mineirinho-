#!/usr/bin/env python3
"""ENTRADA DO JOGO — execute este arquivo no terminal do VS Code.

Instalar: python -m pip install -r requirements.txt
Jogar:   python main.py
Fases:   levels/level_01.py, level_02.py, level_03.py e level_template.py
"""
import argparse
import os
from pathlib import Path

os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
try:
    import pygame
except ImportError:
    raise SystemExit('Instale a dependência: python -m pip install -r requirements.txt')

from app import App


def smoke_test(app, image_directory=None):
    """Carrega artes, menus e dez ataques. Use --smoke-test para verificar mudanças."""
    if image_directory:
        image_directory.mkdir(parents=True,exist_ok=True)

    def draw(name):
        app.render()
        if image_directory:
            pygame.image.save(app.canvas,str(image_directory / (name+'.png')))

    draw('menu_inicial')
    app.select_levels()
    draw('selecao_de_fases')
    app.start_level('castelo')
    model=app.level.model
    model.invincible=True
    for phase in (1,2,3,4):
        for attack in ('horizontal','giant','flame','fan','aimed','steps','sine','bounce','burst','rain'):
            model.force_phase(phase)
            model.prepare_attack(attack)
            model.attack_timer=999
            for i in range(150):
                app.update(1/60)
                if i in (20,80,120):
                    app.render()
    model.force_phase(3)
    model.prepare_attack('horizontal')
    model.attack_timer=999
    app.keys={pygame.K_s,pygame.K_j}
    for _ in range(121):
        app.update(1/60)
    draw('rajada_horizontal')
    app.pause()
    draw('pausa')
    app.controls()
    draw('controles')
    pygame.quit()
    print('OK: menu, seleção de fases, pausa, controles, artes e 10 ataques nas 4 etapas.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mute',action='store_true',help='Inicia sem som.')
    parser.add_argument('--debug',action='store_true',help='Habilita F3 para mostrar colisões.')
    parser.add_argument('--smoke-test',action='store_true',help='Verifica menus, imagens e ataques e encerra.')
    parser.add_argument('--screenshots',type=Path,help='Pasta de imagens da verificação --smoke-test.')
    args=parser.parse_args()
    app=App(persistence=not args.smoke_test,sound=not args.mute,debug=args.debug)
    if args.smoke_test:
        smoke_test(app,args.screenshots)
    else:
        app.run()


if __name__=='__main__':
    main()
