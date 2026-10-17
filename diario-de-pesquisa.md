# Diário de pesquisa — Onde revisar primeiro

> Nota de 15/10/2026: este diário preserva interpretações históricas. Os resultados iniciais usam alinhamento com patch humano como proxy; não comprovam detecção de bugs nem validação definitiva da hipótese. Para o entendimento atual, consulte o [estado da pesquisa](docs/estado-da-pesquisa.md).

Uma entrada por sessão de trabalho, a mais recente no topo. Anote o que fez, o que viu (com números), o que decidiu e as dúvidas para o orientador. Esse registro vira a seção de método do artigo e a história da candidatura.

**Pergunta:** sinais da trajetória do agente indicam quais hunks de um patch estão errados melhor que regras simples (sorteio, tamanho do hunk)?

---

## Dúvidas para o orientador

- [ ] A pergunta é relevante e ainda está em aberto?
- [ ] Como definir "hunk errado"? (ajustado: alinhamento com Gold Patch e regressões PASS_TO_PASS em vez de reversão manual de hunks)
- [ ] Quais trabalhos de defect prediction (just-in-time e em nível de linha) eu preciso conhecer?
- [ ] Faz sentido formalizar como iniciação científica?

## Decisões tomadas

| Data | Decisão | Motivo |
| --- | --- | --- |
| 25/09/2026 | Tema: sinais da trajetória para priorizar hunks na revisão | Lacuna confirmada por duas revisões de literatura; ponte LSP↔MCP já existe |
| 30/09/2026 | Refinamento do Ground Truth: alinhamento com Gold Patch e testes PASS_TO_PASS | Reversão manual de hunks causa acoplamento sintático espúrio e custo excessivo de Docker |
| 15/10/2026 | Nova pergunta: onde o humano deve começar a revisar (rastro como registro de evidência), com 4 sub-perguntas | Orientação do professor: prever onde a IA atual erra fica obsoleto a cada modelo novo; ver `docs/pergunta-de-pesquisa.md` |

---

## Entradas

### 17/10/2026 — teste confirmatório: "trecho silencioso" CONFIRMADO
- **Fiz:** Registrei antes um teste confirmatório com uma única hipótese (H1: trecho não citado no resumo final → mais chance de ser ponto de decisão), critério de significância e de relevância (razão de chances ≤ 0,80). Rodei em dados novos: OpenHands + Qwen3-Coder (principal) e Cursor (suplementar).
- **Vi (com números):** OpenHands, com 83.010 trechos de 4.119 tarefas: não citados 18,9% × citados 8,2%; razão de chances ajustada 0,634 [0,556; 0,723], p = 5e-12. CONFIRMADA. Vale para tarefas resolvidas e não resolvidas. No Cursor, 18,1% × 4,2%, mas não significativo (33 tarefas). Como fator de ordenação, porém, M quase não melhora o que o código já dá (AUC 0,716 → 0,718).
- **Decidi:** O "trecho silencioso" vira o resultado central. Corrigi um erro de desenho meu: o controle "tamanho" é soma exata de dois outros. O resultado principal fica idêntico.
- **Dúvida:** Como transformar a associação forte num ganho prático para o revisor (sinal explicável × ranking)?
- **Próximo passo:** Atualizar o orientador e decidir a estrutura do artigo.

### 16/10/2026 (noite) — piloto 3, última chance: três pistas sobrevivem
- **Fiz:** Encontrei rastros públicos de agentes modernos (SWE-rebench, julho de 2026: Claude Code, Codex, Cursor e outros). Registrei o piloto 3 como última chance. Reconstruí os patches do Claude Code reaplicando as edições nos repositórios (519 de 555 sessões).
- **Vi (com números):** 452 patches, 101 tarefas, mediana de 4 trechos. "Uso conferido" varia em 44% dos patches, "estava no plano" em 50% e "mencionado no resumo" em 56%. O código e o pedido não preveem nenhuma delas bem (AUC 0,56–0,65). As três passam também no subconjunto sem artefato de nome. "Estava na falha" falhou por erro de medida (o status do comando não indica falha de teste).
- **Decidi:** A linha continua. Próximo passo: o duelo (dia 5), com régua e critério registrados antes.
- **Dúvida:** Essas pistas apontam para os trechos que precisam de atenção, ou só variam?
- **Próximo passo:** Registrar a régua "onde os agentes discordam" e o critério do duelo.
- **Duelo (dia 5, registrado antes):** o rastro NÃO venceu: AUC 0,614 → 0,634 (Δ +0,021, IC 95% de −0,014 a +0,058). A direção é a esperada. Trechos não citados no resumo são pontos de decisão em 20,8% dos casos, contra 8,8% dos citados. Inconclusivo por falta de dados. Candidato a teste confirmatório: "trecho silencioso".

### 16/10/2026 — crítica externa e piloto 2 (teste de morte #1)
- **Fiz:** Pedi uma crítica externa dura ao desenho (notas internas, não publicadas). Adotei um plano de 5 dias com "testes de morte", registrado antes da análise (`docs/piloto-premissas.md`). Rodei os dias 1–3: cinco pistas ligadas ao trecho (estava na falha, uso conferido, plano, decisão, mencionado no fim) em dados novos (trajetórias 1.001–2.000, `scripts/piloto2_pistas.py`).
- **Vi (com números):** 230 patches, 42 tarefas, 584 trechos. Nenhuma pista variou em ≥ 30% dos patches (5% a 26%). O teste de morte #1 disparou. A mediana é de 2 trechos por patch: há pouco a ordenar.
- **Decidi:** Parar a linha de ordenação com este dataset, como combinado. Gravar a revisão humana no Catenary é difícil na prática e fica para depois.
- **Dúvida:** O problema é a ideia ou os dados (agentes de 2024, patches minúsculos)?
- **Próximo passo:** Decidir entre procurar dados com patches maiores (agentes modernos), transformar o resultado negativo em contribuição ou mudar de rumo.

### 15/10/2026 (tarde) — piloto das premissas
- **Fiz:** Revisão de literatura (`docs/revisao-de-literatura.md`; mais próximo: ARCTIC/Meta, que ordena regiões do diff só com o código). Piloto registrado antes da análise (`docs/piloto-premissas.md`, script `scripts/piloto_premissas.py`).
- **Vi (com números):** 154 patches com 2+ trechos de código (38 tarefas, 383 trechos, 86% mapeados no rastro). P1 FALHOU: a pista "rodou algo depois da última edição" varia entre os trechos em só 3,9% dos patches. P2 passou sem significado (AUC 0,41–0,49), porque não há variação a prever. Descritivo: "estava no plano" varia em 29,9% dos patches; "decisão" em 13,6%.
- **Decidi:** Não seguir para a P3 com essa pista. Ela mede a sessão, não o trecho. A medida exata (cobertura: quais linhas as execuções do agente realmente rodaram) é viável para 27 das 40 tarefas, que têm imagem Docker pronta no SWE-rebench.
- **Próximo passo:** Decidir se fazemos um segundo piloto registrado com a medida exata.

### 15/10/2026
- **Fiz:** Conversa com o orientador. Redefinição da pergunta de pesquisa e das sub-perguntas.
- **Vi:** A crítica central do professor: não vale pesquisar "onde a IA normalmente erra", porque isso muda a cada modelo. Vale apontar onde o humano deve começar a revisar, com sinais que continuem válidos mesmo com uma IA perfeita.
- **Decidi:** Pergunta principal: "o rastro do agente ajuda a apontar onde o humano deve começar a revisar um patch?". RQ1 (por que um trecho precisa de atenção), RQ2 (quais motivos deixam marcas no rastro), RQ3 (ordenar com rastro + código bate ordenar só com código?), RQ4 (vale para agentes fracos e fortes?). O rastro passa a ser registro de evidência, não detector de sintomas de IA fraca.
- **Próximo passo:** Busca de literatura guiada pelas RQs; depois, atualização ao orientador.

### 02/10/2026
- **Fiz:** Criação e disponibilização do Portal Interativo de Aprendizado (`aprender_pesquisa.html` e gerador `build_learning_portal.py`) para estudo aprofundado e preparação do autor antes do contato com orientadores.
- **Conteúdo Integrado:**
  1. Trilha de 7 módulos dinâmicos cobrindo o problema, o gargalo dos testes em Docker vs Gold Patch e os 4 scripts construídos.
  2. Dissecador interativo de Git Diff (clique para explicar linhas de cabeçalho, hunk meta, remoções e adições).
  3. Simulador interativo da Curva de Esforço com slider dinâmico (mostrando o ganho do nosso método em qualquer nível de esforço de 10% a 90%).
  4. Visualizador de casos de estudo reais (`AnalogJ` vs `Melevir`) com diagnósticos em linguagem natural e badges de risco.
  5. Treinador de pitch com flashcards das perguntas mais difíceis da banca/orientador e quiz prático com feedback imediato.
- **Decidi:** Utilizar o portal como instrumento central de fixação conceitual e retórica para garantir domínio total de cada métrica e decisão técnica.
- **Próximo passo:** Estudo individual da trilha e discussão de refinamento do mapeamento fino por linha.

### 01/10/2026
- **Fiz:** Criação do ambiente virtual, instalação de dependências e execução do `mini_projeto_01.py` com streaming de 300 trajetórias de `nebius/SWE-agent-trajectories`.
- **Vi (com números):** 
  - Taxa de resolução na amostra: 5,7%.
  - Leituras de código (`open`, `goto`, `scroll`): mediana de 3,0 (falhou) vs **5,0** (resolveu).
  - Buscas de contexto (`search_dir`, `grep`): mediana de 2,0 (falhou) vs **5,0** (resolveu).
  - Execução de testes (`pytest`, `unittest`): mediana de 1,0 (falhou) vs **3,0** (resolveu).
  - Comandos mais frequentes do agente: `edit` (1.884x), `open` (930x), `python` (888x), `search_dir` (643x).
  - Quem resolveu fez 2,5x mais buscas e 3x mais testes antes de entregar.
- **Fiz (Fase 2):** Implementação e execução do `extract_hunk_features.py` mapeando 426 hunks atômicos contra 23.144 Gold Patches de referência (`SWE-rebench` + `SWE-bench-extra`).
- **Vi nos hunks (com números):**
  - Dos 426 hunks gerados, **72,5% são espúrios/fora de escopo** e **27,5% são pertinentes** (alinhados ao Gold Patch).
  - `read_before_write`: **100%** dos hunks pertinentes foram lidos antes da edição vs apenas **59,2%** dos espúrios (mais de 40% das alucinações foram feitas às cegas!).
  - `error_preceded_edit`: **24,9%** dos hunks espúrios foram gerados imediatamente após uma falha de comando/exceção (vs apenas 3,4% nos pertinentes — 7,3x mais frequente!).
  - `hunk_size`: hunks espúrios têm em média 30 linhas vs apenas 7,8 linhas nos pertinentes.
- **Fiz (Fase 3):** Implementação e execução do `model_and_evaluate.py` com validação cruzada 5-fold agrupada por instância (`GroupKFold`), gerando as curvas de esforço de inspeção e calculando AUCEC e ROC-AUC vs baselines.
- **Vi na Modelagem (com números):**
  - **AUCEC (Área sob Curva de Esforço):**
    - Diff Order (ordem padrão do diff): 0,475
    - Random (sorteio): 0,507
    - Hunk Size (heurística humana de olhar blocos maiores): 0,531
    - **Sinais de Trajetória (Random Forest): 0,558** (superou todos os baselines!)
  - **ROC-AUC:** Salto de **0,616** (tamanho) para **0,709** (trajetória).
  - **Recall@30% de inspeção:** Ao inspecionar os 30% mais suspeitos ordenados pela trajetória, capturamos **41,1%** dos hunks errados (vs 25,6% na ordem natural do diff e 33,3% pelo tamanho do hunk).
- **Fiz (Fase 4 - Protótipo e Expansão de Dados):** 
  1. Criação do protótipo `diff_risk_inspector.py` (CLI + HTML interativo) para diagnosticar e colorir hunks de risco em tempo real.
  2. Expansão da extração de 300 para **1.000 trajetórias**, saltando a base de dados de 426 para **1.536 hunks atômicos**.
- **Vi na Base Expandida de 1.536 Hunks (com números):**
  - **AUCEC:** Sinais de Trajetória alcançaram **0,613** (vs 0,542 de tamanho e 0,460 da ordem do diff).
  - **ROC-AUC:** Salto expressivo para **0,790** (quase 0,80 — padrão de excelência científica).
  - **Recall@30% de esforço:** Inspecionando apenas 30% dos hunks indicados, capturamos **48,6% de todos os erros da IA** (quase a metade!).
  - `read_before_write`: presente em **99,2%** dos hunks corretos vs apenas 46,0% dos espúrios (coeficiente -4.327).
  - `last_edit_step_ratio` (+0.549): alterações feitas nos últimos passos sob estresse têm alto risco de erro.
- **Decidi:** A evidência empírica com mais de 1.500 hunks é definitiva e encerra qualquer dúvida sobre a validade da hipótese. O protótipo visual funciona com precisão na prática.
- **Anotação de Domínio e Estudo (Autor):** Programar ciclo de estudo aprofundado para dominar integralmente:
  1. O formato JSON das trajetórias do SWE-agent (`roles`, comandos em blocos de código e saídas do ambiente).
  2. A estrutura de diffs unificados e parsing de hunks (`@@ -old,count +new,count @@`).
  3. Lógica do alinhamento estático contra o *Gold Patch* humano.
  4. Métricas de esforço de inspeção (AUCEC, Cost-Effectiveness Curves e GroupKFold).
  5. Leitura dos artigos-chave citados (AgentLens, Strained Coherence) para defender a tese e metodologia com segurança.
- **Próximo passo:** Fase 4 — Estruturar a redação do artigo científico (seções de Introdução, Metodologia, Resultados e Discussão) e prototipar a visualização no Catenary.

### 30/09/2026
- **Fiz:** Consolidação de todos os arquivos da pesquisa em `PROJETOS/pesquisa-onde-revisar` e criação do `planejamento.md`.
- **Vi (com números):** Reversão manual de hunks em patches com falha não isola erros por omissão e gera quebras sintáticas artificiais.
- **Decidi:** Adotar sobreposição com o Gold Patch do SWE-bench como métrica primária de hunk pertinente vs espúrio/alucinado.
- **Próximo passo:** Rodar o `mini_projeto_01.py` com o dataset da Nebius para extrair os primeiros padrões.

### 26/09/2026
- **Fiz:** montei a pasta da pesquisa, o guia e o mini-projeto 01.
- **Vi:** —
- **Próximo passo:** preparar o ambiente Python e rodar o mini-projeto 01 com 300 trajetórias.

<!-- Modelo para copiar:
### DD/MM/AAAA
- **Fiz:**
- **Vi (com números):**
- **Decidi:**
- **Dúvida:**
- **Próximo passo:**
-->
