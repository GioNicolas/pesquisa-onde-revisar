"""
Piloto 2, dias 1-3: pistas do rastro ligadas ao trecho (ver docs/piloto-premissas.md,
registrado antes da análise).

Usa as trajetórias 1.001-2.000 (nunca analisadas) e o mesmo mapeamento trecho -> edição
do piloto 1. Pistas por trecho:
  T  - o trecho (arquivo + função) apareceu num traceback de comando do agente antes da edição
  U  - o agente buscou (search_dir/search_file/grep/rg) pelo nome do trecho
  Pl - o nome do trecho foi mencionado antes da edição
  D  - a mensagem da edição tem marcadores de escolha/suposição
  M  - o nome do trecho aparece nas 3 últimas ações do agente

Para cada pista: P1 (varia em >= 30% dos patches) e P2 (código + pedido preveem com AUC < 0,70).

Uso: python scripts/piloto2_pistas.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_dataset
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
from piloto_premissas import (MARCADORES_DECISAO, RE_EXECUCAO, RE_NOME, RE_TESTE, edicoes,  # noqa: E402
                              normaliza, passos_do_rastro, trechos_do_patch)

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_CSV = RAIZ / "dados" / "piloto2_trechos.csv"
INICIO, N = 1000, 1000

RE_FRAME = re.compile(r'File "([^"]+)", line \d+, in (\S+)')
RE_BUSCA = re.compile(r"^\s*(search_dir|search_file|grep|rg)\b")
RE_PEDIDO = re.compile(r"ISSUE:\n(.*?)(?:\n\s*INSTRUCTIONS:|$)", re.S)
PISTAS = ["T", "U", "Pl", "D", "M"]
COLS_CODIGO = ["linhas_add", "linhas_rem", "tamanho", "posicao", "posicao_rel", "hunks_no_arquivo",
               "arquivos_no_patch", "primeiro_do_arquivo", "ultimo_do_arquivo",
               "nome_no_pedido", "arquivo_no_pedido"]


def texto_do_pedido(trajetoria):
    passos = json.loads(trajetoria) if isinstance(trajetoria, str) else (trajetoria or [])
    for p in passos:
        if p.get("role") == "user":
            m = RE_PEDIDO.search(str(p.get("text", "")))
            return m.group(1) if m else ""
    return ""


def analisa_trajetoria(item):
    trechos = [t for t in trechos_do_patch(item.get("generated_patch"))
               if not (t["old_start"] == 0 and t["old_count"] == 0) and not RE_TESTE.search(t["arquivo"])]
    if len(trechos) < 2:
        return []
    acoes = passos_do_rastro(item.get("trajectory"))
    eds = edicoes(acoes)
    pedido = texto_do_pedido(item.get("trajectory"))
    # frames de traceback vistos em saídas de comandos de execução, por passo
    frames = [(i, RE_FRAME.findall(a["observacao"])) for i, a in enumerate(acoes)
              if RE_EXECUCAO.search(a["comando"]) and "Traceback" in a["observacao"]]
    buscas = " \n ".join(a["comando"] for a in acoes if RE_BUSCA.search(a["comando"]))
    fim = " ".join(a["pensamento"] for a in acoes[-3:])
    n_arquivos = len({t["arquivo"] for t in trechos})
    linhas = []
    for t in trechos:
        alvo = normaliza(t["adicionadas"])
        candidatas = [e for e in eds if e["arquivo"] == t["arquivo"] and alvo & e["inseridas"]]
        nomes_def = RE_NOME.findall(t["contexto"])
        nome = nomes_def[0] if nomes_def else None
        base = {
            "instance_id": item["instance_id"], "model_name": item.get("model_name"),
            "task_resolved": bool(item.get("target")), "arquivo": t["arquivo"], "nome": nome,
            "posicao": t["posicao"], "posicao_rel": t["posicao"] / max(1, len(trechos) - 1),
            "linhas_add": len(t["adicionadas"]), "linhas_rem": len(t["removidas"]),
            "tamanho": len(t["adicionadas"]) + len(t["removidas"]),
            "hunks_no_arquivo": t["hunks_no_arquivo"], "arquivos_no_patch": n_arquivos,
            "primeiro_do_arquivo": int(t["idx_no_arquivo"] == 0),
            "ultimo_do_arquivo": int(t["idx_no_arquivo"] == t["hunks_no_arquivo"] - 1),
            "nome_no_pedido": int(bool(nome) and nome in pedido),
            "arquivo_no_pedido": int(Path(t["arquivo"]).name in pedido or t["arquivo"] in pedido),
            "n_trechos_patch": len(trechos), "mapeado": bool(candidatas),
        }
        if candidatas:
            ed = max(candidatas, key=lambda e: e["passo"])
            pensamento = acoes[ed["passo"]]["pensamento"].lower()
            nomes = nomes_def or [Path(t["arquivo"]).stem]
            antes = " ".join(a["pensamento"] for a in acoes[:ed["passo"]])
            funcao = nome or "<module>"
            base.update({
                "passo_edicao": ed["passo"], "n_passos": len(acoes),
                "T": int(any(caminho.endswith(t["arquivo"]) and f == funcao
                             for i, fs in frames if i < ed["passo"] for caminho, f in fs)),
                "U": int(bool(nome) and nome in buscas),
                "Pl": int(any(n in antes for n in nomes)),
                "D": int(any(m in pensamento for m in MARCADORES_DECISAO)),
                "M": int(any(n in fim for n in nomes)),
            })
        linhas.append(base)
    return linhas


def p2_auc(df, alvo):
    """Melhor ROC-AUC (CV agrupada por tarefa) prevendo a pista só com código + pedido."""
    X, y, g = df[COLS_CODIGO].values, df[alvo].values, df["instance_id"].values
    if y.min() == y.max():
        return {"regressao_logistica": float("nan"), "random_forest": float("nan")}
    modelos = {
        "regressao_logistica": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=0),
    }
    resultado = {}
    for nome, modelo in modelos.items():
        prob = np.full(len(y), y.mean())
        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
            if len(set(y[tr])) < 2:
                continue
            modelo.fit(X[tr], y[tr])
            prob[te] = modelo.predict_proba(X[te])[:, 1]
        resultado[nome] = roc_auc_score(y, prob)
    return resultado


def relatorio(por_patch, titulo):
    patches = por_patch.groupby("patch_id")
    print(f"\n=== {titulo}: {patches.ngroups} patches, {por_patch.instance_id.nunique()} tarefas, {len(por_patch)} trechos ===")
    resumo = []
    for s in PISTAS:
        varia = patches[s].nunique().gt(1).mean()
        taxa = por_patch[s].mean()
        aucs = p2_auc(por_patch, s)
        melhor = np.nanmax(list(aucs.values())) if not all(np.isnan(v) for v in aucs.values()) else float("nan")
        p1, p2 = varia >= 0.30, (melhor < 0.70) if not np.isnan(melhor) else False
        aviso = " (pouco informativa: prevalência extrema)" if taxa < 0.05 or taxa > 0.95 else ""
        print(f"  {s:2s} presente {taxa:6.1%} | P1 varia {varia:6.1%} -> {'PASSOU' if p1 else 'FALHOU'}"
              f" | P2 AUC LR={aucs['regressao_logistica']:.3f} RF={aucs['random_forest']:.3f} -> {'PASSOU' if p2 else 'FALHOU'}{aviso}")
        resumo.append({"pista": s, "presente": taxa, "varia": varia, "auc_lr": aucs["regressao_logistica"],
                       "auc_rf": aucs["random_forest"], "P1": p1, "P2": p2, "sobrevive": p1 and p2})
    return pd.DataFrame(resumo)


def main():
    print(f"-> Lendo trajetórias {INICIO + 1}-{INICIO + N} de nebius/SWE-agent-trajectories ...")
    vistas, linhas = set(), []
    for k, item in enumerate(load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True).take(INICIO + N)):
        if k < INICIO:
            vistas.add(item["instance_id"])
            continue
        pid = f"{item['instance_id']}|{item.get('model_name')}|{hashlib.sha1((item.get('generated_patch') or '').encode()).hexdigest()[:10]}"
        for l in analisa_trajetoria(item):
            l["patch_id"] = pid
            l["tarefa_nova"] = item["instance_id"] not in vistas
            linhas.append(l)
    df = pd.DataFrame(linhas)
    df.to_csv(SAIDA_CSV, index=False)
    print(f"Trechos de código em patches com 2+ trechos: {len(df)}  | mapeados no rastro: {df.mapeado.mean():.1%}")

    m = df[df.mapeado].copy()
    por_patch = m.groupby("patch_id").filter(lambda g: len(g) >= 2)
    principal = relatorio(por_patch, "PRINCIPAL (trajetórias 1.001-2.000)")
    novas = por_patch[por_patch.tarefa_nova]
    if novas.patch_id.nunique() >= 20:
        relatorio(novas, "SECUNDÁRIO (só tarefas não vistas nas trajetórias 1-1.000)")
    else:
        print(f"\nSECUNDÁRIO: só {novas.patch_id.nunique()} patches de tarefas novas; não reportado")
    vivas = principal[principal.sobrevive].pista.tolist()
    print(f"\nTeste de morte #1: {'DISPAROU (nenhuma pista sobreviveu)' if not vivas else 'não disparou; sobrevivem: ' + ', '.join(vivas)}")
    print(f"Dados salvos em {SAIDA_CSV}")


if __name__ == "__main__":
    main()
