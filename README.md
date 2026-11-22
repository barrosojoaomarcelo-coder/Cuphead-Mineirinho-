
# Mineirinho — base editável em Python + Pygame

Abra **esta pasta inteira** no VS Code. O arquivo de entrada é `main.py`.
Mantenha `assets/`, `levels/` e os demais arquivos junto dele.

## Executar

Use Python 3.10 ou superior. Esta versão foi testada com Python 3.12 e Pygame 2.6.1.

No terminal do VS Code, dentro da pasta do projeto:

```sh
python -m pip install -r requirements.txt
python main.py
```

Se o seu Windows usa `py`, substitua `python` por `py` nos dois comandos.
No VS Code, escolha o mesmo interpretador Python que recebeu o Pygame.
Também há configurações para executar ou depurar com **F5**.

Para usar um ambiente virtual (opcional):

```sh
python -m venv .venv
```

Ative-o no Windows com `.venv\Scripts\activate`, ou no Linux/macOS com
`source .venv/bin/activate`, e execute os dois primeiros comandos.

## O que está pronto

- Tela inicial com **Jogar**, **Escolher fase**, **Controles** e **Sair**.
- Seleção de fases com teclado e mouse. A lista ganha páginas ao passar de três fases.
- Fase 1 jogável: dragão com duas formas, dez tipos de ataque, rajadas horizontais
  rápidas, três vidas, tiros de pão de queijo e transformação do castelo para a noite.
- As mesmas artes e folhas de animação do personagem, dragão e castelo.
- Pausa, reinício, vitória, derrota, tela cheia, som e recordes separados por fase.
- Fases 2 e 3 **reservadas para você desenvolver**. Seus chefes ainda não foram criados.
- Um modelo de fase independente do dragão, pronto para copiar e modificar.

A tela inicial é o menu de entrada no jogo. Não exige cadastro ou conexão.

## Onde modificar

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| `main.py` | Iniciar o programa e executar a verificação opcional |
| `app.py` | Janela, tela inicial, seleção de fases, menus e teclado/mouse |
| `settings.py` | Tamanho da janela, FPS, passo de física e teclas |
| `levels/__init__.py` | Lista `LEVELS`: cadastro e ordem das fases |
| `levels/base.py` | Interface comum usada pelo menu para conversar com qualquer fase |
| `levels/level_01.py` | Integração da fase do dragão com a aplicação |
| `levels/level_02.py` | Lugar para desenvolver a segunda fase |
| `levels/level_03.py` | Lugar para desenvolver a terceira fase |
| `levels/level_template.py` | Exemplo comentado para construir fases novas |
| `engine.py` | Física, tiros, colisões, dano e ataques do dragão |
| `scene.py` | Animações, escolha de quadros, cenários e efeitos da fase 1 |
| `audio.py` | Efeitos sonoros e música sintetizados |
| `progress.py` | Gravação de preferências, fases concluídas e melhores tempos |
| `assets/` | Imagens e folhas de animação |
| `assets/manifest.json` | Quadros, pivôs e posição do dedo para a saída dos tiros |

## Começar a segunda ou terceira fase

1. Abra `levels/level_02.py` ou `levels/level_03.py`.
2. Troque `available = False` para `available = True`.
3. Execute `python main.py` e escolha essa fase no menu.
4. Substitua os métodos `start()`, `update()` e `draw()` do exemplo pelo seu conteúdo.

Ao ativar um espaço reservado, ele executa **apenas o modelo de desenvolvimento**:
um boneco que anda, pula e vence ao alcançar a porta. Use isso para conferir o
fluxo de menus antes de programar seu novo chefe.

## Adicionar uma quarta fase ou mais

Crie `levels/level_04.py`:

```python
from .level_template import TemplateLevel


class Level04(TemplateLevel):
    id = "fase_04"            # identificador único, usado nos recordes
    number = 4
    title = "Minha nova fase"
    subtitle = "Uma nova aventura"
    available = True

    # start(): zere a fase e suas variáveis; chame super().start().
    # update(dt, inputs): física, inimigos, ataques e colisões.
    # draw(target, debug=False): desenho com comandos do Pygame.
```

Depois, em `levels/__init__.py`, importe e acrescente a classe:

```python
from .level_04 import Level04

LEVELS = [Level01, Level02, Level03, Level04]
```

O menu e a paginação reconhecem a fase pela lista. O botão de próxima fase aparece
na vitória quando houver outra fase disponível depois da atual.
Você pode herdar diretamente de `BaseLevel` para criar qualquer outra mecânica.

## Contrato de uma fase

- `start()`: iniciar e também reiniciar; limpe inimigos, tiros e tempos antigos.
- `update(dt, inputs)`: `dt` vem em segundos. `inputs` é um dicionário de ações:
  `left`, `right`, `up`, `down`, `jump`, `shoot`, `dash`.
- `draw(target, debug=False)`: desenhe numa `pygame.Surface` de **1280 × 720**.
- `pause()` e `resume()`: a implementação básica já congela o exemplo.
- `state`: `playing`, `paused`, `dead` ou `victory`. A fase 1 também tem `intro` e `transform`.
- `elapsed`, `lives`, `max_lives`, `stats` e `hud_title`: informações exibidas no HUD.
- Ao vencer, mude o estado para `victory` e retorne `[dict(type="victory")]`
  **uma única vez** em `update()` para salvar o recorde.

Os menus controlam a navegação. Cada fase controla seu mundo e suas regras.
As quatro etapas internas do dragão ficam dentro da fase 1; não são quatro levels.

## Ajustar a fase do dragão

Comece por `Rules`, no início de `engine.py`:

```python
lives: int = 3
max_boss_hp: int = 480
shot_interval: float = 1 / 12
shot_speed: float = 1450
player_speed: float = 310
jump_speed: float = 680
```

Procure `prepare_attack()` para alterar a sequência e os avisos. Em `_release()`,
ajuste quantidades, velocidades e espaçamento. A rajada horizontal usa velocidades
de 520 a 640 px/s; a bola gigante usa 500/580 px/s. A vida do chefe não tem barra.

`player_pose()` em `scene.py` escolhe os quadros. `actual_muzzle()` usa o ponto do dedo
descrito em `manifest.json`; preserve esse alinhamento ao substituir sprites.
O chão da primeira arena fica em y=622, e x/y do jogador representam os pés.

## Controles

| Ação | Teclas |
| --- | --- |
| Navegar pelos menus / confirmar | Setas ou Tab / Enter |
| Mover | A/D ou ←/→ |
| Pular | Espaço ou Z; segure para pular mais alto |
| Atirar | Segure J ou X |
| Dash | Shift ou K |
| Mirar acima / diagonal | W ou ↑; combine com direção |
| Agachar | S ou ↓ |
| Pausar / reiniciar | P ou Esc / R |
| Abrir controles | H |
| Som / tela cheia | M / F11 |

Na seleção, 1/2/3 abrem as fases da página; ←/→ trocam a página.
Ao perder o foco, a partida pausa. Fechar a ajuda mantém a luta pausada;
use **Continuar** para retomar. Reiniciar e sair para o menu descartam a luta atual.

## Conferir suas alterações

```sh
python -m unittest discover -s tests -v
python main.py --smoke-test
python main.py --debug
```

Com `--debug`, F3 mostra as áreas de colisão. `--mute` inicia sem som.
Os 26 testes cobrem combate, menus, gravação e adição de uma fase de teste.
Um deles compara 146 estados em 44 cenários com os resultados da versão publicada,
incluindo os ataques horizontais; a referência está em `tests/original_cases.json`.
Se você mudar as regras intencionalmente, revise as expectativas dos testes.

Esta entrega passou nos testes e no desenho automatizado com os drivers SDL dummy
no Linux. A janela e o áudio no Windows dependem da instalação local.

Recordes são salvos na pasta de dados do usuário em `MineirinhoPygame/progresso.json`
(`%LOCALAPPDATA%` no Windows). Arquivos de código e imagens permanecem editáveis.

# Cuphead-Mineirinho-
Paygame 
