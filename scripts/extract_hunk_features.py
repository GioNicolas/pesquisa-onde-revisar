"""
Extrator de Sinais de Trajetória e Alinhamento de Hunks (Fase 2)

Projeto: Priorização de Hunks em Patches Gerados por Agentes de IA via Sinais de Trajetória
Autor: Giorgio Nicolas de A. Bertino (CDIA — UFPB)
Data: Outubro/2026

Objetivo:
1. Fazer o parse de patches unificados (git diff) em unidades atômicas (hunks: @@ ... @@).
2. Construir o Ground Truth por alinhamento estático com os Gold Patches humanos
   (SWE-rebench / SWE-bench-extra).
3. Mapear cada hunk para os eventos da trajetória do agente (leitura prévia,
   rotatividade de edições, verificação por testes, proximidade com erros).
4. Gerar o dataset tabular 'hunk_features_dataset.csv' para modelagem e curvas de esforço.
"""

import json
import os
import re
import sys
import pandas as pd

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
from datasets import load_dataset

# ==============================================================================
# 1. PARSER DE DIFF E HUNKS
# ==============================================================================

RE_FILE_DIFF = re.compile(r"(?=diff --git )")
RE_FILE_HEADER = re.compile(r"^diff --git a/(.*?) b/(.*?)$", re.M)
RE_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$", re.M)

def parse_patch_hunks(patch_str: str) -> list[dict]:
    """
    Recebe uma string de patch unificado (git diff) e devolve a lista de hunks
    com metadados: arquivo, coordenadas de linha (old/new), linhas adicionadas e removidas.
    """
    if not patch_str or not isinstance(patch_str, str):
        return []

    hunks = []
    file_chunks = [c for c in RE_FILE_DIFF.split(patch_str) if c.strip()]

    overall_hunk_idx = 0
    for chunk in file_chunks:
        m_file = RE_FILE_HEADER.search(chunk)
        if not m_file:
            continue
        file_path = m_file.group(2).strip()

        # Encontra todos os blocos de hunk dentro do arquivo
        matches = list(RE_HUNK_HEADER.finditer(chunk))
        for i, m in enumerate(matches):
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) else 1
            header_context = m.group(5).strip()

            # Conteúdo do hunk entre este cabeçalho e o próximo (ou fim do chunk)
            start_pos = m.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(chunk)
            body = chunk[start_pos:end_pos]

            lines_added = sum(1 for line in body.splitlines() if line.startswith("+") and not line.startswith("+++"))
            lines_removed = sum(1 for line in body.splitlines() if line.startswith("-") and not line.startswith("---"))

            hunks.append({
                "file_path": file_path,
                "hunk_idx_in_file": i,
                "hunk_idx_global": overall_hunk_idx,
                "old_start": old_start,
                "old_count": old_count,
                "new_start": new_start,
                "new_count": new_count,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "hunk_size": lines_added + lines_removed,
                "header_context": header_context,
            })
            overall_hunk_idx += 1

    return hunks


def compute_gold_alignment(agent_hunk: dict, gold_hunks: list[dict], line_tolerance: int = 15) -> dict:
    """
    Compara um hunk do agente com a lista de hunks do Gold Patch humano.
    Retorna se o arquivo está no gold patch e se há sobreposição de linhas.
    """
    gold_files = {gh["file_path"] for gh in gold_hunks}
    hunk_file = agent_hunk["file_path"]

    in_gold_file = 1 if hunk_file in gold_files else 0
    if not in_gold_file:
        return {
            "in_gold_file": 0,
            "overlaps_gold_hunk": 0,
            "min_distance_to_gold": 999999,
            "is_pertinent": 0,       # Fora do escopo humano
            "is_spurious": 1         # Hunk alucinado/desnecessário
        }

    # Procura sobreposição de linhas no mesmo arquivo
    agent_start = agent_hunk["new_start"]
    agent_end = agent_start + max(1, agent_hunk["new_count"])

    overlaps = 0
    min_dist = 999999

    for gh in gold_hunks:
        if gh["file_path"] != hunk_file:
            continue
        g_start = gh["new_start"]
        g_end = g_start + max(1, gh["new_count"])

        # Distância entre intervalos [agent_start, agent_end] e [g_start, g_end]
        if agent_end < g_start:
            dist = g_start - agent_end
        elif g_end < agent_start:
            dist = agent_start - g_end
        else:
            dist = 0  # Há sobreposição direta

        min_dist = min(min_dist, dist)
        if dist <= line_tolerance:
            overlaps = 1

    is_pertinent = 1 if overlaps else 0
    return {
        "in_gold_file": 1,
        "overlaps_gold_hunk": overlaps,
        "min_distance_to_gold": min_dist,
        "is_pertinent": is_pertinent,
        "is_spurious": 1 - is_pertinent
    }


# ==============================================================================
# 2. SINAIS DE TRAJETÓRIA (FEATURE ENGINEERING)
# ==============================================================================

RE_CODE_BLOCK = re.compile(r"```(?:[a-zA-Z]*)\n(.*?)```", re.S)
RE_TEST_CMD = re.compile(r"\b(pytest|unittest|tox|python\s+\S*(test|reproduce)\S*)", re.I)
RE_READ_CMD = re.compile(r"\b(open|goto|scroll_down|scroll_up|cat|head|tail|less|view_file)\b")
RE_EDIT_CMD = re.compile(r"\b(edit|create|insert|replace|sed)\b")
RE_ERROR_HINT = re.compile(r"\b(error|exception|traceback|failed|syntaxerror|nameerror|attributeerror)\b", re.I)

def extract_command_from_text(text: str) -> str:
    """Extrai o último bloco de comando executado em um turno de role ai."""
    blocks = RE_CODE_BLOCK.findall(text or "")
    return blocks[-1].strip() if blocks else ""

def parse_trajectory_steps(traj_raw) -> list[dict]:
    """Uniformiza a trajetória em lista de passos com turno, comando e se houve erro."""
    if isinstance(traj_raw, str):
        try:
            steps_data = json.loads(traj_raw)
        except Exception:
            return []
    else:
        steps_data = traj_raw or []

    parsed = []
    for step in steps_data:
        role = step.get("role", "")
        text = str(step.get("text", ""))
        cmd = extract_command_from_text(text) if role == "ai" else ""
        has_error = bool(RE_ERROR_HINT.search(text)) if role == "user" else False

        parsed.append({
            "role": role,
            "text": text,
            "cmd": cmd,
            "has_error": has_error
        })
    return parsed

def compute_hunk_trajectory_features(file_path: str, steps: list[dict]) -> dict:
    """
    Analisa os passos da trajetória em relação a um arquivo específico do patch.
    Calcula:
      - read_before_write: leu o arquivo antes da 1ª edição?
      - edit_churn: quantas edições no arquivo ao longo da trajetória?
      - post_edit_verification: rodou teste após a última edição no arquivo?
      - error_preceded_edit: o passo anterior à edição foi um erro?
      - last_edit_step_ratio: em que ponto (0.0 a 1.0) ocorreu a última edição?
    """
    basename = os.path.basename(file_path)
    total_steps = len(steps)
    if total_steps == 0:
        return {
            "read_before_write": 0,
            "edit_churn": 0,
            "post_edit_verification": 0,
            "error_preceded_edit": 0,
            "last_edit_step_ratio": 0.0
        }

    first_edit_step = None
    last_edit_step = None
    edit_count = 0
    read_before = 0
    error_preceded = 0

    for idx, s in enumerate(steps):
        cmd = s["cmd"]
        text = s["text"]

        touches_file = (file_path in cmd) or (basename in cmd) or (file_path in text) or (basename in text)
        is_edit = bool(RE_EDIT_CMD.search(cmd)) and touches_file
        is_read = bool(RE_READ_CMD.search(cmd)) and touches_file

        if is_read and first_edit_step is None:
            read_before = 1

        if is_edit:
            edit_count += 1
            if first_edit_step is None:
                first_edit_step = idx
                # Checa se o turno anterior de 'user' continha erro
                if idx > 0 and steps[idx - 1]["has_error"]:
                    error_preceded = 1
            last_edit_step = idx

    # Verificação pós-edição: o agente rodou teste após o last_edit_step?
    tested_after = 0
    if last_edit_step is not None:
        for idx in range(last_edit_step + 1, total_steps):
            if bool(RE_TEST_CMD.search(steps[idx]["cmd"])):
                tested_after = 1
                break

    last_step_ratio = (last_edit_step / total_steps) if last_edit_step is not None else 0.0

    return {
        "read_before_write": read_before,
        "edit_churn": edit_count,
        "post_edit_verification": tested_after,
        "error_preceded_edit": error_preceded,
        "last_edit_step_ratio": round(last_step_ratio, 3)
    }


# ==============================================================================
# 3. PIPELINE CONSOLIDADO DE EXTRAÇÃO
# ==============================================================================

def build_gold_patch_map() -> dict[str, str]:
    """Carrega os patches oficiais de referência (Gold Patches) dos datasets locais."""
    print("-> Carregando Gold Patches dos benchmarks de referência...")
    gold_map = {}

    # 1. SWE-rebench (split test)
    try:
        rebench = load_dataset("nebius/SWE-rebench", split="test")
        for item in rebench:
            if item.get("patch"):
                gold_map[item["instance_id"]] = item["patch"]
        print(f"   [SWE-rebench] {len(gold_map)} gold patches carregados.")
    except Exception as e:
        print(f"   Aviso ao carregar SWE-rebench: {e}")

    # 2. SWE-bench-extra (split train)
    try:
        extra = load_dataset("nebius/SWE-bench-extra", split="train")
        extra_count = 0
        for item in extra:
            inst = item.get("instance_id")
            if inst and inst not in gold_map and item.get("patch"):
                gold_map[inst] = item["patch"]
                extra_count += 1
        print(f"   [SWE-bench-extra] +{extra_count} gold patches adicionados. Total: {len(gold_map)}")
    except Exception as e:
        print(f"   Aviso ao carregar SWE-bench-extra: {e}")

    return gold_map


def extract_features(num_trajectories: int = 300, output_csv=RAIZ / "dados" / "hunk_features_dataset.csv"):
    """Executa a extração em nível de hunk sobre N trajetórias do dataset público."""
    gold_map = build_gold_patch_map()

    print(f"\n-> Carregando {num_trajectories} trajetórias de 'nebius/SWE-agent-trajectories' via streaming...")
    stream = load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True)
    traj_samples = list(stream.take(num_trajectories))

    dataset_rows = []
    instances_with_patch = 0
    total_hunks_extracted = 0

    for row_idx, item in enumerate(traj_samples):
        instance_id = item["instance_id"]
        agent_patch = item.get("generated_patch")
        if not agent_patch:
            continue

        instances_with_patch += 1
        gold_patch = gold_map.get(instance_id, "")
        gold_hunks = parse_patch_hunks(gold_patch) if gold_patch else []

        agent_hunks = parse_patch_hunks(agent_patch)
        if not agent_hunks:
            continue

        steps = parse_trajectory_steps(item.get("trajectory"))

        for hunk in agent_hunks:
            total_hunks_extracted += 1
            # 1. Alinhamento com Gold Patch (Ground Truth)
            gold_metrics = compute_gold_alignment(hunk, gold_hunks, line_tolerance=15)

            # 2. Sinais de Trajetória do Hunk
            traj_metrics = compute_hunk_trajectory_features(hunk["file_path"], steps)

            dataset_rows.append({
                "instance_id": instance_id,
                "model_name": item.get("model_name", "unknown"),
                "task_resolved": bool(item.get("target")),
                "file_path": hunk["file_path"],
                "hunk_idx_global": hunk["hunk_idx_global"],
                # Baselines
                "hunk_size": hunk["hunk_size"],
                "lines_added": hunk["lines_added"],
                "lines_removed": hunk["lines_removed"],
                # Trajectory features
                "read_before_write": traj_metrics["read_before_write"],
                "edit_churn": traj_metrics["edit_churn"],
                "post_edit_verification": traj_metrics["post_edit_verification"],
                "error_preceded_edit": traj_metrics["error_preceded_edit"],
                "last_edit_step_ratio": traj_metrics["last_edit_step_ratio"],
                # Ground truth labels
                "in_gold_file": gold_metrics["in_gold_file"],
                "overlaps_gold_hunk": gold_metrics["overlaps_gold_hunk"],
                "min_distance_to_gold": gold_metrics["min_distance_to_gold"],
                "is_pertinent": gold_metrics["is_pertinent"],
                "is_spurious": gold_metrics["is_spurious"],
            })

    df = pd.DataFrame(dataset_rows)
    df.to_csv(output_csv, index=False)
    print(f"\n Concluído com sucesso!")
    print(f"   Tarefas com patch gerado: {instances_with_patch}")
    print(f"   Total de hunks individuais extraídos: {total_hunks_extracted}")
    print(f"   Dataset salvo em: {output_csv}")

    # Resumo analítico
    if not df.empty:
        print("\n--- Estatísticas Preliminares do Dataset de Hunks ---")
        print(f"Taxa de hunks espúrios (fora de escopo/alucinados): {round(df['is_spurious'].mean() * 100, 1)}%")
        print(f"Taxa de hunks pertinentes (alinhados ao Gold Patch): {round(df['is_pertinent'].mean() * 100, 1)}%")
        print("\nSinais da trajetória vs Pertinência do Hunk (Médias):")
        signals = ["read_before_write", "post_edit_verification", "error_preceded_edit", "last_edit_step_ratio", "hunk_size"]
        print(df.groupby("is_spurious")[signals].mean().T)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    n_traj = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    extract_features(num_trajectories=n_traj, output_csv=RAIZ / "dados" / "hunk_features_dataset.csv")
