"""
Piloto 3 ("última chance"): as pistas do piloto 2 em rastros de um agente moderno
(Claude Code / Fable 5, SWE-rebench julho de 2026). Ver docs/piloto-premissas.md,
registrado antes da análise.

Etapas:
  1. baixa os 5 rastros do Claude Code (555 sessões, 111 tarefas)
  2. obtém cada repositório no commit base do PR (dados/piloto3_bases.json)
  3. reaplica as edições Edit/Write bem-sucedidas e tira o git diff (= patch final)
  4. liga cada trecho à última edição que o produziu e mede T, U, Pl, D, M
  5. P1 (varia em >= 30% dos patches) e P2 (código + pedido preveem com AUC < 0,70)

Uso: python scripts/piloto3_moderno.py [pasta_dos_repositorios]
"""

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parent))
from piloto_premissas import MARCADORES_DECISAO, normaliza, trechos_do_patch  # noqa: E402
from piloto2_pistas import p2_auc  # noqa: E402
import piloto2_pistas  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
BASES = RAIZ / "dados" / "piloto3_bases.json"
SAIDA_CSV = RAIZ / "dados" / "piloto3_trechos.csv"
SAIDA_SESSOES = RAIZ / "dados" / "piloto3_sessoes.csv"
DATASET = "ibragim-bad/swe_rebench_07_2026_trajectories"
PISTAS = ["T", "U", "Pl", "D", "M"]

EXT_CODIGO = {".py", ".go", ".java", ".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".kt"}
RE_TESTE = re.compile(r"(^|/)(tests?|testing|__tests__|spec|testdata|e2e)(/|$)|(^|/)test_[^/]*\.py$|_test\.(py|go)$"
                      r"|Tests?\.(java|kt)$|\.(test|spec)\.[jt]sx?$|(^|/)src/test/|(^|/)conftest\.py$")
ATRIBUTOS = "*.py diff=python\n*.go diff=golang\n*.java diff=java\n*.kt diff=java\n*.rs diff=rust\n"
RE_FUNC_GO = re.compile(r"\bfunc\s*(?:\([^)]*\)\s*)?([A-Za-z_]\w*)")
RE_IDENT_PAREN = re.compile(r"([A-Za-z_$][\w$]*)\s*(?:<[^()]*>)?\s*\(")
NAO_NOMES = {"if", "for", "while", "switch", "catch", "return", "func", "function", "fn", "def", "match",
             "new", "await", "async", "super", "this", "typeof", "sizeof", "assert", "print", "else"}
# comandos de terminal que podem alterar arquivos fora das ferramentas Edit/Write (secundário)
RE_BASH_EDITA = re.compile(
    r"sed\s+(-\w*\s+)*-i|perl\s+-\w*i|git\s+(apply|checkout\s+--|restore|stash)|\bpatch\s+-p"
    r"|>\s*(?!/dev/null|&|/tmp)[\w./-]+\.(py|go|java|rs|tsx?|jsx?|kt)\b|\btee\s+(?!/tmp)[\w./-]+\.(py|go|java|rs|tsx?|kt)\b"
    r"|write_text\(|open\([^)]*['\"]w|gofmt\s+-w|go\s+fmt|cargo\s+fmt|rustfmt|prettier\s+.*--write|\bblack\b"
    r"|ruff\s+format|eslint\s+.*--fix|spotless:apply|npm\s+run\s+(format|lint:fix)|goimports\s+-w")
RE_BUSCA_BASH = re.compile(r"\b(grep|rg|ag|git\s+grep)\b")


def longo(caminho):
    """Caminho com prefixo de caminho longo no Windows, para aceitar mais de 260 caracteres."""
    c = os.path.abspath(str(caminho)).replace("/", "\\")
    return r"\\?" + "\\" + c if sys.platform == "win32" and not c.startswith("\\\\") else c


def git(args, cwd, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr[:300]}")
    return r.stdout


def carrega_sessoes():
    linhas = []
    for k in range(5):
        f = hf_hub_download(DATASET, f"trajectories/claude-code/run_{k}.jsonl.gz", repo_type="dataset")
        linhas += [json.loads(l) for l in gzip.open(f, "rt", encoding="utf-8")]
    return linhas


def prepara_repos(pasta, bases):
    """Prepara cada repositório uma única vez (em paralelo entre repositórios)."""
    por_repo = {}
    for iid, b in bases.items():
        por_repo.setdefault(b["repo"], []).append((iid, b["base_sha"]))

    def um_repo(item):
        repo, tarefas = item
        saida = []
        for iid, sha in tarefas:
            try:
                saida.append((iid, prepara_repo(pasta, repo, sha), None))
            except Exception as ex:  # noqa: BLE001
                saida.append((iid, None, str(ex)[:200]))
        return saida
    with ThreadPoolExecutor(2) as pool:
        return {iid: (dest, erro) for lote in pool.map(um_repo, por_repo.items()) for iid, dest, erro in lote}


def prepara_repo(pasta, repo, sha):
    """Repositório raso, só com o commit base, sem conversão de fim de linha."""
    destino = pasta / repo.replace("/", "__")
    if not (destino / ".git" / "HEAD").exists():
        if destino.exists():
            shutil.rmtree(destino, ignore_errors=True)
        destino.mkdir(parents=True, exist_ok=True)
        git(["init", "-q", "--template="], destino)
        git(["config", "core.autocrlf", "false"], destino)
        git(["config", "core.longpaths", "true"], destino)
        git(["remote", "add", "origin", f"https://github.com/{repo}.git"], destino)
        (destino / ".git" / "info").mkdir(exist_ok=True)
        (destino / ".git" / "info" / "attributes").write_text(ATRIBUTOS)
    if subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=destino, capture_output=True).returncode != 0:
        git(["fetch", "-q", "--depth", "1", "origin", sha], destino)
    return destino


def resultados_por_id(eventos):
    return {e.get("tool_call_id"): e for e in eventos if e["type"] == "tool_result"}


def reaplica(sessao, destino, sha):
    """Reaplica Edit/Write bem-sucedidos; devolve (patch, edições) ou (None, motivo)."""
    git(["checkout", "-q", "-f", sha], destino)
    git(["clean", "-q", "-fdx"], destino)
    prefixo = "/" + sessao["repository"].split("/")[1] + "/"
    res = resultados_por_id(sessao["events"])
    eds = []
    for i, e in enumerate(sessao["events"]):
        if e["type"] != "tool_call" or e.get("tool") not in ("Edit", "Write"):
            continue
        if res.get(e.get("tool_call_id"), {}).get("status") != "success":
            continue
        caminho = e["input"].get("file_path", "")
        if not caminho.startswith(prefixo):
            continue
        rel = caminho[len(prefixo):]
        arq = destino / rel
        if e["tool"] == "Write":
            conteudo = e["input"].get("content", "")
            os.makedirs(longo(arq.parent), exist_ok=True)
            with open(longo(arq), "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
                f.write(conteudo)
            novo = conteudo
        else:
            velho, novo = e["input"].get("old_string", ""), e["input"].get("new_string", "")
            atual = None
            if os.path.exists(longo(arq)):
                with open(longo(arq), encoding="utf-8", errors="surrogateescape", newline="") as f:
                    atual = f.read()
            if atual is None and velho == "":
                os.makedirs(longo(arq.parent), exist_ok=True)
                atual = ""
            elif atual is None or velho not in atual:
                return None, "edicao_nao_aplicada"
            atual = atual.replace(velho, novo) if e["input"].get("replace_all") else atual.replace(velho, novo, 1)
            with open(longo(arq), "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
                f.write(atual)
        eds.append({"evento": i, "arquivo": rel, "inseridas": normaliza(novo.splitlines())})
    patch = git(["-c", "core.quotepath=off", "diff", "--no-color", "-U3", sha], destino)
    return patch, eds


def nome_do_trecho(contexto, arquivo):
    if arquivo.endswith(".go"):
        m = RE_FUNC_GO.search(contexto)
        return m.group(1) if m else None
    for m in RE_IDENT_PAREN.finditer(contexto):
        if m.group(1) not in NAO_NOMES:
            return m.group(1)
        break
    return None


def texto(c):
    return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False) if c is not None else ""


def analisa_sessao(sessao, patch, eds):
    ev = sessao["events"]
    res = resultados_por_id(ev)
    pedido = " ".join(texto(p.get("content")) for p in sessao.get("prompts", []) if p.get("role") == "user")
    trechos = [t for t in trechos_do_patch(patch)
               if not (t["old_start"] == 0 and t["old_count"] == 0)
               and Path(t["arquivo"]).suffix in EXT_CODIGO and not RE_TESTE.search(t["arquivo"])]
    msgs = [(i, texto(e.get("content"))) for i, e in enumerate(ev) if e["type"] in ("assistant_message", "assistant_analysis")]
    finais = [texto(e.get("content")) for e in ev if e["type"] == "final_message"]
    final = finais[-1] if finais else ""
    falhas = []   # (evento, saída) de comandos que terminaram com erro
    buscas = []   # textos de busca
    for i, e in enumerate(ev):
        if e["type"] != "tool_call":
            continue
        entrada = e.get("input") or {}
        if e.get("tool") == "Bash":
            cmd = entrada.get("command", "")
            r = res.get(e.get("tool_call_id"), {})
            if r.get("status") == "error":
                falhas.append((i, texto(r.get("content"))))
            if RE_BUSCA_BASH.search(cmd):
                buscas.append(cmd)
        elif e.get("tool") == "Grep":
            buscas.append(texto(entrada.get("pattern")))
    buscas_txt = "\n".join(buscas)
    passos_edicao = sorted(x["evento"] for x in eds)
    n_arquivos = len({t["arquivo"] for t in trechos})
    linhas = []
    for t in trechos:
        alvo = normaliza(t["adicionadas"])
        candidatas = [x for x in eds if x["arquivo"] == t["arquivo"] and alvo & x["inseridas"]]
        nome = nome_do_trecho(t["contexto"], t["arquivo"])
        base_arq = Path(t["arquivo"]).name
        nomes = [nome] if nome else [Path(t["arquivo"]).stem]
        base = {
            "instance_id": sessao["instance_id"], "patch_id": sessao["trajectory_id"], "language": sessao["language"],
            "task_resolved": bool(sessao["evaluation"]["resolved"]), "arquivo": t["arquivo"], "nome": nome,
            "posicao": t["posicao"], "posicao_rel": t["posicao"] / max(1, len(trechos) - 1),
            "linhas_add": len(t["adicionadas"]), "linhas_rem": len(t["removidas"]),
            "tamanho": len(t["adicionadas"]) + len(t["removidas"]),
            "hunks_no_arquivo": t["hunks_no_arquivo"], "arquivos_no_patch": n_arquivos,
            "primeiro_do_arquivo": int(t["idx_no_arquivo"] == 0),
            "ultimo_do_arquivo": int(t["idx_no_arquivo"] == t["hunks_no_arquivo"] - 1),
            "nome_no_pedido": int(bool(nome) and nome in pedido),
            "arquivo_no_pedido": int(base_arq in pedido or t["arquivo"] in pedido),
            "n_trechos_patch": len(trechos), "mapeado": bool(candidatas),
        }
        if candidatas:
            ed = max(candidatas, key=lambda x: x["evento"])["evento"]
            anterior = max([p for p in passos_edicao if p < ed], default=-1)
            antes = " ".join(m for i, m in msgs if i < ed)
            recentes = " ".join(m for i, m in msgs if anterior < i < ed).lower()
            base.update({
                "evento_edicao": ed, "n_eventos": len(ev),
                "T": int(bool(nome) and any(i < ed and base_arq in s and nome in s for i, s in falhas)),
                "U": int(bool(nome) and len(nome) >= 4 and nome in buscas_txt),
                "Pl": int(any(n in antes for n in nomes)),
                "D": int(any(m in recentes for m in MARCADORES_DECISAO)),
                "M": int(any(n in final for n in nomes)),
            })
        linhas.append(base)
    return linhas


def main(pasta_repos):
    pasta_repos = Path(pasta_repos)
    bases = json.loads(BASES.read_text())
    sessoes = carrega_sessoes()
    print(f"-> {len(sessoes)} sessões do Claude Code, {len(bases)} tarefas")

    prontos = prepara_repos(pasta_repos, bases)
    falhou = {iid: erro for iid, (dest, erro) in prontos.items() if dest is None}
    print(f"-> repositórios prontos: {len(bases) - len(falhou)}/{len(bases)}")
    for iid, erro in list(falhou.items())[:5]:
        print(f"   falhou {iid}: {erro}")

    linhas, info = [], []
    for k, s in enumerate(sessoes):
        dest = prontos.get(s["instance_id"], (None, None))[0]
        reg = {"patch_id": s["trajectory_id"], "instance_id": s["instance_id"], "language": s["language"],
               "bash_edita": any(RE_BASH_EDITA.search((e.get("input") or {}).get("command", "") or "")
                                 for e in s["events"] if e["type"] == "tool_call" and e.get("tool") == "Bash"),
               "tem_resumo": any(e["type"] == "final_message" for e in s["events"])}
        if dest is None:
            reg["status"] = "sem_repositorio"
        else:
            patch, eds = reaplica(s, dest, bases[s["instance_id"]]["base_sha"])
            if patch is None:
                reg["status"] = eds
            else:
                reg["status"] = "ok"
                for l in analisa_sessao(s, patch, eds):
                    l["bash_edita"] = reg["bash_edita"]
                    linhas.append(l)
        info.append(reg)
        if (k + 1) % 50 == 0:
            print(f"   {k + 1}/{len(sessoes)} sessões")
    info = pd.DataFrame(info)
    info.to_csv(SAIDA_SESSOES, index=False)
    df = pd.DataFrame(linhas)
    df.to_csv(SAIDA_CSV, index=False)

    print(f"\nReconstrução: {info.status.value_counts().to_dict()}")
    print(f"Sessões com comandos de terminal que podem editar arquivos: {info.bash_edita.mean():.1%}  | com resumo final: {info.tem_resumo.mean():.1%}")
    print(f"Trechos de código (arquivos existentes, sem testes): {len(df)}  | mapeados a uma edição: {df.mapeado.mean():.1%}")

    m = df[df.mapeado].copy()
    por_patch = m.groupby("patch_id").filter(lambda g: len(g) >= 2)
    print(f"Trechos por patch elegível: mediana {por_patch.groupby('patch_id').size().median():.0f}")
    principal = piloto2_pistas.relatorio(por_patch, "PRINCIPAL (Claude Code, 555 sessões)")
    sec = por_patch[~por_patch.bash_edita]
    if sec.patch_id.nunique() >= 20:
        piloto2_pistas.relatorio(sec, "SECUNDÁRIO (sem comandos de terminal que editam arquivos)")
    vivas = principal[principal.sobrevive].pista.tolist()
    print(f"\nDecisão: {'nenhuma pista sobreviveu -> encerrar a linha' if not vivas else 'sobrevivem: ' + ', '.join(vivas)}")
    print(f"Dados salvos em {SAIDA_CSV} e {SAIDA_SESSOES}")


if __name__ == "__main__":
    piloto2_pistas.PISTAS = PISTAS
    piloto2_pistas.COLS_CODIGO = piloto2_pistas.COLS_CODIGO  # mesmas 11 características
    main(sys.argv[1] if len(sys.argv) > 1 else RAIZ / ".cache" / "repos")
