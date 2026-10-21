# Piloto: as premissas valem?

**Registrado em 15/10/2026, ANTES de rodar a análise.** Os critérios abaixo não podem ser alterados depois de ver os resultados. Qualquer mudança posterior deve ser registrada como desvio, com data e motivo.

## Objetivo

Testar, de forma barata, se a pesquisa vale a pena. Ela depende de três premissas:

- **P1 — Varia dentro do patch:** num patch com vários trechos, a evidência do rastro muda de um trecho para outro.
- **P2 — O código sozinho não mostra:** características do código (tamanho, posição, arquivo) não conseguem prever bem essa evidência.
- **P3 — Tem relação com o que importa:** trechos sem evidência de verificação (ou com decisão de julgamento) são os que mais precisam de atenção humana.

## Dados

- 1.000 primeiras trajetórias de `nebius/SWE-agent-trajectories` (mesmas do estudo inicial).
- **Trechos de código:** hunks que modificam arquivos que já existiam no repositório (excluídos arquivos novos criados pelo agente e arquivos de teste).
- **Patches elegíveis:** com 2 ou mais trechos de código mapeados no rastro. Estimativa prévia: ~160 patches, 35 tarefas, ~400 trechos.

## Pistas do rastro (por trecho)

1. **V — Verificado depois (pista principal):** o agente executou algum teste ou programa (ex.: `python ...`, `pytest`, `unittest`) **depois** da última edição que produziu aquele trecho.
2. **D — Decisão (descritiva):** a mensagem do agente na edição que produziu o trecho contém marcadores de escolha ou suposição. Lista fixa: `assum`, `instead`, `alternativ`, `for simplicity`, `simplif`, `workaround`, `not sure`, `unclear`, `decide`, `choose`, `option`.
3. **Pl — Estava no plano (descritiva):** o nome da função (ou, sem função, o nome do arquivo) do trecho aparece em mensagens do agente antes da edição que o produziu.

**Mapeamento trecho → edição:** cada trecho do patch final é associado à última edição do agente cujo texto inserido coincide com linhas adicionadas do trecho. Trechos sem correspondência (ex.: só remoções) ficam fora e a taxa de mapeamento é reportada.

## Critérios de "vale a pena" (aprovados pelo autor em 15/10/2026)

| Premissa | Critério de sucesso |
|---|---|
| **P1** | Em **≥ 30%** dos patches elegíveis, a pista V muda de um trecho para outro |
| **P2** | O melhor de dois modelos (regressão logística e random forest), usando só características do código, prevê V com **ROC-AUC < 0,70** (validação cruzada agrupada por tarefa) |
| **P3** | Nos trechos rotulados pelo autor (30–40, cegos ao rastro), a proporção sem verificação é **≥ 20 pontos percentuais maior** entre os que precisam de atenção. Com poucos trechos, isso indica direção, não prova |

**Decisão:** se P1 e P2 passarem, a ideia é viável e segue para a rotulagem da P3. Se P1 ou P2 falharem, registramos o resultado e repensamos antes de investir mais.

Características do código usadas na P2: linhas adicionadas, linhas removidas, tamanho do hunk, posição do hunk no patch (absoluta e relativa), número de hunks no mesmo arquivo, número de arquivos no patch, se é o primeiro/último hunk do arquivo.

## Limitações conhecidas

- V é aproximada: "rodou algo depois" não garante que aquele trecho foi executado. A versão exata (re-executar com medição de cobertura, via Docker) fica para uma etapa seguinte.
- Agentes antigos (SWE-agent com modelos Llama).

## Esclarecimento decidido antes da análise (registrado depois, por falha de comando)

- **Comandos que contam como execução para V:** `python`, `pytest`, `unittest`, `tox`, `nosetests`, `bash`, `sh`, `make`, `asv` (roda benchmarks, executa o código) e equivalentes de outras linguagens. **Não contam** linters que só leem o texto, como `flake8`.
- Essa decisão foi tomada e anunciada ao autor **antes** de rodar a análise, depois de um teste que olhou apenas a taxa de mapeamento (79% em 200 trajetórias; quase todos os não mapeados eram só remoções), sem calcular P1 ou P2. O comando que deveria gravar este parágrafo no documento falhou e ele só foi gravado **depois** da análise. O registro fica aqui por transparência.

## Resultado (15/10/2026)

| | Valor |
|---|---|
| Trechos de código em patches com 2+ trechos | 475 |
| Mapeados a uma edição do rastro | 86,3% |
| Patches elegíveis (2+ trechos mapeados) | 154, de 38 tarefas, com 383 trechos |
| **P1** — patches em que V varia entre os trechos | **3,9% (6/154) → FALHOU** (critério ≥ 30%) |
| Taxa geral de V | 58,0% dos trechos |
| **P2** — prever V só com o código (ROC-AUC) | regressão logística 0,410; random forest 0,492 → passou, **mas sem significado** (ver abaixo) |
| [descritivo] D — decisão | presente em 19,8% dos trechos; varia em 13,6% dos patches |
| [descritivo] Pl — estava no plano | presente em 76,2% dos trechos; varia em 29,9% dos patches |

**Decisão, conforme registrado:** P1 falhou. Não seguimos para a P3 com esta pista; repensamos antes de investir mais.

**Interpretação:** a pista V, do jeito aproximado que foi medida ("rodou algo depois da última edição"), é praticamente uma propriedade da **sessão inteira**, não do trecho: o agente costuma fazer todas as edições e depois rodar (ou não rodar) alguma coisa, então todos os trechos do patch recebem o mesmo valor. Por isso a P2 "passou" sem significado: não há variação dentro do patch para o código prever. É a mesma armadilha já anotada antes ("pistas da trajetória inteira não distinguem trechos").

**O que isso não mostra:** que a verificação não varia por trecho. Mostra que **esta medida aproximada** não enxerga a variação. A medida exata — quais linhas cada execução do agente realmente executou (cobertura) — ainda não foi testada.

---

# Piloto 2: plano de 5 dias com "testes de morte"

**Registrado em 16/10/2026, ANTES de escrever o código de análise e de olhar qualquer resultado.** Plano adotado pelo autor após uma crítica externa ao desenho (notas internas, não publicadas). Regra geral: se um teste de morte disparar, paramos aquela linha em vez de insistir.

**Lição do piloto 1 que orienta tudo:** nenhuma pista pode ser do tipo "algo aconteceu na sessão depois do momento t". Toda pista cruza a **identidade do trecho** (arquivo, nome da função) com **eventos do rastro**.

## Dias 1–3 — pistas ligadas ao trecho (sem Docker)

**Dados:** trajetórias **1.001 a 2.000** de `nebius/SWE-agent-trajectories` (nunca analisadas). Mesma elegibilidade e mesmo mapeamento trecho → edição do piloto 1. Relatório secundário: só as tarefas que não aparecem nas trajetórias 1–1.000.

**Nome do trecho:** o nome da função ou classe no cabeçalho do hunk (`@@ ... @@ def nome`). Sem nome, o trecho é "de módulo".

**Pistas (cada uma testada separadamente):**

| Pista | Definição | Por que vale com IA perfeita |
|---|---|---|
| **T — estava na falha observada** | Antes da edição que produziu o trecho, a saída de algum comando de execução do agente contém uma linha de traceback `File "...<arquivo do trecho>", line N, in <nome do trecho>` (para trecho de módulo: `in <module>`). Tracebacks do texto do pedido **não** contam (isso é informação de código + pedido) | Separa mudança com evidência observada de necessidade de mudança lateral/preventiva |
| **U — uso conferido** | Em algum momento da sessão, o agente rodou uma busca (`search_dir`, `search_file`, `grep`, `rg`) cujo termo contém o nome do trecho. Trecho de módulo: U = 0 | Mede se o impacto da mudança (quem usa) foi observado |
| **Pl — estava no plano** | Igual ao piloto 1 (nome mencionado nas mensagens do agente antes da edição) — agora testada em dados novos | Mudança planejada × mudança feita "de passagem" |
| **D — decisão** | Igual ao piloto 1 (marcadores de escolha/suposição na mensagem da edição) — agora testada em dados novos | Decisão de julgamento depende da tarefa, não do modelo |
| **M — mencionado no fim** | O nome do trecho (ou, sem nome, o nome do arquivo) aparece nas mensagens das 3 últimas ações do agente | Trecho omitido no fechamento é ponto cego |

**Critérios (os mesmos já aprovados no piloto 1, para cada pista):**

- **P1:** a pista varia entre os trechos em **≥ 30%** dos patches elegíveis.
- **P2:** o melhor de dois modelos (regressão logística e random forest), com validação cruzada agrupada por tarefa, prevê a pista **só com código + pedido** com **ROC-AUC < 0,70**. Características: as 9 do piloto 1 + "nome do trecho citado no pedido" + "arquivo do trecho citado no pedido". (Assim a pista precisa mostrar algo que o código e o texto do pedido não mostram.)
- Pista presente em menos de 5% ou mais de 95% dos trechos: P2 é reportada, mas marcada como pouco informativa.

**Teste de morte #1:** se **nenhuma** pista passar em P1 e P2, concluímos que o rastro destes agentes não guarda evidência por trecho; paramos a linha de ordenação com este dataset e repensamos (dados mais ricos/agentes modernos). Se uma ou mais passarem, só elas seguem para os dias 4–5. Todas as cinco são reportadas, inclusive as que falharem.

## Dia 4 — cobertura: rastro × testes do projeto (Docker)

Até 20 tarefas com imagem do SWE-rebench, começando por 5 para medir o custo. Para cada trecho, considerando só as linhas adicionadas executáveis (excluídas linhas de `def`, `class`, decoradores e `import`, que rodam ao importar o arquivo):

- **Cov_Rastro:** alguma dessas linhas executou ao reexecutar, sobre o código final, os comandos de execução que o agente rodou depois da última edição do trecho (scripts descartáveis reconstruídos a partir do rastro).
- **Cov_Suite:** alguma dessas linhas executou rodando os testes já existentes do projeto listados pelo SWE-rebench para a tarefa (`PASS_TO_PASS`), sem olhar o rastro.

**Teste de morte #2:** se Cov_Rastro e Cov_Suite concordarem em **mais de 90%** dos trechos avaliáveis, abandonamos a cobertura bruta (um avaliador diria que rodar os testes com cobertura faz o mesmo sem rastro).

## Dia 5 — duelo: só código × código + rastro

Régua escolhida pelo autor: **"onde os agentes discordam"** (trechos em regiões em que tentativas diferentes para a mesma tarefa divergem = pontos de decisão). A definição exata e o critério de vitória serão registrados aqui **antes** do dia 5.

## Resultado dos dias 1–3 (16/10/2026)

Script: `scripts/piloto2_pistas.py` · saída: `dados/piloto2_trechos.csv`. Antes da análise, a leitura (tracebacks, texto do pedido, buscas) foi conferida **só em trajetórias antigas (1–200)**, sem calcular P1 ou P2.

**Dados:** 1.442 trechos de código em patches com 2+ trechos; 42,5% ligados a uma edição (95% dos não ligados só removem linhas, excluídos por definição). **Patches elegíveis: 230, de 42 tarefas, 584 trechos.** Todas as 42 tarefas são novas (nenhuma aparece nas trajetórias 1–1.000), então o relatório secundário é idêntico ao principal.

| Pista | Presente | P1: varia (≥ 30%) | P2: código + pedido preveem (AUC < 0,70) | Sobrevive? |
|---|---|---|---|---|
| T — estava na falha observada | 5,1% | 5,2% ❌ | 0,49 ✅ (pouco informativa) | não |
| U — uso conferido | 41,6% | 23,5% ❌ | 0,77 ❌ | não |
| Pl — estava no plano | 81,8% | 22,6% ❌ | 0,67 ✅ | não |
| D — decisão | 33,6% | 15,2% ❌ | 0,45 ✅ | não |
| M — mencionado no fim | 39,7% | 26,1% ❌ | 0,55 ✅ | não |

**Decisão, conforme registrado: o teste de morte #1 disparou.** Nenhuma pista sobreviveu. Paramos a linha de ordenação com este dataset; os dias 4–5 não são executados com ele.

**Checagens posteriores (não pré-registradas; só para interpretar, não mudam a decisão):**

- O resultado não vem de patches estranhos: o maior patch elegível tem 12 trechos; a mediana é **2 trechos** por patch (75% têm até 3).
- Calculando a variação por tarefa (para nenhuma tarefa com muitos patches dominar): T 7%, U 20%, Pl 28%, D 18%, M 21% — mesma conclusão.
- Em 50% dos patches **alguma** das cinco pistas varia. Isso é olhar depois e juntar pistas ("pintar o alvo"), então **não** conta como sucesso; serve apenas como pista para o próximo desenho.
- U falhou também em P2: buscar o nome da função é previsível pelo pedido (o agente busca o que o pedido cita).

**Interpretação (piloto 2):** nestes dados, o rastro quase não diferencia os trechos de um mesmo patch. Uma explicação provável é **estrutural**: os agentes de 2024 em tarefas do tipo SWE-bench produzem patches minúsculos (mediana de 2 trechos, muitas vezes na mesma função), em que há pouco a ordenar e pouco espaço para variar. Isso **não** mostra que a ideia falha em patches grandes de agentes modernos — mas também não há, ainda, evidência a favor.

---

# Piloto 3: última chance, com agentes modernos

**Registrado em 16/10/2026, ANTES de escrever o código de análise e de calcular qualquer pista.** Decisão do autor: é a **última tentativa** desta linha. Se falhar, encerramos a ordenação pelo rastro.

**Por que outro dataset (e o que já foi olhado):** o piloto 2 sugeriu que os patches dos agentes de 2024 eram pequenos demais (mediana de 2 trechos). Antes deste registro, olhamos **apenas o formato e o tamanho** dos dados novos: no Claude Code, a mediana é de 4 edições de código em 2 arquivos, e 72% das sessões têm 3 ou mais edições. Nenhuma pista foi calculada.

## Dados

- `ibragim-bad/swe_rebench_07_2026_trajectories` (SWE-rebench, julho de 2026): 111 tarefas reais de GitHub em Python, Go, Java, Rust e TypeScript.
- **Participante: Claude Code** (modelo Fable 5), 5 tentativas × 111 tarefas = 555 rastros. Foi escolhido porque registra cada edição exatamente (`Edit`/`Write`), o que permite reconstruir o patch. Os outros participantes editam por comandos de terminal.
- O raciocínio interno foi removido do dataset; restam as mensagens visíveis do agente e o **resumo final**.

## Reconstrução do patch

- O repositório é obtido no commit base do PR (API do GitHub) e as edições `Edit`/`Write` são reaplicadas em ordem. Se alguma edição não se aplicar (texto antigo não encontrado), o rastro é excluído. A taxa de sucesso é reportada.
- Edições feitas por terminal (`sed -i`, redirecionamentos, scripts) não são reaplicadas. **Secundário:** repetir a análise sem os rastros que têm comandos desse tipo.
- Patch final = `git diff` contra a base, com os detectores de função do git para cada linguagem. **Trechos** = hunks em arquivos de código que já existiam, excluídos arquivos de teste. O mapeamento trecho → edição segue a mesma regra dos pilotos 1 e 2 (última edição cujo texto novo coincide com linhas adicionadas do trecho).
- **Nome do trecho:** o identificador logo antes do primeiro `(` no cabeçalho do hunk. Sem ele, o trecho é "de módulo".

## Pistas (as cinco do piloto 2, adaptadas)

| Pista | Definição |
|---|---|
| **T — estava na falha observada** | Antes da edição, algum comando do agente terminou com erro e a saída contém o nome do arquivo do trecho **e** o nome do trecho |
| **U — uso conferido** | Em algum momento, uma busca (`Grep` ou `grep`/`rg`/`git grep` no terminal) contém o nome do trecho. Nomes com menos de 4 caracteres ou trecho de módulo: U = 0 |
| **Pl — estava no plano** | O nome do trecho (ou, sem nome, o nome do arquivo) aparece em mensagens do agente antes da edição |
| **D — decisão** | Marcadores de escolha/suposição (mesma lista) nas mensagens do agente desde a edição anterior até esta |
| **M — mencionado no resumo** | O nome do trecho (ou, sem nome, o nome do arquivo) aparece na mensagem final do agente |

## Critérios (os mesmos de antes)

- **P1:** a pista varia entre os trechos em **≥ 30%** dos patches elegíveis (2+ trechos mapeados).
- **P2:** código + pedido preveem a pista com **ROC-AUC < 0,70** (melhor entre regressão logística e random forest; validação cruzada agrupada por tarefa; mesmas 11 características do piloto 2).
- Prevalência abaixo de 5% ou acima de 95%: P2 é marcada como pouco informativa.

## Decisão

- **Se nenhuma pista sobreviver:** encerramos a linha "ordenar trechos pelo rastro". O autor avalia se o conjunto dos três pilotos negativos vale publicação.
- **Se uma ou mais sobreviverem:** seguem para os dias 4–5 neste dataset. A régua "onde os agentes discordam" e o critério do duelo serão registrados antes.

## Resultado do piloto 3 (16/10/2026)

Script: `scripts/piloto3_moderno.py` · saídas: `dados/piloto3_trechos.csv`, `dados/piloto3_sessoes.csv`, `dados/piloto3_bases.json`. Antes da análise, só a mecânica foi conferida (reconstrução e nomes, na tentativa 0), sem calcular pistas. Ajustes mecânicos feitos nessa etapa: leitura de arquivos compatível com Python 3.12, um repositório preparado por vez, caminhos longos do Windows, e, em Go, o receptor do método (`func (r *X) Nome(`) é ignorado ao extrair o nome.

**Reconstrução:** 519 de 555 sessões (93,5%); 36 tinham uma edição que não se aplicou. 59,8% das sessões têm comandos de terminal que podem editar arquivos; 99,1% têm resumo final. Trechos de código: 2.589, 96,8% ligados a uma edição. **Patches elegíveis: 452, de 101 tarefas, 2.450 trechos; mediana de 4 trechos por patch** (no piloto 2 era 2).

| Pista | Presente | P1: varia (≥ 30%) | P2: AUC código + pedido (< 0,70) | Sobrevive? | Secundário (sem edição por terminal: 190 patches) |
|---|---|---|---|---|---|
| T — estava na falha | 0,0% | 0% ❌ | — | não | igual |
| **U — uso conferido** | 22,6% | **44,2%** ✅ | 0,64 ✅ | **sim** | 45,8% / 0,59 ✅ |
| **Pl — estava no plano** | 28,4% | **49,8%** ✅ | 0,56 ✅ | **sim** | 49,5% / 0,52 ✅ |
| D — decisão | 2,4% | 7,7% ❌ | 0,74 ❌ | não | igual |
| **M — mencionado no resumo** | 59,3% | **56,4%** ✅ | 0,65 ✅ | **sim** | 58,9% / 0,55 ✅ |

**Decisão, conforme registrado: U, Pl e M sobrevivem.** A linha não é encerrada; seguimos para o duelo (dia 5), cuja régua e critério serão registrados antes.

**Checagens posteriores (não pré-registradas; só para interpretar):**

- **Possível artefato do nome:** U vale 0 quando o trecho não tem nome, e Pl/M usam o nome do arquivo nesse caso. Então a variação poderia vir só de "tem nome ou não". Teste: só os 192 patches em que **todos** os trechos têm nome → varia: U 40%, Pl 31%, M 51%; AUC (código + pedido): U 0,45–0,50, Pl 0,45–0,52, M 0,63–0,65. **As três continuam passando.** Na amostra inteira, se "tem nome" entra como característica do código, M sobe para AUC 0,76 (falharia); U 0,69 e Pl 0,68 ficam no limite. Conclusão: o resultado se apoia melhor no subconjunto limpo, e no duelo "tem nome" entra como característica do código.
- Variação média por tarefa: U 43%, Pl 49%, M 55%.
- Por linguagem: TypeScript é a mais fraca (U varia em 18%), porque o git não detecta funções de TypeScript (43% dos trechos ficam sem nome).
- **T = 0% é falha de medida, não do sinal:** a definição exigia comando "com erro", mas o Claude Code costuma filtrar a saída (`| tail`), então o comando termina "com sucesso" mesmo quando os testes falham (297 saídas com marcas de falha tinham status de sucesso; só 96 comandos tiveram status de erro). Uma T corrigida seria uma **nova** hipótese, a registrar antes de testar.
- D quase não existe aqui porque o raciocínio interno foi removido do dataset.

**O que isso mostra e o que ainda não mostra:** pela primeira vez, o rastro guarda informação **por trecho** que o código e o pedido não preveem bem. Isso é **necessário, mas não suficiente**: ainda falta mostrar que essas pistas apontam para os trechos que **precisam de atenção** (dia 5).

## Dia 5 — duelo: só código × código + rastro

**Registrado em 16/10/2026, ANTES de calcular a régua ou rodar o duelo. Desenho aprovado pelo autor.** O dia 4 (cobertura via Docker) foi pulado: ele testava a cobertura, que não está entre as pistas sobreviventes.

**Dados:** os trechos dos patches elegíveis do piloto 3 (`dados/piloto3_trechos.csv`).

**Régua — "ponto de decisão" (onde os agentes discordam):**

- **Unidade** de cada trecho: (arquivo, nome do trecho); sem nome, (arquivo).
- Para cada trecho de uma tentativa, olhamos as **outras tentativas reconstruídas da mesma tarefa** (até 4) e contamos quantas mexeram na mesma unidade (qualquer trecho de código delas, ligado ou não a uma edição).
- **Y = 1 (ponto de decisão)** se no máximo 25% das outras tentativas mexeram nessa unidade (com 4 outras: 0 ou 1). Caso contrário, Y = 0 (caminho comum).
- Tarefas com menos de 3 outras tentativas reconstruídas ficam de fora. Se Y estiver em menos de 5% ou mais de 95% dos trechos, o duelo é marcado como pouco informativo.

**Os dois competidores** (regressão logística padronizada, mesmo modelo nos dois):

- **(a) Só código + pedido:** as 11 características anteriores + "tem nome".
- **(b) Código + pedido + rastro:** (a) + U, Pl, M.
- Validação cruzada em 5 partes agrupada por tarefa; previsões fora da amostra.

**Medida e critério de vitória do rastro:**

- **Principal:** ROC-AUC de (b) menos ROC-AUC de (a). O rastro vence se **Δ ≥ 0,03** **e** o intervalo de 95% de um bootstrap por tarefa (1.000 reamostragens) ficar **todo acima de zero**.
- **Secundário:** em patches com pelo menos um trecho Y = 1 e um Y = 0, a fração em que o trecho ordenado em 1º lugar é Y = 1, para (a) e (b). Também reportamos a mesma análise só nos patches em que todos os trechos têm nome, e os coeficientes de U, Pl e M (direção descritiva).

**Decisão:** se o rastro vencer, temos o primeiro resultado de que ele ajuda a apontar onde revisar, e a pesquisa vale a pena. Se não vencer, as pistas variam mas não apontam pontos de decisão; registramos e avaliamos com o autor o que fazer (incluindo publicar os resultados).

## Resultado do dia 5 (16/10/2026)

Script: `scripts/piloto3_duelo.py` · saída: `dados/piloto3_duelo.csv`. 2.391 trechos com régua (441 patches, 97 tarefas); **Y = 1 (ponto de decisão) em 13,6%**.

| | (a) só código + pedido | (b) + rastro | Δ AUC | IC 95% (bootstrap por tarefa) | 1º lugar é ponto de decisão (a → b) |
|---|---|---|---|---|---|
| **Principal** | 0,614 | 0,634 | **+0,021** | [−0,014; +0,058] | 44,9% → 51,9% (156 patches) |
| Secundário (todos os trechos nomeados) | 0,580 | 0,639 | +0,059 | [−0,005; +0,119] | 55,6% → 63,0% (54 patches) |

**Decisão, conforme registrado: o rastro NÃO vence o duelo** (Δ < 0,03 e o intervalo inclui zero).

**Descritivo (não é teste):** a direção é a esperada nas duas análises. A pista mais forte é **M**: trechos **não citados no resumo final** são pontos de decisão em **20,8%** dos casos, contra **8,8%** dos citados (2,4×; coeficiente −0,32, e −0,71 no subconjunto nomeado). Para Pl: 15,3% × 9,6%. Para U: 14,7% × 10,2%.

**Interpretação:** o efeito, se existe, é pequeno demais para ser confirmado com 97 tarefas — o intervalo é largo (±0,036). Os dados não permitem dizer que o rastro ajuda, nem que não ajuda. A hipótese mais promissora para um teste confirmatório é uma só: **"trecho silencioso" (não citado no resumo) → ponto de decisão**, a testar em dados novos, com registro prévio e uma única hipótese.

---

# Teste confirmatório: o "trecho silencioso"

**Registrado em 17/10/2026, ANTES de calcular a pista ou a régua em qualquer dado novo.** Desenho aprovado pelo autor ("quanto mais estruturado, melhor"). Antes deste registro, olhamos **só a viabilidade**: formato, número de tentativas por tarefa, presença de resumo final e tamanho dos patches.

## Hipótese única (H1)

> Num patch de agente, um trecho de código **não citado no resumo final** do agente tem **mais chance de ser um ponto de decisão** (uma escolha que a maioria das outras tentativas da mesma tarefa não fez) do que um trecho citado — mesmo levando em conta as características do código e do pedido.

Origem: observação exploratória do piloto 3 (Claude Code: 20,8% × 8,8%). Aqueles dados **não** são reusados aqui.

## Dados

- **C1 — principal (decide):** `nebius/SWE-rebench-openhands-trajectories` (OpenHands v0.54 + Qwen3-Coder-480B, 2025). Outro agente, outro modelo e **outras tarefas** (6.306 tarefas reais de GitHub, mediana de 10 tentativas por tarefa). O patch final vem pronto (`model_patch`).
  - Sessões usadas: as que terminaram normalmente (`exit_status = submit`).
  - Resumo final = a mensagem da ferramenta `finish`. Sessões sem ela ficam fora.
- **C2 — replicação suplementar (não decide):** Cursor, no dataset de julho de 2026. Só as sessões em que todas as edições têm o arquivo completo depois da edição sem corte (187 de 555 na checagem de viabilidade). A amostra é **pequena e enviesada para arquivos pequenos**. Reconstrução como no piloto 3, gravando o arquivo completo de cada edição; resumo = `final_message`.

## Definições (as mesmas do piloto 3)

- **Trechos:** hunks em arquivos de código que já existiam, excluídos testes (mesmas regras). **Patches elegíveis:** 2+ trechos.
- **Nome do trecho:** o identificador logo antes do primeiro `(` no cabeçalho do hunk. Em C1, o cabeçalho é o que veio no `model_patch` (detector padrão do git), o que pode diferir do piloto 3.
- **M = 1** se o nome do trecho (ou, sem nome, o nome do arquivo sem extensão) aparece no resumo final.
- **Unidade:** (arquivo, nome). **Y = 1 (ponto de decisão)** se no máximo 25% das **outras** tentativas da mesma tarefa (sessões válidas, com patch) mexeram na mesma unidade. Tarefas com menos de 3 outras tentativas válidas ficam fora.
- **Características do código + pedido (controles):** as 12 do duelo (11 anteriores + "tem nome").

## Análise principal (C1)

- Regressão logística: **Y ~ M + 12 controles** (controles padronizados), com **erros-padrão agrupados por tarefa**.
- **H1 confirmada se as duas condições valerem:**
  1. **Significância:** o coeficiente de M é negativo com p unilateral < 0,05 (o limite superior do intervalo de 90% da razão de chances fica abaixo de 1);
  2. **Relevância:** a razão de chances estimada para M é **≤ 0,80**, ou seja, ser citado reduz em pelo menos 20% a chance de ser ponto de decisão. Isso evita "confirmar" um efeito minúsculo só porque há muitos dados.
- **Refutada** se o coeficiente for ≥ 0 ou não significativo. **Inconclusiva** se for significativo, mas com razão de chances > 0,80.

## Análises secundárias (reportadas, não decidem)

- S1: duelo AUC (a) só controles × (a) + M, com Δ e intervalo de 95% por bootstrap de tarefas.
- S2: fração de patches em que o 1º trecho da ordenação é ponto de decisão, (a) × (a + M).
- S3: H1 só nos patches com todos os trechos nomeados.
- S4: H1 em C2 (Cursor), mesmo modelo; reportamos a razão de chances e o intervalo.
- S5: separação por tarefa resolvida × não resolvida (descritivo).

## Decisão

- **Confirmada:** o "trecho silencioso" vira o resultado central do artigo (RQ2/RQ3), com a evidência exploratória (Claude Code) mais a confirmatória (OpenHands).
- **Refutada ou inconclusiva:** registramos e o artigo relata os pilotos como resultado negativo/misto, de forma honesta.

## Resultado do teste confirmatório (17/10/2026)

Scripts: `scripts/confirmatorio_silencioso.py` (C1), `scripts/confirmatorio_cursor.py` (C2) · saídas: `dados/confirmatorio_c1_trechos.csv`, `dados/confirmatorio_c2_trechos.csv`. Antes da análise, só a mecânica foi conferida em 20 sessões (extração do pedido, do resumo e dos trechos), sem calcular M nem Y.

### C1 — principal (OpenHands + Qwen3-Coder)

67.074 sessões; 60.697 válidas; **elegíveis: 83.010 trechos, 25.838 patches, 4.119 tarefas**. Y = 1 em 11,4%; M = 1 em 69,9%.

| | Não citado no resumo (M = 0) | Citado (M = 1) | Razão de chances ajustada (IC 95%) | p unilateral |
|---|---|---|---|---|
| **Principal** | **18,9%** são pontos de decisão | **8,2%** | **0,634 [0,556; 0,723]** | 5 × 10⁻¹² |
| S3: só patches com todos os trechos nomeados | 11,5% | 6,4% | 0,737 [0,628; 0,864] | 8 × 10⁻⁵ |
| S5: tarefas resolvidas | 16,1% | 6,7% | — | — |
| S5: tarefas não resolvidas | 20,9% | 9,4% | — | — |

**Decisão, conforme registrado: H1 CONFIRMADA** (significativa, com razão de chances 0,634 ≤ 0,80): ser citado no resumo reduz em cerca de 37% a chance de o trecho ser um ponto de decisão, mesmo controlando pelo código e pelo pedido.

**Secundárias de ordenação (S1, S2):** AUC só controles 0,716 → com M 0,718 (Δ +0,002, IC 95% [−0,001; +0,006]); 1º lugar é ponto de decisão: 61,3% → 62,5% (4.434 patches). **Ou seja: a associação é robusta, mas, como ingrediente de ordenação, M acrescenta muito pouco ao que o código já dá neste dataset.**

### C2 — suplementar (Cursor)

187 de 555 sessões reconstruídas sem corte; 178 válidas; elegíveis: 643 trechos, 151 patches, **33 tarefas**. Mesma direção e efeito maior: **18,1% × 4,2%**; razão de chances 0,364, IC 95% [0,099; 1,346], p unilateral = 0,065. **Não significativa**: com 33 tarefas, a amostra não tem poder para confirmar nem refutar. (O critério registrado chamaria isso de "refutada" — a classificação é reportada, mas a leitura correta é "mesma direção, sem significância em amostra pequena".)

### Desvio de implementação (registrado por transparência)

O modelo registrado tinha 12 controles, mas **"tamanho" é exatamente linhas adicionadas + linhas removidas**, o que deixa a matriz com uma coluna redundante (posto 11 de 12). Em C1 o ajuste contornou isso sozinho; em C2 (amostra pequena) o cálculo falhou (razão de chances 0, sem intervalo). A correção foi retirar "tamanho" — o espaço de colunas é o mesmo, e **o resultado de C1 é idêntico** (0,634 [0,556; 0,723]) com e sem a coluna. O script também passou a marcar "não estimável" em vez de "refutada" quando o modelo não converge.

**Segundo desvio (achado em 20/10/2026):** o controle "posição relativa" dividia a posição do trecho entre **todos** os hunks do patch (incluindo testes e arquivos novos) pelo número de trechos de **código**, por isso passava de 1 em 30,4% dos trechos. Com a conta certa (ordem entre os trechos de código, de 0 a 1), o resultado de C1 **não muda**: razão de chances 0,634 [0,556; 0,722], p unilateral = 4 × 10⁻¹². O script do confirmatório foi corrigido. Os scripts dos pilotos 1 a 3 têm a mesma conta e foram mantidos como estavam, para reproduzir os números registrados; nesses pilotos ela só afeta os controles (P2 e o duelo), não a variação das pistas (P1).

### Leitura

1. **Confirmado em dados novos, com outro agente, outro modelo e outras tarefas:** trechos que o agente **não menciona no resumo final** são escolhas próprias (que a maioria das outras tentativas não fez) **2,3 vezes mais** (18,9% × 8,2%). Vale em tarefas resolvidas e não resolvidas, e no subconjunto sem artefato de nome. O piloto 3 (Claude Code: 20,8% × 8,8%) e o Cursor (18,1% × 4,2%) mostram o mesmo padrão.
2. **Limite importante:** como fator de ordenação, somado às características do código, o ganho é pequeno (Δ AUC +0,002). O valor prático mais claro é como **sinal explicável** para o revisor ("o agente não te contou sobre este trecho"), não como um ganho grande de ranking.
3. **Limitações:** a régua "ponto de decisão" é uma aproximação (discordância entre tentativas), não "precisa de atenção" medido por pessoas; em C1 a unidade costuma ser a classe, não o método (cabeçalho padrão do git).

---

# Validação humana da régua — registro

**Registrado em 20/10/2026, ANTES de sortear a amostra e de qualquer pessoa ver os trechos.**

## Pergunta

A régua automática "ponto de decisão" (no máximo 25% das outras tentativas mexeram na mesma unidade) concorda com o julgamento de uma pessoa sobre **o que foi uma decisão própria do agente**? Secundariamente: os trechos silenciosos são os que uma pessoa mais ia querer que lhe avisassem?

## Amostra

- Origem: trechos elegíveis do C1 (OpenHands + Qwen3-Coder).
- Para a leitura ser viável: trechos com 2 a 40 linhas alteradas, no máximo **um trecho por tarefa**.
- **100 trechos, 25 em cada combinação** de régua (Y = 0/1) × resumo (citado/não citado). Sorteio com semente fixa (20261020) em `scripts/validacao_amostra.py`.
- Ordem de apresentação aleatória.

## O que a pessoa vê e o que não vê

- **Vê:** o pedido da tarefa (texto da issue), o arquivo, o trecho e, se quiser, o resto do patch.
- **Não vê:** o resumo final do agente, as outras tentativas, se a tarefa foi resolvida, o valor da régua e se o trecho foi citado. O gabarito fica num arquivo separado, que só o script de análise abre.

## Perguntas (para cada trecho)

- **P1 (decide):** "Esse trecho é uma decisão própria do agente, algo que o pedido não deixava óbvio?" (Sim / Não / Não sei)
- **P2 (secundária):** "Se você fosse revisar esse patch, ia querer ser avisado sobre esse trecho?" (Sim / Não / Não sei)
- Comentário opcional.

## Análise e critério (fixados agora)

"Não sei" sai da conta de cada pergunta, e a quantidade é reportada.

- **V1 — principal:** proporção de P1 = Sim entre os trechos com Y = 1, comparada com Y = 0.
  - **Régua validada:** diferença de **pelo menos 20 pontos percentuais**, com teste exato de Fisher unilateral p < 0,05.
  - **Validação fraca:** significativa, mas com diferença menor que 20 pontos.
  - **Não validada:** não significativa ou na direção oposta.
  - Também é reportado o kappa de Cohen entre P1 e Y.
- **V2 — secundária (não decide):** proporção de P2 = Sim nos trechos não citados × citados (Fisher unilateral), e o mesmo para P1.
- Se mais de 20% das respostas de P1 forem "Não sei", o resultado é marcado como frágil.

## Decisão

- **Validada:** o artigo apresenta a régua como medida apoiada por julgamento humano.
- **Fraca ou não validada:** o artigo descreve a régua como "discordância entre tentativas", sem chamá-la de decisão, e relata a validação como limite.

## Limites conhecidos

- **Um único avaliador**, o autor, que conhece a hipótese. O cegamento (sem régua, sem resumo, ordem aleatória) reduz o viés, mas não o elimina. Se houver um segundo avaliador, ele responde os 30 primeiros trechos da mesma ordem, e reportamos a concordância entre os dois.
- O avaliador julga a partir do pedido; um mantenedor do projeto poderia julgar diferente.

## Andamento (20/10/2026): validação humana não realizada

- **Por falta de tempo, a validação humana não foi feita.** Foram preenchidos 35 dos 100 trechos (V001–V035), mas **por um modelo de IA**, não por uma pessoa. O autor só olhou por cima. Isso não atende ao protocolo e **não é reportado como validação humana**.
- Por transparência, eis o que a avaliação por IA deu (é evidência fraca: um único modelo, e não dá para garantir que ele não teve acesso ao gabarito, que estava na mesma pasta):
  - P1 "decisão própria": régua Y = 1 em 65% (11/17) × Y = 0 em 56% (10/18), Fisher p = 0,42, kappa 0,09.
  - P2 "ia querer ser avisado": não citado em 79% (11/14) × citado em 48% (10/21), p = 0,07.
  - Em todos os 35 trechos, P1 e P2 tiveram a mesma resposta.
- **Decisão, conforme a regra registrada para "não validada":** no artigo, a régua é descrita como **"discordância entre tentativas"**, e não como "decisão" medida por pessoas. A validação humana fica como limitação declarada e próximo passo.
- **Para uma validação futura:** o autor viu as respostas da IA em V001–V035, então esses trechos não servem mais para ele avaliar às cegas. Um avaliador novo (por exemplo, o orientador ou um colega) pode usar a página inteira; o autor, só V036–V100.
