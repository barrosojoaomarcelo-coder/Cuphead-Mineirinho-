"""Janela, tela inicial, seleção de fases, pausa e entrada de teclado/mouse.

A aplicação só conhece o contrato BaseLevel. Para criar conteúdo novo, edite
levels/; você não precisa mudar este laço principal nem os menus.
"""
from math import cos, pi, sin
import pygame

from audio import Audio
from levels import LEVELS, get_level, next_available
from progress import Progress
from scene import CREAM, GOLD, INK
from settings import ACTION_KEYS, FPS, HEIGHT, TITLE, WIDTH, WINDOW_SIZE

ACTIVE = ('intro', 'playing', 'transform')


def time_label(seconds):
    return f'{int(seconds)//60:02}:{int(seconds)%60:02}'


class App:
    def __init__(self, *, persistence=True, sound=True, window_size=WINDOW_SIZE, debug=False, save_file=None):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.window = pygame.display.set_mode(window_size, pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.world = self.canvas.copy()
        self.clock = pygame.time.Clock()
        self.viewport = pygame.Rect(0, 0, *window_size)
        self.window_size = window_size
        self.fullscreen, self.running = False, True
        self.debug, self.hitboxes = debug, False
        self.progress = Progress(save_file, enabled=persistence)
        self.audio = Audio(self.progress.sound and sound)
        # A prévia fornece as artes e as fontes do menu; não simula a luta.
        self.preview = LEVELS[0]()
        self.ui = self.preview.scene
        pygame.display.set_icon(pygame.transform.smoothscale(self.ui.bread, (32,32)))
        self.level = None
        self.screen = 'home'  # home / levels / game
        self.controls_open = False
        self.page = self.focus = 0
        self.keys = set()
        self.buttons = []

    def clear_input(self):
        self.keys.clear()

    def start_level(self, level_id):
        level_class = get_level(level_id)
        if level_class is None or not level_class.available:
            return False
        self.clear_input()
        self.controls_open = False
        self.level = self.preview if level_class is type(self.preview) else level_class()
        self.level.start()
        self.screen, self.focus = 'game', 0
        return True

    def restart(self):
        if self.level:
            self.clear_input()
            self.level.start()
            self.focus = 0

    def go_home(self):
        if self.level:
            self.level.pause()
        self.clear_input()
        self.level, self.screen, self.focus = None, 'home', 0
        self.preview.model.reset()

    def select_levels(self):
        if self.level:
            self.level.pause()
        self.clear_input()
        self.level, self.screen, self.focus = None, 'levels', 0
        self.page = min(self.page, max(0, (len(LEVELS)-1)//3))
        self.preview.model.reset()

    def change_page(self, delta):
        self.page = max(0, min((len(LEVELS)-1)//3, self.page + delta))
        self.focus = 0

    def pause(self):
        if not self.level:
            return
        self.clear_input()
        self.level.resume() if self.level.state == 'paused' else self.level.pause()
        self.focus = 0

    def controls(self):
        self.controls_open = not self.controls_open
        if self.controls_open and self.level:
            self.level.pause()
        self.clear_input()
        self.focus = 0

    def toggle_sound(self):
        self.audio.enabled = not self.audio.enabled
        if self.audio.available and not self.audio.enabled:
            pygame.mixer.stop()
        self.progress.sound = self.audio.enabled
        self.progress.save()

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.window_size = self.window.get_size()
        self.fullscreen = not self.fullscreen
        self.window = pygame.display.set_mode((0,0) if self.fullscreen else self.window_size,
                                              pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)

    def quit(self):
        self.running = False

    def logical_point(self, point):
        if not self.viewport.collidepoint(point):
            return -1, -1
        return ((point[0]-self.viewport.x)*WIDTH/self.viewport.width,
                (point[1]-self.viewport.y)*HEIGHT/self.viewport.height)

    def menu_actions(self):
        """Os mesmos botões servem ao teclado e ao mouse."""
        if self.controls_open:
            return [('FECHAR CONTROLES', (450,594,380,46), self.controls, True)]
        if self.screen == 'home':
            first = next((level for level in LEVELS if level.available), None)
            return ([('JOGAR', (160,350,580,56), lambda:self.start_level(first.id), True)] if first else []) + [
                ('ESCOLHER FASE', (160,420,580,52), self.select_levels, False),
                ('CONTROLES', (160,486,280,48), self.controls, False),
                ('SAIR', (460,486,280,48), self.quit, False)]
        if self.screen == 'levels':
            result = []
            for i, level in enumerate(LEVELS[self.page*3:self.page*3+3]):
                if level.available:
                    result.append(('JOGAR', (113+i*375,428,300,48), lambda lid=level.id:self.start_level(lid), True))
            if self.page:
                result.append(('PÁGINA ANTERIOR', (88,540,300,46), lambda:self.change_page(-1), False))
            if (self.page+1)*3 < len(LEVELS):
                result.append(('PRÓXIMA PÁGINA', (838,540,300,46), lambda:self.change_page(1), False))
            return result + [('MENU INICIAL', (465,600,350,48), self.go_home, False)]
        if not self.level or self.level.state in ACTIVE:
            return []
        result = []
        if self.level.state == 'paused':
            result.append(('CONTINUAR', self.pause, True))
        following = next_available(self.level.id) if self.level.state == 'victory' else None
        if following:
            result.append(('PRÓXIMA FASE', lambda:self.start_level(following.id), True))
        result += [('TENTAR NOVAMENTE' if self.level.state == 'dead' else 'REINICIAR FASE', self.restart, not result),
                   ('ESCOLHER FASE', self.select_levels, False), ('MENU INICIAL', self.go_home, False)]
        return [(label,(380,370+i*56,520,44),callback,primary) for i,(label,callback,primary) in enumerate(result)]

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit()
        elif event.type == pygame.WINDOWFOCUSLOST:
            self.clear_input()
            if self.level:
                self.level.pause()
        elif event.type == pygame.KEYUP:
            self.keys.discard(event.key)
        elif event.type == pygame.KEYDOWN:
            key = event.key
            if self.controls_open:
                if key in (pygame.K_ESCAPE,pygame.K_h,pygame.K_RETURN):
                    self.controls()
                return
            if key in ACTION_KEYS and self.screen == 'game' and self.level.state in ACTIVE:
                self.keys.add(key)
            if getattr(event,'repeat',False):
                return
            if key == pygame.K_m:
                self.toggle_sound()
            elif key == pygame.K_F11:
                self.toggle_fullscreen()
            elif key == pygame.K_h:
                self.controls()
            elif key == pygame.K_F3 and self.debug:
                self.hitboxes = not self.hitboxes
            elif key == pygame.K_r and self.screen == 'game':
                self.restart()
            elif key in (pygame.K_p,pygame.K_ESCAPE) and self.screen == 'game':
                if key == pygame.K_ESCAPE and self.level.state in ('dead','victory'):
                    self.select_levels()
                else:
                    self.pause()
            elif key == pygame.K_ESCAPE and self.screen == 'levels':
                self.go_home()
            elif self.screen == 'levels' and key in (pygame.K_LEFT,pygame.K_RIGHT):
                self.change_page(-1 if key == pygame.K_LEFT else 1)
            elif self.screen == 'levels' and pygame.K_1 <= key <= pygame.K_3:
                index = self.page*3 + key-pygame.K_1
                if index < len(LEVELS):
                    self.start_level(LEVELS[index].id)
            else:
                actions = self.menu_actions()
                if actions:
                    if key in (pygame.K_UP,pygame.K_w):
                        self.focus = (self.focus-1) % len(actions)
                    elif key in (pygame.K_DOWN,pygame.K_s,pygame.K_TAB):
                        self.focus = (self.focus+1) % len(actions)
                    elif key == pygame.K_RETURN:
                        actions[self.focus % len(actions)][2]()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            point = self.logical_point(event.pos)
            for rect, action in reversed(self.buttons):
                if rect.collidepoint(point):
                    action()
                    break

    def update(self, dt):
        if self.screen == 'game' and self.level:
            inputs = {ACTION_KEYS[k]:True for k in self.keys if k in ACTION_KEYS} if not self.controls_open else {}
            events = self.level.update(dt, inputs)
            self.audio.process(events)
            for event in events:
                if event['type'] in ('transform','death','victory'):
                    self.clear_input()
                    self.focus = 0
                if event['type'] == 'victory':
                    self.progress.record(self.level.id, self.level.elapsed)
            if self.level.music_model is not None:
                self.audio.update(dt, self.level.music_model)
        else:
            self.preview.scene.update(dt)

    def text(self, text, pos, size=22, color=CREAM, center=False, max_width=None, serif=False):
        if max_width:
            while size > 12 and self.ui.font(size,serif).size(text)[0] > max_width:
                size -= 1
        return self.ui.text(self.canvas,text,pos,size,color,center,serif)

    def button(self, label, rect, callback, primary=False, focused=False):
        rect = pygame.Rect(rect)
        hover = rect.collidepoint(self.logical_point(pygame.mouse.get_pos()))
        fill = ('#ffcf80' if hover or focused else GOLD) if primary else ('#76523d' if hover or focused else '#452c26')
        pygame.draw.rect(self.canvas,'#211418',rect.move(0,4),border_radius=8)
        pygame.draw.rect(self.canvas,fill,rect,border_radius=8)
        pygame.draw.rect(self.canvas,CREAM if focused else '#b88051',rect,3 if focused else 2,border_radius=8)
        self.text(label,rect.center,18,INK if primary else CREAM,True,max_width=rect.width-24)
        self.buttons.append((rect,callback))

    def heart(self, x, y, alive):
        points=[]
        for i in range(48):
            t=i/48*2*pi
            points.append((x+16*sin(t)**3,y-(13*cos(t)-5*cos(2*t)-2*cos(3*t)-cos(4*t))))
        pygame.draw.polygon(self.canvas,INK,points)
        center=pygame.Vector2(x,y)
        pygame.draw.polygon(self.canvas,'#bd493b' if alive else '#6c5147',
                            [center+(pygame.Vector2(p)-center)*.83 for p in points])

    def shade(self, alpha):
        layer=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        layer.fill((26,16,23,alpha))
        self.canvas.blit(layer,(0,0))

    def draw_header(self):
        self.text('MINEIRINHO', (38,24), 24, GOLD, serif=True)
        self.button('SOM: '+('ON' if self.audio.enabled and self.audio.available else 'OFF'),(902,16,135,40),self.toggle_sound)
        self.button('TELA CHEIA',(1052,16,190,40),self.toggle_fullscreen)

    def draw_home(self):
        self.preview.scene.draw_background(self.canvas)
        self.shade(140)
        pygame.draw.rect(self.canvas,'#eed5ad',(110,120,680,470),border_radius=18)
        pygame.draw.rect(self.canvas,'#845638',(120,130,660,450),2,border_radius=12)
        self.text('PRIMEIRO ATO', (450,170),17,'#845638',True)
        self.text('MINEIRINHO',(450,232),62,INK,True,serif=True)
        self.text('A FORNALHA DO CASTELO',(450,291),28,'#845638',True)
        self.text('Fogo, coragem e pão de queijo.',(450,326),19,'#795440',True)
        hero=self.ui.player_frames['01_parado'][0][0]
        hero=pygame.transform.smoothscale(hero,(310,310))
        self.canvas.blit(hero,(870,230))
        self.text('Três chefes. Uma aventura.',(1040,560),21,CREAM,True,max_width=330)
        self.draw_header()
        self.text('Setas / Tab escolhem · Enter confirma · H controles · F11 tela cheia',(640,675),18,CREAM,True)

    def draw_levels(self):
        self.preview.scene.draw_background(self.canvas)
        self.shade(182)
        self.draw_header()
        self.text('ESCOLHA SUA FASE',(640,110),42,GOLD,True,serif=True)
        for i,level in enumerate(LEVELS[self.page*3:self.page*3+3]):
            x=88+i*375
            pygame.draw.rect(self.canvas,'#edd4ac' if level.available else '#b9aa94',(x,185,350,315),border_radius=15)
            self.text(f'{level.number:02}',(x+175,237),53,'#94513a' if level.available else '#776b60',True,serif=True)
            self.text(level.title,(x+175,305),28,INK,True,max_width=310,serif=True)
            self.text(level.subtitle,(x+175,352),18,'#6f5140',True,max_width=316)
            if not level.available:
                self.text('EM DESENVOLVIMENTO',(x+175,449),18,'#65574e',True)
            elif level.id in self.progress.completed:
                self.text('CONCLUÍDA',(x+175,389),16,'#56633b',True)
            elif level.id in self.progress.best_times:
                self.text('RECORDE '+time_label(self.progress.best_times[level.id]),(x+175,389),16,'#56633b',True)
        self.text(f'PÁGINA {self.page+1} / {max(1,(len(LEVELS)+2)//3)}',(640,561),18,CREAM,True)
        self.text('1 / 2 / 3 escolhem uma fase · ← → mudam de página · Esc volta',(640,687),17,CREAM,True)

    def draw_hud(self):
        level=self.level
        pygame.draw.rect(self.canvas,'#2e2021',(0,0,1280,62))
        pygame.draw.line(self.canvas,'#b78655',(0,61),(1280,61),2)
        for i in range(level.max_lives):
            self.heart(34+i*39,30,i<level.lives)
        self.text(level.hud_title,(170,21),18,max_width=410)
        self.text(time_label(level.elapsed),(647,30),24,center=True)
        self.button('SOM',(721,11,90,38),self.toggle_sound)
        self.button('CONTROLES',(823,11,153,38),self.controls)
        self.button('MENU',(988,11,120,38),self.go_home)
        self.button('CONTINUAR' if level.state=='paused' else 'PAUSA',(1120,11,148,38),self.pause)
        pygame.draw.rect(self.canvas,'#2e2021',(0,687,1280,33))
        self.text('A/D mover · Espaço pular · J atirar · Shift dash · S agachar · W mirar · P pausa · R reiniciar',(640,703),16,center=True)

    def draw_game_menu(self):
        level=self.level
        if level.state in ACTIVE:
            return
        self.shade(145)
        pygame.draw.rect(self.canvas,'#f0d6aa',(330,155,620,480),border_radius=17)
        titles={'paused':'Uma pausa para respirar.','dead':'Essa foi por pouco.','victory':'NOCAUTE!'}
        self.text(titles.get(level.state,'Pronto para jogar?'),(640,228),40,INK,True,max_width=570,serif=True)
        self.text(level.title,(640,282),22,'#795440',True,max_width=560)
        best=self.progress.best_times.get(level.id)
        detail='A batalha continua de onde você parou.' if level.state=='paused' else 'TEMPO '+time_label(level.elapsed)
        if best and level.state!='paused':
            detail+=' · RECORDE '+time_label(best)
        self.text(detail,(640,325),19,'#795440',True)

    def draw_controls(self):
        self.shade(215)
        pygame.draw.rect(self.canvas,'#f0d6aa',(260,80,760,575),border_radius=15)
        self.text('CONTROLES',(640,126),36,INK,True,serif=True)
        rows=[('Mover','A / D ou ← / →'),('Pular (altura variável)','Espaço / Z'),
              ('Atirar continuamente','Segure J / X'),('Dash / esquiva','Shift / K'),
              ('Mirar para cima / diagonal','W / ↑ + direção'),('Agachar','S / ↓'),
              ('Pausar / reiniciar','P ou Esc / R'),('Som / tela cheia','M / F11')]
        for i,(action,key) in enumerate(rows):
            y=182+i*42
            self.text(action,(298,y),21,INK)
            self.text(key,(655,y),20,'#895638')
        self.text('Fogo baixo: pule ou dê dash. Fogo alto: agache.',(640,548),20,INK,True)

    def render(self):
        self.buttons.clear()
        w,h=self.window.get_size()
        scale=min(w/WIDTH,h/HEIGHT)
        size=max(1,round(WIDTH*scale)),max(1,round(HEIGHT*scale))
        self.viewport=pygame.Rect((w-size[0])//2,(h-size[1])//2,*size)
        if self.screen=='game' and self.level:
            self.level.draw(self.world,self.hitboxes)
            self.canvas.blit(self.world,(0,0))
            self.draw_hud()
            self.draw_game_menu()
        elif self.screen=='levels':
            self.draw_levels()
        else:
            self.draw_home()
        if self.controls_open:
            self.buttons.clear()  # Um clique na ajuda não ativa botões por baixo dela.
            self.draw_controls()
        actions=self.menu_actions()
        for i,(label,rect,action,primary) in enumerate(actions):
            self.button(label,rect,action,primary,i==self.focus%len(actions))
        if self.progress.warning:
            self.text(self.progress.warning,(640,666),16,GOLD,True)
        self.window.fill('#160f14')
        self.window.blit(self.canvas if size==(WIDTH,HEIGHT) else pygame.transform.smoothscale(self.canvas,size),self.viewport)
        pygame.display.flip()

    def run(self):
        try:
            self.render()
            while self.running:
                dt=min(self.clock.tick(FPS)/1000,.1)
                for event in pygame.event.get():
                    self.handle_event(event)
                self.update(dt)
                self.render()
        finally:
            pygame.quit()
