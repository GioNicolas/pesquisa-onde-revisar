"""
Análise da validação humana da régua, com os critérios registrados em docs/piloto-premissas.md.

Uso: python scripts/validacao_analisa.py [respostas_validacao.csv]
     (padrão: pasta Downloads do usuário)
"""

import sys
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact
from sklearn.metrics import cohen_kappa_score

RAIZ = Path(__file__).resolve().parent.parent
GABARITO = RAIZ / "resultados" / "validacao" / "gabarito_NAO_ABRIR.csv"


def compara(df, pergunta, grupo, alto, baixo, titulo):
    """Proporção de 'sim' em grupo == alto contra grupo == baixo (Fisher unilateral)."""
    sub = df[df[pergunta].isin(["sim", "nao"])]
    a, b = sub[sub[grupo] == alto], sub[sub[grupo] == baixo]
    ta, tb = (a[pergunta] == "sim").mean(), (b[pergunta] == "sim").mean()
    tabela = [[(a[pergunta] == "sim").sum(), (a[pergunta] == "nao").sum()],
              [(b[pergunta] == "sim").sum(), (b[pergunta] == "nao").sum()]]
    _, p = fisher_exact(tabela, alternative="greater")
    print(f"  {titulo}: {ta:.0%} ({tabela[0][0]}/{len(a)}) × {tb:.0%} ({tabela[1][0]}/{len(b)})"
          f"  diferença {100 * (ta - tb):+.0f} p.p.  Fisher unilateral p = {p:.3g}")
    return ta - tb, p, sub


def main(caminho):
    gab = pd.read_csv(GABARITO)
    resp = pd.read_csv(caminho, encoding="utf-8-sig", dtype=str).fillna("")
    df = gab.merge(resp, on="id", how="left").fillna({"p1": "", "p2": ""})
    faltam = (df.p1 == "") | (df.p2 == "")
    print(f"Respostas: {len(df) - faltam.sum()} de {len(df)} completas")
    if faltam.any():
        print("  Sem resposta:", ", ".join(df.id[faltam]))
    nao_sei = (df.p1 == "nao_sei").mean()
    print(f"P1 'não sei': {nao_sei:.0%}" + ("  -> FRÁGIL (mais de 20%)" if nao_sei > 0.20 else ""))

    print("\nV1 (principal): P1 = decisão própria, régua Y = 1 × Y = 0")
    dif, p, sub = compara(df, "p1", "Y", 1, 0, "P1 sim")
    kappa = cohen_kappa_score(sub.Y, (sub.p1 == "sim").astype(int))
    print(f"  kappa de Cohen (P1 × régua): {kappa:.2f}")
    if p < 0.05 and dif >= 0.20:
        veredito = "RÉGUA VALIDADA"
    elif p < 0.05 and dif > 0:
        veredito = "VALIDAÇÃO FRACA (significativa, diferença < 20 p.p.)"
    else:
        veredito = "NÃO VALIDADA"
    print(f"  -> {veredito}")

    print("\nV2 (secundária): não citado no resumo (M = 0) × citado (M = 1)")
    compara(df, "p2", "M", 0, 1, "P2 ia querer ser avisado")
    compara(df, "p1", "M", 0, 1, "P1 decisão própria    ")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "Downloads" / "respostas_validacao.csv")
