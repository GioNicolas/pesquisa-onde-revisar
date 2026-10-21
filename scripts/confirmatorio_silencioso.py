"""
Teste confirmatório do "trecho silencioso" (ver docs/piloto-premissas.md, registrado antes).

H1: trecho não citado no resumo final (M = 0) tem mais chance de ser ponto de decisão (Y = 1),
controlando pelas características do código + pedido.

C1 (principal): nebius/SWE-rebench-openhands-trajectories (OpenHands + Qwen3-Coder).
C2 (suplementar): Cursor no SWE-rebench de julho de 2026 -> scripts/confirmatorio_cursor.py

Uso: python scripts/confirmatorio_silencioso.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import statsmodels.api as sm
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from piloto3_moderno import EXT_CODIGO, RE_TESTE, nome_do_trecho  # noqa: E402
from piloto_premissas import trechos_do_patch  # noqa: E402
import piloto3_duelo as duelo_mod  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "confirmatorio_c1_trechos.csv"
CONTROLES = ["linhas_add", "linhas_rem", "tamanho", "posicao", "posicao_rel", "hunks_no_arquivo",
             "arquivos_no_patch", "primeiro_do_arquivo", "ultimo_do_arquivo",
             "nome_no_pedido", "arquivo_no_pedido", "tem_nome"]
RE_PEDIDO = re.compile(r"<issue_description>(.*?)</issue_description>", re.S)


def resumo_e_pedido(trajetoria):
    resumo, pedido = None, ""
    for m in trajetoria:
        if m["role"] == "user" and not pedido:
            c = m.get("content") or ""
            achado = RE_PEDIDO.search(c)
            pedido = achado.group(1) if achado else c
        for tc in (m.get("tool_calls") or []):
            if tc["function"]["name"] == "finish":
                try:
                    resumo = json.loads(tc["function"]["arguments"]).get("message", "")
                except (json.JSONDecodeError, AttributeError):
                    resumo = tc["function"]["arguments"]
    return resumo, pedido


def trechos_de_codigo(patch):
    return [t for t in trechos_do_patch(patch or "")
            if not (t["old_start"] == 0 and t["old_count"] == 0)
            and Path(t["arquivo"]).suffix in EXT_CODIGO and not RE_TESTE.search(t["arquivo"])]


def linhas_da_sessao(pid, iid, trechos, resumo, pedido):
    n_arquivos = len({t["arquivo"] for t in trechos})
    saida = []
    for k, t in enumerate(trechos):
        nome = nome_do_trecho(t["contexto"], t["arquivo"])
        nomes = [nome] if nome else [Path(t["arquivo"]).stem]
        base_arq = Path(t["arquivo"]).name
        saida.append({
            "patch_id": pid, "instance_id": iid, "arquivo": t["arquivo"], "nome": nome,
            # posicao conta todos os hunks do patch; posicao_rel usa só os trechos de código (0 a 1)
            "posicao": t["posicao"], "posicao_rel": k / max(1, len(trechos) - 1),
            "linhas_add": len(t["adicionadas"]), "linhas_rem": len(t["removidas"]),
            "tamanho": len(t["adicionadas"]) + len(t["removidas"]),
            "hunks_no_arquivo": t["hunks_no_arquivo"], "arquivos_no_patch": n_arquivos,
            "primeiro_do_arquivo": int(t["idx_no_arquivo"] == 0),
            "ultimo_do_arquivo": int(t["idx_no_arquivo"] == t["hunks_no_arquivo"] - 1),
            "nome_no_pedido": int(bool(nome) and nome in pedido),
            "arquivo_no_pedido": int(base_arq in pedido or t["arquivo"] in pedido),
            "tem_nome": int(bool(nome)), "n_trechos_patch": len(trechos),
            "tem_resumo": resumo is not None,
            "M": int(resumo is not None and any(n in resumo for n in nomes)),
        })
    return saida


def rotula(df, validas):
    """Y por trecho: no máximo 25% das outras tentativas válidas mexeram na mesma unidade."""
    u = df.arquivo + "::" + df.nome.fillna("")
    tocadas = df.assign(u=u).groupby("patch_id").u.apply(set).to_dict()
    tentativas = validas.groupby("instance_id").patch_id.apply(list).to_dict()
    y = []
    for pid, iid, un in zip(df.patch_id, df.instance_id, u):
        outras = [p for p in tentativas.get(iid, []) if p != pid]
        y.append(np.nan if len(outras) < 3 else int(np.mean([un in tocadas.get(p, set()) for p in outras]) <= 0.25))
    return np.array(y)


def teste_h1(df, titulo):
    """Regressão logística Y ~ M + controles padronizados, erros agrupados por tarefa."""
    # "tamanho" = linhas_add + linhas_rem exatamente: fica fora para a matriz ter posto completo
    # (mesmo espaço de colunas; em C1 o resultado é idêntico). Ver docs/piloto-premissas.md.
    X = df[[k for k in CONTROLES if k != "tamanho"]].astype(float)
    X = X.loc[:, X.std(ddof=0) > 0]  # controles constantes no subconjunto (ex.: tem_nome em S3) saem
    X = (X - X.mean()) / X.std(ddof=0)
    X.insert(0, "M", df.M.astype(float))
    X = sm.add_constant(X)
    grupos = pd.factorize(df.instance_id)[0]
    fit = sm.GLM(df.Y.astype(float), X, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": grupos})
    b, ep = fit.params["M"], fit.bse["M"]
    from scipy.stats import norm
    p_uni = norm.cdf(b / ep)  # H1: b < 0
    oc, lo90, hi90 = np.exp(b), np.exp(b - 1.645 * ep), np.exp(b + 1.645 * ep)
    lo95, hi95 = np.exp(b - 1.96 * ep), np.exp(b + 1.96 * ep)
    taxa0, taxa1 = df[df.M == 0].Y.mean(), df[df.M == 1].Y.mean()
    if not np.isfinite(ep) or not np.isfinite(b):
        veredito = "NÃO ESTIMÁVEL"
    elif b < 0 and p_uni < 0.05:
        veredito = "CONFIRMADA" if oc <= 0.80 else "INCONCLUSIVA (significativa, mas razão de chances > 0,80)"
    else:
        veredito = "REFUTADA (não significativa ou na direção oposta)"
    print(f"\n=== {titulo}: {df.patch_id.nunique()} patches, {df.instance_id.nunique()} tarefas, {len(df)} trechos"
          f" | Y=1 em {df.Y.mean():.1%} | M=1 em {df.M.mean():.1%} ===")
    print(f"  Ponto de decisão: não citado (M=0) {taxa0:.1%}  × citado (M=1) {taxa1:.1%}")
    print(f"  Razão de chances de M (ajustada): {oc:.3f}  IC90% [{lo90:.3f}; {hi90:.3f}]  IC95% [{lo95:.3f}; {hi95:.3f}]  p unilateral = {p_uni:.2g}")
    print(f"  H1: {veredito}")
    return veredito


def secundarias_duelo(df, titulo):
    duelo_mod.COLS_A = CONTROLES
    duelo_mod.COLS_B = CONTROLES + ["M"]
    pa, pb = duelo_mod.previsoes(df, duelo_mod.COLS_A), duelo_mod.previsoes(df, duelo_mod.COLS_B)
    from sklearn.metrics import roc_auc_score
    lo, hi = duelo_mod.bootstrap_delta(df, pa, pb)
    t1a, n1 = duelo_mod.acerto_top1(df, pa)
    t1b, _ = duelo_mod.acerto_top1(df, pb)
    print(f"  [S1] AUC só controles {roc_auc_score(df.Y, pa):.3f} -> + M {roc_auc_score(df.Y, pb):.3f}"
          f"  Δ {roc_auc_score(df.Y, pb) - roc_auc_score(df.Y, pa):+.3f}  IC95% [{lo:+.3f}; {hi:+.3f}]  ({titulo})")
    print(f"  [S2] 1º lugar é ponto de decisão: {t1a:.1%} -> {t1b:.1%} em {n1} patches com Y misto")


def main():
    arq = hf_hub_download("nebius/SWE-rebench-openhands-trajectories", "trajectories.parquet", repo_type="dataset")
    pf = pq.ParquetFile(arq)
    linhas, sessoes = [], []
    lidas = 0
    for lote in pf.iter_batches(batch_size=300, columns=["trajectory_id", "instance_id", "trajectory",
                                                            "model_patch", "exit_status", "resolved"]):
        for r in lote.to_pylist():
            lidas += 1
            valida = r["exit_status"] == "submit" and bool((r["model_patch"] or "").strip())
            sessoes.append({"patch_id": r["trajectory_id"], "instance_id": r["instance_id"],
                            "valida": valida, "resolved": r["resolved"]})
            if not valida:
                continue
            trechos = trechos_de_codigo(r["model_patch"])
            if not trechos:
                continue
            resumo, pedido = resumo_e_pedido(r["trajectory"])
            for l in linhas_da_sessao(r["trajectory_id"], r["instance_id"], trechos, resumo, pedido):
                l["resolved"] = r["resolved"]
                linhas.append(l)
        if lidas % 6000 < 300:
            print(f"   {lidas} sessões lidas", flush=True)
    sessoes = pd.DataFrame(sessoes)
    df = pd.DataFrame(linhas)
    validas = sessoes[sessoes.valida]
    df["Y"] = rotula(df, validas)
    df.to_csv(SAIDA, index=False)
    print(f"\nSessões: {len(sessoes)} | válidas (submit + patch): {len(validas)} | trechos de código: {len(df)}")
    analisa(df)


def analisa(df):
    eleg = df[df.tem_resumo & (df.n_trechos_patch >= 2)].dropna(subset=["Y"]).copy()
    eleg["Y"] = eleg.Y.astype(int)
    print(f"Elegíveis (patch com 2+ trechos, com resumo, tarefa com 3+ outras tentativas): {len(eleg)} trechos")
    veredito = teste_h1(eleg, "C1 PRINCIPAL — OpenHands + Qwen3-Coder")
    secundarias_duelo(eleg, "C1")
    nomeados = eleg.groupby("patch_id").filter(lambda g: g.tem_nome.all())
    teste_h1(nomeados, "[S3] C1 só patches com todos os trechos nomeados")
    for res in (1, 0):
        sub = eleg[eleg.resolved == res]
        print(f"  [S5] resolved={res}: não citado {sub[sub.M == 0].Y.mean():.1%} × citado {sub[sub.M == 1].Y.mean():.1%} ({len(sub)} trechos)")
    print(f"\nDecisão (C1): H1 {veredito}")


if __name__ == "__main__":
    if "--do-csv" in sys.argv:
        analisa(pd.read_csv(SAIDA))
    else:
        main()
