"""
Teste confirmatório, C2 (suplementar): H1 do "trecho silencioso" no Cursor
(SWE-rebench julho de 2026). Ver docs/piloto-premissas.md.

Só sessões em que todas as edições bem-sucedidas trazem o arquivo completo depois da
edição sem corte. Reconstrução: commit base + arquivo completo de cada edição, em ordem.

Uso: python scripts/confirmatorio_cursor.py [pasta_dos_repositorios]
"""

import gzip
import json
import os
import sys
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
import piloto3_moderno as p3  # noqa: E402
from confirmatorio_silencioso import linhas_da_sessao, rotula, teste_h1, trechos_de_codigo  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "dados" / "confirmatorio_c2_trechos.csv"


def conteudo(resultado):
    c = resultado.get("content")
    if isinstance(c, str):
        try:
            c = json.loads(c)
        except json.JSONDecodeError:
            return None
    return c if isinstance(c, dict) else None


def reaplica_cursor(sessao, destino, sha):
    """Devolve o patch, ou None se alguma edição veio cortada."""
    p3.git(["checkout", "-q", "-f", sha], destino)
    p3.git(["clean", "-q", "-fdx"], destino)
    prefixo = "/" + sessao["repository"].split("/")[1] + "/"
    res = p3.resultados_por_id(sessao["events"])
    for e in sessao["events"]:
        if e["type"] != "tool_call" or e.get("tool") not in ("edit", "delete"):
            continue
        r = res.get(e.get("tool_call_id"))
        if r is None:
            continue
        if r.get("truncated"):
            return None
        c = conteudo(r) or {}
        sucesso = c.get("success")
        caminho = (e.get("input") or {}).get("path", "")
        if not sucesso or not caminho.startswith(prefixo):
            continue
        arq = destino / caminho[len(prefixo):]
        if e["tool"] == "delete":
            if os.path.exists(p3.longo(arq)):
                os.remove(p3.longo(arq))
            continue
        if "afterFullFileContent" not in sucesso:
            return None
        os.makedirs(p3.longo(arq.parent), exist_ok=True)
        with open(p3.longo(arq), "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(sucesso["afterFullFileContent"])
    return p3.git(["-c", "core.quotepath=off", "diff", "--no-color", "-U3", sha], destino)


def main(pasta_repos):
    bases = json.loads(p3.BASES.read_text())
    prontos = p3.prepara_repos(Path(pasta_repos), bases)
    linhas, sessoes = [], []
    for k in range(5):
        f = hf_hub_download(p3.DATASET, f"trajectories/cursor/run_{k}.jsonl.gz", repo_type="dataset")
        for l in gzip.open(f, "rt", encoding="utf-8"):
            s = json.loads(l)
            dest = prontos.get(s["instance_id"], (None, None))[0]
            patch = reaplica_cursor(s, dest, bases[s["instance_id"]]["base_sha"]) if dest else None
            valida = bool(patch and patch.strip())
            sessoes.append({"patch_id": s["trajectory_id"], "instance_id": s["instance_id"],
                            "valida": valida, "reconstruida": patch is not None})
            if not valida:
                continue
            finais = [p3.texto(e.get("content")) for e in s["events"] if e["type"] == "final_message"]
            resumo = finais[-1] if finais else None
            pedido = " ".join(p3.texto(p.get("content")) for p in s.get("prompts", []) if p.get("role") == "user")
            for linha in linhas_da_sessao(s["trajectory_id"], s["instance_id"], trechos_de_codigo(patch), resumo, pedido):
                linha["resolved"] = int(s["evaluation"]["resolved"])
                linhas.append(linha)
    sessoes = pd.DataFrame(sessoes)
    df = pd.DataFrame(linhas)
    df["Y"] = rotula(df, sessoes[sessoes.valida])
    df.to_csv(SAIDA, index=False)
    print(f"Sessões: {len(sessoes)} | reconstruídas sem corte: {sessoes.reconstruida.sum()} | válidas (com patch): {sessoes.valida.sum()}")
    eleg = df[df.tem_resumo & (df.n_trechos_patch >= 2)].dropna(subset=["Y"]).copy()
    print(f"Elegíveis (2+ trechos, com resumo, tarefa com 3+ outras tentativas válidas): {len(eleg)} trechos")
    if eleg.Y.nunique() < 2 or eleg.M.nunique() < 2 or eleg.instance_id.nunique() < 5:
        print("C2: dados insuficientes para o teste")
        return
    eleg["Y"] = eleg.Y.astype(int)
    teste_h1(eleg, "C2 SUPLEMENTAR — Cursor")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else RAIZ / ".cache" / "repos")
