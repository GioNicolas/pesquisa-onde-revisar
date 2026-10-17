"""
Dia 5 do piloto 3: duelo "só código + pedido" × "código + pedido + rastro"
(ver docs/piloto-premissas.md, registrado antes da análise).

Régua: Y = 1 (ponto de decisão) se no máximo 25% das outras tentativas reconstruídas
da mesma tarefa mexeram na mesma unidade (arquivo + nome do trecho).

Uso: python scripts/piloto3_duelo.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parent.parent
TRECHOS = RAIZ / "dados" / "piloto3_trechos.csv"
SESSOES = RAIZ / "dados" / "piloto3_sessoes.csv"
SAIDA = RAIZ / "dados" / "piloto3_duelo.csv"

COLS_A = ["linhas_add", "linhas_rem", "tamanho", "posicao", "posicao_rel", "hunks_no_arquivo",
          "arquivos_no_patch", "primeiro_do_arquivo", "ultimo_do_arquivo",
          "nome_no_pedido", "arquivo_no_pedido", "tem_nome"]
COLS_B = COLS_A + ["U", "Pl", "M"]


def unidade(df):
    return df.arquivo + "::" + df.nome.fillna("")


def rotula(trechos, sessoes):
    """Y por trecho, a partir das unidades tocadas nas outras tentativas da mesma tarefa."""
    ok = sessoes[sessoes.status == "ok"]
    tocadas = trechos.assign(u=unidade(trechos)).groupby("patch_id").u.apply(set).to_dict()
    tentativas = ok.groupby("instance_id").patch_id.apply(list).to_dict()
    y, n_outras = [], []
    for pid, iid, u in zip(trechos.patch_id, trechos.instance_id, unidade(trechos)):
        outras = [p for p in tentativas.get(iid, []) if p != pid]
        n_outras.append(len(outras))
        frac = np.mean([u in tocadas.get(p, set()) for p in outras]) if outras else np.nan
        y.append(np.nan if len(outras) < 3 else int(frac <= 0.25))
    return np.array(y), np.array(n_outras)


def previsoes(df, cols):
    X, y, g = df[cols].values, df.Y.values, df.instance_id.values
    modelo = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    prob = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, g):
        modelo.fit(X[tr], y[tr])
        prob[te] = modelo.predict_proba(X[te])[:, 1]
    return prob


def bootstrap_delta(df, pa, pb, n=1000, semente=0):
    rng = np.random.default_rng(semente)
    tarefas = df.instance_id.unique()
    idx = {t: np.where(df.instance_id.values == t)[0] for t in tarefas}
    y = df.Y.values
    deltas = []
    for _ in range(n):
        amostra = np.concatenate([idx[t] for t in rng.choice(tarefas, len(tarefas), replace=True)])
        if len(set(y[amostra])) < 2:
            continue
        deltas.append(roc_auc_score(y[amostra], pb[amostra]) - roc_auc_score(y[amostra], pa[amostra]))
    return np.percentile(deltas, [2.5, 97.5])


def acerto_top1(df, prob):
    d = df.assign(p=prob)
    acertos = []
    for _, g in d.groupby("patch_id"):
        if g.Y.nunique() < 2:
            continue
        acertos.append(int(g.loc[g.p.idxmax(), "Y"] == 1))
    return np.mean(acertos), len(acertos)


def duelo(df, titulo):
    pa, pb = previsoes(df, COLS_A), previsoes(df, COLS_B)
    auc_a, auc_b = roc_auc_score(df.Y, pa), roc_auc_score(df.Y, pb)
    lo, hi = bootstrap_delta(df, pa, pb)
    t1a, n1 = acerto_top1(df, pa)
    t1b, _ = acerto_top1(df, pb)
    vence = (auc_b - auc_a >= 0.03) and lo > 0
    print(f"\n=== {titulo}: {df.patch_id.nunique()} patches, {df.instance_id.nunique()} tarefas, {len(df)} trechos | Y=1 em {df.Y.mean():.1%} ===")
    print(f"  (a) só código + pedido:          AUC {auc_a:.3f}")
    print(f"  (b) código + pedido + rastro:    AUC {auc_b:.3f}")
    print(f"  Δ = {auc_b - auc_a:+.3f}  | IC 95% bootstrap por tarefa [{lo:+.3f}, {hi:+.3f}]  -> {'RASTRO VENCE' if vence else 'rastro NÃO vence'}")
    print(f"  [secundário] 1º lugar é ponto de decisão: (a) {t1a:.1%}  (b) {t1b:.1%}  em {n1} patches com Y misto")
    modelo = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(df[COLS_B].values, df.Y.values)
    coefs = dict(zip(COLS_B, modelo[-1].coef_[0]))
    print("  [descritivo] coeficientes padronizados: " + ", ".join(f"{k}={coefs[k]:+.2f}" for k in ["U", "Pl", "M"]))
    print("  [descritivo] taxa de Y=1 com pista 0 × 1: "
          + ", ".join(f"{s}: {df[df[s] == 0].Y.mean():.1%} × {df[df[s] == 1].Y.mean():.1%}" for s in ["U", "Pl", "M"]))
    return vence


def main():
    trechos = pd.read_csv(TRECHOS)
    sessoes = pd.read_csv(SESSOES)
    trechos["Y"], trechos["n_outras"] = rotula(trechos, sessoes)
    trechos["tem_nome"] = trechos.nome.notna().astype(int)
    m = trechos[trechos.mapeado]
    elegiveis = m.groupby("patch_id").filter(lambda g: len(g) >= 2)
    df = elegiveis.dropna(subset=["Y"]).copy()
    df["Y"] = df.Y.astype(int)
    df.to_csv(SAIDA, index=False)
    print(f"Trechos elegíveis: {len(elegiveis)}  | com régua (3+ outras tentativas): {len(df)}")
    if df.Y.mean() < 0.05 or df.Y.mean() > 0.95:
        print("AVISO: prevalência extrema de Y; duelo pouco informativo")
    vence = duelo(df, "PRINCIPAL")
    nomeados = df.groupby("patch_id").filter(lambda g: g.tem_nome.all())
    duelo(nomeados, "SECUNDÁRIO (só patches com todos os trechos nomeados)")
    print(f"\nDecisão: {'o rastro vence o duelo' if vence else 'o rastro não vence o duelo'}")


if __name__ == "__main__":
    main()
