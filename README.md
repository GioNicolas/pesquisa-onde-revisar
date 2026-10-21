# Onde Revisar Primeiro — por onde começar a revisar o patch de um agente

Agentes de código (SWE-agent, OpenHands, Claude Code, Codex, Cursor) entregam patches com vários trechos mais rápido do que uma pessoa consegue revisá-los. A pergunta desta pesquisa é: **o rastro do agente (o que ele leu, rodou e disse) ajuda a apontar por onde o humano deve começar a revisar?**

Todo sinal usado precisa passar num teste de durabilidade: *"isso continuaria valendo se a IA fosse perfeita?"*. Prever onde a IA atual erra fica obsoleto a cada modelo novo; apontar o que o revisor precisa saber, não.

**Autor:** Giorgio Nicolas de A. Bertino (CDIA — UFPB)
**Status:** pesquisa em andamento, sem publicação revisada por pares. Hipóteses e critérios são registrados antes de cada análise.

**English summary:** Do coding-agent traces help a human decide where to start reviewing a patch? In a pre-registered confirmatory test (OpenHands + Qwen3-Coder, 4,119 real GitHub tasks, 83,010 code hunks), hunks the agent does **not** mention in its final summary were decision points (changes most other attempts at the same task did not make) 2.3× as often as mentioned hunks (18.9% vs 8.2%; adjusted odds ratio 0.63, 95% CI 0.56–0.72), controlling for code and task features. The effect holds for resolved and unresolved tasks. As a ranking feature it adds little on top of code features; its main value is as an explainable warning to the reviewer.

## Resultado principal: o "trecho silencioso"

> Trechos que o agente **não menciona no resumo final** são pontos de decisão (mudanças que a maioria das outras tentativas da mesma tarefa não fez) **2,3 vezes mais** do que os trechos mencionados.

Teste confirmatório com hipótese, dados e critério de decisão fixados antes da análise, em dados que não tinham sido usados: OpenHands + Qwen3-Coder-480B, 4.119 tarefas reais do GitHub, 25.838 patches, 83.010 trechos.

| | Não citado no resumo | Citado | Razão de chances ajustada (IC 95%) |
|---|---:|---:|---|
| **Todos os trechos** | **18,9%** são pontos de decisão | **8,2%** | **0,634 [0,556; 0,722]**, p = 5 × 10⁻¹² |
| Tarefas resolvidas | 16,1% | 6,7% | — |
| Tarefas não resolvidas | 20,9% | 9,4% | — |
| Só patches com todos os trechos nomeados | 11,5% | 6,4% | 0,737 [0,628; 0,864] |

O mesmo padrão aparece em outros dois agentes: no Claude Code, piloto exploratório que originou a hipótese (20,8% × 8,8%), e no Cursor (18,1% × 4,2%, com só 33 tarefas e sem significância estatística).

**Por que é durável:** numa tarefa ambígua, até um agente perfeito precisa escolher. O revisor precisa saber o que foi escolhido sem ser contado. O efeito aparece também em tarefas resolvidas, então não depende de o agente errar.

**Limites:**
- Como ingrediente de uma ordenação que já usa as características do código, o ganho é pequeno (AUC 0,716 → 0,718). O valor prático mais claro é um **aviso explicável**: "o agente mexeu aqui e não te contou".
- "Ponto de decisão" é uma aproximação, medida pela discordância entre tentativas. Ainda não é atenção medida com revisores humanos: a validação da régua com um avaliador humano está preparada (`scripts/validacao_*.py`), mas ainda não foi feita.

### Como chegamos aqui

Três pilotos vieram antes, todos com critérios registrados antes da análise. Os dois primeiros, com agentes de 2024, deram resultado negativo: os patches eram pequenos demais (mediana de 2 trechos) para o rastro diferenciar trechos. O terceiro, com um agente de 2026, mostrou pistas que variam por trecho e originou a hipótese testada acima. Os resultados negativos estão relatados por inteiro.

- [Pergunta de pesquisa](docs/pergunta-de-pesquisa.md): a versão atual e por que ela mudou.
- [Registro dos pilotos e do teste confirmatório](docs/piloto-premissas.md): critérios, resultados e desvios.
- [Revisão de literatura](docs/revisao-de-literatura.md), incluindo a busca pelos trabalhos mais próximos.

### Como reproduzir

Requer Python 3.12 e git. Os dados vêm do Hugging Face, e o teste confirmatório baixa cerca de 2 GB.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

python scripts/piloto2_pistas.py            # piloto 2 (SWE-agent, 2024)
python scripts/piloto3_moderno.py           # piloto 3: reconstrói os patches do Claude Code a partir dos repositórios
python scripts/piloto3_duelo.py             # piloto 3: duelo de ordenação
python scripts/confirmatorio_silencioso.py  # teste confirmatório (OpenHands)
python scripts/confirmatorio_cursor.py      # replicação suplementar (Cursor)
```

---

## Fase exploratória inicial (histórica)

A primeira versão da pesquisa perguntava se sinais do rastro indicam **quais trechos têm mais chance de estar errados**. Ela foi substituída pela pergunta acima, porque depende de onde a IA atual costuma errar. O material abaixo foi mantido como histórico.

### Como interpretar

Os números abaixo são preliminares. **Diferença em relação ao patch humano não demonstra erro:** soluções corretas podem alterar outros trechos, e uma alteração na mesma região pode estar errada. O alvo automático `is_spurious` deve ser interpretado como ausência de alinhamento segundo a heurística implementada, não como confirmação de bug ou alucinação.

Consulte o [estado e as limitações da fase inicial](docs/estado-da-pesquisa.md) e a [definição de hunk errado](docs/definicao-hunk-errado.md) antes de usar essas conclusões, os gráficos ou os protótipos.

### Método

- **Dados:** trajetórias públicas do SWE-agent ([fonte](https://huggingface.co/datasets/nebius/SWE-agent-trajectories)). Referências humanas: [SWE-rebench](https://huggingface.co/datasets/nebius/SWE-rebench) e [SWE-bench-extra](https://huggingface.co/datasets/nebius/SWE-bench-extra).
- **Rótulo automático (proxy):** alinhamento do hunk com regiões do *Gold Patch* humano, usando tolerância de 15 linhas. Os nomes históricos `is_pertinent` e `is_spurious` não equivalem a código correto e incorreto.
- **Sinais da trajetória:** leitura antes da edição (`read_before_write`), verificação depois da edição, erro de ferramenta logo antes da edição, posição da edição na trajetória, tamanho do hunk, entre outros.
- **Avaliação:** validação cruzada 5-fold agrupada por instância (`GroupKFold`), com curva de esforço de inspeção, AUCEC, ROC-AUC e Recall@K. O esforço conta hunks, não tempo humano ou linhas; o ranking é agregado, sem demonstração de ganho dentro de cada patch.

### Resultados sobre o proxy

1.536 hunks extraídos de 1.000 trajetórias (`resultados/metricas_avaliacao_modelos.csv`). Não representam taxa de detecção de erros confirmados.

| Estratégia                      | AUCEC | ROC-AUC | Recall@20% | Recall@30% |
| :------------------------------ | ----: | ------: | ---------: | ---------: |
| Random (sorteio)                | 0,505 |   0,512 |      20,5% |      29,7% |
| Diff Order (ordem do diff)      | 0,460 |   0,365 |      18,5% |      31,1% |
| Hunk Size (maior primeiro)      | 0,542 |   0,607 |      25,0% |      38,2% |
| Trajetória (Regressão Logística)| 0,610 |   0,783 |      32,3% |      48,5% |
| Trajetória (Random Forest)      | 0,613 |   0,790 |      32,6% |      48,6% |

![Curva de esforço de inspeção](resultados/figuras/curva_esforco_inspecao.png)

### Como reproduzir a fase inicial

```bash
python scripts/mini_projeto_01.py           # Fase 1: exploração de 300 trajetórias
python scripts/extract_hunk_features.py 1000 # Fase 2: extrai hunks e sinais -> dados/
python scripts/model_and_evaluate.py        # Fase 3: modelos, métricas e curva -> resultados/
python scripts/diff_risk_inspector.py       # Fase 4: protótipo do inspetor -> resultados/prototipos/
python scripts/build_learning_portal.py     # gera paineis/aprender_pesquisa.html
```

Os PDFs, painéis e protótipos dessa fase preservam a terminologia da época.

## Estrutura do repositório

```
├── docs/          Pergunta de pesquisa, registro dos pilotos, literatura e limites
├── scripts/       Código dos pilotos, do teste confirmatório e da fase inicial
├── dados/         Tabelas geradas pelos scripts
├── resultados/    Métricas, figuras e protótipos da fase inicial
├── paineis/       Painel e portal de estudo da fase inicial (HTML)
├── planejamento.md       Planejamento original
└── diario-de-pesquisa.md Diário com decisões e números de cada sessão
```
