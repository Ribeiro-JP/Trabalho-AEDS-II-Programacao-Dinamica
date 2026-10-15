"""Módulo para geração e plotagem dos gráficos científicos de experimentos (AEDS-II).

Convenções Obrigatórias:
1. Resolução: PNG a 200 DPI salvos de forma sincronizada em:
   - 'docs/figures/'
   - 'relatorio/figuras/'
   - 'web/figures/'
2. Textos e rótulos: 100% em Português do Brasil com rigor terminológico acadêmico.
3. Estilo Visual: Dark Slate moderno, alto contraste e padrão editorial científico.
4. Fidelidade aos Dados: Proibido suavizar artificialmente ou adulterar pontos observados.
   As curvas refletem dados reais agregados (trimmed mean) com bandas de incerteza (std).
5. Limpeza Visual: ZERO caixas de texto com parágrafos explicativos sobre as curvas.
   Apenas títulos objetivos, eixos com grandezas explícitas e unidades (ns, µs, ms, s, KB, MB, %),
   legendas desobstruídas e grades suaves.
"""

from __future__ import annotations

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Diretórios do projeto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
DOCS_FIGURES_DIR = os.path.join(ROOT_DIR, "docs", "figures")
RELATORIO_FIGURES_DIR = os.path.join(ROOT_DIR, "relatorio", "figuras")
WEB_FIGURES_DIR = os.path.join(ROOT_DIR, "web", "figures")

# Paleta oficial padronizada de alto contraste
PALETTE: dict[str, str] = {
    "naive": "#ef4444",         # Vermelho Alerta (Força Bruta Exponencial)
    "memo": "#0284c7",          # Azul Ciano (Top-Down com Memoização)
    "memo_warm": "#06b6d4",     # Ciano Suave (Consulta Cache O(1))
    "bottom_up": "#16a34a",     # Verde Esmeralda (Bottom-Up Tabulação)
    "bottom_up_cpp": "#f59e0b", # Âmbar/Dourado (C++ Nativo -O3)
    "two_rows": "#9333ea",      # Roxo Técnico (Otimização de Duas Linhas)
    "one_row": "#9333ea",       # Roxo Técnico (Vetor 1D)
    "o1_space": "#a855f7",      # Púrpura Claro (Espaço O(1))
    "greedy": "#94a3b8",        # Cinza/Ardósia (Heurística Gulosa)
    "catalan": "#ec4899",       # Rosa Técnico (Combinatória de Catalan)
    "reference": "#38bdf8",     # Azul Céu (Referência Ótima)
}


def setup_theme() -> None:
    """Configura o tema Dark Slate editorial e parâmetros globais do matplotlib."""
    plt.rcParams.update({
        "figure.facecolor": "#0f172a",
        "axes.facecolor": "#1e293b",
        "axes.edgecolor": "#475569",
        "axes.labelcolor": "#f8fafc",
        "xtick.color": "#cbd5e1",
        "ytick.color": "#cbd5e1",
        "text.color": "#f8fafc",
        "grid.color": "#334155",
        "grid.alpha": 0.45,
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "font.family": "sans-serif",
        "font.size": 9.5,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.0,
        "axes.labelweight": "semibold",
        "legend.facecolor": "#1e293b",
        "legend.edgecolor": "#475569",
        "legend.fontsize": 9.0,
        "legend.framealpha": 0.95,
        "figure.dpi": 200,
        "savefig.dpi": 200,
    })


def save_figure(fig: plt.Figure, canonical_filename: str, aliases: list[str] | None = None) -> None:
    """Salva a figura a 200 DPI em docs/figures/, relatorio/figuras/ e web/figures/."""
    os.makedirs(DOCS_FIGURES_DIR, exist_ok=True)
    os.makedirs(RELATORIO_FIGURES_DIR, exist_ok=True)
    os.makedirs(WEB_FIGURES_DIR, exist_ok=True)

    filenames = [canonical_filename] + (aliases or [])

    for fname in filenames:
        dest_docs = os.path.join(DOCS_FIGURES_DIR, fname)
        dest_relatorio = os.path.join(RELATORIO_FIGURES_DIR, fname)
        dest_web = os.path.join(WEB_FIGURES_DIR, fname)

        fig.savefig(dest_docs, dpi=200, bbox_inches="tight")
        fig.savefig(dest_relatorio, dpi=200, bbox_inches="tight")
        fig.savefig(dest_web, dpi=200, bbox_inches="tight")

    plt.close(fig)
    print(f"      [FIG] Salvo: {canonical_filename} (e {len(aliases or [])} aliases) em docs, relatorio e web.")


def load_dataset(filename: str, required_cols: list[str] | None = None) -> pd.DataFrame | None:
    """Carrega dataset CSV com validação explícita de colunas e existência de arquivo."""
    filepath = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"      [AVISO] Arquivo '{filename}' não encontrado em {RESULTS_DIR}.")
        return None

    try:
        df = pd.read_csv(filepath)
    except Exception as err:
        print(f"      [ERRO] Falha ao carregar '{filename}': {err}")
        return None

    if required_cols:
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"      [ERRO] Colunas obrigatórias ausentes em '{filename}': {missing}")
            return None

    return df


# -----------------------------------------------------------------------------
# 1. Experimento E1: Fibonacci
# -----------------------------------------------------------------------------
def plot_e1_fibonacci_tempo() -> None:
    """E1: Fibonacci - Tempo geral em escala logarítmica (Força Bruta vs PD)."""
    df = load_dataset("e1_fibonacci.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e1_fibonacci.csv não encontrado. Execute: benchmarks/run_benchmarks.py --only E1")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")
    df_valid = df_valid.dropna(subset=["time_seconds"])

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("naive", "Força Bruta (Naive, Θ(φⁿ))", PALETTE["naive"]),
        ("memo", "Memoização (Top-Down, Θ(n))", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up, Θ(n))", PALETTE["bottom_up"]),
        ("o1_space", "Espaço O(1) (Iterativo, Θ(n))", PALETTE["o1_space"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["time_seconds"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-8, top=5.0)
    ax.set_title("E1: Fibonacci — Tempo de Execução vs. Termo n")
    ax.set_xlabel("Índice do Termo na Sequência (n)")
    ax.set_ylabel("Tempo de Execução (s, escala log)")
    ax.grid(True)
    ax.legend(loc="lower right")

    fig.tight_layout()
    save_figure(fig, "e1_fibonacci_tempo.png", aliases=["e1_fibonacci.png"])


def plot_e1_fibonacci_dp() -> None:
    """E1: Fibonacci - Comparação fina das abordagens de PD em escala linear (µs)."""
    df = load_dataset("e1_fibonacci.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e1_fibonacci.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_us"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce") * 1e6
    df_valid = df_valid.dropna(subset=["time_us"])

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("memo", "Memoização (Top-Down, do zero)", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up)", PALETTE["bottom_up"]),
        ("o1_space", "Espaço O(1)", PALETTE["o1_space"]),
        ("memo_warm", "Memoização (Consulta Cache O(1))", PALETTE["memo_warm"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["time_us"],
            label=label, color=color, linestyle="-",
            marker="s", markersize=3.5, linewidth=2.0
        )
        if "time_std" in sub.columns:
            std_us = pd.to_numeric(sub["time_std"], errors="coerce").fillna(0.0) * 1e6
            ax.fill_between(
                sub["n"],
                np.maximum(0, sub["time_us"] - std_us),
                sub["time_us"] + std_us,
                color=color, alpha=0.15
            )

    ax.set_title("E1: Fibonacci — Comparação Fina das Variantes de Programação Dinâmica")
    ax.set_xlabel("Índice do Termo na Sequência (n)")
    ax.set_ylabel("Tempo Médio de Execução (µs, escala linear)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e1_fibonacci_dp.png")


def plot_e1_fibonacci_chamadas() -> None:
    """E1: Fibonacci - Contagem de chamadas recursivas e subproblemas resolvidos."""
    df = load_dataset("e1_fibonacci.csv", ["approach", "n", "calls", "status"])
    if df is None:
        raise FileNotFoundError("e1_fibonacci.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["calls"] = pd.to_numeric(df_valid["calls"], errors="coerce")
    df_valid = df_valid.dropna(subset=["calls"])

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("naive", "Força Bruta (2F(n+1)−1 chamadas, Θ(φⁿ))", PALETTE["naive"]),
        ("memo", "Memoização (2n - 1 chamadas)", PALETTE["memo"]),
        ("bottom_up", "Tabulação (1 chamada / loop iterativo)", PALETTE["bottom_up"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["calls"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=0.8, top=1e8)
    ax.set_title("E1: Fibonacci — Quantidade de Chamadas de Função vs. Termo n")
    ax.set_xlabel("Índice do Termo na Sequência (n)")
    ax.set_ylabel("Invocações de Função (escala log)")
    ax.grid(True)
    ax.legend(loc="lower right")

    fig.tight_layout()
    save_figure(fig, "e1_fibonacci_chamadas.png")


def plot_e1_fibonacci_speedup() -> None:
    """E1: Fibonacci - Speedup empírico da Programação Dinâmica em relação à Força Bruta."""
    df = load_dataset("e1_fibonacci.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e1_fibonacci.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    naive_df = df_valid[df_valid["approach"] == "naive"].set_index("n")["time_seconds"]
    if naive_df.empty:
        return

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    dp_variants = [
        ("memo", "Speedup: Memoização / Naive", PALETTE["memo"]),
        ("bottom_up", "Speedup: Bottom-Up / Naive", PALETTE["bottom_up"]),
        ("o1_space", "Speedup: Espaço O(1) / Naive", PALETTE["o1_space"]),
    ]

    for app_id, label, color in dp_variants:
        sub = df_valid[df_valid["approach"] == app_id].set_index("n")["time_seconds"]
        common_ns = sorted(list(set(naive_df.index).intersection(set(sub.index))))
        if not common_ns:
            continue

        speedups = [naive_df.loc[n] / max(sub.loc[n], 1e-12) for n in common_ns]
        ax.plot(
            common_ns, speedups,
            label=label, color=color, linestyle="-",
            marker="^", markersize=4.0, linewidth=2.0
        )

    ax.set_yscale("log")
    ax.set_title("E1: Fibonacci — Fator de Aceleração (Speedup: T_naive / T_dp)")
    ax.set_xlabel("Índice do Termo na Sequência (n)")
    ax.set_ylabel("Speedup Relativo (vezes mais rápido, escala log)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e1_fibonacci_speedup.png")


# -----------------------------------------------------------------------------
# 2. Experimento E2: Rod Cutting
# -----------------------------------------------------------------------------
def plot_e2_rod_cutting_tempo() -> None:
    """E2: Corte de hastes - Tempo de execução dos algoritmos exatos."""
    df = load_dataset("e2_rod_cutting.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e2_rod_cutting.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("naive", "Força Bruta (Corte Exaustivo, Θ(2ⁿ))", PALETTE["naive"]),
        ("memo", "Memoização (Top-Down, Θ(n²))", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up, Θ(n²))", PALETTE["bottom_up"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["time_seconds"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-7, top=5.0)
    ax.set_title("E2: Corte de Hastes — Tempo de Execução vs. Comprimento (n)")
    ax.set_xlabel("Comprimento da Haste (n)")
    ax.set_ylabel("Tempo de Execução (s, escala log)")
    ax.grid(True)
    ax.legend(loc="lower right")

    fig.tight_layout()
    save_figure(fig, "e2_rod_cutting_tempo.png", aliases=["e2_rod_cutting.png"])


def plot_e2_rod_cutting_qualidade() -> None:
    """E2: Corte de hastes - Receita ótima vs heurística gulosa e erro relativo."""
    df = load_dataset("e2_rod_cutting.csv", ["approach", "n", "notes", "status"])
    if df is None:
        raise FileNotFoundError("e2_rod_cutting.csv não encontrado.")

    # Filtra registros com dados gulosos
    greedy_rows = df[df["approach"] == "greedy"].sort_values("n")
    if greedy_rows.empty:
        return

    import re
    ns = []
    opt_revs = []
    greedy_revs = []
    loss_pcts = []

    for _, row in greedy_rows.iterrows():
        notes_str = str(row.get("notes", ""))
        m_greedy = re.search(r"Receita:\s*(\d+)", notes_str)
        m_opt = re.search(r"Ótimo:\s*(\d+)", notes_str)
        m_loss = re.search(r"Perda:\s*([\d\.]+)%", notes_str)

        if m_greedy and m_opt and m_loss:
            ns.append(int(row["n"]))
            greedy_revs.append(int(m_greedy.group(1)))
            opt_revs.append(int(m_opt.group(1)))
            loss_pcts.append(float(m_loss.group(1)))

    if not ns:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.0))

    # Painel 1: Receita absoluta
    ax1.plot(ns, opt_revs, label="Receita Ótima (PD)", color=PALETTE["bottom_up"], linestyle="-", marker="o", markersize=3.5, linewidth=2.0)
    ax1.plot(ns, greedy_revs, label="Receita Gulosa (p_i / i)", color=PALETTE["greedy"], linestyle="--", marker="x", markersize=4.0, linewidth=2.0)
    ax1.set_title("E2: Receita Obtida (PD Ótima vs. Guloso)")
    ax1.set_xlabel("Comprimento da Haste (n)")
    ax1.set_ylabel("Receita ($)")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    # Painel 2: Erro relativo percentual
    ax2.plot(ns, loss_pcts, label="Erro Relativo: ((Opt - Guloso) / Opt) %", color=PALETTE["naive"], linestyle="-", marker="s", markersize=3.5, linewidth=2.0)
    ax2.set_title("E2: Subotimalidade da Heurística Gulosa (%)")
    ax2.set_xlabel("Comprimento da Haste (n)")
    ax2.set_ylabel("Defasagem em Relação ao Ótimo (%)")
    ax2.set_ylim(-1, max(loss_pcts + [15]) * 1.2)
    ax2.grid(True)
    ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e2_rod_cutting_qualidade.png")


# -----------------------------------------------------------------------------
# 3. Experimento E3: LCS e Memória
# -----------------------------------------------------------------------------
def plot_e3_lcs_memoria() -> None:
    """E3: LCS - Consumo de memória (Tabela completa vs Duas linhas)."""
    df = load_dataset("e3_lcs_memory.csv", ["approach", "n", "memory_bytes", "status"])
    if df is None:
        raise FileNotFoundError("e3_lcs_memory.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["mem_kb"] = pd.to_numeric(df_valid["memory_bytes"], errors="coerce") / 1024.0

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("bottom_up", "Tabela Completa (Θ(mn) espaço)", PALETTE["bottom_up"]),
        ("two_rows", "Duas Linhas (Θ(min(m,n)) espaço)", PALETTE["two_rows"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["mem_kb"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_title("E3: LCS — Pico de Memória Alocada (Tabela Completa vs. 2 Linhas)")
    ax.set_xlabel("Comprimento das Sequências (n = m)")
    ax.set_ylabel("Pico de Memória Alocada (KB)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e3_lcs_memoria.png", aliases=["e3_lcs_memory.png"])


def plot_e3_lcs_tempo() -> None:
    """E3: LCS - Tempo de execução das versões de tabela completa e duas linhas."""
    df = load_dataset("e3_lcs_memory.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e3_lcs_memory.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("bottom_up", "Tabela Completa (com traceback)", PALETTE["bottom_up"]),
        ("two_rows", "Duas Linhas (apenas comprimento)", PALETTE["two_rows"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["time_seconds"],
            label=label, color=color, linestyle="-",
            marker="s", markersize=3.5, linewidth=2.0
        )

    ax.set_title("E3: LCS — Tempo de Execução em Sequências Longas")
    ax.set_xlabel("Comprimento das Sequências (n = m)")
    ax.set_ylabel("Tempo de Execução (s)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e3_lcs_tempo.png")


# -----------------------------------------------------------------------------
# 4. Experimento E4: Python vs C++
# -----------------------------------------------------------------------------
def plot_e4_lcs_python_cpp() -> None:
    """E4: LCS - Comparativo de tempo Python (CPython 3.11) vs C++17 (-O3)."""
    df = load_dataset("e4_lcs_cpp.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e4_lcs_cpp.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    sub_py = df_valid[df_valid["approach"] == "bottom_up"].sort_values("n")
    sub_cpp = df_valid[df_valid["approach"] == "bottom_up_cpp"].sort_values("n")

    if sub_cpp.empty:
        raise FileNotFoundError("Dados válidos de C++ não disponíveis em E4.")

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    ax.plot(
        sub_py["n"], sub_py["time_seconds"],
        label="Python 3.11 (CPython Bottom-Up)", color=PALETTE["bottom_up"],
        linestyle="-", marker="o", markersize=4.0, linewidth=2.0
    )

    ax.plot(
        sub_cpp["n"], sub_cpp["time_seconds"],
        label="C++17 (g++ -O3 Bottom-Up Nativo)", color=PALETTE["bottom_up_cpp"],
        linestyle="-", marker="s", markersize=4.0, linewidth=2.0
    )

    ax.set_yscale("log")
    ax.set_title("E4: LCS — Desempenho CPython 3.11 vs. C++17 Nativo (-O3)")
    ax.set_xlabel("Comprimento das Cadeias (n = m)")
    ax.set_ylabel("Tempo de Execução (s, escala log)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e4_lcs_python_cpp.png", aliases=["e4_lcs_cpp_vs_python.png"])


def plot_e4_lcs_speedup() -> None:
    """E4: LCS - Speedup empírico relativo entre C++ e Python (T_python / T_cpp)."""
    df = load_dataset("e4_lcs_cpp.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e4_lcs_cpp.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    sub_py = df_valid[df_valid["approach"] == "bottom_up"].set_index("n")["time_seconds"]
    sub_cpp = df_valid[df_valid["approach"] == "bottom_up_cpp"].set_index("n")["time_seconds"]

    if sub_cpp.empty:
        raise FileNotFoundError("Dados de C++ não disponíveis para cálculo de speedup.")

    common_ns = sorted(list(set(sub_py.index).intersection(set(sub_cpp.index))))
    if not common_ns:
        return

    speedups = [sub_py.loc[n] / max(sub_cpp.loc[n], 1e-12) for n in common_ns]

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    ax.plot(
        common_ns, speedups,
        label="Speedup Empírico (T_python / T_cpp)", color=PALETTE["bottom_up_cpp"],
        linestyle="-", marker="D", markersize=4.5, linewidth=2.2
    )

    ax.axhline(y=1.0, color="#64748b", linestyle=":", linewidth=1.2, label="Paridade (1x)")
    ax.set_title("E4: LCS — Fator de Aceleração do C++ Nativo sobre o CPython")
    ax.set_xlabel("Comprimento das Cadeias (n = m)")
    ax.set_ylabel("Speedup Relativo (vezes mais rápido)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e4_lcs_speedup.png")


# -----------------------------------------------------------------------------
# 5. Experimento E5: Limite de Recursão
# -----------------------------------------------------------------------------
def plot_e5_recursao_tempo() -> None:
    """E5: Limite de recursão - Desempenho apenas na faixa onde ambos concluem sem erro."""
    df = load_dataset("e5_recursion_limit.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e5_recursion_limit.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    # Filtra apenas tamanhos onde ambas as abordagens concluíram com sucesso
    ns_memo = set(df_valid[df_valid["approach"] == "memo"]["n"])
    ns_bu = set(df_valid[df_valid["approach"] == "bottom_up"]["n"])
    common_safe_ns = sorted(list(ns_memo.intersection(ns_bu)))

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    sub_memo = df_valid[(df_valid["approach"] == "memo") & (df_valid["n"].isin(common_safe_ns))].sort_values("n")
    sub_bu = df_valid[(df_valid["approach"] == "bottom_up") & (df_valid["n"].isin(common_safe_ns))].sort_values("n")

    ax.plot(
        sub_memo["n"], sub_memo["time_seconds"],
        label="Top-Down Memoizado (no domínio seguro de recursão)", color=PALETTE["memo"],
        linestyle="-", marker="o", markersize=4.0, linewidth=2.0
    )

    ax.plot(
        sub_bu["n"], sub_bu["time_seconds"],
        label="Bottom-Up Tabulado (iterativo)", color=PALETTE["bottom_up"],
        linestyle="-", marker="s", markersize=4.0, linewidth=2.0
    )

    ax.set_title("E5: Tempo de Execução no Domínio Válido (n < Limite de Pilha)")
    ax.set_xlabel("Tamanho da Entrada (n)")
    ax.set_ylabel("Tempo de Execução (s)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e5_recursao_tempo.png")


def plot_e5_recursao_limites() -> None:
    """E5: Limite de recursão - Visualização de robustez e status categórico."""
    df = load_dataset("e5_recursion_limit.csv", ["approach", "n", "status"])
    if df is None:
        raise FileNotFoundError("e5_recursion_limit.csv não encontrado.")

    fig, ax = plt.subplots(figsize=(9.0, 4.8))

    sub_memo = df[df["approach"] == "memo"].sort_values("n")
    sub_bu = df[df["approach"] == "bottom_up"].sort_values("n")

    # Mapeamento numérico de status para visualização categórica limpa
    # 1: Sucesso, 0: RecursionError
    y_memo = [1.0 if s == "success" else 0.0 for s in sub_memo["status"]]
    y_bu = [1.0 if s == "success" else 0.0 for s in sub_bu["status"]]

    ax.step(
        sub_memo["n"], y_memo,
        where="mid", label="Top-Down Memoizado (Pilha)", color=PALETTE["memo"],
        linewidth=2.4
    )

    ax.step(
        sub_bu["n"], y_bu,
        where="mid", label="Bottom-Up Tabulado (Heap Iterativo)", color=PALETTE["bottom_up"],
        linestyle="--", linewidth=2.4
    )

    # Identifica o limite real da pilha
    first_err = sub_memo[sub_memo["status"] == "recursion_error"]["n"].min()
    if pd.notna(first_err):
        ax.axvline(
            x=first_err, color=PALETTE["naive"], linestyle=":", linewidth=1.8,
            label=f"Barreira de Pilha: RecursionError (n = {int(first_err)})"
        )

    ax.set_yticks([0.0, 1.0])
    ax.set_yticklabels(["RecursionError (Falha)", "Execução Concluída (Sucesso)"])
    ax.set_ylim(-0.2, 1.25)
    ax.set_title("E5: Robustez Arquitetural vs. Limite de Profundidade de Pilha")
    ax.set_xlabel("Tamanho da Entrada (n)")
    ax.grid(True, axis="x")
    ax.legend(loc="center left")

    fig.tight_layout()
    save_figure(fig, "e5_recursao_limites.png", aliases=["e5_recursion_limit.png"])


# -----------------------------------------------------------------------------
# 6. Experimento E6: Falha do Algoritmo Guloso
# -----------------------------------------------------------------------------
def plot_e6_greedy_failure() -> None:
    """E6: Corte de hastes - Taxa de falha % e perda média % da heurística gulosa."""
    df = load_dataset(
        "e6_greedy_failure.csv",
        ["n", "failure_rate_percent", "average_loss_percent", "num_instances"]
    )
    if df is None:
        raise FileNotFoundError("e6_greedy_failure.csv não encontrado.")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.0))
    df_sorted = df.sort_values("n")

    # Painel 1: Taxa de falha empírica (%)
    ax1.plot(
        df_sorted["n"], df_sorted["failure_rate_percent"],
        color=PALETTE["naive"], linestyle="-", marker="o", markersize=4.0, linewidth=2.0,
        label="Instâncias em que Guloso < Ótimo (%)"
    )
    ax1.set_title("E6: Frequência em que a Abordagem Gulosa Falha")
    ax1.set_xlabel("Comprimento da Haste (n)")
    ax1.set_ylabel("Taxa de Falha da Heurística (%)")
    ax1.set_ylim(-5, 105)
    ax1.grid(True)
    ax1.legend(loc="lower right")

    # Painel 2: Perda média relativa de receita (%)
    ax2.plot(
        df_sorted["n"], df_sorted["average_loss_percent"],
        color=PALETTE["greedy"], linestyle="-", marker="s", markersize=4.0, linewidth=2.0,
        label="Perda Média de Receita (%)"
    )
    ax2.set_title("E6: Magnitude da Perda de Receita (Quando Falha)")
    ax2.set_xlabel("Comprimento da Haste (n)")
    ax2.set_ylabel("Defasagem Percentual da Receita Ótima (%)")
    ax2.set_ylim(-2, max(df_sorted["average_loss_percent"].max() + 5, 25))
    ax2.grid(True)
    ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e6_guloso_erro.png", aliases=["e6_greedy_failure.png"])


# -----------------------------------------------------------------------------
# 7. Experimento E7: Matrix Chain
# -----------------------------------------------------------------------------
def plot_e7_matrix_chain_tempo() -> None:
    """E7: Cadeia de matrizes - Tempo de execução cúbico Theta(n^3)."""
    df = load_dataset("e7_matrix_chain.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e7_matrix_chain.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("naive", "Força Bruta (Naive, Omega(4ⁿ/n^(3/2)))", PALETTE["naive"]),
        ("memo", "Memoização (Top-Down, Θ(n³))", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up, Θ(n³))", PALETTE["bottom_up"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["time_seconds"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-7, top=10.0)
    ax.set_title("E7: Cadeia de Matrizes — Tempo de Execução vs. Número de Matrizes (n)")
    ax.set_xlabel("Número de Matrizes na Cadeia (n)")
    ax.set_ylabel("Tempo de Execução (s, escala log)")
    ax.grid(True)
    ax.legend(loc="lower right")

    fig.tight_layout()
    save_figure(fig, "e7_matrix_chain_tempo.png", aliases=["e7_matrix_chain.png"])


def plot_e7_matrix_chain_operacoes() -> None:
    """E7: Cadeia de matrizes - Operações poupadas e números de Catalan C(n-1)."""
    df = load_dataset("e7_matrix_chain.csv", ["approach", "n", "catalan_count", "status"])
    if df is None:
        raise FileNotFoundError("e7_matrix_chain.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.0))

    # Painel 1: Multiplicações escalares poupadas (se disponíveis)
    if "optimal_cost" in df_valid.columns and "sequential_cost" in df_valid.columns:
        sub_ops = df_valid[df_valid["approach"] == "bottom_up"].dropna(subset=["optimal_cost", "sequential_cost"]).sort_values("n")
        if not sub_ops.empty:
            ax1.plot(
                sub_ops["n"], sub_ops["sequential_cost"],
                label="Parentização Ingênua (A1*A2)*...*An", color=PALETTE["naive"],
                linestyle="--", marker="x", markersize=4.0, linewidth=2.0
            )
            ax1.plot(
                sub_ops["n"], sub_ops["optimal_cost"],
                label="Parentização Ótima (PD de Cormen)", color=PALETTE["bottom_up"],
                linestyle="-", marker="o", markersize=4.0, linewidth=2.0
            )
            ax1.set_yscale("log")
            ax1.set_title("E7: Multiplicações Escalares (Ótima vs. Ingênua)")
            ax1.set_xlabel("Número de Matrizes (n)")
            ax1.set_ylabel("Multiplicações Escalares (escala log)")
            ax1.grid(True)
            ax1.legend(loc="upper left")

    # Painel 2: Explosão dos números de Catalan C(n-1)
    sub_cat = df_valid.dropna(subset=["catalan_count"]).drop_duplicates(subset=["n"]).sort_values("n")
    if not sub_cat.empty:
        ax2.plot(
            sub_cat["n"], sub_cat["catalan_count"],
            color=PALETTE["catalan"], linestyle="-", marker="s", markersize=4.0, linewidth=2.0,
            label="Parentizações Possíveis: C(n-1)"
        )
        ax2.set_yscale("log")
        ax2.set_title("E7: Explosão Combinatória das Parentizações Possíveis")
        ax2.set_xlabel("Número de Matrizes (n)")
        ax2.set_ylabel("Número de Parentizações (escala log)")
        ax2.grid(True)
        ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e7_matrix_chain_operacoes.png")


# -----------------------------------------------------------------------------
# 8. Experimento E8: Mochila 0/1
# -----------------------------------------------------------------------------
def plot_e8_knapsack_tempo_w() -> None:
    """E8: Mochila 0/1 - Tempo em função da capacidade W (demonstração pseudo-polinomial)."""
    df = load_dataset("e8_knapsack.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e8_knapsack.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    # Filtra as séries onde n representa a capacidade W (com n_items fixo)
    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("bottom_up", "Tabela 2D (O(nW) espaço)", PALETTE["bottom_up"]),
        ("one_row", "Vetor 1D (O(W) espaço)", PALETTE["one_row"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["time_seconds"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_title("E8: Mochila 0/1 — Comportamento Pseudo-Polinomial em W (n = 50 itens)")
    ax.set_xlabel("Capacidade Máxima da Mochila (W)")
    ax.set_ylabel("Tempo de Execução (s)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e8_knapsack_tempo_w.png", aliases=["e8_knapsack.png"])


def plot_e8_knapsack_tempo_n() -> None:
    """E8: Mochila 0/1 - Tempo em função da quantidade de itens n (com W fixo)."""
    df = load_dataset("e8_knapsack.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("e8_knapsack.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    sub_n = df_valid[df_valid["approach"] == "varying_n"].sort_values("n")
    if sub_n.empty:
        return

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    ax.plot(
        sub_n["n"], sub_n["time_seconds"],
        label="Variação de Itens (com Capacidade W = 200 fixa)", color=PALETTE["bottom_up"],
        linestyle="-", marker="s", markersize=4.0, linewidth=2.0
    )

    ax.set_title("E8: Mochila 0/1 — Tempo de Execução vs. Quantidade de Itens (n)")
    ax.set_xlabel("Quantidade de Itens (n)")
    ax.set_ylabel("Tempo de Execução (s)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e8_knapsack_tempo_n.png")


def plot_e8_knapsack_memoria() -> None:
    """E8: Mochila 0/1 - Consumo de memória: Tabela 2D vs Vetor 1D."""
    df = load_dataset("e8_knapsack.csv", ["approach", "n", "memory_bytes", "status"])
    if df is None:
        raise FileNotFoundError("e8_knapsack.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["mem_kb"] = pd.to_numeric(df_valid["memory_bytes"], errors="coerce") / 1024.0

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    series = [
        ("bottom_up", "Tabela 2D (O(nW) memória)", PALETTE["bottom_up"]),
        ("one_row", "Vetor 1D (O(W) memória otimizada)", PALETTE["one_row"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        ax.plot(
            sub["n"], sub["mem_kb"],
            label=label, color=color, linestyle="-",
            marker="o", markersize=3.5, linewidth=2.0
        )

    ax.set_title("E8: Mochila 0/1 — Pico de Memória Alocada (Tabela 2D vs. Vetor 1D)")
    ax.set_xlabel("Capacidade Máxima da Mochila (W)")
    ax.set_ylabel("Pico de Memória Alocada (KB)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e8_knapsack_memoria.png")


# -----------------------------------------------------------------------------
# 9. Dashboard Consolidado das Classes Assintóticas
# -----------------------------------------------------------------------------
def plot_dashboard_summary() -> None:
    """Gera painel consolidado comparando as 4 classes assintóticas fundamentais."""
    df = load_dataset("all_benchmarks.csv", ["experiment", "approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("all_benchmarks.csv não encontrado.")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_num"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")
    df_valid["n_num"] = pd.to_numeric(df_valid["n"], errors="coerce")
    df_valid = df_valid.dropna(subset=["time_num", "n_num"])
    df_valid = df_valid[df_valid["time_num"] > 0]

    fig, ax = plt.subplots(figsize=(10.5, 6.0))

    comparisons = [
        ("E1", "naive", "Fibonacci Força Bruta — Θ(φⁿ)", PALETTE["naive"], "o"),
        ("E7", "bottom_up", "Cadeia de Matrizes — Θ(n³)", PALETTE["memo"], "s"),
        ("E2", "bottom_up", "Corte de Hastes — Θ(n²)", PALETTE["bottom_up"], "^"),
        ("E1", "bottom_up", "Fibonacci Bottom-Up — Θ(n)", PALETTE["two_rows"], "D"),
    ]

    for exp_id, app_id, label, color, marker in comparisons:
        sub = df_valid[(df_valid["experiment"] == exp_id) & (df_valid["approach"] == app_id)].sort_values("n_num")
        sub = sub[sub["n_num"] <= 35]
        if sub.empty:
            continue

        ax.plot(
            sub["n_num"], sub["time_num"],
            label=label, color=color, linestyle="-",
            marker=marker, markersize=4.0, linewidth=2.2
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-7, top=5.0)
    ax.set_title(
        "Síntese Geral das Classes Assintóticas em Programação Dinâmica\n"
        "(Exponencial vs. Cúbica vs. Quadrática vs. Linear)"
    )
    ax.set_xlabel("Tamanho da Entrada (n)")
    ax.set_ylabel("Tempo de Execução (s, escala log)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "summary_complexity_dashboard.png")


# -----------------------------------------------------------------------------
# Ponto de Entrada Principal
# -----------------------------------------------------------------------------
def main() -> None:
    """Executa a geração de todos os gráficos a partir dos dados em benchmarks/results/."""
    print("=" * 70)
    print("  GERADOR DE GRÁFICOS CIENTÍFICOS - PROGRAMAÇÃO DINÂMICA (AEDS-II)")
    print(f"  Diretório de dados: {RESULTS_DIR}")
    print(f"  Destino 1 (docs):   {DOCS_FIGURES_DIR}")
    print(f"  Destino 2 (relat):  {RELATORIO_FIGURES_DIR}")
    print(f"  Destino 3 (web):    {WEB_FIGURES_DIR}")
    print("=" * 70)

    setup_theme()

    plots = [
        # E1 Fibonacci
        ("E1: Fibonacci (Tempo Geral)", plot_e1_fibonacci_tempo),
        ("E1: Fibonacci (DP Linear Fina)", plot_e1_fibonacci_dp),
        ("E1: Fibonacci (Chamadas e Subproblemas)", plot_e1_fibonacci_chamadas),
        ("E1: Fibonacci (Speedup DP)", plot_e1_fibonacci_speedup),
        # E2 Rod Cutting
        ("E2: Corte de Hastes (Tempo Exato)", plot_e2_rod_cutting_tempo),
        ("E2: Corte de Hastes (Qualidade e Erro Guloso)", plot_e2_rod_cutting_qualidade),
        # E3 LCS Memória e Tempo
        ("E3: LCS (Consumo de Memória)", plot_e3_lcs_memoria),
        ("E3: LCS (Tempo de Execução)", plot_e3_lcs_tempo),
        # E4 LCS C++ vs Python
        ("E4: LCS (Python vs C++ Nativo)", plot_e4_lcs_python_cpp),
        ("E4: LCS (Speedup C++ / Python)", plot_e4_lcs_speedup),
        # E5 Limite de Recursão
        ("E5: Limite de Recursão (Tempo no Domínio Válido)", plot_e5_recursao_tempo),
        ("E5: Limite de Recursão (Robustez e Limites)", plot_e5_recursao_limites),
        # E6 Falha do Guloso
        ("E6: Falha do Guloso (Taxa de Erro e Perda)", plot_e6_greedy_failure),
        # E7 Cadeia de Matrizes
        ("E7: Cadeia de Matrizes (Tempo Cúbico)", plot_e7_matrix_chain_tempo),
        ("E7: Cadeia de Matrizes (Operações e Catalan)", plot_e7_matrix_chain_operacoes),
        # E8 Mochila 0/1
        ("E8: Mochila 0/1 (Tempo em W)", plot_e8_knapsack_tempo_w),
        ("E8: Mochila 0/1 (Tempo em n)", plot_e8_knapsack_tempo_n),
        ("E8: Mochila 0/1 (Memória 2D vs 1D)", plot_e8_knapsack_memoria),
        # Dashboard Síntese
        ("Dashboard Síntese", plot_dashboard_summary),
    ]

    success_count = 0
    skipped_count = 0
    error_count = 0

    for title, plot_fn in plots:
        print(f"\n[*] Gerando {title}...")
        try:
            plot_fn()
            success_count += 1
        except FileNotFoundError as fnf_err:
            print(f"      [IGNORADO] Dados não disponíveis: {fnf_err}")
            skipped_count += 1
        except Exception as err:
            print(f"      [FALHA] Erro ao gerar {title}: {err}")
            error_count += 1

    print("\n" + "=" * 70)
    print(f"Relatório de Geração: {success_count} gerados com sucesso, {skipped_count} ignorados, {error_count} erros.")
    if error_count == 0 and success_count > 0:
        print("Todos os gráficos disponíveis foram gerados com sucesso a 200 DPI!")
# -----------------------------------------------------------------------------
# Aliases de compatibilidade para suítes de teste e automações
# -----------------------------------------------------------------------------
plot_e1_fibonacci = plot_e1_fibonacci_tempo
plot_e2_rod_cutting = plot_e2_rod_cutting_tempo
plot_e3_lcs = plot_e3_lcs_memoria
plot_e4_lcs_cpp_vs_python = plot_e4_lcs_python_cpp
plot_e5_recursion_limit = plot_e5_recursao_limites
plot_e6_greedy_failure = plot_e6_greedy_failure
plot_e7_matrix_chain = plot_e7_matrix_chain_tempo
plot_e8_knapsack = plot_e8_knapsack_tempo_w
plot_all = main


if __name__ == "__main__":
    main()
