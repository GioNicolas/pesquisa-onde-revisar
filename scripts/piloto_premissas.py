"""
Piloto das premissas P1 e P2 (ver docs/piloto-premissas.md, registrado antes da análise).

Para cada patch com 2+ trechos de código (hunks que modificam arquivos já existentes,
fora de arquivos de teste), liga cada trecho à última edição do agente que o produziu
e mede pistas do rastro:
  V  - o agente executou algum teste/programa depois dessa edição (pista principal)
  D  - a mensagem da edição tem marcadores de escolha/suposição (descritiva)
  Pl - a função/arquivo do trecho foi mencionado antes da edição (descritiva)

P1: fração de patches em que V varia entre os trechos (critério: >= 30%).
P2: ROC-AUC de prever V só com características do código (critério: < 0,70).

Uso: python scripts/piloto_premissas.py [n_trajetorias]
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

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_CSV = RAIZ / "dados" / "piloto_trechos.csv"

RE_DIFF = re.compile(r"(?=^diff --git )", re.M)
RE_ARQ = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.M)
RE_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$", re.M)
RE_BLOCO = re.compile(r"```[^\n]*\n(.*?)```", re.S)
RE_ARQ_ABERTO = re.compile(r"^\[File: (/\S+) \(", re.M)
RE_TESTE = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")
RE_EXECUCAO = re.compile(r"^\s*(python3?|pytest|tox|nosetests|bash|sh|make|asv|node|npm|go|cargo|mvn|gradle|java)\b"
                         r"|^\s*\./|-m\s+(pytest|unittest)")
RE_EDICAO_FALHOU = re.compile(r"Your proposed edit has introduced|edit was not applied|Error: start_line", re.I)
MARCADORES_DECISAO = ["assum", "instead", "alternativ", "for simplicity", "simplif", "workaround",
                      "not sure", "unclear", "decide", "choose", "option"]
RE_NOME = re.compile(r"\b(?:def|class)\s+([A-Za-z_]\w*)")


def trechos_do_patch(patch):
    """Hunks do patch com arquivo, posição, linhas adicionadas/removidas e contexto do cabeçalho."""
    saida = []
    for bloco in (b for b in RE_DIFF.split(patch or "") if b.strip()):
        m = RE_ARQ.search(bloco)
        if not m:
            continue
        arquivo = m.group(2).strip()
        cabecalhos = list(RE_HUNK.finditer(bloco))
        for i, h in enumerate(cabecalhos):
            fim = cabecalhos[i + 1].start() if i + 1 < len(cabecalhos) else len(bloco)
            corpo = bloco[h.end():fim].splitlines()
            saida.append({
                "arquivo": arquivo,
                "old_start": int(h.group(1)),
                "old_count": int(h.group(2) or 1),
                "contexto": h.group(5).strip(),
                "adicionadas": [l[1:] for l in corpo if l.startswith("+") and not l.startswith("+++")],
                "removidas": [l[1:] for l in corpo if l.startswith("-") and not l.startswith("---")],
                "idx_no_arquivo": i,
                "hunks_no_arquivo": len(cabecalhos),
            })
    for pos, t in enumerate(saida):
        t["posicao"] = pos
    return saida


def normaliza(linhas):
    """Linhas não triviais, sem espaços nas pontas (para comparar texto inserido)."""
    return {l.strip() for l in linhas if len(l.strip()) > 3}


def passos_do_rastro(trajetoria):
    """Lista de ações do agente: texto, comando e a observação seguinte."""
    passos = json.loads(trajetoria) if isinstance(trajetoria, str) else (trajetoria or [])
    acoes = []
    for k, p in enumerate(passos):
        if p.get("role") != "ai":
            continue
        texto = str(p.get("text", ""))
        blocos = RE_BLOCO.findall(texto)
        comando = blocos[-1].strip() if blocos else ""
        observacao = str(passos[k + 1].get("text", "")) if k + 1 < len(passos) else ""
        pensamento = RE_BLOCO.sub(" ", texto)
        acoes.append({"comando": comando, "observacao": observacao, "pensamento": pensamento})
    return acoes


def edicoes(acoes):
    """Edições aplicadas: passo, arquivo (relativo ao repositório) e linhas inseridas."""
    saida = []
    for i, a in enumerate(acoes):
        cmd = a["comando"]
        if not cmd.startswith("edit "):
            continue
        if RE_EDICAO_FALHOU.search(a["observacao"]):
            continue
        m = RE_ARQ_ABERTO.search(a["observacao"])
        if not m:
            continue
        partes = m.group(1).strip("/").split("/", 1)
        if len(partes) < 2:
            continue
        linhas = cmd.splitlines()[1:]
        if linhas and linhas[-1].strip() == "end_of_edit":
            linhas = linhas[:-1]
        saida.append({"passo": i, "arquivo": partes[1], "inseridas": normaliza(linhas)})
    return saida


def analisa_trajetoria(item):
    trechos = [t for t in trechos_do_patch(item.get("generated_patch"))
               if not (t["old_start"] == 0 and t["old_count"] == 0) and not RE_TESTE.search(t["arquivo"])]
    if len(trechos) < 2:
        return []
    acoes = passos_do_rastro(item.get("trajectory"))
    eds = edicoes(acoes)
    execucoes = [i for i, a in enumerate(acoes) if RE_EXECUCAO.search(a["comando"])]
    n_arquivos = len({t["arquivo"] for t in trechos})
    linhas = []
    for t in trechos:
        alvo = normaliza(t["adicionadas"])
        candidatas = [e for e in eds if e["arquivo"] == t["arquivo"] and alvo & e["inseridas"]]
        base = {
            "instance_id": item["instance_id"], "model_name": item.get("model_name"),
            "task_resolved": bool(item.get("target")), "arquivo": t["arquivo"],
            "posicao": t["posicao"], "posicao_rel": t["posicao"] / max(1, len(trechos) - 1),
            "linhas_add": len(t["adicionadas"]), "linhas_rem": len(t["removidas"]),
            "tamanho": len(t["adicionadas"]) + len(t["removidas"]),
            "hunks_no_arquivo": t["hunks_no_arquivo"], "arquivos_no_patch": n_arquivos,
            "primeiro_do_arquivo": int(t["idx_no_arquivo"] == 0),
            "ultimo_do_arquivo": int(t["idx_no_arquivo"] == t["hunks_no_arquivo"] - 1),
            "n_trechos_patch": len(trechos), "mapeado": bool(candidatas),
        }
        if candidatas:
            ed = max(candidatas, key=lambda e: e["passo"])
            pensamento = acoes[ed["passo"]]["pensamento"].lower()
            nomes = RE_NOME.findall(t["contexto"]) or [Path(t["arquivo"]).stem]
            antes = " ".join(a["pensamento"] for a in acoes[:ed["passo"]])
            base.update({
                "passo_edicao": ed["passo"], "n_passos": len(acoes),
                "V": int(any(x > ed["passo"] for x in execucoes)),
                "D": int(any(m in pensamento for m in MARCADORES_DECISAO)),
                "Pl": int(any(n in antes for n in nomes)),
            })
        linhas.append(base)
    return linhas


def p2_auc(df):
    """Melhor ROC-AUC (validação cruzada agrupada por tarefa) prevendo V só com o código."""
    cols = ["linhas_add", "linhas_rem", "tamanho", "posicao", "posicao_rel", "hunks_no_arquivo",
            "arquivos_no_patch", "primeiro_do_arquivo", "ultimo_do_arquivo"]
    X, y, g = df[cols].values, df["V"].values, df["instance_id"].values
    modelos = {
        "regressao_logistica": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
        "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3, random_state=0),
    }
    resultado = {}
    for nome, modelo in modelos.items():
        prob = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
            modelo.fit(X[tr], y[tr])
            prob[te] = modelo.predict_proba(X[te])[:, 1]
        resultado[nome] = roc_auc_score(y, prob)
    return resultado


def main(n=1000):
    print(f"-> Lendo {n} trajetórias de nebius/SWE-agent-trajectories ...")
    linhas = []
    for item in load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True).take(n):
        for i, l in enumerate(analisa_trajetoria(item)):
            l["patch_id"] = f"{item['instance_id']}|{item.get('model_name')}|{hashlib.sha1((item.get('generated_patch') or '').encode()).hexdigest()[:10]}"
            linhas.append(l)
    df = pd.DataFrame(linhas)
    df.to_csv(SAIDA_CSV, index=False)

    print(f"\nTrechos de código em patches com 2+ trechos: {len(df)}  | mapeados no rastro: {df.mapeado.mean():.1%}")
    m = df[df.mapeado].copy()
    por_patch = m.groupby("patch_id").filter(lambda g: len(g) >= 2)
    patches = por_patch.groupby("patch_id")
    print(f"Patches elegíveis (2+ trechos mapeados): {patches.ngroups}  | tarefas: {por_patch.instance_id.nunique()}  | trechos: {len(por_patch)}")

    varia = patches["V"].nunique().gt(1)
    print(f"\nP1 - patches em que V varia entre os trechos: {varia.mean():.1%} ({varia.sum()}/{len(varia)})  -> critério >= 30%: {'PASSOU' if varia.mean() >= 0.30 else 'FALHOU'}")
    print(f"     taxa geral de V (verificado depois): {por_patch.V.mean():.1%}")
    for s in ("D", "Pl"):
        print(f"     [descritivo] {s}: presente em {por_patch[s].mean():.1%} dos trechos; varia em {patches[s].nunique().gt(1).mean():.1%} dos patches")

    aucs = p2_auc(por_patch)
    melhor = max(aucs.values())
    print("\nP2 - prever V só com o código (ROC-AUC, CV agrupada por tarefa): "
          + ", ".join(f"{k}={v:.3f}" for k, v in aucs.items())
          + f"  -> critério < 0,70: {'PASSOU' if melhor < 0.70 else 'FALHOU'}")
    print(f"\nDados salvos em {SAIDA_CSV}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1000)
