# Pergunta de pesquisa

Versão 2 · decidida em 15/10/2026, depois da conversa com o professor

## Por que a pergunta mudou

A versão 1 perguntava se o rastro do agente indica **quais trechos têm mais chance de estar errados**. O professor apontou que isso depende de **onde a IA atual costuma errar**, e isso muda a cada modelo novo: em poucos meses o resultado deixaria de servir.

A versão 2 pergunta **onde o humano deve começar a revisar**, algo que continua útil mesmo com uma IA muito melhor. Todo sinal usado precisa passar no teste:

> **"Isso continua valendo se a IA fosse perfeita?"**

O rastro continua no centro, mas muda de papel: deixa de ser um **detector de sintomas de IA fraca** (loop, fim de contexto, editar sem ler) e passa a ser um **registro de evidência** — o que foi verificado, o que foi decidido, o que foi pedido.

## Pergunta principal

> **O rastro do agente ajuda a apontar onde o humano deve começar a revisar um patch?**

## Ideia central: dois lados da atenção

Um trecho precisa da atenção do revisor quando:

1. **É importante** — tem impacto (muita coisa depende dele), envolve uma decisão de julgamento (a tarefa era ambígua e alguém escolheu) ou muda algo que ninguém pediu;
2. **E há pouca evidência de que está certo** — nada executou ou verificou aquele trecho.

O **rótulo** ("precisa de atenção? por quê?") vem do código, da tarefa e dos testes oficiais, **sem olhar o rastro** (cegamento). O rastro entra como **pista**. Assim a conta não fica circular.

## Sub-perguntas (RQs)

| RQ | Pergunta | Como responder | O que entrega, mesmo se a próxima falhar |
|---|---|---|---|
| **RQ1** | Por que um trecho precisa da atenção do revisor? | Rotular hunks com os motivos; conferir com comentários de revisores reais (amostra do AIDev); segunda pessoa rotula uma parte para medir concordância | Uma taxonomia de motivos duráveis + um conjunto de dados rotulado |
| **RQ2** | Quais desses motivos deixam marcas no rastro, e quais só aparecem no código? | Para cada motivo, procurar a pista correspondente no rastro (ex.: o trecho foi executado por algum teste? o agente escreveu "vou assumir que..."?) | Um mapa do que o rastro revela que o código esconde |
| **RQ3** | Ordenar os trechos usando rastro + código coloca os que precisam de atenção mais cedo do que usar só o código? | Comparar com ordens simples (ordem do diff, maiores primeiro, só código); medir quantos trechos importantes aparecem nos primeiros 20–30% | A frase prática: "revisando X% dos trechos, encontra-se Y% do que importa" |
| **RQ4** | O resultado se mantém em agentes de força diferente? | Repetir a RQ3 com agentes fracos e fortes (modelos 8B/70B/405B; trajetórias de várias épocas no SWE-bench) | A prova de que o método não depende de a IA errar |

**Prioridade:** RQ1 e RQ2 são o coração e já formam um primeiro artigo. RQ3 e RQ4 vêm em seguida. Um estudo com pessoas usando a ferramenta fica como trabalho futuro.

## O que aproveitamos da versão 1

- O cuidado com a evidência (leitura + testes, atribuição de falhas, testes que cobram o "jeito" da solução humana) — ver `docs/definicao-hunk-errado.md`.
- O cegamento.
- Os 18 hunks já rotulados (`dados/rotulagem_manual.csv`), que serão re-rotulados com o critério novo.
- Rótulos e decisões que já apontavam nessa direção: `fora_do_escopo` (caso 6), "testes não verificam um `print`" (caso 7), decisões de julgamento (casos 10 e 15).

## O que deixamos de lado

- Prever "erro da IA" como objetivo.
- Sinais de sintoma de agente fraco como contribuição principal.
- O modelo antigo (rótulo "15 linhas do Gold Patch").

## Próximo passo

Busca de literatura guiada pelas quatro RQs: o que já existe, quem está pesquisando e onde está a lacuna.
