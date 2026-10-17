# Revisão de literatura — o que já existe

Versão 1 · 15/10/2026 · busca em bases de artigos (arXiv e afins), guiada pelas RQs de `docs/pergunta-de-pesquisa.md`

> Busca rápida, não sistemática. Refazer antes de escrever o artigo: a área publica toda semana (vários trabalhos abaixo são de agosto a outubro de 2026).

## Veredito em uma frase

Não encontramos ninguém usando o rastro do agente **como registro de evidência** (o que foi testado, lido e decidido) para **ordenar os trechos de um patch** para revisão humana, com **dados públicos** e testando se isso **vale para agentes fracos e fortes**. Mas há trabalhos muito próximos e muito recentes — a janela existe, e é curta.

## Os trabalhos mais próximos e como nos diferenciamos

| Trabalho | O que faz | Onde para (nossa diferença) |
|---|---|---|
| **ARCTIC** — Maddila et al. (Meta), "From Code Review to Code Critique: Intent, Drift, and Spotlight for AI-Generated Diffs at Scale", arXiv 2607.29516 (ago/2026) | "Spotlight" ordena as regiões de um diff que mais merecem atenção humana; "Drift" mede mudanças não pedidas; usa a conversa com o agente para inferir a intenção | O Spotlight olha **só o código** (diff + contexto); a conversa entra apenas para a intenção e **exclui as chamadas de ferramenta** (testes, leituras). Drift é medido no diff inteiro, não por trecho. Dados internos da Meta, **não públicos** |
| **LEDGER** — "Claim-to-Evidence Trace Graphs for Auditing LLM Agents", arXiv 2608.18398 (ago/2026) | Transforma a sessão do agente num grafo que liga cada afirmação às ações, arquivos e verificações que a sustentam (arestas "checked_by") | É uma ferramenta de **visualização**: não ordena trechos e não mede se ajuda (só estudos de caso). Mostra que a ideia "rastro como evidência" é atual — nós a transformamos em algo **medido** |
| **Test Coverage Analysis of Agentic Pull Requests**, arXiv 2607.18057 (jul/2026) | Mede quantas linhas alteradas por agentes são executadas por testes: só 27% em Python; em 64,8% dos PRs nenhuma linha alterada é testada | Usa os testes existentes do projeto, **não o rastro**, e não ordena para revisão. É um ótimo argumento para o motivo "falta de verificação" |
| **Who Pays the Review Cost?** — Rahman et al., arXiv 2610.11179 (out/2026) | Questionário com 239 revisores: o esforço de revisão depende de intenção clara, **escopo limitado**, **validação além do CI** e responsabilidade; chama a falta disso de **"dívida de revisabilidade"** | É uma pesquisa de opinião, sem método para apontar trechos. **Confirma os nossos motivos** (escopo, validação, justificativa) vindos de revisores reais |
| **Code Review Activity Prediction** — arXiv 2404.10703 (2024) | Prevê quais **arquivos** de um patch serão comentados ou revisados; reordenar os arquivos aumentou os comentários em 23% num estudo com 29 especialistas | Nível de arquivo, código humano, sem rastro. Serve de **método e baseline** para a RQ3 |
| **Explaining Risk of Code Changes** — arXiv 2607.02782 (jul/2026) | Destaca os **hunks** mais arriscados de um diff usando um modelo de previsão de defeitos; cobre 54% das linhas que causaram falhas olhando os 2 primeiros hunks | Só código, defeitos de código humano. É o **baseline "só código"** natural para a RQ3 |

## O que existe por sub-pergunta

### RQ1 — Por que um trecho precisa de atenção?
- **Temas dos comentários de revisão em PRs de agentes** — arXiv 2601.19287: 12 temas a partir de 19.450 comentários do AIDev (além de correção: documentação, refatoração, estilo, testes, segurança).
- **ARCTIC** (acima): taxonomia de 6 temas a partir de 18 mil revisões; revisores priorizam correção, segurança e desempenho.
- **Dívida de revisabilidade** (acima): intenção, escopo, validação, responsabilidade.
- **Motivos de rejeição de PRs de agentes** — arXiv 2601.15195, 2606.13468, 2602.04226: incluem "funcionalidade não pedida" e "desalinhamento do agente".
- **Inconsistência entre descrição e código** — arXiv 2601.04886: o tipo mais comum é "a descrição afirma mudanças que não foram feitas".
- **Implicação:** não precisamos criar a taxonomia do zero. Nossa contribuição é outra: os **motivos duráveis** (que valem com IA perfeita) no nível do **trecho**, mapeados para essas taxonomias.

### RQ2 — Quais motivos deixam marcas no rastro?
- **LEDGER** (acima) e **Tracekit** (arXiv 2609.35659, registro intenção–raciocínio–ação): mostram que dá para ligar ações do rastro a artefatos e verificações.
- **Assay** (arXiv 2609.36170): liga cada afirmação do agente ("os testes passam") ao código que ela cobre e define o "raio de impacto" de uma mudança — próximo dos motivos impacto e verificação.
- **Ambiguidade e suposições:** Ambig-SWE (2502.13069), "Ask or Assume?" (2603.26233), CONTRA (2610.01769) e UnderSpecBench, "Coding Agents Are Guessing" (2607.02294): mesmo os melhores agentes **adivinham** quando a tarefa é ambígua (55,8–67,8% das execuções violam algum limite). Isso sustenta que o motivo **"decisão de julgamento" é durável**: depende da tarefa, não da força do modelo.
- **Lacuna:** ninguém mediu, trecho a trecho, se essas marcas do rastro coincidem com o que precisa de atenção.

### RQ3 — Ordenar com rastro + código bate ordenar só com código?
- **A ordem importa:** "First Come First Served" (arXiv 2208.04259) — arquivos mostrados antes recebem mais comentários e defeitos no fim são menos achados; "Does Order Matter?" (arXiv 2609.22610) — em 330 mil PRs, a taxa de bugs latentes sobe com a posição do arquivo.
- **Baselines prontos:** ordem do diff, tamanho, previsão por arquivo (2404.10703), risco por hunk só com código (2607.02782) e um revisor de IA que olha só o código (estilo Spotlight do ARCTIC).
- **Lacuna:** nenhum desses usa o rastro.

### RQ4 — Vale para agentes fracos e fortes?
- **Groundability, Not Scale Alone** (arXiv 2610.01023): com evidência de execução, revisores "fracos" conseguem auditar agentes fortes (GPT-5.4, Gemini). Reforça a ideia de que **evidência** é mais durável que o tamanho do modelo.
- **Habituação** (arXiv 2606.22721): revisores aprovam mais e comentam menos à medida que se acostumam com PRs de agentes — motivo para priorizar bem a atenção.
- Fontes de trajetórias de agentes de diferentes épocas: repositório público de submissões do SWE-bench; Nebius (modelos 8B/70B/405B).

## O que muda nas RQs depois da busca

1. **RQ1** passa a **adaptar** taxonomias existentes (temas de revisão, dívida de revisabilidade) ao nível do trecho, em vez de criar do zero.
2. **RQ2** ganha uma definição concreta para "falta de verificação": usar o rastro para saber se cada trecho foi executado por algum teste ou comando — comparável ao estudo de cobertura (2607.18057), mas a partir do rastro.
3. **RQ3** ganha baselines definidos, incluindo um revisor de IA que olha só o código: a pergunta vira "o rastro acrescenta algo ao que **até um bom revisor de IA** já vê no código?".
4. **RQ4** ganha argumento na literatura (evidência > escala).

## Riscos

- **Velocidade:** ARCTIC, LEDGER e "Who Pays the Review Cost?" saíram entre agosto e outubro de 2026. Uma equipe grande pode juntar rastro + ordenação de trechos a qualquer momento. Vale mirar um primeiro artigo curto (RQ1 + RQ2) logo.
- **Dados dos agentes atuais:** o AIDev tem PRs reais, mas não tem trajetórias; os dados com trajetória são de agentes antigos. O Catenary pode, no futuro, gerar rastros de agentes modernos.

## Referências (arXiv)

- 2607.29516 — ARCTIC: Intent, Drift, and Spotlight for AI-Generated Diffs at Scale (Meta)
- 2608.18398 — LEDGER: Claim-to-Evidence Trace Graphs for Auditing LLM Agents
- 2607.18057 — Test Coverage Analysis of Agentic Pull Requests
- 2610.11179 — Who Pays the Review Cost? Triage, Fairness, and Accountability in AI-authored PRs
- 2404.10703 — An Empirical Study on Code Review Activity Prediction and Its Impact in Practice
- 2607.02782 — A Preliminary Study on Explaining Risk of Code Changes using LLM-Based Prediction Models
- 2601.19287 — Understanding Dominant Themes in Reviewing Agentic AI-authored Code
- 2601.15195 — Where Do AI Coding Agents Fail? Failed Agentic PRs in GitHub
- 2606.13468 — Understanding the Rejection of Fixes Generated by Agentic Pull Requests
- 2602.04226 — Why Agentic-PRs Get Rejected: A Comparative Study of Coding Agents
- 2601.04886 — Analyzing Message-Code Inconsistency in AI Coding Agent-Authored PRs
- 2609.35659 — Tracekit: Intent-Reasoning-Action Auditing for Autonomous Coding Agents
- 2609.36170 — Assay: Content-Addressed Evidence Graphs for AI-Assisted Software Delivery
- 2502.13069 — Ambig-SWE: Interactive Agents to Overcome Underspecificity
- 2603.26233 — Ask or Assume? Uncertainty-Aware Clarification-Seeking in Coding Agents
- 2610.01769 — CONTRA: Behavior-Changing Questions for Selective Clarification
- 2607.02294 — Coding Agents Are Guessing: Action-Boundary Violations in Underspecified DevOps Instructions
- 2208.04259 — First Come First Served: The Impact of File Position on Code Review
- 2609.22610 — Does Order Matter? File Ordering and Code Review Effectiveness
- 2610.01023 — Groundability, Not Scale Alone: When Weak Reviewers Can Audit Strong Coding Agents
- 2606.22721 — Habituation at the Gate: Declining Scrutiny in Human Review of AI Agent Code
- 2602.09185 — AIDev: Studying AI Coding Agents on GitHub (dataset)
- 2601.00753 — Early-Stage Prediction of Review Effort in AI-Generated Pull Requests
- 2607.06184 — What Resolve Rate Hides: Trajectory Structure Diagnostics (TraceProbe)
- 2302.07248 — Vasconcelos et al., Uncertainty Highlighting in AI Code Completions

---

## Busca de ineditismo focada: o "trecho silencioso" (17/10/2026)

Busca em bases de artigos (arXiv e afins) por três ângulos: (1) mudanças feitas mas não descritas no resumo/descrição de agentes; (2) discordância entre execuções repetidas como sinal; (3) uso disso para guiar a revisão. Também olhamos quem cita os trabalhos mais próximos.

### Os vizinhos mais próximos e a diferença

| Trabalho | O que faz | Diferença para o nosso achado |
|---|---|---|
| **Plans They Abandon, Reports They Author** — Kraishan & Jitkajornwanich, arXiv 2609.12205 (set/2026) | Em 5.851 sessões reais (SWE-chat, 83% Claude Code), o resumo final do agente cita só ~1 em cada 11 ações; a omissão é um pouco maior em sessões cujas linhas o desenvolvedor depois alterou (+1,6 p.p.) | Mede omissão de **ações** (ler, escrever, executar) no nível da **sessão**. Não olha **trechos do diff**, não liga omissão a **pontos de decisão**, não ordena revisão. O efeito sessão-nível (+1,6 p.p.) é **coerente** com o nosso e serve de apoio externo |
| **What Coding Agents Leave Unsaid (CTXGAP)** — Xu et al. (Tencent), arXiv 2610.20003 (out/2026) | Mede quanto do "estado da tarefa" (falhas, riscos, alternativas) dá para recuperar lendo só os relatórios do agente: 52% contra 93% com o contexto completo (37 tarefas) | Nível de **estado da tarefa** via perguntas; não trechos do diff, não decisões entre execuções, não ordenação |
| **Message-Code Inconsistency em PRs de agentes** — Gong et al., arXiv 2601.04886 (MSR 2026) | Inconsistência descrição × código em 23 mil PRs; o tipo "Scope Understated" (descrição omite mudanças significativas) é 22% dos PRs muito inconsistentes | Nível de **PR inteiro**, medida heurística; foca em descrições que **afirmam** o que não foi feito. Não liga omissão a trechos nem a decisões |
| **When Agents Disagree With Themselves** — arXiv 2602.11619 | Variação entre execuções repetidas como sinal de incerteza (nível de tarefa, HotpotQA + SWE-bench) | Usa discordância para a **tarefa inteira**; nós usamos para **trechos** e como régua de "ponto de decisão" |
| **ARCTIC** (Meta, 2607.29516) e **TraceProbe** (2607.06184) | Ordenam regiões do diff só pelo código / alinham execuções para achar onde divergem | Não usam o resumo do agente por trecho |

### Veredito

Não encontramos trabalho que mostre, **no nível do trecho do diff**, que **o que o agente deixa de mencionar no resumo final concentra as escolhas próprias dele** (pontos em que execuções repetidas divergem), nem que teste isso com **registro prévio em vários agentes**. A combinação é inédita até onde a busca alcança.

**Mas a vizinhança é muito próxima e muito recente:** dois trabalhos de setembro/outubro de 2026 estudam exatamente "o que o resumo do agente deixa de fora", em nível de sessão. A próxima pergunta natural deles é a nossa. **A janela é curta** — vale escrever logo e citar os dois como base (eles mostram que o resumo é incompleto; nós mostramos **o que** ele omite e **por que importa para a revisão**).

### Referências novas

- 2609.12205 — Plans They Abandon, Reports They Author: The Narrative Layer of Autonomous Agents
- 2610.20003 — What Coding Agents Leave Unsaid: Measuring Task-State Gaps Between Execution and Reports
- 2602.11619 — When Agents Disagree With Themselves: Behavioral Consistency as an Uncertainty Signal for LLM Agents
- 2609.20812 — Quantifying Overclaiming Propensity in Frontier LLM Agents (direção oposta: afirmar o que não fez)
- 2610.11351 — Deception by Omission: Language Models Knowingly Hide Their Mistakes
- 2601.17627 — Code Change Characteristics and Description Alignment: Agentic versus Human PRs
