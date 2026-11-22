# Branches e tarefas da equipe

A versão simplificada validada está em `main`. Cada integrante trabalha em sua branch e abre pull request para integrar as mudanças.

| Integrante | GitHub | Branch | Frente | Revisor | Tarefas |
| --- | --- | --- | --- | --- | --- |
| Moisés | @mguedesjr | `moises/mecanicas` | config.py, sprites.py, engine.py, attacks.py | Davi | #2 e #3 |
| Davi | @davimoreiraesteves-beep | `davi/arte-som` | assets.py, scene.py, audio.py, assets/ | João Marcelo | #4 e #5 |
| João Marcelo | @barrosojoaomarcelo-coder | `joao/interface-entrega` | main.py, instalação, documentação e integração | Moisés | #6 e #7 |

## Tarefas

- [Moisés: colisões e balanceamento](https://github.com/barrosojoaomarcelo-coder/Cuphead-Mineirinho-/issues/2)
- [Moisés: teste final e revisão](https://github.com/barrosojoaomarcelo-coder/Cuphead-Mineirinho-/issues/3)
- [Davi: animações, avisos e volumes](https://github.com/barrosojoaomarcelo-coder/Cuphead-Mineirinho-/issues/4)
- [Davi: créditos e revisão](https://github.com/barrosojoaomarcelo-coder/Cuphead-Mineirinho-/issues/5)
- [João: retorno ao menu e instalação](https://github.com/barrosojoaomarcelo-coder/Cuphead-Mineirinho-/issues/6)
- [João: README, vídeo e entrega](https://github.com/barrosojoaomarcelo-coder/Cuphead-Mineirinho-/issues/7)

Pendência: Davi não apareceu no seletor de responsáveis. Confirmar perfil/convite e atribuir #4 e #5 quando disponível. O nome e o perfil informado estão nas descrições.

## Como começar

No GitHub Desktop: Fetch origin e escolher sua branch em Current branch. No terminal, por exemplo para Moisés:

~~~sh
git fetch origin
git switch moises/mecanicas
~~~

Davi usa `git switch davi/arte-som`; João usa `git switch joao/interface-entrega`. Cada um usa sua própria conta.

## Fluxo combinado

1. Fazer mudanças pequenas e reais na sua frente.
2. Registrar commits claros e enviar para sua branch.
3. Abrir pull request para `main`, vinculado à tarefa, explicando a mudança e como testar.
4. O revisor executa o jogo e confere os testes antes de incorporar.
5. Atualizar a branch a partir de `main` antes da próxima tarefa.

Manter a main jogável. Não usar force push ou commits artificiais para aparentar participação. Combinar mudanças entre módulos. A base gerada com IA não representa contribuição individual anterior dos alunos.

## Branch anterior

`Primeira` preserva o trabalho anterior de João Marcelo. Sua estrutura difere desta base: comparar as alterações antes de integrar, sem apagar ou substituir esse trabalho automaticamente.

## Prazo

Encerrar novas funcionalidades no domingo à noite. Segunda-feira, 23/11/2026, até 10h: testar uma cópia nova, conferir vídeo, README, créditos e acesso do professor. Reservar margem para a entrega até 12h.
