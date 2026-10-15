# Definição de "hunk errado" — rascunho

Versão 0.1 · iniciada em 09/10/2026 · cresce a cada caso rotulado

## Para que serve

Antes de tentar prever hunks errados a partir do rastro do agente, é preciso saber o que conta como "hunk errado". Este documento registra essa definição e cada decisão tomada durante a rotulagem manual.

**Regra básica:** o rótulo vem do **código** (leitura humana + resultado dos testes), nunca do rastro do agente. O rastro é o que vamos usar para *prever* o rótulo; se o rótulo viesse dele, a conta seria circular.

## Rótulos

| Rótulo | Quando usar |
|---|---|
| `errado_regressao` | O hunk quebra algo que funcionava antes: código (testes que passavam começam a falhar) ou um teste existente (o teste deixa de verificar o que verificava). |
| `errado_nao_resolve` | O hunk não faz o que a tarefa pedia. Inclui o hunk que está no lugar da correção e "parece" corrigir, mas não muda o comportamento. |
| `certo_com_ressalva` | O comportamento está certo, mas há algo que um revisor pediria para mudar (código morto, sujeira, duplicação). |
| `certo` | Faz o que devia, sem quebrar nada e sem nada a corrigir. |

Um hunk pode ter mais de um rótulo de erro (ex.: regressão e não resolve ao mesmo tempo).

## Evidência

- **Leitura:** analisar o hunk junto com a tarefa e o código ao redor.
- **Testes:** resultado em `eval_logs` (FAIL_TO_PASS = testes que a correção deve consertar; PASS_TO_PASS = testes que já passavam e devem continuar passando).
- Rótulo **forte** = leitura e testes concordam. Se discordarem, anotar a dúvida.

## Decisões tomadas

1. **Código morto conta como `certo_com_ressalva`, não como `certo`.** (09/10, caso 1, tentativa A)
   Motivo: o comportamento está certo, mas o código tem uma linha que nunca executa e que um revisor pediria para apagar.
   Atenção: o critério **não** é "ficou diferente do Gold Patch". Uma solução diferente da humana pode estar 100% certa. O critério é "um revisor pediria mudança?".
2. **Hunk sem efeito no lugar da correção é `errado_nao_resolve`.** (09/10, caso 2, tentativa C, hunk 1)
   Motivo: não estraga nada, mas finge corrigir. Para o revisor, é perigoso justamente porque parece certo.
3. **Hunks de teste também são rotulados.** Estragar um teste existente é `errado_regressao`. (09/10, caso 2, tentativa C, hunk 2)
   Motivo: um teste estragado esconde bugs no futuro, e o revisor precisa pegar isso.
4. **Rotular o efeito, não a intenção.** (09/10, caso 2)
   Motivo: não dá para saber o que o agente "quis" fazer; dá para ver o que o hunk faz.
5. **Rotular antes de olhar o rastro (cegamento).** (09/10)
   Motivo: saber que o agente se perdeu influencia o julgamento sobre o código.
6. **Saída indevida é regressão, mesmo com os testes passando.** (10/10, caso 7)
   Motivo: um `print` de depuração muda o que o usuário vê no uso normal; os testes só não verificam isso.
7. **Atribuir falha de teste ao hunk só quando ele pode tê-la causado.** (10/10, casos 5, 15 e 16)
   Motivo: os testes rodam no patch inteiro. Comentários não causam `ValueError` (caso 15); as datas erradas vêm de outro hunk (caso 5). Teste sem relação com a tarefa (o de CSS no caso 16) é ignorado.
8. **Avaliar o comportamento pedido antes de reprovar por diferença de assinatura ou nome.** (10/10, casos 11 e 12)
   Motivo: alguns testes cobram o "jeito" da solução humana (nome de método, parâmetro novo). Nome incompatível e funcionalidade ausente são registrados separadamente.
9. **Teste que não carrega ou não roda não impede rótulo pela leitura.** (10/10, casos 13 e 14)
   Motivo: quando o código sustenta a conclusão sozinho, o rótulo vale, com a confiança registrada.
10. **Registrar a confiança (alta, média, baixa) em todo rótulo.** (10/10)
    Motivo: casos sem teste ou com atribuição difícil precisam ser distinguidos dos casos sólidos.

## Decisões pendentes

- **Criar o rótulo `fora_do_escopo`?** (proposta do caso 6) Para a mudança que altera comportamento sem relação com a tarefa (ex.: aceitar 'male'/'female' quando o pedido era aceitar hífen), separando-a da tentativa de correção que não funciona.
- **Caso 10 (ulid):** `from_timestamp` e `from_randomness` também decodificam texto e continuam sem normalização. Se a tarefa exige o padrão em todos os caminhos, o rótulo vira `errado_nao_resolve`.

## Lições dos casos

- **Proximidade com o Gold Patch não é correção.** No caso 1, a tentativa B mexeu na mesma linha da solução humana (regra antiga: "pertinente") e quebrou 3 testes que passavam.
- **"Rodou teste" é diferente de "testou de verdade".** No caso 1, a tentativa A rodou um comando de teste que executou 0 testes e respondeu "OK".
- **O rastro pode "avisar".** No caso 2, o agente viu o mesmo erro antes e depois de editar, entrou em loop (24 buscas iguais) e o patch foi enviado porque o contexto acabou.

## Perguntas em aberto (levar ao orientador)

- Erros por **omissão** (faltou mudar algo em outro lugar) não aparecem em nenhum hunk. Como registrar?
- Hunks de apoio **novos** (`reproduce.py`, scripts de depuração, arquivos gerados): entram na rotulagem ou ficam de fora? (Testes existentes já decidimos: entram.)
- Hunk **inútil fora do lugar da correção** (ex.: mexe num arquivo que nada tem a ver, sem efeito): é `certo_com_ressalva` ou precisa de um rótulo próprio? (ligada à proposta `fora_do_escopo`)
- **Desequilíbrio:** dos 18 hunks rotulados, só 1 é `certo` e 3 são `certo_com_ressalva`; quase todos vêm de tarefas que o agente não resolveu. Como amostrar mais hunks certos?
- **Nível do sinal:** pistas como "o contexto acabou" valem para a trajetória inteira e não distinguem hunks do mesmo patch. Para a pergunta da pesquisa (qual hunk revisar primeiro), precisamos de patches com hunks certos **e** errados misturados.
