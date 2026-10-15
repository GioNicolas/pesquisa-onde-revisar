# Estado e limitações — Onde Revisar Primeiro

Atualizado em 15/10/2026 para a apresentação pública do repositório.

## Pergunta e material disponível

A pesquisa investiga se sinais dos logs de execução de agentes ajudam a ordenar trechos de um diff para revisão humana. Há scripts de extração, dados tabulares, métricas exploratórias, figuras e protótipos de inspeção. O experimento registrado usa 1.000 trajetórias e 1.536 hunks.

O código e os resultados são artefatos de um estudo inicial. Ainda não há demonstração de melhoria na detecção de bugs confirmados por revisão independente, nem estudo de tempo economizado por revisores humanos.

## O que os resultados atuais medem

O extrator usa sobreposição com regiões de um patch humano de referência, com tolerância de 15 linhas. O alvo `is_spurious` indica falta desse alinhamento. Os modelos da tabela publicada foram avaliados contra esse alvo automático.

Esse proxy pode reprovar soluções alternativas corretas e aceitar alterações erradas próximas à solução humana. Casos sem patch de referência também recebem o alvo negativo de alinhamento na implementação atual e precisam de auditoria de cobertura antes de novas conclusões.

Os sinais são associados ao arquivo e à trajetória e replicados nos hunks correspondentes; sua resolução não é necessariamente a região exata de cada hunk. O agrupamento por instância na validação evita misturar a mesma instância entre treino e validação, mas não demonstra transferência entre repositórios ou agentes.

As curvas e Recall@K são calculados num ranking agregado de hunks. O esforço corresponde à quantidade de hunks, sem ponderação pelo tamanho em linhas ou por tempo. Melhorar essa métrica não demonstra automaticamente melhor priorização dos trechos dentro de cada patch.

## Revisão dos rótulos

A [definição de hunk errado](definicao-hunk-errado.md) passou a distinguir correção de simples alinhamento: a análise considera comportamento, evidências de testes, ressalvas e confiança. Existe rotulagem manual em andamento, ainda não integrada aos números exploratórios.

Avaliações por modelos de IA não equivalem a validação humana independente. Pacotes de auditoria em elaboração, respostas e chaves locais não integram esta publicação inicial. O planejamento e o diário documentam a evolução das hipóteses e podem conter interpretações posteriormente revistas.

## Interpretação dos materiais históricos

Afirmações de que a hipótese estaria definitivamente validada, de que todos os itens não alinhados seriam alucinações ou de que as métricas provariam qualidade científica não são sustentadas pelo experimento inicial. O diário, os PDFs e os painéis preservam o histórico de desenvolvimento; o README e este documento explicitam os limites atuais.

Não foram produzidos novos resultados nem reexecutado o pipeline para preparar a apresentação pública. Os números publicados são os registrados no CSV original.

## Próximas verificações

- Auditar a disponibilidade e o alinhamento das referências humanas.
- Consolidar rótulos de correção com confiança e atribuição cuidadosa das falhas de teste.
- Avaliar patches que misturem hunks corretos e incorretos, incluindo priorização dentro do patch.
- Comparar com heurísticas simples e medir incerteza, custo de revisão e generalização.
- Atualizar modelos, figuras e protótipos somente após essa validação.
