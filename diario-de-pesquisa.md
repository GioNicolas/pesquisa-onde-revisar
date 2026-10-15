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

---

## Entradas

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
