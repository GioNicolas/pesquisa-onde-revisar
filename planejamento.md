# Planejamento da Pesquisa — Onde Revisar Primeiro

> Nota de 15/10/2026: este planejamento contém hipóteses e escolhas históricas. Alinhamento com patch humano é um proxy e não um rótulo confirmado de correção. Para o estado atual e suas limitações, consulte o [estado da pesquisa](docs/estado-da-pesquisa.md).

> **Projeto:** Priorização de Hunks em Patches Gerados por Agentes de IA via Sinais de Trajetória  
> **Autor:** Giorgio Nicolas de A. Bertino (CDIA — UFPB)  
> **Data de Atualização:** 30 de setembro de 2026  
> **Status:** Em planejamento e estruturação pré-experimental  

---

## 1. Contexto e Motivação

### 1.1 O Gargalo da Revisão de Código de Agentes
Agentes modernos de desenvolvimento autônomo (Claude Code, OpenAI Codex, OpenHands, SWE-agent) já conseguem sintetizar patches inteiros de dezenas ou centenas de linhas em poucos minutos. Contudo, a velocidade de geração do agente supera drasticamente a capacidade humana de inspeção cuidadosa (*code review*).
* O desenvolvedor experiente não tem tempo de auditar cada linha em detalhes.
* O desenvolvedor iniciante muitas vezes não possui repertório técnico suficiente para identificar armadilhas sutis, dependências quebradas ou lógicas tortuosas.

### 1.2 Por que passar nos testes não é suficiente?
A literatura recente de 2025 e 2026 aponta que patches que passam nas suítes de teste de benchmarks como o SWE-bench frequentemente sofrem do fenômeno de **"Lucky Passes"** (aprox. 10,7% segundo Sahoo et al., 2026, *AgentLens*):
* O agente passa nos testes por overfitting ou efeito colateral acidental.
* O processo de geração exibe anti-padrões: ciclos cegos de tentativa e erro, ausência de verificação prévia e regressões latentes.
* Na prática, patches gerados por agentes introduzem dívida técnica ou bugs de borda não cobertos pelos testes existentes.

### 1.3 A Pergunta Central
> **"Sinais extraídos da trajetória de execução do agente conseguem indicar quais hunks de um patch têm maior probabilidade de estar errados ou fora de escopo, superando baselines ingênuos como tamanho do hunk ou complexidade ciclomática?"**

O objetivo aplicado é oferecer ao revisor humano uma ordenação inteligente no diff: **"Olhe estes trechos primeiro"**.

---

## 2. Ajuste Metodológico Crítico (O "Calcanhar de Aquiles")

### 2.1 O Problema da Proposta Inicial
A proposta original sugeria o seguinte método para definir o que é um *"hunk errado"*:
> *"Em patches que falham, reverter um hunk por vez e ver qual reversão muda o resultado dos testes."*

Essa abordagem apresenta três falhas metodológicas e operacionais graves:
1. **Acoplamento sintático e dependência entre hunks:** Em código real, um hunk frequentemente depende de outro (ex: o Hunk 1 define uma função ou importa um módulo; o Hunk 2 a utiliza). Reverter o Hunk 1 isoladamente causará um erro sintático ou `NameError`, fazendo os testes falharem de forma espúria e mascarando a real causa do erro.
2. **Falhas por omissão:** Em patches que falham, a causa mais frequente não é um trecho de código "a mais", mas sim código que **deixou de ser escrito** (omissão de tratamento de erro, falta de implementação de ramo condicional). Reverter hunks em código incompleto raramente fará testes passarem.
3. **Custo impraticável de computação:** Executar suítes completas de teste do SWE-bench exige ambientes Docker pesados e consome de 5 a 20 minutos por tarefa. Reverter e re-testar $N$ hunks em centenas de tarefas demandaria milhares de horas de Docker, inviabilizando a pesquisa local e rápida.

### 2.2 As Soluções Metodológicas Robustas (Ground Truth Viável)

Para resolver esse gargalo sem custo de infraestrutura e com rigor acadêmico aceito em conferências como MSR e SBES, adotaremos as seguintes abordagens:

| Abordagem | Como Funciona | Vantagens |
| :--- | :--- | :--- |
| **A. Alinhamento com o *Gold Patch* (Principal)** | O SWE-bench fornece o patch humano oficial que resolveu a issue (*ground truth*). Classificamos cada hunk do agente pelo grau de sobreposição com os métodos, funções ou arquivos que o patch humano tocou. | • Custo de execução zero (puramente estático).<br>• Identifica hunks espúrios e alucinações de escopo.<br>• Padrão aceito na literatura de *fault localization*. |
| **B. Regressões `PASS_TO_PASS`** | O SWE-bench separa os testes entre `FAIL_TO_PASS` (o bug) e `PASS_TO_PASS` (funcionalidades existentes que não podiam quebrar). Patches que quebram `PASS_TO_PASS` introduziram regressões diretas. | • Permite isolar com precisão falhas que o agente introduziu ativamente em código que já funcionava. |
| **C. Análise Estática / Linters nos Hunks** | Passagem de linters (Ruff, Flake8, Mypy) apenas nas linhas adicionadas/modificadas pelo hunk. | • Detecta erros sintáticos, variáveis não utilizadas, referências nulas e más práticas sem depender de rodar a suíte inteira. |

---

## 3. Extração de Sinais da Trajetória (Feature Engineering)

Para garantir reprodutibilidade, baixo custo e ausência de ruído subjetivo, priorizaremos **sinais determinísticos estruturais** extraídos diretamente do log de execução (JSON):

### 3.1 Sinais Estruturais (Foco Inicial)
1. **`read_before_write` (Leitura prévia):** O agente executou comando de leitura (`open`, `cat`, `view_file`, `head`) no arquivo e região antes da primeira edição? *(Hipótese: edições às cegas têm maior taxa de erro).*
2. **`edit_churn` (Rotatividade de edições):** Quantas vezes aquele arquivo ou intervalo de linhas foi reeditado, revertido ou modificado ao longo da trajetória? *(Hipótese: regiões com alto retrabalho contêm maior incerteza).*
3. **`post_edit_verification` (Verificação posterior):** Houve execução de testes ou checagens pelo agente *após* a última edição desse hunk? *(Hipótese: hunks editados no último passo sem validação são mais arriscados).*
4. **`tool_error_proximity` (Proximidade com erros de ferramenta):** O hunk foi gerado logo após um comando que retornou `exit code != 0` ou exceção no `stderr`?
5. **`phase_in_trajectory` (Momento temporal):** O hunk foi gerado no terço inicial da trajetória (planejamento/foco) ou no terço final (fase de esgotamento/looping)?
6. **`prompt_distance` (Distância do escopo inicial):** O arquivo alterado foi explicitamente citado na issue inicial ou foi descoberto tardiamente via comandos de busca?

### 3.2 Sinais Semânticos (Fase Futura, se necessário)
* Alinhamento entre a intenção declarada em linguagem natural pelo agente e o comando executado (avaliado via LLM juiz).

---

## 4. Baselines de Comparação e Métricas

### 4.1 Baselines (Regras Ingênuas)
Qualquer técnica de priorização só é útil se superar heurísticas triviais:
* **Random:** Ordem aleatória dos hunks.
* **Diff Order:** Ordem natural de aparição no `git diff`.
* **Hunk Size:** Número de linhas adicionadas/removidas (a heurística intuitiva mais comum do revisor humano).
* **Code Complexity:** Complexidade ciclomática / profundidade de AST do trecho modificado.

### 4.2 Métricas de Eficácia
* **Curva de Esforço de Inspeção (*Cost-Effectiveness Curve*):**
  * Eixo X: % acumulada de hunks (ou linhas) revisados.
  * Eixo Y: % acumulada de hunks problemáticos identificados.
* **AUCEC (*Area Under Cost-Effectiveness Curve*):** Mede o ganho global da ordenação da trajetória versus o baseline de tamanho.
* **Top-K Recall / Precision@K:** Ex: "Revisando apenas os 20% mais suspeitos, quantos % dos erros capturamos?"

---

## 5. Cronograma e Fases de Execução (Roadmap Lean)

```
[Fase 1: Exploração] ──> [Fase 2: Extrator & Ground Truth] ──> [Fase 3: Modelagem & Curvas] ──> [Fase 4: Artigo & Catenary]
     (1 semana)                    (2 semanas)                         (1 semana)                       (2 semanas)
```

### Fase 1: Exploração e Aquecimento (Dias 1 a 7)
- [x] Configurar ambiente local e dependências (`datasets`, `pandas`, `matplotlib`).
- [x] Executar o `mini_projeto_01.py` com o dataset `nebius/SWE-agent-trajectories`.
- [x] Analisar a distribuição estatística básica: número de passos, edições e ferramentas em trajetórias que resolveram vs que falharam.

### Fase 2: Extrator de Hunks e Alinhamento com Gold Patch (Dias 8 a 21)
- [x] Criar o script `extract_hunk_features.py`:
  - [x] Fazer o parse do `generated_patch` em blocos `@@ ... @@`.
  - [x] Mapear cada hunk para o histórico de comandos correspondente no arquivo.
  - [x] Extrair as features determinísticas de trajetória para cada hunk.
- [x] Implementar a rotulagem de Ground Truth baseada na sobreposição com o `gold_patch` do SWE-bench.
- [x] Gerar dataset tabular consolidado: `hunk_features_dataset.csv`.

### Fase 3: Modelagem e Curvas de Avaliação (Dias 22 a 28)
- [x] Treinar regressores/classificadores simples (Regressão Logística, Random Forest) sob validação cruzada `GroupKFold`.
- [x] Gerar as curvas de esforço de inspeção e calcular AUCEC vs Baselines (Random, Diff Order, Hunk Size).
- [x] Verificar a hipótese nula: *Os sinais de trajetória superam o tamanho do hunk (AUCEC 0.558 vs 0.531 e ROC-AUC 0.709 vs 0.616; Recall@30% de 41.1% vs 33.3%).*

### Fase 4: Redação Científica e Aplicação Prática (Dias 29 a 42)
- [ ] **No Catenary:** Prototipar o recurso visual de destaque de diff de risco (*"Hunk Risk Highlighter"*).
- [ ] **Na Academia:**
  - Estruturar o artigo nos moldes do **MSR (Mining Software Repositories)** ou **SBES (Simpósio Brasileiro de Engenharia de Software / CBSoft)**.
  - Apresentar os resultados preliminares a potenciais orientadores na UFPB para formalização de bolsa PIBIC/CNPq.

---

## 6. Arquivos e Estrutura do Diretório da Pesquisa

Esta pasta reúne todos os artefatos, scripts, datasets e ferramentas interativas do projeto:

```
C:\Users\Nicolas\PROJETOS\pesquisa-onde-revisar\
├── diario-de-pesquisa.md                               # Log de bordo para anotações e dúvidas
├── planejamento.md                                     # Planejamento estratégico consolidado
│
├── docs/
│   ├── Proposta-de-pesquisa-Onde-revisar-primeiro.pdf  # Documento original da proposta
│   └── 00-Guia-de-inicio-da-pesquisa.pdf               # Guia de início e cronograma detalhado
│
├── scripts/
│   ├── mini_projeto_01.py                              # Fase 1: Exploração preliminar (300 tarefas)
│   ├── extract_hunk_features.py                        # Fase 2: Extrator atômico de hunks e alinhamento
│   ├── model_and_evaluate.py                           # Fase 3: Modelagem GroupKFold, AUCEC e curvas
│   ├── diff_risk_inspector.py                          # Fase 4: Protótipo do Revisor Inteligente (CLI/HTML)
│   └── build_learning_portal.py                        # Gerador do Portal Interativo de Aprendizado
│
├── dados/
│   ├── hunk_features_dataset.csv                       # Dataset consolidado com 1.536 hunks extraídos
│   └── pistas_por_trajetoria.csv                       # Dataset descritivo da Fase 1 (300 instâncias)
│
├── resultados/
│   ├── metricas_avaliacao_modelos.csv                  # Tabela com métricas comparativas vs baselines
│   ├── figuras/
│   │   ├── curva_esforco_inspecao.png                  # Gráfico oficial das Curvas de Esforço (AUCEC)
│   │   └── passos_por_resultado.png                    # Gráfico boxplot de passos por resultado
│   └── prototipos/
│       └── prototipo_inspecao_<instancia>.html         # Relatórios gerados pelo diff_risk_inspector.py
│
└── paineis/
    ├── aprender_pesquisa.html                          # Portal Interativo de Domínio e Aprendizado
    └── dashboard_pesquisa.html                         # Painel visual dos resultados empíricos
```

Os scripts gravam e leem a partir da raiz do projeto, então podem ser rodados de qualquer diretório (ex.: `python scripts/model_and_evaluate.py`).

---

## 7. Referências Centrais

1. **Sahoo et al. (2026)** — *AgentLens: Revealing The Lucky Pass Problem in SWE-Agent Evaluation.* arXiv.
2. **Shu et al. (2026)** — *What Resolve Rate Hides: Trajectory Structure Diagnostics for Coding Agents.* arXiv.
3. **Pandya, Zhang, Lyu (2026)** — *Strained Coherence: A Pre-Failure Signal in Coding Agent Execution Trajectories.* arXiv.
4. **Minh et al. (MSR 2026)** — *Early-Stage Prediction of Review Effort in AI-Generated Pull Requests.*
5. **Vasconcelos et al. (ACM TOCHI)** — *Generation Probabilities Are Not Enough: Uncertainty Highlighting in AI Code Completions.*
6. **Majgaonkar et al. (2025)** — *Understanding Code Agent Behaviour: An Empirical Study of Success and Failure Trajectories.* arXiv.
