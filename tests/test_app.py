"""Fluxo do jogo e extensão por fases; SDL dummy permite testar sem uma tela."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame
from app import App
from levels import LEVELS
from levels.level_template import TemplateLevel
from progress import Progress


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=App(persistence=False,sound=False,window_size=(960,700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        a=self.app
        a.controls_open=False
        a.go_home()
        a.progress.best_times.clear()
        a.progress.completed.clear()
        a.page=0
        a.render()

    def key(self,key):
        self.app.handle_event(pygame.event.Event(pygame.KEYDOWN,key=key))

    def click_logical(self,x,y):
        a=self.app
        pos=(a.viewport.x+x*a.viewport.width/1280,a.viewport.y+y*a.viewport.height/720)
        a.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos))

    def test_home_menu_keyboard_select_and_back(self):
        a=self.app
        self.assertEqual(a.screen,'home')
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(a.screen,'levels')
        self.key(pygame.K_ESCAPE)
        self.assertEqual(a.screen,'home')
        self.key(pygame.K_RETURN)
        self.assertEqual((a.screen,a.level.state),('game','intro'))

    def test_mouse_start_and_letterboxed_coordinates(self):
        a=self.app
        self.assertLess(a.viewport.height,a.window.get_height())
        self.click_logical(450,378)
        self.assertEqual((a.screen,a.level.id),('game','castelo'))
        self.assertEqual(a.logical_point((1,1)),(-1,-1))

    def test_reserved_levels_do_not_start(self):
        a=self.app
        a.select_levels()
        self.key(pygame.K_2)
        self.assertEqual(a.screen,'levels')
        self.assertFalse(a.start_level('nao_existe'))
        self.assertFalse(a.start_level('fase_03'))
        self.key(pygame.K_1)
        self.assertEqual(a.level.id,'castelo')

    def test_pause_controls_focus_and_restart(self):
        a=self.app
        a.start_level('castelo')
        for _ in range(108): a.update(1/60)
        self.assertEqual(a.level.state,'playing')
        self.key(pygame.K_d)
        a.update(.1)
        self.assertGreater(a.level.model.player.x,190)
        self.key(pygame.K_h)
        before=a.level.model.snapshot()
        self.key(pygame.K_j)
        a.update(.1)
        a.render()
        self.assertEqual(a.level.state,'paused')
        self.assertFalse(a.keys)
        self.assertEqual(a.level.model.snapshot(),before)
        self.key(pygame.K_ESCAPE)
        self.assertFalse(a.controls_open)
        self.key(pygame.K_RETURN)
        self.assertEqual(a.level.state,'playing')
        a.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(a.level.state,'paused')
        self.key(pygame.K_r)
        self.assertEqual((a.level.state,a.level.lives),('intro',3))

    def test_help_does_not_leak_clicks_to_hidden_home_buttons(self):
        a=self.app
        a.controls()
        a.render()
        self.click_logical(450,378)
        self.assertTrue(a.controls_open)
        self.assertEqual(a.screen,'home')
        self.click_logical(640,617)
        self.assertFalse(a.controls_open)

    def test_fresh_level_has_no_old_shots_keys_or_dip(self):
        a=self.app
        a.start_level('castelo')
        m=a.level.model
        m.force_phase(4)
        m.prepare_attack('horizontal')
        a.keys={pygame.K_j}
        a.update(.1)
        a.go_home()
        self.assertFalse(a.keys)
        a.start_level('castelo')
        self.assertEqual(m.boss.hp,480)
        self.assertFalse(m.fire or m.shots or m.beams or m.warnings)
        self.assertIsNone(m.boss.horizontal)
        self.assertFalse(m.boss.dip_active)

    def test_register_new_level_and_pagination_without_changing_app(self):
        a=self.app
        class Level04(TemplateLevel):
            id='teste04'
            number=4
            title='Quarta fase'
            available=True
        with patch('levels.LEVELS',LEVELS+[Level04]),patch('app.LEVELS',LEVELS+[Level04]):
            a.select_levels()
            self.key(pygame.K_RIGHT)
            self.assertEqual(a.page,1)
            a.render()
            self.key(pygame.K_1)
            self.assertEqual(a.level.id,'teste04')
            a.update(.1)
            a.render()
            self.assertEqual(a.level.state,'playing')
            a.pause()
            before=a.level.elapsed
            a.update(.1)
            self.assertEqual(a.level.elapsed,before)
            a.pause()
            a.level.pos.x=1160
            a.update(1/60)
            self.assertEqual(a.level.state,'victory')
            self.assertIn('teste04',a.progress.completed)
            a.render()

    def test_level_victory_records_best_time_and_menu_returns(self):
        a=self.app
        a.start_level('castelo')
        a.level.model.force_phase(3)
        a.level.model.elapsed=44.5
        a.level.model.damage_boss(480)
        a.update(1/60)
        self.assertEqual(a.progress.best_times['castelo'],44.5)
        self.assertIn('castelo',a.progress.completed)
        a.render()
        a.select_levels()
        a.render()
        a.go_home()
        self.assertIsNone(a.level)

    def test_every_player_sprite_and_crouched_fingertip_stays_aligned(self):
        from scene import player_pose, PLAYER_SIZE
        a=self.app
        a.start_level('castelo')
        scene=a.level.scene
        for action,frames in scene.player_frames.items():
            self.assertEqual(len(frames),scene.manifest['player']['actions'][action]['count'])
            for right,left in frames:
                self.assertGreater(right.get_bounding_rect().width,10)
                self.assertEqual(left.get_size(),right.get_size())
        p=a.level.model.player
        p.crouch=p.shooting=True
        for facing in (1,-1):
            p.facing=facing
            action,frame=player_pose(p)
            muzzle=scene.manifest['player']['actions'][action]['muzzles'][frame]
            x,y=scene.actual_muzzle()
            self.assertAlmostEqual(x,p.x+(muzzle[0]-120)*PLAYER_SIZE/256*facing)
            self.assertAlmostEqual(y,p.y+(muzzle[1]-240)*PLAYER_SIZE/256*.78)

    def test_menu_exit_and_quit_event(self):
        a=self.app
        self.key(pygame.K_DOWN)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertFalse(a.running)
        a.running=True
        a.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertFalse(a.running)
        a.running=True


class ProgressTests(unittest.TestCase):
    def test_corrupt_data_and_valid_per_level_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'save.json'
            path.write_text('{invalid',encoding='utf-8')
            store=Progress(path)
            self.assertEqual(store.best_times,{})
            path.write_text(json.dumps(dict(best_times={'a':'invalid','b':float('nan'),'c':22.5},completed=[5,'c'],sound=False)))
            store=Progress(path)
            self.assertEqual(store.best_times,{'c':22.5})
            self.assertEqual(store.completed,{'c'})
            self.assertFalse(store.sound)
            store.record('castelo',44.5)
            store.record('castelo',49)
            self.assertEqual(Progress(path).best_times['castelo'],44.5)
            self.assertIn('castelo',Progress(path).completed)


if __name__=='__main__':
    unittest.main()
