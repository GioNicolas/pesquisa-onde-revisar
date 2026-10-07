# Mini-projeto 01 — primeiro contato com trajetórias de agentes
#
# Objetivo: ler algumas centenas de trajetórias públicas e comparar, com
# estatística descritiva, as que resolveram a tarefa com as que falharam.
# Ainda não é a pesquisa (que é por hunk); é aprender o formato dos dados.
#
# Dados: nebius/SWE-agent-trajectories (Hugging Face, CC-BY-4.0).
#   Colunas: instance_id, model_name, target (resolveu?), trajectory,
#   exit_status, generated_patch, eval_logs.
#   trajectory = lista de passos {role: system | ai | user, text: ...}.
#
# Preparação (uma vez), no terminal, dentro desta pasta:
#   python -m venv .venv
#   .venv\Scripts\activate            (Windows)
#   pip install datasets pandas matplotlib
#
# Rodar: abra no VS Code/Catenary e execute célula por célula (# %%),
# ou rode inteiro com: python mini_projeto_01.py
#
# Não foi testado nesta máquina (sem rede para baixar os pacotes).
# Se algo quebrar, a célula 2 mostra o formato real dos dados: ajuste a
# partir do que ela imprimir.

# %% 1. Carregar N trajetórias sem baixar o dataset inteiro (1,1 GB)
import json
import re

import pandas as pd

from pathlib import Path

# no modo célula (# %%) __file__ pode não existir; nesse caso roda a partir da raiz do projeto
RAIZ = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd()
from datasets import load_dataset

N = 300
stream = load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True)
rows = list(stream.take(N))
print(f"{len(rows)} trajetórias carregadas")
print("colunas:", list(rows[0].keys()))

# %% 2. Olhar uma trajetória de perto (sempre comece por aqui)
def parse_traj(t):
    # o campo pode vir como texto JSON ou já como lista
    return json.loads(t) if isinstance(t, str) else t

exemplo = parse_traj(rows[0]["trajectory"])
print("passos:", len(exemplo))
for passo in exemplo[:6]:
    texto = str(passo.get("text", ""))[:300].replace("\n", " ")
    print(f"[{passo.get('role')}] {texto}\n")

print("resolveu?", rows[0]["target"], "| saída:", rows[0]["exit_status"])
print("patch (início):\n", (rows[0]["generated_patch"] or "")[:500])

# %% 3. Extrair pistas simples por trajetória
# No SWE-agent, cada passo do agente (role "ai") termina com o comando
# dentro de um bloco ```...```. Pegamos o último bloco como "o comando".
BLOCO = re.compile(r"```(?:[a-zA-Z]*)\n(.*?)```", re.S)
TESTE = re.compile(r"\b(pytest|unittest|tox|python\s+\S*(test|reproduce)\S*)", re.I)

def comando(texto):
    blocos = BLOCO.findall(texto or "")
    return blocos[-1].strip() if blocos else ""

def pistas(row):
    passos = parse_traj(row["trajectory"])
    cmds = [comando(p.get("text")) for p in passos if p.get("role") == "ai"]
    primeiras = [c.split()[0] if c else "" for c in cmds]
    patch = row["generated_patch"] or ""
    return {
        "instance_id": row["instance_id"],
        "resolveu": bool(row["target"]),
        "passos_do_agente": len(cmds),
        "edicoes": sum(p in ("edit", "create", "insert") for p in primeiras),
        "leituras": sum(p in ("open", "goto", "scroll_down", "scroll_up", "cat") for p in primeiras),
        "buscas": sum(p in ("search_file", "search_dir", "find_file", "grep", "find") for p in primeiras),
        "rodou_teste": sum(bool(TESTE.search(c)) for c in cmds),
        "arquivos_no_patch": patch.count("diff --git"),
        "hunks_no_patch": len(re.findall(r"^@@ ", patch, re.M)),
    }

df = pd.DataFrame([pistas(r) for r in rows])
print(df.head())
print("\ncomandos mais comuns (confira se as categorias acima fazem sentido):")
todos = [comando(p.get("text")).split()[0]
         for r in rows for p in parse_traj(r["trajectory"])
         if p.get("role") == "ai" and comando(p.get("text"))]
print(pd.Series(todos).value_counts().head(15))

# %% 4. Comparar quem resolveu com quem falhou
colunas = ["passos_do_agente", "edicoes", "leituras", "buscas",
           "rodou_teste", "arquivos_no_patch", "hunks_no_patch"]
print("taxa de resolução:", round(df["resolveu"].mean() * 100, 1), "%")
print("\nmedianas por grupo:")
print(df.groupby("resolveu")[colunas].median().T)

# %% 5. Um gráfico e salvar os dados
import matplotlib.pyplot as plt

df.boxplot(column="passos_do_agente", by="resolveu")
plt.title("Passos do agente: falhou (False) x resolveu (True)")
plt.suptitle("")
plt.savefig(RAIZ / "resultados" / "figuras" / "passos_por_resultado.png", dpi=150, bbox_inches="tight")
df.to_csv(RAIZ / "dados" / "pistas_por_trajetoria.csv", index=False)
print("salvo: resultados/figuras/passos_por_resultado.png e dados/pistas_por_trajetoria.csv")

# %% 6. Perguntas para anotar no diário
# - As trajetórias que falham são mais longas? (a literatura diz que sim:
#   arXiv 2511.00197). Os seus dados confirmam?
# - Quem roda teste resolve mais?
# - Patches com mais hunks falham mais? (isso vira uma baseline!)
# - Alguma categoria de comando ficou mal classificada na célula 3?
