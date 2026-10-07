"""
Protótipo do Revisor Inteligente de Patches (Diff Risk Inspector)

Projeto: Priorização de Hunks em Patches Gerados por Agentes de IA via Sinais de Trajetória
Autor: Giorgio Nicolas de A. Bertino (CDIA — UFPB)
Data: Outubro/2026

Objetivo:
Receber um patch gerado por agente e o histórico de passos (trajetória),
avaliar cada bloco de alteração (hunk) segundo os sinais empíricos de risco/proteção,
e exibir uma ordenação visual com diagnósticos em linguagem natural:
  🟢 [NÚCLEO CONFIÁVEL / REVISE PRIMEIRO]
  🟡 [RISCO MODERADO]
  🔴 [ALERTA DE ALUCINAÇÃO / DESVIO DE ESCOPO]
"""

import json
import os
import re
import sys
import pandas as pd

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
from datasets import load_dataset

# Garante suporte UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from extract_hunk_features import (
    parse_patch_hunks,
    parse_trajectory_steps,
    compute_hunk_trajectory_features,
    compute_gold_alignment,
    build_gold_patch_map
)

# Cores ANSI para o terminal
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

def calculate_hunk_risk_score(traj_metrics: dict, hunk: dict) -> tuple[float, list[str]]:
    """
    Calcula uma pontuação de risco (0 a 100) baseada nos coeficientes empíricos
    descobertos na pesquisa, e lista os fatores de diagnóstico.
    """
    reasons = []
    
    # Base de risco: 50%
    score = 50.0

    # 1. Leitura prévia (Forte proteção: reduz ~40 pontos de risco)
    if traj_metrics["read_before_write"]:
        score -= 40.0
        reasons.append("✅ Arquivo inspecionado pelo agente antes da edição.")
    else:
        score += 35.0
        reasons.append("⚠️ EDIÇÃO ÀS CEGAS: O agente nunca abriu este arquivo antes de alterar!")

    # 2. Erro precedente (Alto risco: aumenta ~30 pontos de risco)
    if traj_metrics["error_preceded_edit"]:
        score += 30.0
        reasons.append("🚨 GERADO SOB ERRO: O passo anterior à edição falhou no terminal (crash/exceção).")

    # 3. Retrabalho de edições (churn)
    if traj_metrics["edit_churn"] > 3:
        score += 15.0
        reasons.append(f"⚠️ Alto retrabalho: arquivo reeditado {traj_metrics['edit_churn']} vezes.")
    elif traj_metrics["edit_churn"] == 1:
        reasons.append("✅ Edição atômica e direta (apenas 1 ciclo de modificação).")

    # 4. Verificação posterior por testes
    if traj_metrics["post_edit_verification"]:
        score -= 15.0
        reasons.append("✅ O agente executou testes após a última alteração neste arquivo.")
    else:
        score += 10.0
        reasons.append("⚠️ Sem validação posterior: nenhum teste executado após a alteração.")

    # 5. Tamanho excessivo (hunks gigantescos)
    if hunk["hunk_size"] > 40:
        score += 10.0
        reasons.append(f"⚠️ Volume elevado: hunk com {hunk['hunk_size']} linhas modificadas.")

    # Limita entre 0 e 100
    final_score = max(0.0, min(100.0, score))
    return round(final_score, 1), reasons


def inspect_instance_patch(instance_id: str, gold_map: dict = None, generate_html: bool = True):
    """Analisa uma instância específica do dataset e gera o relatório do revisor."""
    print(f"\n{BOLD}{BLUE}========================================================================={RESET}")
    print(f"{BOLD}🔍 INSPECIONANDO PATCH DO AGENTE: {instance_id}{RESET}")
    print(f"{BOLD}{BLUE}========================================================================={RESET}")

    if gold_map is None:
        gold_map = build_gold_patch_map()

    # Busca a trajetória no dataset
    print(f"Buscando trajetória de '{instance_id}' no dataset...")
    stream = load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True)
    target_item = None
    for item in stream.take(500):
        if item["instance_id"] == instance_id:
            target_item = item
            break

    if not target_item:
        print(f"{RED}Instância '{instance_id}' não encontrada na amostra.{RESET}")
        return

    agent_patch = target_item.get("generated_patch", "")
    if not agent_patch:
        print(f"{YELLOW}Esta instância não gerou patch final.{RESET}")
        return

    steps = parse_trajectory_steps(target_item.get("trajectory"))
    hunks = parse_patch_hunks(agent_patch)
    gold_patch = gold_map.get(instance_id, "")
    gold_hunks = parse_patch_hunks(gold_patch) if gold_patch else []

    print(f"• Total de passos na trajetória: {len(steps)}")
    print(f"• Hunks individuais encontrados no patch: {len(hunks)}")
    print(f"• Resolveu a tarefa oficialmente? {'SIM' if target_item.get('target') else 'NÃO'}\n")

    # Avalia cada hunk
    evaluated_hunks = []
    for h in hunks:
        traj_m = compute_hunk_trajectory_features(h["file_path"], steps)
        gold_m = compute_gold_alignment(h, gold_hunks, line_tolerance=15)
        risk_score, reasons = calculate_hunk_risk_score(traj_m, h)

        evaluated_hunks.append({
            "hunk": h,
            "traj_metrics": traj_m,
            "gold_metrics": gold_m,
            "risk_score": risk_score,
            "reasons": reasons
        })

    # Ordena os hunks: os mais confiáveis primeiro (menor risco) ou os mais urgentes de revisão
    # Para o revisor, destacamos primeiro os blocos com alta confiabilidade para revisão de negócio,
    # e alertamos em separado os que têm alto risco de alucinação.
    evaluated_hunks.sort(key=lambda x: x["risk_score"])

    # Exibição no Terminal
    for idx, eh in enumerate(evaluated_hunks):
        h = eh["hunk"]
        score = eh["risk_score"]
        is_spurious_real = eh["gold_metrics"]["is_spurious"]

        if score < 35:
            badge = f"{GREEN}[🟢 CONFIÁVEL / REVISE PRIMEIRO]{RESET}"
        elif score < 65:
            badge = f"{YELLOW}[🟡 ATENÇÃO / RISCO MODERADO]{RESET}"
        else:
            badge = f"{RED}[🔴 ALERTA DE ALUCINAÇÃO / FORA DE ESCOPO]{RESET}"

        real_verdict = f"{RED}(Realidade: ESPÚRIO){RESET}" if is_spurious_real else f"{GREEN}(Realidade: PERTINENTE AO BUG){RESET}"

        print(f"{BOLD}--- Hunk #{h['hunk_idx_global'] + 1} em: {h['file_path']} (Linha {h['new_start']}) ---{RESET}")
        print(f"Status Previsto: {badge}  |  Score de Risco: {BOLD}{score}/100{RESET}  |  {real_verdict}")
        print(f"Dimensões: +{h['lines_added']} / -{h['lines_removed']} linhas (Tamanho total: {h['hunk_size']})")
        print("Diagnósticos da Trajetória:")
        for r in eh["reasons"]:
            print(f"   {r}")
        print()

    # Gera HTML interativo se solicitado
    if generate_html:
        generate_html_report(instance_id, evaluated_hunks, agent_patch)


def generate_html_report(instance_id: str, evaluated_hunks: list, patch_str: str):
    """Gera visualização HTML do protótipo com realce de diff e badges."""
    html_hunks = ""
    for eh in evaluated_hunks:
        h = eh["hunk"]
        score = eh["risk_score"]
        is_sp = eh["gold_metrics"]["is_spurious"]
        
        badge_class = "badge-safe" if score < 35 else ("badge-warn" if score < 65 else "badge-danger")
        badge_text = "🟢 CONFIÁVEL / NÚCLEO" if score < 35 else ("🟡 MODERADO" if score < 65 else "🔴 ALTO RISCO DE ALUCINAÇÃO")
        real_text = "ALUCINADO / FORA DE ESCOPO" if is_sp else "PERTINENTE AO BUG HUMANO"
        real_class = "badge-danger" if is_sp else "badge-safe"

        reasons_li = "".join(f"<li>{r}</li>" for r in eh["reasons"])

        html_hunks += f"""
        <div class="hunk-card">
          <div class="hunk-header">
            <div>
              <span class="file-tag">{h['file_path']}</span>
              <span style="color: #94a3b8; font-size: 0.85rem;">Linhas +{h['new_start']} ({h['lines_added']} adicionadas, {h['lines_removed']} removidas)</span>
            </div>
            <div>
              <span class="{badge_class}">{badge_text} ({score}/100)</span>
              <span class="{real_class}" style="margin-left: 0.5rem;">Ground Truth: {real_text}</span>
            </div>
          </div>
          <ul class="diag-list">
            {reasons_li}
          </ul>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Revisor Inteligente — {instance_id}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 2rem; line-height: 1.5; }}
  .container {{ max-width: 950px; margin: 0 auto; }}
  h1 {{ color: #38bdf8; font-size: 1.8rem; margin-bottom: 0.3rem; }}
  .subtitle {{ color: #94a3b8; margin-bottom: 2rem; }}
  .hunk-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; margin-bottom: 1.5rem; padding: 1.2rem; }}
  .hunk-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 0.8rem; margin-bottom: 0.8rem; flex-wrap: wrap; gap: 0.5rem; }}
  .file-tag {{ background: #0284c7; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-family: monospace; font-size: 0.9rem; margin-right: 0.5rem; }}
  .badge-safe {{ background: rgba(52, 211, 153, 0.2); color: #34d399; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; }}
  .badge-warn {{ background: rgba(251, 191, 36, 0.2); color: #fbbf24; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; }}
  .badge-danger {{ background: rgba(248, 113, 113, 0.2); color: #f87171; padding: 3px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; }}
  .diag-list {{ list-style: none; padding-left: 0; margin-top: 0.5rem; font-size: 0.95rem; }}
  .diag-list li {{ padding: 0.2rem 0; }}
</style>
</head>
<body>
<div class="container">
  <h1>🛡️ Protótipo: Revisor Inteligente de Hunks</h1>
  <div class="subtitle">Instância: <strong>{instance_id}</strong> • Ordenação inteligente por Sinais de Trajetória</div>
  {html_hunks}
</div>
</body>
</html>"""

    output_path = RAIZ / "resultados" / "prototipos" / f"prototipo_inspecao_{instance_id}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{GREEN}Relatório interativo do protótipo salvo em: {output_path}{RESET}")


if __name__ == "__main__":
    # Teste no caso emblemático que analisamos: AnalogJ__lexicon-336
    target_id = sys.argv[1] if len(sys.argv) > 1 else "AnalogJ__lexicon-336"
    inspect_instance_patch(target_id)
