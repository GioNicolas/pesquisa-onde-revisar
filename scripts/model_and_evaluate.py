"""
Modelagem Estatística e Curvas de Esforço de Inspeção (AUCEC) — Fase 3

Projeto: Priorização de Hunks em Patches Gerados por Agentes de IA via Sinais de Trajetória
Autor: Giorgio Nicolas de A. Bertino (CDIA — UFPB)
Data: Outubro/2026

Objetivo:
1. Treinar modelos de classificação sob validação cruzada agrupada por instância (GroupKFold)
   para prevenir vazamento de dados entre hunks do mesmo patch.
2. Comparar os sinais de trajetória contra baselines clássicos de revisão de código:
   - Random (aleatório)
   - Diff Order (ordem natural de leitura do git diff)
   - Hunk Size (heurística do revisor humano: 'olhar os maiores blocos primeiro')
3. Construir as Curvas de Esforço de Inspeção (Cost-Effectiveness Curves) e calcular o AUCEC.
4. Calcular Recall@20% e Recall@30% de inspeção.
5. Salvar gráfico comparativo 'curva_esforco_inspecao.png'.
"""

import numpy as np
import pandas as pd

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

def compute_aucec_curve(y_true: np.ndarray, scores: np.ndarray):
    """
    Calcula a curva de esforço de inspeção:
    Eixo X: fração acumulada de hunks inspecionados (0.0 a 1.0).
    Eixo Y: fração acumulada de hunks problemáticos encontrados (0.0 a 1.0).
    Retorna (x_vals, y_vals, aucec_score).
    """
    # Ordena os hunks em ordem decrescente de pontuação de suspeita
    order = np.argsort(-scores)
    y_sorted = y_true[order]

    total_bugs = np.sum(y_true)
    if total_bugs == 0:
        return np.linspace(0, 1, len(y_true)), np.linspace(0, 1, len(y_true)), 0.5

    cum_bugs = np.cumsum(y_sorted) / total_bugs
    cum_effort = np.arange(1, len(y_true) + 1) / len(y_true)

    # Adiciona ponto de origem (0, 0)
    x = np.concatenate([[0.0], cum_effort])
    y = np.concatenate([[0.0], cum_bugs])

    # AUCEC via regra trapezoidal (compatível com NumPy 2.x e 1.x)
    if hasattr(np, "trapezoid"):
        aucec = np.trapezoid(y, x)
    else:
        aucec = np.trapz(y, x)
    return x, y, aucec

def evaluate_models(csv_path=RAIZ / "dados" / "hunk_features_dataset.csv"):
    df = pd.read_csv(csv_path)
    print(f"Dataset carregado: {len(df)} hunks distribuídos em {df['instance_id'].nunique()} instâncias.")

    target = "is_spurious"
    y = df[target].values

    # Features puras de trajetória
    traj_features = [
        "read_before_write",
        "error_preceded_edit",
        "post_edit_verification",
        "last_edit_step_ratio",
        "edit_churn"
    ]

    # Prepara validação cruzada agrupada por instância para evitar vazamento
    gkf = GroupKFold(n_splits=5)
    groups = df["instance_id"].values

    # Arrays para armazenar predições Out-Of-Fold (OOF)
    oof_lr = np.zeros(len(df))
    oof_rf = np.zeros(len(df))

    X_traj = df[traj_features].fillna(0).values

    for train_idx, val_idx in gkf.split(X_traj, y, groups=groups):
        X_tr, y_tr = X_traj[train_idx], y[train_idx]
        X_va = X_traj[val_idx]

        # 1. Regressão Logística (sinais de trajetória puros)
        clf_lr = LogisticRegression(class_weight="balanced", random_state=42)
        clf_lr.fit(X_tr, y_tr)
        oof_lr[val_idx] = clf_lr.predict_proba(X_va)[:, 1]

        # 2. Random Forest (sinais de trajetória puros)
        clf_rf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42, class_weight="balanced")
        clf_rf.fit(X_tr, y_tr)
        oof_rf[val_idx] = clf_rf.predict_proba(X_va)[:, 1]

    # Definição dos Baselines
    np.random.seed(42)
    scores_dict = {
        "Random (Sorteio)": np.random.rand(len(df)),
        "Diff Order (Sequencial)": -df["hunk_idx_global"].values, # 1º hunk revisado primeiro
        "Hunk Size (Maior Primeiro)": df["hunk_size"].values,      # Heurística ingênua comum
        "Trajetória (Regressão Logística)": oof_lr,
        "Trajetória (Random Forest)": oof_rf,
    }

    results = []
    curves = {}

    print("\n" + "="*70)
    print(f"{'Estratégia de Priorização':<32} | {'AUCEC':<8} | {'ROC-AUC':<8} | {'Recall@20%':<10} | {'Recall@30%'}")
    print("="*70)

    for name, scores in scores_dict.items():
        x_c, y_c, aucec = compute_aucec_curve(y, scores)
        curves[name] = (x_c, y_c)
        roc = roc_auc_score(y, scores)

        # Recall inspecionando apenas os primeiros 20% e 30% dos hunks
        k20 = int(0.20 * len(df))
        k30 = int(0.30 * len(df))
        order = np.argsort(-scores)
        recall_20 = np.sum(y[order[:k20]]) / np.sum(y) * 100
        recall_30 = np.sum(y[order[:k30]]) / np.sum(y) * 100

        results.append({
            "Estratégia": name,
            "AUCEC": round(aucec, 3),
            "ROC-AUC": round(roc, 3),
            "Recall@20%": f"{recall_20:.1f}%",
            "Recall@30%": f"{recall_30:.1f}%"
        })
        print(f"{name:<32} | {aucec:<8.3f} | {roc:<8.3f} | {recall_20:>9.1f}% | {recall_30:>9.1f}%")

    print("="*70)

    # Gera gráfico das curvas de esforço de inspeção
    plt.figure(figsize=(9, 7))
    colors = {
        "Random (Sorteio)": "#95a5a6",
        "Diff Order (Sequencial)": "#7f8c8d",
        "Hunk Size (Maior Primeiro)": "#e67e22",
        "Trajetória (Regressão Logística)": "#2980b9",
        "Trajetória (Random Forest)": "#27ae60",
    }
    linestyles = {
        "Random (Sorteio)": "--",
        "Diff Order (Sequencial)": ":",
        "Hunk Size (Maior Primeiro)": "-.",
        "Trajetória (Regressão Logística)": "-",
        "Trajetória (Random Forest)": "-",
    }

    for name, (x_c, y_c) in curves.items():
        plt.plot(x_c * 100, y_c * 100, label=f"{name}", color=colors[name],
                 linestyle=linestyles[name], linewidth=2.2 if "Trajetória" in name else 1.5)

    # Marcação da linha de 20% de inspeção
    plt.axvline(x=20, color="red", linestyle=":", alpha=0.6, label="20% de Esforço de Inspeção")
    plt.title("Curva de Esforço de Inspeção (Cost-Effectiveness Curve)\nPriorização de Hunks em Patches de Agentes de IA", fontsize=12, fontweight="bold")
    plt.xlabel("% Acumulada de Hunks Inspecionados pelo Revisor", fontsize=11)
    plt.ylabel("% Acumulada de Hunks Problemáticos/Espúrios Detectados", fontsize=11)
    plt.xlim(0, 100)
    plt.ylim(0, 100)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.legend(loc="lower right", fontsize=10)
    plt.tight_layout()

    chart_file = RAIZ / "resultados" / "figuras" / "curva_esforco_inspecao.png"
    plt.savefig(chart_file, dpi=180)
    print(f"\n Gráfico salvo com sucesso: {chart_file}")

    # Salva resumo em CSV
    res_df = pd.DataFrame(results)
    res_df.to_csv(RAIZ / "resultados" / "metricas_avaliacao_modelos.csv", index=False)
    print(" Métricas salvas em: resultados/metricas_avaliacao_modelos.csv")

    # Exibe coeficientes da Regressão Logística para interpretabilidade
    print("\n--- Coeficientes do Modelo Linear (Importância das Pistas) ---")
    final_lr = LogisticRegression(class_weight="balanced", random_state=42)
    final_lr.fit(X_traj, y)
    coefs = pd.Series(final_lr.coef_[0], index=traj_features).sort_values(ascending=False)
    for feat, coef in coefs.items():
        interpretacao = "Aumenta probabilidade de erro (ARRISCADO)" if coef > 0 else "Reduz probabilidade de erro (PROTETIVO)"
        print(f"  • {feat:<24}: {coef:>6.3f}  -> {interpretacao}")

if __name__ == "__main__":
    evaluate_models()
