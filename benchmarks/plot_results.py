"""Módulo para geração e plotagem dos gráficos científicos de experimentos (AEDS-II).

Convenções Obrigatórias:
1. Resolução: PNG a 200 DPI salvos em 'docs/figures/' e 'relatorio/figuras/'.
2. Textos e rótulos: 100% em Português do Brasil (títulos, eixos, legendas).
3. Estilo Visual: Dark Slate moderno, alto contraste e padrão editorial científico.
4. Linhas: Exclusivamente contínuas (sólidas, sem tracejados ou pontilhados) e SEM pontos/marcadores.
5. Tratamento de Outliers: Filtragem de ruídos espúrios (pausas de SO/GC) para curvas suaves e contínuas.
6. Paleta Oficial do Projeto:
   - Ingênuo (Naive):           Vermelho (#ef4444 / #d62728)
   - Memoização (Top-Down):     Azul     (#0284c7 / #1f77b4)
   - Bottom-Up (Tabulação):     Verde    (#16a34a / #2ca02c)
   - Duas Linhas / Otimizado:   Roxo     (#9333ea / #9467bd)
   - Guloso (Greedy):           Cinza    (#64748b / #7f7f7f)
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

# Paleta oficial padronizada
PALETTE: dict[str, str] = {
    "naive": "#ef4444",
    "memo": "#0284c7",
    "bottom_up": "#16a34a",
    "bottom_up_cpp": "#f59e0b",
    "two_rows": "#9333ea",
    "one_row": "#9333ea",
    "o1_space": "#9333ea",
    "greedy": "#64748b",
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
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.labelsize": 10.5,
        "axes.labelweight": "semibold",
        "legend.facecolor": "#1e293b",
        "legend.edgecolor": "#475569",
        "legend.fontsize": 9.5,
        "legend.framealpha": 0.95,
        "figure.dpi": 200,
        "savefig.dpi": 200,
    })


def save_figure(fig: plt.Figure, filename: str) -> None:
    """Salva a figura a 200 DPI em docs/figures/, relatorio/figuras/ e web/figures/."""
    os.makedirs(DOCS_FIGURES_DIR, exist_ok=True)
    os.makedirs(RELATORIO_FIGURES_DIR, exist_ok=True)
    os.makedirs(WEB_FIGURES_DIR, exist_ok=True)

    dest_docs = os.path.join(DOCS_FIGURES_DIR, filename)
    dest_relatorio = os.path.join(RELATORIO_FIGURES_DIR, filename)
    dest_web = os.path.join(WEB_FIGURES_DIR, filename)

    fig.savefig(dest_docs, dpi=200, bbox_inches="tight")
    fig.savefig(dest_relatorio, dpi=200, bbox_inches="tight")
    fig.savefig(dest_web, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"      [FIG] Salvo: {filename} em docs/figures, relatorio/figuras e web/figures.")


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


def filter_and_smooth_series(y_vals: pd.Series | np.ndarray) -> np.ndarray:
    """Trata outliers espúrios (picos isolados causados por agendador de SO) e suaviza a curva.

    Garante que a linha represente com fidelidade o crescimento assintótico sem ruídos abruptos.
    """
    arr = np.array(y_vals, dtype=float)
    if len(arr) < 3:
        return arr

    clean = arr.copy()
    # 1. Identificação e atenuação de picos agudos isolados
    for i in range(1, len(clean) - 1):
        prev_v = clean[i - 1]
        next_v = clean[i + 1]
        local_ref = max(prev_v, next_v)
        local_floor = min(prev_v, next_v)
        # Se for um pico anormal isolado acima dos vizinhos
        if local_ref > 0 and clean[i] > local_ref * 1.30:
            clean[i] = (prev_v + next_v) / 2.0
        # Se for uma queda anômala isolada
        elif local_floor > 0 and clean[i] < local_floor * 0.70:
            clean[i] = (prev_v + next_v) / 2.0

    # 2. Suavização suave com janela móvel para continuidade geométrica
    smoothed = pd.Series(clean).rolling(window=3, center=True, min_periods=1).mean().values
    return smoothed


# -----------------------------------------------------------------------------
# Gráficos dos Experimentos E1 a E8
# -----------------------------------------------------------------------------

def plot_e1_fibonacci() -> None:
    """E1: Fibonacci - Tempo e número de chamadas recursivas x n (linhas contínuas, sem marcadores)."""
    df = load_dataset("e1_fibonacci.csv", ["approach", "n", "time_seconds", "calls", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E1'")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")
    df_valid["calls"] = pd.to_numeric(df_valid["calls"], errors="coerce")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    approaches = [
        ("naive", "Força Bruta (Naive)", PALETTE["naive"]),
        ("memo", "Memoização (Top-Down)", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up)", PALETTE["bottom_up"]),
        ("o1_space", "Espaço O(1)", PALETTE["o1_space"]),
    ]

    for app_id, label, color in approaches:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        # Aplica filtragem de outliers para garantir curva contínua suave
        y_time = filter_and_smooth_series(sub["time_seconds"])
        ax1.plot(
            sub["n"], y_time,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )
        sub_calls = sub.dropna(subset=["calls"])
        if not sub_calls.empty and app_id in ["naive", "memo"]:
            ax2.plot(
                sub_calls["n"], sub_calls["calls"],
                label=label, color=color, linestyle="-",
                linewidth=2.4
            )

    # Painel 1: Tempo
    ax1.set_yscale("log")
    ax1.set_title("E1: Tempo de Execução x n (Fibonacci)")
    ax1.set_xlabel("Índice do Termo (n)")
    ax1.set_ylabel("Tempo de Execução (s, escala log)")
    ax1.set_ylim(bottom=1e-8, top=2.0)
    ax1.grid(True)
    ax1.legend(loc="lower right")

    # Painel 2: Chamadas
    ax2.set_yscale("log")
    ax2.set_title("E1: Quantidade de Chamadas Recursivas")
    ax2.set_xlabel("Índice do Termo (n)")
    ax2.set_ylabel("Número de Invocações (escala log)")
    ax2.set_ylim(bottom=1, top=1e8)
    ax2.grid(True)
    ax2.legend(loc="lower right")

    fig.tight_layout()
    save_figure(fig, "e1_fibonacci.png")


def plot_e2_rod_cutting() -> None:
    """E2: Corte de hastes - Tempo x n (Força bruta x Memoização x Bottom-Up)."""
    df = load_dataset("e2_rod_cutting.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E2'")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_seconds"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")

    fig, ax = plt.subplots(figsize=(9, 5.5))

    series = [
        ("naive", "Força Bruta (Naive, Θ(2ⁿ))", PALETTE["naive"]),
        ("memo", "Memoização (Top-Down, Θ(n²))", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up, Θ(n²))", PALETTE["bottom_up"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        y_time = filter_and_smooth_series(sub["time_seconds"])
        ax.plot(
            sub["n"], y_time,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-7, top=5.0)
    ax.set_title("E2: Corte de Hastes - Crescimento de Tempo x Comprimento da Haste (n)")
    ax.set_xlabel("Comprimento da Haste (n)")
    ax.set_ylabel("Tempo de Execução (s, escala log)")
    ax.grid(True)
    ax.legend(loc="lower right")

    fig.tight_layout()
    save_figure(fig, "e2_rod_cutting.png")


def plot_e3_lcs_memory() -> None:
    """E3: LCS - Pico de memória e tempo (Tabela completa x Duas linhas)."""
    df = load_dataset("e3_lcs_memory.csv", ["approach", "n", "time_seconds", "memory_bytes", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E3'")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["mem_kb"] = df_valid["memory_bytes"] / 1024.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    series = [
        ("bottom_up", "Tabela Completa (Θ(mn))", PALETTE["bottom_up"]),
        ("two_rows", "Duas Linhas (Θ(min(m,n)))", PALETTE["two_rows"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        # Memória em KB (suavizada)
        y_mem = filter_and_smooth_series(sub["mem_kb"])
        ax1.plot(
            sub["n"], y_mem,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )
        # Tempo em segundos (suavizado)
        y_time = filter_and_smooth_series(sub["time_seconds"])
        ax2.plot(
            sub["n"], y_time,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )

    ax1.set_title("E3: LCS - Pico de Memória Alocada (KB)")
    ax1.set_xlabel("Tamanho das Strings (n = m)")
    ax1.set_ylabel("Pico de Memória (KB)")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    ax2.set_title("E3: LCS - Tempo de Execução")
    ax2.set_xlabel("Tamanho das Strings (n = m)")
    ax2.set_ylabel("Tempo de Execução (segundos)")
    ax2.grid(True)
    ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e3_lcs_memory.png")


def plot_e4_cpp_vs_python() -> None:
    """E4: LCS - Comparativo de desempenho Python x C++."""
    df = load_dataset("e4_lcs_cpp.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E4'")

    df_valid = df[df["status"] == "success"].copy()

    fig, ax = plt.subplots(figsize=(9, 5.5))

    sub_py = df_valid[df_valid["approach"] == "bottom_up"].sort_values("n")
    if not sub_py.empty:
        y_py = filter_and_smooth_series(sub_py["time_seconds"])
        ax.plot(
            sub_py["n"], y_py,
            label="Python 3.11 (CPython Bottom-Up)", color=PALETTE["bottom_up"],
            linestyle="-", linewidth=2.4
        )

    sub_cpp = df_valid[df_valid["approach"] == "bottom_up_cpp"].sort_values("n")
    if not sub_cpp.empty:
        y_cpp = filter_and_smooth_series(sub_cpp["time_seconds"])
        ax.plot(
            sub_cpp["n"], y_cpp,
            label="C++17 (g++ -O3 Bottom-Up)", color=PALETTE["bottom_up_cpp"],
            linestyle="-", linewidth=2.4
        )
    else:
        ax.text(
            0.5, 0.15,
            "Binário C++ não compilado no ambiente atual.\nExibindo curva contínua do CPython.",
            transform=ax.transAxes, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#334155", edgecolor="#64748b", alpha=0.9),
            fontsize=9.5, color="#f8fafc"
        )

    ax.set_title("E4: LCS - Desempenho e Overhead de Interpretador (Python vs. C++)")
    ax.set_xlabel("Tamanho das Cadeias (n)")
    ax.set_ylabel("Tempo de Execução (segundos)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e4_lcs_cpp_vs_python.png")


def plot_e5_recursion_limit() -> None:
    """E5: Limite de recursão (RecursionError) na memoização vs Bottom-Up."""
    df = load_dataset("e5_recursion_limit.csv", ["approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E5'")

    fig, ax = plt.subplots(figsize=(10, 5.5))

    # Identifica o ponto onde a recursão falhou
    memo_errors = df[(df["approach"] == "memo") & (df["status"] == "recursion_error")]
    first_error_n = memo_errors["n"].min() if not memo_errors.empty else None

    # Plota apenas medições de sucesso com remoção de picos anômalos
    sub_memo = df[(df["approach"] == "memo") & (df["status"] == "success")].sort_values("n")
    if not sub_memo.empty:
        y_memo = filter_and_smooth_series(sub_memo["time_seconds"])
        ax.plot(
            sub_memo["n"], y_memo,
            label="Memoização (Top-Down, esgota pilha em n=1000)",
            color=PALETTE["memo"], linestyle="-", linewidth=2.4
        )

    sub_bu = df[(df["approach"] == "bottom_up") & (df["status"] == "success")].sort_values("n")
    if not sub_bu.empty:
        y_bu = filter_and_smooth_series(sub_bu["time_seconds"])
        ax.plot(
            sub_bu["n"], y_bu,
            label="Tabulação (Bottom-Up, imune a limite de recursão)",
            color=PALETTE["bottom_up"], linestyle="-", linewidth=2.4
        )

    # Linha vertical contínua indicando o limite empírico de estouro (SEM pontos scatter)
    if first_error_n is not None and pd.notna(first_error_n):
        ax.axvline(
            x=first_error_n, color=PALETTE["naive"], linestyle="-", linewidth=1.6, alpha=0.75,
            label=f"RecursionError (Pilha Esgotada em n={first_error_n})"
        )

    ax.set_title("E5: Vulnerabilidade da Recursão Top-Down ao Limite de Pilha do Python")
    ax.set_xlabel("Tamanho da Entrada (n)")
    ax.set_ylabel("Tempo de Execução (segundos)")
    ax.grid(True)
    ax.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e5_recursion_limit.png")


def plot_e6_greedy_failure() -> None:
    """E6: Corte de hastes - Taxa de erro percentual e perda média da heurística gulosa."""
    df = load_dataset(
        "e6_greedy_failure.csv",
        ["n", "failure_rate_percent", "average_loss_percent", "num_instances"]
    )
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E6'")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    df_sorted = df.sort_values("n")

    # Painel 1: Taxa de Falha % (suavizada, contínua)
    y_fail = filter_and_smooth_series(df_sorted["failure_rate_percent"])
    ax1.plot(
        df_sorted["n"], y_fail,
        color=PALETTE["naive"], linestyle="-", linewidth=2.4,
        label="Taxa de Falha da Heurística (%)"
    )
    ax1.set_title("E6: Frequência em que a Abordagem Gulosa Falha")
    ax1.set_xlabel("Comprimento da Haste (n)")
    ax1.set_ylabel("Instâncias em que Guloso < Ótimo (%)")
    ax1.set_ylim(-5, 105)
    ax1.grid(True)
    ax1.legend(loc="lower right")

    # Painel 2: Perda Média % (suavizada, contínua)
    y_loss = filter_and_smooth_series(df_sorted["average_loss_percent"])
    ax2.plot(
        df_sorted["n"], y_loss,
        color=PALETTE["greedy"], linestyle="-", linewidth=2.4,
        label="Perda Média de Receita (%)"
    )
    ax2.set_title("E6: Magnitude da Perda de Receita (Quando Falha)")
    ax2.set_xlabel("Comprimento da Haste (n)")
    ax2.set_ylabel("Diferença Percentual da Receita Ótima (%)")
    ax2.set_ylim(-2, 50)
    ax2.grid(True)
    ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e6_greedy_failure.png")


def plot_e7_matrix_chain() -> None:
    """E7: Cadeia de matrizes - Tempo de PD Theta(n^3) e crescimento de Catalan C(n-1)."""
    df = load_dataset(
        "e7_matrix_chain.csv",
        ["approach", "n", "time_seconds", "catalan_count", "status"]
    )
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E7'")

    df_valid = df[df["status"] == "success"].copy()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    series = [
        ("naive", "Força Bruta (Naive)", PALETTE["naive"]),
        ("memo", "Memoização (Top-Down, Θ(n³))", PALETTE["memo"]),
        ("bottom_up", "Tabulação (Bottom-Up, Θ(n³))", PALETTE["bottom_up"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        y_time = filter_and_smooth_series(sub["time_seconds"])
        ax1.plot(
            sub["n"], y_time,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )

    ax1.set_yscale("log")
    ax1.set_ylim(bottom=1e-7, top=10.0)
    ax1.set_title("E7: Cadeia de Matrizes - Tempo de Execução x n")
    ax1.set_xlabel("Número de Matrizes na Cadeia (n)")
    ax1.set_ylabel("Tempo de Execução (s, escala log)")
    ax1.grid(True)
    ax1.legend(loc="lower right")

    # Painel 2: Explosão combinatória de Catalan C(n-1) obtido exclusivamente de catalan_count
    sub_catalan = df_valid.dropna(subset=["catalan_count"]).drop_duplicates(subset=["n"]).sort_values("n")
    if not sub_catalan.empty:
        ax2.plot(
            sub_catalan["n"], sub_catalan["catalan_count"],
            color="#ec4899", linestyle="-", linewidth=2.4,
            label="Parentizações Possíveis: C(n-1) = (1/n)binom(2n-2, n-1)"
        )

    ax2.set_yscale("log")
    ax2.set_title("E7: Explosão Combinatória dos Números de Catalan")
    ax2.set_xlabel("Número de Matrizes (n)")
    ax2.set_ylabel("Parentizações Possíveis (escala log)")
    ax2.grid(True)
    ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e7_matrix_chain.png")


def plot_e8_knapsack() -> None:
    """E8: Mochila 0/1 - Tempo e memória x capacidade W (pseudo-polinomial)."""
    df = load_dataset("e8_knapsack.csv", ["approach", "n", "time_seconds", "memory_bytes", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py --only E8'")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["mem_kb"] = df_valid["memory_bytes"] / 1024.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    series = [
        ("bottom_up", "Tabela 2D (O(nW) espaço)", PALETTE["bottom_up"]),
        ("one_row", "Vetor 1D (O(W) espaço)", PALETTE["one_row"]),
    ]

    for app_id, label, color in series:
        sub = df_valid[df_valid["approach"] == app_id].sort_values("n")
        if sub.empty:
            continue
        # Tempo (suavizado)
        y_time = filter_and_smooth_series(sub["time_seconds"])
        ax1.plot(
            sub["n"], y_time,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )
        # Memória (suavizada)
        y_mem = filter_and_smooth_series(sub["mem_kb"])
        ax2.plot(
            sub["n"], y_mem,
            label=label, color=color, linestyle="-",
            linewidth=2.4
        )

    ax1.set_title("E8: Mochila 0/1 - Natureza Pseudo-Polinomial O(nW)")
    ax1.set_xlabel("Capacidade da Mochila (W)")
    ax1.set_ylabel("Tempo de Execução (segundos)")
    ax1.grid(True)
    ax1.legend(loc="upper left")

    ax2.set_title("E8: Mochila 0/1 - Consumo de Memória (KB)")
    ax2.set_xlabel("Capacidade da Mochila (W)")
    ax2.set_ylabel("Pico de Memória (KB)")
    ax2.grid(True)
    ax2.legend(loc="upper left")

    fig.tight_layout()
    save_figure(fig, "e8_knapsack.png")


def plot_dashboard_summary() -> None:
    """Gera painel consolidado comparando as classes assintóticas fundamentais."""
    df = load_dataset("all_benchmarks.csv", ["experiment", "approach", "n", "time_seconds", "status"])
    if df is None:
        raise FileNotFoundError("Necessário executar 'python benchmarks/run_benchmarks.py'")

    df_valid = df[df["status"] == "success"].copy()
    df_valid["time_num"] = pd.to_numeric(df_valid["time_seconds"], errors="coerce")
    df_valid["n_num"] = pd.to_numeric(df_valid["n"], errors="coerce")
    df_valid = df_valid.dropna(subset=["time_num", "n_num"])
    df_valid = df_valid[df_valid["time_num"] > 0]

    fig, ax = plt.subplots(figsize=(11, 6.5))

    comparisons = [
        ("E1", "naive", "Fibonacci Força Bruta — Θ(2ⁿ)", PALETTE["naive"]),
        ("E7", "bottom_up", "Cadeia de Matrizes — Θ(n³)", PALETTE["memo"]),
        ("E2", "bottom_up", "Corte de Hastes — Θ(n²)", PALETTE["bottom_up"]),
        ("E1", "bottom_up", "Fibonacci Bottom-Up — Θ(n)", PALETTE["two_rows"]),
    ]

    for exp_id, app_id, label, color in comparisons:
        sub = df_valid[(df_valid["experiment"] == exp_id) & (df_valid["approach"] == app_id)].sort_values("n_num")
        sub = sub[sub["n_num"] <= 35]
        if sub.empty:
            continue

        y_time = filter_and_smooth_series(sub["time_num"])
        ax.plot(
            sub["n_num"], y_time,
            label=label, color=color, linestyle="-",
            linewidth=2.5
        )

    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-7, top=5.0)
    ax.set_title(
        "Visão Geral das Classes Assintóticas em Programação Dinâmica\n"
        "(Exponencial vs. Cúbica vs. Quadrática vs. Linear)",
        fontweight="bold"
    )
    ax.set_xlabel("Tamanho da Entrada (n)")
    ax.set_ylabel("Tempo de Execução (segundos, escala log)")
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
    print("=" * 70)

    setup_theme()

    plots = [
        ("E1: Fibonacci", plot_e1_fibonacci),
        ("E2: Corte de Hastes", plot_e2_rod_cutting),
        ("E3: LCS Memória", plot_e3_lcs_memory),
        ("E4: LCS C++ vs Python", plot_e4_cpp_vs_python),
        ("E5: Limite de Recursão", plot_e5_recursion_limit),
        ("E6: Falha do Guloso", plot_e6_greedy_failure),
        ("E7: Cadeia de Matrizes", plot_e7_matrix_chain),
        ("E8: Mochila 0/1", plot_e8_knapsack),
        ("Dashboard Resumo", plot_dashboard_summary),
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
    print("=" * 70)


if __name__ == "__main__":
    main()
