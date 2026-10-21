"""
Validação humana da régua "ponto de decisão" (ver docs/piloto-premissas.md, registrada antes).

Sorteia 100 trechos do C1 (25 por combinação régua × citado no resumo), busca o pedido e o
patch no dataset original e gera:
  resultados/validacao/rotular.html            página para rotular (sem régua e sem resumo)
  resultados/validacao/gabarito_NAO_ABRIR.csv  régua e resumo de cada trecho (só a análise lê)

Uso: python scripts/validacao_amostra.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from confirmatorio_silencioso import resumo_e_pedido  # noqa: E402
from piloto_premissas import RE_ARQ, RE_DIFF, RE_HUNK  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "dados" / "confirmatorio_c1_trechos.csv"
PASTA = RAIZ / "resultados" / "validacao"
MODELO_HTML = Path(__file__).resolve().parent / "validacao_pagina.html"
SEMENTE = 20261020
POR_CELULA = 25
MAX_PEDIDO, MAX_PATCH = 8000, 30000


def sorteia(df):
    eleg = df[df.tem_resumo & (df.n_trechos_patch >= 2)].dropna(subset=["Y"])
    eleg = eleg[eleg.tamanho.between(2, 40)].sample(frac=1, random_state=SEMENTE)
    escolhidos, tarefas, contagem = [], set(), {}
    for idx, r in eleg.iterrows():
        celula = (int(r.Y), int(r.M))
        if contagem.get(celula, 0) >= POR_CELULA or r.instance_id in tarefas:
            continue
        escolhidos.append(idx)
        tarefas.add(r.instance_id)
        contagem[celula] = contagem.get(celula, 0) + 1
        if len(escolhidos) == 4 * POR_CELULA:
            break
    return eleg.loc[escolhidos].sample(frac=1, random_state=SEMENTE + 1).reset_index(drop=True)


def hunks_crus(patch):
    """Texto de cada hunk, na mesma ordem (e numeração) de trechos_do_patch."""
    saida = []
    for bloco in (b for b in RE_DIFF.split(patch or "") if b.strip()):
        m = RE_ARQ.search(bloco)
        if not m:
            continue
        cab = list(RE_HUNK.finditer(bloco))
        for i, h in enumerate(cab):
            fim = cab[i + 1].start() if i + 1 < len(cab) else len(bloco)
            saida.append((m.group(2).strip(), bloco[h.start():fim].rstrip("\n")))
    return saida


def busca_textos(ids):
    arq = hf_hub_download("nebius/SWE-rebench-openhands-trajectories", "trajectories.parquet", repo_type="dataset")
    achados = {}
    for lote in pq.ParquetFile(arq).iter_batches(batch_size=300, columns=["trajectory_id", "model_patch", "trajectory"]):
        for r in lote.to_pylist():
            if r["trajectory_id"] in ids:
                _, pedido = resumo_e_pedido(r["trajectory"])
                achados[r["trajectory_id"]] = (r["model_patch"], pedido)
        if len(achados) == len(ids):
            break
    return achados


def main():
    amostra = sorteia(pd.read_csv(ENTRADA))
    print("Por combinação (Y, M):", amostra.groupby(["Y", "M"]).size().to_dict())
    textos = busca_textos(set(amostra.patch_id))
    itens, gabarito = [], []
    for k, r in amostra.iterrows():
        patch, pedido = textos[r.patch_id]
        arquivo, trecho = hunks_crus(patch)[int(r.posicao)]
        assert arquivo == r.arquivo, (r.patch_id, arquivo, r.arquivo)
        vid = f"V{k + 1:03d}"
        itens.append({"id": vid, "repo": r.instance_id.rsplit("-", 1)[0].replace("__", "/"),
                      "pedido": pedido.strip()[:MAX_PEDIDO], "arquivo": arquivo, "trecho": trecho,
                      "patch": patch[:MAX_PATCH]})
        gabarito.append({"id": vid, "patch_id": r.patch_id, "instance_id": r.instance_id, "arquivo": arquivo,
                         "nome": r.nome, "posicao": int(r.posicao), "tamanho": int(r.tamanho),
                         "Y": int(r.Y), "M": int(r.M), "resolved": int(r.resolved)})
    PASTA.mkdir(parents=True, exist_ok=True)
    dados = json.dumps(itens, ensure_ascii=False).replace("</", "<\\/")
    html = MODELO_HTML.read_text(encoding="utf-8").replace("/*DADOS*/[]", dados)
    (PASTA / "rotular.html").write_text(html, encoding="utf-8")
    pd.DataFrame(gabarito).to_csv(PASTA / "gabarito_NAO_ABRIR.csv", index=False)
    print(f"{len(itens)} trechos -> {PASTA / 'rotular.html'}")


if __name__ == "__main__":
    main()
