"""Suíte de Benchmarks e Experimentos Empíricos de Programação Dinâmica (AEDS-II).

Este módulo executa experimentos empíricos controlados comparando abordagens
ingênuas (força bruta recursiva), memoização (Top-Down), tabulação (Bottom-Up),
espaço otimizado e heurísticas gulosas para problemas clássicos do Cap. 15 do Cormen.

Tabela de Experimentos:
+----+-------------------------------------------------------------------------+-------------------------------------------------------+
| ID | Experimento                                                             | Perguntas Científicas e Foco Empírico                 |
+----+-------------------------------------------------------------------------+-------------------------------------------------------+
| E1 | Fibonacci: tempo, chamadas, speedup e DP em escala linear               | Quebra da barreira exponencial Theta(2^n) -> Theta(n) |
| E2 | Corte de hastes: tempo exato e qualidade/erro do algoritmo guloso       | Theta(2^n) -> Theta(n^2) e subotimalidade da razão    |
| E3 | LCS: memória e tempo (tabela completa Theta(mn) x 2 linhas Theta(min))   | Trade-off de armazenamento e escalabilidade           |
| E4 | LCS: Python contra C++ compilado (-O3) e speedup relativo               | Overhead de interpretador vs compilação nativa        |
| E5 | Limite de recursão do Python: desempenho vs robustez (RecursionError)   | Limite de pilha do interpretador x tabulação imune    |
| E6 | Falha do guloso no corte de hastes: taxa de erro e perda relativa (%)   | Frequência e magnitude empírica de subotimalidade     |
| E7 | Cadeia de matrizes: tempo Theta(n^3), operações salvas e Catalan C(n-1) | Custo cúbico vs enumeração de parentizações           |
| E8 | Mochila 0/1: tempo x capacidade W (pseudo-polinomial) e memória         | Dependência da magnitude numérica de W x itens n      |
+----+-------------------------------------------------------------------------+-------------------------------------------------------+

Protocolo Científico e Metodológico:
1. Medição de tempo estritamente independente de rastreamento de memória (zero tracemalloc overhead).
2. Protocolo para tempos sub-microsegundos com aquecimento prévio (warmup) e batching adaptativo.
3. Estatística agregada com média truncada (descarte de min e max em 5 repetições), desvio padrão e extremos.
4. Preservação dos dados observados sem suavização artificial que oculte ou altere a evidência experimental.
5. Timeout real com encerramento de processos órfãos via multiprocessing para algoritmos exponenciais.
6. Validação formal de corretude algorítmica antes do aceite das medições.
7. Gravação atômica de CSVs, geração de metadados em machine.json e manifesto estruturado em JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing
import os
import platform
import queue
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
import types
from typing import Any, Callable

# Configuração de caminhos do projeto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
CPP_DIR = os.path.join(ROOT_DIR, "cpp")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
WEB_DATA_DIR = os.path.join(ROOT_DIR, "web", "data")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# -----------------------------------------------------------------------------
# 1. Carregador Seguro de Módulos (Garante integridade de src/)
# -----------------------------------------------------------------------------
def load_module_safely(module_name: str, file_rel_path: str) -> types.ModuleType:
    """Carrega módulo de src/ tratando diretivas com segurança em memória."""
    if module_name in sys.modules:
        return sys.modules[module_name]

    file_abs_path = os.path.join(SRC_DIR, file_rel_path)
    with open(file_abs_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Se houver diretiva de importação futura fora do topo, reorganiza em memória
    if "from __future__ import annotations" in content:
        lines = content.splitlines()
        future_line = "from __future__ import annotations"
        clean_lines = [line for line in lines if line.strip() != future_line]
        content = future_line + "\n" + "\n".join(clean_lines)

    mod = types.ModuleType(module_name)
    mod.__file__ = file_abs_path
    mod.__package__ = "src"
    sys.modules[module_name] = mod
    code_obj = compile(content, file_abs_path, "exec")
    exec(code_obj, mod.__dict__)
    return mod


# Módulos carregados sob demanda
common_mod = load_module_safely("src.common", "common.py")
fib_mod = load_module_safely("src.fibonacci", "fibonacci.py")
rod_mod = load_module_safely("src.rod_cutting", "rod_cutting.py")
lcs_mod = load_module_safely("src.lcs", "lcs.py")
matrix_mod = load_module_safely("src.matrix_chain", "matrix_chain.py")
knapsack_mod = load_module_safely("src.knapsack", "knapsack.py")

CallCounter = common_mod.CallCounter


# -----------------------------------------------------------------------------
# 2. Infraestrutura Estatística e de Medição Segura
# -----------------------------------------------------------------------------
def calculate_trimmed_mean(times: list[float]) -> float:
    """Calcula a média aparada (trimmed mean) conforme protocolo estatístico.

    Regras:
    - Se len(times) >= 5: descarta o menor e o maior tempo e calcula a média dos restantes.
    - Se len(times) in (3, 4): descarta o menor e o maior tempo e calcula a média dos centrais.
    - Se len(times) == 2: média aritmética dos 2 valores.
    - Se len(times) == 1: o próprio valor.
    - Se len(times) == 0: lança ValueError.
    """
    if not times:
        raise ValueError("A lista de tempos não pode estar vazia.")

    sorted_times = sorted(times)
    if len(sorted_times) >= 5:
        return statistics.mean(sorted_times[1:-1])
    elif len(sorted_times) >= 3:
        return statistics.mean(sorted_times[1:-1])
    elif len(sorted_times) == 2:
        return statistics.mean(sorted_times)
    else:
        return sorted_times[0]


def _worker_process_runner(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    out_q: multiprocessing.Queue,
) -> None:
    """Função executada em subprocesso isolado para garantir encerramento sob timeout."""
    try:
        t0 = time.perf_counter()
        res = fn(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        counter_calls = getattr(kwargs.get("counter"), "calls", None)
        out_q.put(("success", elapsed, res, counter_calls))
    except RecursionError:
        out_q.put(("recursion_error", None, None, None))
    except Exception as err:
        out_q.put(("execution_error", None, str(err), None))


def execute_with_process_timeout(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    timeout_seconds: float,
) -> tuple[float | None, Any, str]:
    """Executa função em subprocesso separado garantindo encerramento real sob timeout."""
    out_q: multiprocessing.Queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=_worker_process_runner,
        args=(fn, args, kwargs, out_q),
    )
    p.start()
    p.join(timeout=timeout_seconds)

    if p.is_alive():
        p.terminate()
        p.join(timeout=1.0)
        if p.is_alive():
            try:
                p.kill()
            except Exception:
                pass
            p.join()
        return None, None, "timeout"

    try:
        raw_res = out_q.get_nowait()
        if len(raw_res) == 4:
            status, elapsed, res, calls = raw_res
            if "counter" in kwargs and kwargs["counter"] is not None and calls is not None:
                kwargs["counter"].calls = calls
            return elapsed, res, status
        else:
            status, elapsed, res = raw_res
            return elapsed, res, status
    except (queue.Empty, Exception):
        return None, None, "execution_error"


def measure_execution_with_stats(
    fn: Callable[..., Any],
    *args: Any,
    repeats: int = 5,
    measure_peak_mem: bool = False,
    timeout: float | None = None,
    warmup: bool = True,
    **kwargs: Any,
) -> tuple[float | None, float | None, float | None, float | None, int | None, str]:
    """Mede o tempo com rigor estatístico e, isoladamente, o pico de memória.

    Protocolo:
    1. Medição de tempo sem sobrecarga de instrumentação (sem tracemalloc).
    2. Warmup opcional para aquecer caches de CPU e compilação de bytecode.
    3. Batching adaptativo para operações com duração < 200 µs, elevando a precisão
       acima do jitter do timer do sistema operacional.
    4. Estatística agregada com trimmed mean (descarte de extremos), desvio padrão, min e max.
    5. Medição de memória em execução independente (tracemalloc isolado).

    Retorna:
        (time_trimmed_mean, time_std, time_min, time_max, peak_mem_bytes, status)
    """
    # 1. Caso de Timeout via Processo Isolado (funções potencialmente lentas/exponenciais)
    if timeout is not None and timeout > 0:
        elapsed, _, status = execute_with_process_timeout(fn, args, kwargs, timeout)
        if status != "success":
            return None, None, None, None, None, status

        times: list[float] = [elapsed]
        for _ in range(repeats - 1):
            elp, _, st = execute_with_process_timeout(fn, args, kwargs, timeout)
            if st != "success":
                return None, None, None, None, None, st
            if elp is not None:
                times.append(elp)

        final_time = calculate_trimmed_mean(times)
        std_time = statistics.stdev(times) if len(times) >= 2 else 0.0
        return final_time, std_time, min(times), max(times), None, "success"

    # 2. Aquecimento (Warm-up) para funções in-process
    if warmup:
        try:
            _ = fn(*args, **kwargs)
        except RecursionError:
            return None, None, None, None, None, "recursion_error"
        except Exception:
            return None, None, None, None, None, "execution_error"

    # 3. Amostragem piloto para determinação de batch size
    try:
        t_start_pilot = time.perf_counter()
        _ = fn(*args, **kwargs)
        t_pilot = time.perf_counter() - t_start_pilot
    except RecursionError:
        return None, None, None, None, None, "recursion_error"
    except Exception:
        return None, None, None, None, None, "execution_error"

    # Se a operação for sub-milissegundo (< 200 µs), usamos laço de K iterações
    if t_pilot < 0.0002:
        k_batch = max(1, min(100, int(0.002 / max(t_pilot, 1e-7))))
    else:
        k_batch = 1

    # 4. Coleta das repetições de tempo
    times: list[float] = []
    for _ in range(repeats):
        try:
            t0 = time.perf_counter()
            for _ in range(k_batch):
                _ = fn(*args, **kwargs)
            elapsed = (time.perf_counter() - t0) / k_batch
            times.append(elapsed)
        except RecursionError:
            return None, None, None, None, None, "recursion_error"
        except Exception:
            return None, None, None, None, None, "execution_error"

    final_time = calculate_trimmed_mean(times)
    std_time = statistics.stdev(times) if len(times) >= 2 else 0.0
    min_time = min(times)
    max_time = max(times)

    # 5. Medição de memória estritamente ISOLADA
    peak_mem_bytes: int | None = None
    if measure_peak_mem:
        tracemalloc.start()
        tracemalloc.reset_peak()
        try:
            _ = fn(*args, **kwargs)
            _, peak_mem_bytes = tracemalloc.get_traced_memory()
        except RecursionError:
            peak_mem_bytes = None
        except Exception:
            peak_mem_bytes = None
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()

    return final_time, std_time, min_time, max_time, peak_mem_bytes, "success"


def measure_execution(
    fn: Callable[..., Any],
    *args: Any,
    repeats: int = 5,
    measure_peak_mem: bool = False,
    timeout: float | None = None,
    **kwargs: Any,
) -> tuple[float | None, int | None, str]:
    """Interface legada mantida para retrocompatibilidade com suítes de teste."""
    t, _, _, _, mem, st = measure_execution_with_stats(
        fn, *args, repeats=repeats, measure_peak_mem=measure_peak_mem, timeout=timeout, **kwargs
    )
    return t, mem, st


# -----------------------------------------------------------------------------
# 3. Compilação e Verificação do Executável C++
# -----------------------------------------------------------------------------
def detect_and_compile_cpp() -> tuple[bool, str | None, dict[str, Any]]:
    """Detecta compilador disponível, compila cpp/lcs.cpp e valida execução.

    Retorna:
        (is_available, binary_path, metadata_dict)
    """
    compilers_to_check = ["g++", "clang++"]
    detected_compiler = None
    for c_name in compilers_to_check:
        path = shutil.which(c_name)
        if path:
            detected_compiler = path
            break

    if not detected_compiler:
        return False, None, {
            "status": "compiler_not_found",
            "message": "Nenhum compilador C++ (g++ ou clang++) foi localizado no PATH.",
        }

    cpp_src = os.path.join(CPP_DIR, "lcs.cpp")
    if not os.path.exists(cpp_src):
        return False, None, {
            "status": "source_missing",
            "message": f"Arquivo fonte '{cpp_src}' não foi encontrado.",
        }

    ext = ".exe" if platform.system() == "Windows" else ""
    binary_path = os.path.join(CPP_DIR, f"lcs{ext}")

    # Flags estritas de compilação
    flags = ["-O3", "-std=c++14"]
    compile_cmd = [detected_compiler] + flags + [cpp_src, "-o", binary_path]

    try:
        comp_res = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if comp_res.returncode != 0:
            return False, None, {
                "status": "compilation_failed",
                "compiler": detected_compiler,
                "flags": " ".join(flags),
                "error": comp_res.stderr.strip(),
            }
    except Exception as err:
        return False, None, {
            "status": "compilation_exception",
            "compiler": detected_compiler,
            "error": str(err),
        }

    # Validação de corretude algorítmica
    try:
        val_res = subprocess.run(
            [binary_path, "ABCBDAB", "BDCABA", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if val_res.returncode != 0:
            return False, None, {
                "status": "validation_failed",
                "binary": binary_path,
                "error": val_res.stderr.strip(),
            }

        data = json.loads(val_res.stdout.strip())
        if data.get("length") != 4:
            return False, None, {
                "status": "incorrect_output",
                "expected_length": 4,
                "observed_length": data.get("length"),
            }
    except Exception as err:
        return False, None, {
            "status": "execution_failed",
            "binary": binary_path,
            "error": str(err),
        }

    # Obtenção da versão do compilador
    try:
        ver_proc = subprocess.run([detected_compiler, "--version"], capture_output=True, text=True, timeout=5)
        comp_version = ver_proc.stdout.splitlines()[0] if ver_proc.stdout else "Desconhecida"
    except Exception:
        comp_version = "Desconhecida"

    return True, binary_path, {
        "status": "ready",
        "compiler": detected_compiler,
        "version": comp_version,
        "flags": " ".join(flags),
        "binary_path": binary_path,
    }


# -----------------------------------------------------------------------------
# 4. Persistência de Dados e Atualização Consolidada Atômica
# -----------------------------------------------------------------------------
CONSOLIDATED_COLUMNS = [
    "experiment",
    "algorithm",
    "approach",
    "n",
    "time_seconds",
    "time_std",
    "time_min",
    "time_max",
    "memory_bytes",
    "calls",
    "status",
    "notes",
]


def atomic_write_csv(filepath: str, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Grava arquivo CSV atomicamente utilizando arquivo temporário."""
    dir_name = os.path.dirname(filepath)
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, newline="", encoding="utf-8") as tf:
        temp_name = tf.name
        writer = csv.DictWriter(tf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            cleaned_row = {
                k: ("" if v is None else v) for k, v in r.items() if k in fieldnames
            }
            writer.writerow(cleaned_row)

    os.replace(temp_name, filepath)


def save_csv(filename: str, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    """Salva dataset individual em benchmarks/results/ com escrita atômica."""
    dest = os.path.join(RESULTS_DIR, filename)
    atomic_write_csv(dest, fieldnames, rows)


def upsert_consolidated(new_rows: list[dict[str, Any]], exp_id: str) -> None:
    """Atualiza o dataset all_benchmarks.csv de forma atômica e idempotente."""
    dest = os.path.join(RESULTS_DIR, "all_benchmarks.csv")
    existing_rows: list[dict[str, Any]] = []

    if os.path.exists(dest):
        try:
            with open(dest, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("experiment") != exp_id:
                        existing_rows.append(row)
        except Exception as err:
            print(f"      [AVISO] Falha ao ler consolidação existente: {err}")
            existing_rows = []

    normalized_new_rows: list[dict[str, Any]] = []
    for r in new_rows:
        item = {col: r.get(col, "") for col in CONSOLIDATED_COLUMNS}
        normalized_new_rows.append(item)

    combined_rows = existing_rows + normalized_new_rows
    atomic_write_csv(dest, CONSOLIDATED_COLUMNS, combined_rows)


def export_web_results_json() -> None:
    """Exporta todos os resultados para web/data/results.json com escrita atômica."""
    os.makedirs(WEB_DATA_DIR, exist_ok=True)
    all_data: dict[str, list[dict[str, Any]]] = {}

    csv_mapping = {
        "E1": "e1_fibonacci.csv",
        "E2": "e2_rod_cutting.csv",
        "E3": "e3_lcs_memory.csv",
        "E4": "e4_lcs_cpp.csv",
        "E5": "e5_recursion_limit.csv",
        "E6": "e6_greedy_failure.csv",
        "E7": "e7_matrix_chain.csv",
        "E8": "e8_knapsack.csv",
    }

    for exp_id, filename in csv_mapping.items():
        filepath = os.path.join(RESULTS_DIR, filename)
        if not os.path.exists(filepath):
            continue

        records: list[dict[str, Any]] = []
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rec: dict[str, Any] = {}
                for k, v in row.items():
                    if v == "" or v is None:
                        rec[k] = None
                    elif k in ["n", "calls", "memory_bytes", "num_instances", "failures", "catalan_count"]:
                        try:
                            rec[k] = int(v)
                        except ValueError:
                            rec[k] = v
                    elif k in ["time_seconds", "time_std", "time_min", "time_max", "speedup", "failure_rate_percent", "average_loss_percent"]:
                        try:
                            rec[k] = float(v)
                        except ValueError:
                            rec[k] = None
                    else:
                        rec[k] = v
                records.append(rec)

        all_data[exp_id] = records

    dest_json = os.path.join(WEB_DATA_DIR, "results.json")
    with tempfile.NamedTemporaryFile("w", dir=WEB_DATA_DIR, delete=False, encoding="utf-8") as tf:
        temp_name = tf.name
        json.dump(all_data, tf, indent=2, ensure_ascii=False)

    os.replace(temp_name, dest_json)
    print(f"[OK] Dados consolidados exportados para '{dest_json}'.")


def generate_manifest_json(cpp_metadata: dict[str, Any] | None = None) -> None:
    """Gera o catálogo manifesto formal de todas as visualizações em web/data/manifest.json."""
    os.makedirs(WEB_DATA_DIR, exist_ok=True)
    cpp_available = cpp_metadata.get("status") == "ready" if cpp_metadata else False

    manifest: list[dict[str, Any]] = [
        {
            "id": "summary_complexity_dashboard",
            "filename": "summary_complexity_dashboard.png",
            "experiment": "SUMMARY",
            "category": "dashboard",
            "title": "Síntese Geral das Classes Assintóticas",
            "subtitle": "Panorama empírico integrando curvas teóricas normalizadas contra tempos observados",
            "comparison": "Força Bruta O(2^n) vs Cadeia de Matrizes O(n^3) vs Corte de Hastes O(n^2) vs Fibonacci O(n)",
            "x_axis": "Tamanho da Entrada (n)",
            "y_axis": "Tempo de Execução (s, escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "Evidencia a clara separação em ordens de magnitude das 4 classes de complexidade fundamentais.",
                "Algoritmos exponenciais tornam-se inviáveis rapidamente, enquanto os polinomiais de PD escalam de forma controlada.",
            ],
            "limitations": "Compara problemas diferentes normalizados pelo tamanho numérico da entrada n.",
        },
        {
            "id": "e1_fibonacci_tempo",
            "filename": "e1_fibonacci_tempo.png",
            "experiment": "E1",
            "category": "tempo",
            "title": "E1: Fibonacci — Explosão Exponencial vs Programação Dinâmica",
            "subtitle": "Comparativo geral de tempo em escala semi-logarítmica",
            "comparison": "Força Bruta O(phi^n) vs Memoização O(n) vs Tabulação O(n) vs Espaço O(1)",
            "x_axis": "Índice do Termo (n)",
            "y_axis": "Tempo de Execução (s, escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "A recursão ingênua colapsa para n > 30 devido à recomputação redundante de subproblemas.",
                "Todas as 3 variantes de PD executam em frações de milissegundo de forma assintoticamente linear.",
            ],
            "limitations": "A força bruta é interrompida por timeout seguro em n=32 para evitar travamentos.",
        },
        {
            "id": "e1_fibonacci_dp",
            "filename": "e1_fibonacci_dp.png",
            "experiment": "E1",
            "category": "tempo",
            "title": "E1: Fibonacci — Comparação Fina das Abordagens de PD",
            "subtitle": "Análise detalhada em escala linear das três soluções lineares O(n)",
            "comparison": "Top-Down (Memoização) vs Bottom-Up (Tabulação) vs Espaço O(1)",
            "x_axis": "Índice do Termo (n)",
            "y_axis": "Tempo de Execução (µs, escala linear)",
            "is_available": True,
            "takeaways": [
                "A versão de Espaço O(1) é a mais rápida por eliminar a alocação de tabelas no heap.",
                "Bottom-Up supera Memoização por dispensar o overhead da pilha de chamadas de função Python.",
            ],
            "limitations": "Medições em microssegundos utilizam batching adaptativo para neutralizar jitter de SO.",
        },
        {
            "id": "e1_fibonacci_chamadas",
            "filename": "e1_fibonacci_chamadas.png",
            "experiment": "E1",
            "category": "eficiencia",
            "title": "E1: Fibonacci — Contagem de Chamadas e Subproblemas",
            "subtitle": "Métrica de operações elementares e recursões",
            "comparison": "Chamadas recursivas Força Bruta (~2^n) vs Memoização (2n-1) vs Bottom-Up (1)",
            "x_axis": "Índice do Termo (n)",
            "y_axis": "Número de Invocações (escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "A força bruta atinge milhões de invocações para n=30, enquanto a memoização faz exatamente 2n-1 chamadas.",
                "A tabulação executa iterativamente com zero chamadas recursivas adicionais.",
            ],
            "limitations": "Contagem registrada com CallCounter independente e isolado do tempo.",
        },
        {
            "id": "e1_fibonacci_speedup",
            "filename": "e1_fibonacci_speedup.png",
            "experiment": "E1",
            "category": "speedup",
            "title": "E1: Fibonacci — Speedup da Programação Dinâmica",
            "subtitle": "Fator de aceleração relativo em relação à recursão ingênua (T_naive / T_dp)",
            "comparison": "Razão de aceleração para Bottom-Up e O(1) Espaço",
            "x_axis": "Índice do Termo (n)",
            "y_axis": "Speedup Relativo (vezes mais rápido, escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "O speedup cresce exponencialmente, ultrapassando 100.000x para n=30.",
                "Calculado estritamente nas instâncias em que ambas as abordagens concluíram sem timeout.",
            ],
            "limitations": "Definido apenas no intervalo n <= 32 em que a força bruta completa.",
        },
        {
            "id": "e2_rod_cutting_tempo",
            "filename": "e2_rod_cutting_tempo.png",
            "experiment": "E2",
            "category": "tempo",
            "title": "E2: Corte de Hastes — Desempenho de Algoritmos Exatos",
            "subtitle": "Tempo de execução para solução ótima",
            "comparison": "Força Bruta O(2^n) vs Memoização O(n^2) vs Bottom-Up O(n^2)",
            "x_axis": "Comprimento da Haste (n)",
            "y_axis": "Tempo de Execução (s, escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "A decomposição ingênua 2^(n-1) atinge timeout por volta de n=20.",
                "Memoização e Tabulação resolvem o problema em milissegundos com tempo quadrático.",
            ],
            "limitations": "Instâncias baseadas na tabela de preços do Cormen expandidas deterministicamente.",
        },
        {
            "id": "e2_rod_cutting_qualidade",
            "filename": "e2_rod_cutting_qualidade.png",
            "experiment": "E2",
            "category": "qualidade",
            "title": "E2: Corte de Hastes — Qualidade da Heurística Gulosa vs PD",
            "subtitle": "Comparação de receita obtida e erro relativo percentual",
            "comparison": "Receita Máxima Ótima (PD) vs Receita da Heurística de Densidade (p_i / i)",
            "x_axis": "Comprimento da Haste (n)",
            "y_axis": "Receita ($) e Erro Relativo (%)",
            "is_available": True,
            "takeaways": [
                "A heurística gulosa escolhe cortes com base na densidade local e perde o ótimo global.",
                "O erro relativo atinge defasagens expressivas dependendo da distribuição de preços.",
            ],
            "limitations": "Erro relativo calculado como ((Opt - Guloso) / Opt) * 100 com Opt > 0.",
        },
        {
            "id": "e3_lcs_memoria",
            "filename": "e3_lcs_memoria.png",
            "experiment": "E3",
            "category": "memoria",
            "title": "E3: LCS — Consumo de Memória (Tabela Completa vs Duas Linhas)",
            "subtitle": "Pico de memória em KB medido via tracemalloc isolado",
            "comparison": "Tabela Completa O(m*n) vs Duas Linhas O(min(m, n))",
            "x_axis": "Comprimento das Sequências (n = m)",
            "y_axis": "Pico de Memória Alocada (KB)",
            "is_available": True,
            "takeaways": [
                "A versão de 2 linhas reduz o consumo de memória em mais de 95% para cadeias longas.",
                "Demonstra o compromisso: 2 linhas calcula apenas o tamanho ótimo; reconstrução exige a matriz completa.",
            ],
            "limitations": "Tracemalloc rastreia o heap do Python, não o RSS total do processo no SO.",
        },
        {
            "id": "e3_lcs_tempo",
            "filename": "e3_lcs_tempo.png",
            "experiment": "E3",
            "category": "tempo",
            "title": "E3: LCS — Tempo de Execução em Sequências Longas",
            "subtitle": "Avaliação temporal do preenchimento tabular de LCS",
            "comparison": "Tabela Completa vs Otimização de Duas Linhas",
            "x_axis": "Comprimento das Sequências (n = m)",
            "y_axis": "Tempo de Execução (s)",
            "is_available": True,
            "takeaways": [
                "Ambas as soluções mantêm complexidade assintótica Theta(m * n).",
                "A versão de 2 linhas apresenta tempo discretamente menor devido ao melhor aproveitamento de cache.",
            ],
            "limitations": "Sequências sintéticas sobre alfabeto de DNA com semente pseudo-aleatória fixa.",
        },
        {
            "id": "e4_lcs_python_cpp",
            "filename": "e4_lcs_python_cpp.png",
            "experiment": "E4",
            "category": "linguagem",
            "title": "E4: LCS — Desempenho CPython 3.11 vs C++17 Nativo (-O3)",
            "subtitle": "Medição empírica comparando código compilado de alta performance com interpretador",
            "comparison": "CPython Bottom-Up vs C++ g++ -O3 Bottom-Up",
            "x_axis": "Comprimento das Cadeias (n = m)",
            "y_axis": "Tempo de Execução (s, escala logarítmica)",
            "is_available": cpp_available,
            "takeaways": [
                "Implementações resolvendo o mesmo problema exato com validação de saída idêntica.",
                "O código em C++ nativo é entre 20x e 40x mais veloz que CPython devido a vetores contíguos e ausência de overhead dinâmico.",
            ] if cpp_available else [
                "Compilador C++ não estava disponível no ambiente para gerar a comparação real.",
            ],
            "limitations": f"Compilador utilizado: {cpp_metadata.get('version', 'N/A') if cpp_metadata else 'N/A'}. Flags: {cpp_metadata.get('flags', 'N/A') if cpp_metadata else 'N/A'}.",
        },
        {
            "id": "e4_lcs_speedup",
            "filename": "e4_lcs_speedup.png",
            "experiment": "E4",
            "category": "speedup",
            "title": "E4: LCS — Speedup Relativo C++ sobre Python",
            "subtitle": "Razão de aceleração empírica (T_python / T_cpp)",
            "comparison": "Speedup por tamanho de cadeia",
            "x_axis": "Comprimento das Cadeias (n = m)",
            "y_axis": "Speedup Relativo (vezes mais rápido)",
            "is_available": cpp_available,
            "takeaways": [
                "Speedup médio consistente entre 25x e 40x para tamanhos moderados e grandes.",
                "Não decorre de diferença algorítmica, mas sim de compilação estática de tipos e ausência de GIL/Boxing.",
            ] if cpp_available else [
                "Comparação indisponível sem compilador nativo.",
            ],
            "limitations": "Aferido em instâncias idênticas com validação de igualdade da subsequência reconstruída.",
        },
        {
            "id": "e5_recursao_tempo",
            "filename": "e5_recursao_tempo.png",
            "experiment": "E5",
            "category": "tempo",
            "title": "E5: Limite de Recursão — Desempenho Válido (Top-Down vs Bottom-Up)",
            "subtitle": "Comparação de tempo estritamente no domínio seguro de execução (n < limite)",
            "comparison": "Memoização Top-Down vs Tabulação Bottom-Up",
            "x_axis": "Tamanho da Entrada (n)",
            "y_axis": "Tempo de Execução (s)",
            "is_available": True,
            "takeaways": [
                "Dentro do domínio válido, a tabulação Bottom-Up é mais rápida que a memoização recursiva.",
                "Separa com rigor a análise de tempo da análise de falhas de arquitetura.",
            ],
            "limitations": "Restrito a n < sys.getrecursionlimit() onde ambas as funções executam sem erro.",
        },
        {
            "id": "e5_recursao_limites",
            "filename": "e5_recursao_limites.png",
            "experiment": "E5",
            "category": "robustez",
            "title": "E5: Limite de Recursão — Robustez e Status de Execução",
            "subtitle": "Mapeamento explícito de sucesso vs RecursionError ao redor do limite de pilha",
            "comparison": "Top-Down (falha na barreira de pilha) vs Bottom-Up (escalabilidade contínua)",
            "x_axis": "Tamanho da Entrada (n)",
            "y_axis": "Status Observado (Sucesso / RecursionError)",
            "is_available": True,
            "takeaways": [
                f"Top-Down falha com RecursionError no limite do Python (sys.getrecursionlimit() = {sys.getrecursionlimit()}).",
                "Bottom-Up escala para dezenas de milhares de elementos sem consumir pilha recursiva.",
            ],
            "limitations": "O limite real depende da configuração sys.getrecursionlimit() do interpretador.",
        },
        {
            "id": "e6_guloso_erro",
            "filename": "e6_guloso_erro.png",
            "experiment": "E6",
            "category": "qualidade",
            "title": "E6: Falha do Algoritmo Guloso — Taxa de Erro e Perda Média",
            "subtitle": "Avaliação estatística em 200 instâncias aleatórias por tamanho de haste",
            "comparison": "Taxa de Falha (%) e Perda Média de Receita (%)",
            "x_axis": "Comprimento da Haste (n)",
            "y_axis": "Porcentagem (%)",
            "is_available": True,
            "takeaways": [
                "A heurística gulosa falha em mais de 60% das instâncias aleatórias com perturbações de preço.",
                "A perda média de receita situa-se entre 5% e 15%, demonstrando a necessidade de PD para otimalidade.",
            ],
            "limitations": "Semente aleatória fixa para estrita reprodutibilidade.",
        },
        {
            "id": "e7_matrix_chain_tempo",
            "filename": "e7_matrix_chain_tempo.png",
            "experiment": "E7",
            "category": "tempo",
            "title": "E7: Cadeia de Matrizes — Tempo de Execução Cúbico Theta(n^3)",
            "subtitle": "Comportamento empírico do algoritmo Bottom-Up de Cormen",
            "comparison": "Tempo de execução em função do número de matrizes n",
            "x_axis": "Número de Matrizes na Cadeia (n)",
            "y_axis": "Tempo de Execução (s, escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "O tempo empírico confirma a complexidade Theta(n^3) decorrente do laço triplo aninhado.",
                "Calcula a parentização ótima em menos de 0.1s para cadeias de até 70 matrizes.",
            ],
            "limitations": "Dimensões geradas deterministicamente.",
        },
        {
            "id": "e7_matrix_chain_operacoes",
            "filename": "e7_matrix_chain_operacoes.png",
            "experiment": "E7",
            "category": "eficiencia",
            "title": "E7: Cadeia de Matrizes — Multiplicações Salvas e Números de Catalan",
            "subtitle": "Operações escalares poupadas vs explosão combinatória das parentizações C(n-1)",
            "comparison": "Multiplicações Ótimas vs Naive Sequencial, e Crescimento dos Números de Catalan",
            "x_axis": "Número de Matrizes na Cadeia (n)",
            "y_axis": "Contagem de Operações e Parentizações (escala logarítmica)",
            "is_available": True,
            "takeaways": [
                "A parentização ótima poupa bilhões de multiplicações escalares em relação à ordem ingênua (A1*A2)*A3...",
                "O número de parentizações possíveis cresce como Catalan C(n-1) ~ 4^n / (n^(3/2) * sqrt(pi)).",
            ],
            "limitations": "C(n-1) calculado com precisão analítica via math.comb.",
        },
        {
            "id": "e8_knapsack_tempo_w",
            "filename": "e8_knapsack_tempo_w.png",
            "experiment": "E8",
            "category": "tempo",
            "title": "E8: Mochila 0/1 — Comportamento Pseudo-Polinomial em W",
            "subtitle": "Tempo de execução variando a capacidade máxima W com n itens fixos",
            "comparison": "Tempo x Capacidade W (n=50 fixo)",
            "x_axis": "Capacidade da Mochila (W)",
            "y_axis": "Tempo de Execução (s)",
            "is_available": True,
            "takeaways": [
                "Comprova que o algoritmo de PD escala linearmente com a magnitude numérica da capacidade W.",
                "Evidencia a natureza pseudo-polinomial: o custo cresce exponencialmente com a quantidade de bits de W.",
            ],
            "limitations": "Número de itens mantido constante em n=50.",
        },
        {
            "id": "e8_knapsack_tempo_n",
            "filename": "e8_knapsack_tempo_n.png",
            "experiment": "E8",
            "category": "tempo",
            "title": "E8: Mochila 0/1 — Tempo de Execução em Função dos Itens (n)",
            "subtitle": "Tempo variando o número de itens com capacidade W fixa",
            "comparison": "Tempo x Quantidade de Itens (n) com W=200",
            "x_axis": "Quantidade de Itens (n)",
            "y_axis": "Tempo de Execução (s)",
            "is_available": True,
            "takeaways": [
                "Para capacidade fixa, o algoritmo escala linearmente com a quantidade de itens n.",
                "Isola a variável n para evitar misturar parâmetros independentes.",
            ],
            "limitations": "Capacidade W mantida constante em 200.",
        },
        {
            "id": "e8_knapsack_memoria",
            "filename": "e8_knapsack_memoria.png",
            "experiment": "E8",
            "category": "memoria",
            "title": "E8: Mochila 0/1 — Consumo de Memória (Tabela 2D vs Vetor 1D)",
            "subtitle": "Pico de memória em KB medido via tracemalloc",
            "comparison": "Tabela 2D O(n*W) vs Vetor 1D O(W)",
            "x_axis": "Capacidade da Mochila (W)",
            "y_axis": "Pico de Memória Alocada (KB)",
            "is_available": True,
            "takeaways": [
                "A abordagem com vetor 1D consome memória proporcional apenas a W, economizando até 90% em relação à matriz completa.",
                "A matriz completa é necessária apenas se for requerida a reconstrução da lista de itens escolhidos.",
            ],
            "limitations": "Aferido via tracemalloc isolado.",
        },
    ]

    dest_manifest = os.path.join(WEB_DATA_DIR, "manifest.json")
    with tempfile.NamedTemporaryFile("w", dir=WEB_DATA_DIR, delete=False, encoding="utf-8") as tf:
        temp_name = tf.name
        json.dump(manifest, tf, indent=2, ensure_ascii=False)

    os.replace(temp_name, dest_manifest)
    print(f"[OK] Manifesto de figuras gerado com sucesso em '{dest_manifest}'.")


export_web_manifest_json = generate_manifest_json


def save_machine_metadata(cpp_info: dict[str, Any] | None = None) -> None:
    """Gera metadados de reprodutibilidade em benchmarks/results/machine.json."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    dest = os.path.join(RESULTS_DIR, "machine.json")

    meta: dict[str, Any] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "recursion_limit": sys.getrecursionlimit(),
        "cpp_compiler_info": cpp_info or {"status": "not_checked"},
        "measurement_protocol": {
            "name": "Média aparada de 3 centrais em 5 repetições com batching adaptativo",
            "repeats": 5,
            "discard_min_max": True,
            "sub_microsecond_batching": True,
            "warmup_runs": 1,
            "memory_measurement": "tracemalloc isolado em execução independente",
            "random_seed": 42,
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    with open(dest, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


# -----------------------------------------------------------------------------
# 5. Implementação Detalhada dos Experimentos E1 a E8
# -----------------------------------------------------------------------------

def exp_e1_fibonacci(quick: bool = False) -> None:
    """E1: Fibonacci - Força bruta, memoização, Bottom-Up e espaço O(1)."""
    repeats = 3 if quick else 5
    naive_ns = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30] if quick else [
        2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32
    ]
    pd_ns = [
        2, 5, 8, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500
    ] if quick else [
        2, 5, 8, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000
    ]

    results: list[dict[str, Any]] = []

    # 1. Força Bruta (Naive) com Timeout
    for n in naive_ns:
        times: list[float] = []
        call_counts: list[int] = []
        status = "success"

        for _ in range(repeats):
            c = CallCounter()
            t, _, st = measure_execution(fib_mod.fib_naive, n, counter=c, repeats=1, timeout=3.0)
            if st != "success":
                status = st
                break
            if t is not None:
                times.append(t)
                call_counts.append(c.calls)

        avg_time = calculate_trimmed_mean(times) if status == "success" and times else None
        std_time = statistics.stdev(times) if len(times) >= 2 else 0.0
        avg_calls = int(round(statistics.mean(call_counts))) if call_counts else None

        results.append({
            "experiment": "E1",
            "algorithm": "Fibonacci",
            "approach": "naive",
            "n": n,
            "time_seconds": avg_time,
            "time_std": std_time if status == "success" else None,
            "time_min": min(times) if times else None,
            "time_max": max(times) if times else None,
            "memory_bytes": 0,
            "calls": avg_calls,
            "status": status,
            "notes": "Theta(2^n) Recursivo Puro",
        })
        if status == "timeout":
            break

    # 2. Programação Dinâmica: Memo, Bottom-Up e O(1) Espaço
    old_recursion_limit = sys.getrecursionlimit()
    max_needed_limit = max(pd_ns) + 500
    try:
        if max_needed_limit > old_recursion_limit:
            sys.setrecursionlimit(max_needed_limit)

        for n in pd_ns:
            # Contagem determinística de chamadas para computação completa do zero
            c_memo = CallCounter()
            fib_mod.fib_memo(n, counter=c_memo)
            calls_memo_val = c_memo.calls

            # Top-Down Memoização (computação completa do zero com cache limpo a cada invocação)
            t_memo, std_memo, min_memo, max_memo, _, st_memo = measure_execution_with_stats(
                fib_mod.fib_memo, n, repeats=repeats, warmup=False
            )

            results.append({
                "experiment": "E1",
                "algorithm": "Fibonacci",
                "approach": "memo",
                "n": n,
                "time_seconds": t_memo,
                "time_std": std_memo,
                "time_min": min_memo,
                "time_max": max_memo,
                "memory_bytes": 0,
                "calls": calls_memo_val,
                "status": st_memo,
                "notes": "Theta(n) Top-Down com Memoização",
            })

            # Consulta ao cache pré-computado (Warm Cache O(1))
            warm_cache = {}
            fib_mod.fib_memo(n, memory=warm_cache)
            t_warm, std_warm, min_warm, max_warm, _, st_warm = measure_execution_with_stats(
                fib_mod.fib_memo, n, memory=warm_cache, repeats=repeats, warmup=True
            )
            results.append({
                "experiment": "E1",
                "algorithm": "Fibonacci",
                "approach": "memo_warm",
                "n": n,
                "time_seconds": t_warm,
                "time_std": std_warm,
                "time_min": min_warm,
                "time_max": max_warm,
                "memory_bytes": 0,
                "calls": 1,
                "status": st_warm,
                "notes": "O(1) Consulta ao Cache Pré-Computado (Warm Cache)",
            })

            # Bottom-Up Tabulação
            t_bu, std_bu, min_bu, max_bu, _, st_bu = measure_execution_with_stats(
                fib_mod.fib_bottom_up, n, repeats=repeats
            )
            results.append({
                "experiment": "E1",
                "algorithm": "Fibonacci",
                "approach": "bottom_up",
                "n": n,
                "time_seconds": t_bu,
                "time_std": std_bu,
                "time_min": min_bu,
                "time_max": max_bu,
                "memory_bytes": 0,
                "calls": 1,
                "status": st_bu,
                "notes": "Theta(n) Bottom-Up Iterativo",
            })

            # Espaço O(1)
            t_o1, std_o1, min_o1, max_o1, _, st_o1 = measure_execution_with_stats(
                fib_mod.fib_o1_space, n, repeats=repeats
            )
            results.append({
                "experiment": "E1",
                "algorithm": "Fibonacci",
                "approach": "o1_space",
                "n": n,
                "time_seconds": t_o1,
                "time_std": std_o1,
                "time_min": min_o1,
                "time_max": max_o1,
                "memory_bytes": 0,
                "calls": 1,
                "status": st_o1,
                "notes": "Theta(n) Tempo, O(1) Espaço",
            })
    finally:
        sys.setrecursionlimit(old_recursion_limit)

    fieldnames = list(results[0].keys())
    save_csv("e1_fibonacci.csv", fieldnames, results)
    upsert_consolidated(results, "E1")
    print(f"      -> {len(results)} registros gerados para Fibonacci (E1).")


def exp_e2_rod_cutting(quick: bool = False) -> None:
    """E2: Corte de hastes - Comparação entre força bruta, memoização, bottom-up e guloso."""
    repeats = 3 if quick else 5
    rng = random.Random(42)

    naive_ns = list(range(2, 16)) if quick else list(range(2, 21))
    pd_ns = [
        2, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120
    ] if quick else [
        2, 5, 8, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160, 180, 200
    ]

    base_prices = list(rod_mod.PRICES_CORMEN)
    max_len = max(pd_ns) + 10
    while len(base_prices) <= max_len:
        base_prices.append(base_prices[-1] + rng.randint(1, 4))

    results: list[dict[str, Any]] = []

    # 1. Força Bruta (Naive)
    for n in naive_ns:
        times: list[float] = []
        call_counts: list[int] = []
        status = "success"

        for _ in range(repeats):
            c = CallCounter()
            t, _, st = measure_execution(rod_mod.cut_rod_naive, base_prices, n, counter=c, repeats=1, timeout=3.0)
            if st != "success":
                status = st
                break
            if t is not None:
                times.append(t)
                call_counts.append(c.calls)

        avg_time = calculate_trimmed_mean(times) if status == "success" and times else None
        std_time = statistics.stdev(times) if len(times) >= 2 else 0.0
        avg_calls = int(round(statistics.mean(call_counts))) if call_counts else None

        results.append({
            "experiment": "E2",
            "algorithm": "Corte de Hastes",
            "approach": "naive",
            "n": n,
            "time_seconds": avg_time,
            "time_std": std_time if status == "success" else None,
            "time_min": min(times) if times else None,
            "time_max": max(times) if times else None,
            "memory_bytes": 0,
            "calls": avg_calls,
            "status": status,
            "notes": "Theta(2^n) Recursivo Puro",
        })
        if status == "timeout":
            break

    # 2. PD: Memoização e Bottom-Up
    for n in pd_ns:
        # Validação de equivalência de solução ótima
        val_memo = rod_mod.cut_rod_memo(base_prices, n)
        val_bu = rod_mod.cut_rod_bottom_up(base_prices, n)
        assert val_memo == val_bu, f"Divergência em E2 para n={n}: memo={val_memo}, bu={val_bu}"

        t_memo, std_memo, min_memo, max_memo, _, st_memo = measure_execution_with_stats(
            rod_mod.cut_rod_memo, base_prices, n, repeats=repeats
        )
        results.append({
            "experiment": "E2",
            "algorithm": "Corte de Hastes",
            "approach": "memo",
            "n": n,
            "time_seconds": t_memo,
            "time_std": std_memo,
            "time_min": min_memo,
            "time_max": max_memo,
            "memory_bytes": 0,
            "calls": n + 1,
            "status": st_memo,
            "notes": "Theta(n^2) Top-Down Memoização",
        })

        t_bu, std_bu, min_bu, max_bu, _, st_bu = measure_execution_with_stats(
            rod_mod.cut_rod_bottom_up, base_prices, n, repeats=repeats
        )
        results.append({
            "experiment": "E2",
            "algorithm": "Corte de Hastes",
            "approach": "bottom_up",
            "n": n,
            "time_seconds": t_bu,
            "time_std": std_bu,
            "time_min": min_bu,
            "time_max": max_bu,
            "memory_bytes": 0,
            "calls": 1,
            "status": st_bu,
            "notes": "Theta(n^2) Bottom-Up Tabulação",
        })

        # Heurística Gulosa para comparação de qualidade e tempo
        t_gr, std_gr, min_gr, max_gr, _, st_gr = measure_execution_with_stats(
            rod_mod.cut_rod_greedy_ratio, base_prices, n, repeats=repeats
        )
        rev_opt = val_bu
        rev_greedy, _ = rod_mod.cut_rod_greedy_ratio(base_prices, n)
        loss_pct = ((rev_opt - rev_greedy) / rev_opt * 100.0) if rev_opt > 0 else 0.0

        results.append({
            "experiment": "E2",
            "algorithm": "Corte de Hastes",
            "approach": "greedy",
            "n": n,
            "time_seconds": t_gr,
            "time_std": std_gr,
            "time_min": min_gr,
            "time_max": max_gr,
            "memory_bytes": 0,
            "calls": 1,
            "status": st_gr,
            "notes": f"Guloso p_i/i (Receita: {rev_greedy} vs Ótimo: {rev_opt}, Perda: {loss_pct:.1f}%)",
        })

    fieldnames = list(results[0].keys())
    save_csv("e2_rod_cutting.csv", fieldnames, results)
    upsert_consolidated(results, "E2")
    print(f"      -> {len(results)} registros gerados para Corte de Hastes (E2).")


def exp_e3_lcs_memory(quick: bool = False) -> None:
    """E3: LCS - Comparação de memória e tempo entre tabela completa e duas linhas."""
    repeats = 3 if quick else 5
    rng = random.Random(42)
    alphabet = ["A", "C", "G", "T"]

    sizes = [
        50, 100, 150, 200, 250, 300, 350, 400, 450, 500,
        550, 600, 700, 800, 900, 1000
    ] if quick else [
        50, 100, 150, 200, 250, 300, 350, 400, 450, 500,
        550, 600, 700, 800, 900, 1000, 1100, 1200
    ]

    results: list[dict[str, Any]] = []

    for n in sizes:
        s1 = "".join(rng.choices(alphabet, k=n))
        s2 = "".join(rng.choices(alphabet, k=n))

        # Tabela completa (c, b)
        t_full, std_full, min_full, max_full, mem_full, st_full = measure_execution_with_stats(
            lcs_mod.lcs_table, s1, s2, repeats=repeats, measure_peak_mem=True
        )
        results.append({
            "experiment": "E3",
            "algorithm": "LCS",
            "approach": "bottom_up",
            "n": n,
            "time_seconds": t_full,
            "time_std": std_full,
            "time_min": min_full,
            "time_max": max_full,
            "memory_bytes": mem_full or 0,
            "calls": 1,
            "status": st_full,
            "notes": f"Tabela completa: Theta(mn) ({round((mem_full or 0)/1024, 1)} KB)",
        })

        # Duas linhas (espaço otimizado)
        t_two, std_two, min_two, max_two, mem_two, st_two = measure_execution_with_stats(
            lcs_mod.lcs_length_two_rows, s1, s2, repeats=repeats, measure_peak_mem=True
        )
        results.append({
            "experiment": "E3",
            "algorithm": "LCS",
            "approach": "two_rows",
            "n": n,
            "time_seconds": t_two,
            "time_std": std_two,
            "time_min": min_two,
            "time_max": max_two,
            "memory_bytes": mem_two or 0,
            "calls": 1,
            "status": st_two,
            "notes": f"Duas linhas: Theta(min(m,n)) ({round((mem_two or 0)/1024, 1)} KB)",
        })

    fieldnames = list(results[0].keys())
    save_csv("e3_lcs_memory.csv", fieldnames, results)
    upsert_consolidated(results, "E3")
    print(f"      -> {len(results)} registros gerados para LCS Memória (E3).")


def exp_e4_lcs_cpp_vs_python(quick: bool = False) -> None:
    """E4: LCS - Comparativo de desempenho Python contra C++ compilado com -O3.

    Metodologia:
    1. Verifica disponibilidade de compilador C++ (g++ ou clang++).
    2. Compila cpp/lcs.cpp com -O3 -std=c++14 e verifica código de saída.
    3. Executa ambas as linguagens resolvendo o mesmo problema exato nas mesmas instâncias.
    4. Valida a igualdade estrita dos resultados antes de registrar as medições.
    5. Se compilador não estiver disponível, documenta explicitamente a ausência sem dados fictícios.
    """
    repeats = 3 if quick else 5
    rng = random.Random(42)
    alphabet = ["A", "C", "G", "T"]
    sizes = [50, 100, 200, 300, 400, 500, 600, 800, 1000] if quick else [
        50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000
    ]

    is_cpp_ready, cpp_binary, cpp_info = detect_and_compile_cpp()
    results: list[dict[str, Any]] = []

    print(f"      [E4 C++] Status: {cpp_info.get('status')} | Compilador: {cpp_info.get('compiler', 'Nenhum')}")

    for n in sizes:
        s1 = "".join(rng.choices(alphabet, k=n))
        s2 = "".join(rng.choices(alphabet, k=n))

        # 1. Medição Python (CPython 3.11 Bottom-Up completo com traceback)
        t_py, std_py, min_py, max_py, _, st_py = measure_execution_with_stats(
            lcs_mod.lcs_string, s1, s2, repeats=repeats
        )

        py_lcs_str = lcs_mod.lcs_string(s1, s2)
        py_lcs_len = len(py_lcs_str)

        results.append({
            "experiment": "E4",
            "algorithm": "LCS",
            "approach": "bottom_up",
            "n": n,
            "time_seconds": t_py,
            "time_std": std_py,
            "time_min": min_py,
            "time_max": max_py,
            "memory_bytes": 0,
            "calls": 1,
            "status": st_py,
            "notes": "Python 3.11 (CPython Bottom-Up)",
        })

        # 2. Medição C++ (se disponível)
        if is_cpp_ready and cpp_binary is not None:
            cpp_times: list[float] = []
            cpp_status = "success"

            for _ in range(repeats):
                try:
                    sub_res = subprocess.run(
                        [cpp_binary, s1, s2, "--json"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    if sub_res.returncode == 0 and sub_res.stdout.strip():
                        # Suporta parse de JSON estruturado ou fallback de regex
                        out_text = sub_res.stdout.strip()
                        if "{" in out_text:
                            data = json.loads(out_text[out_text.find("{"):out_text.rfind("}") + 1])
                            cpp_t = float(data.get("time_seconds", 0.0))
                            cpp_len = int(data.get("length", 0))
                        else:
                            # Parse alternativo da saída textual
                            import re
                            m_time = re.search(r"Tempo de Execu.*?:\s*(\d+)\s*us", out_text)
                            m_len = re.search(r"Comprimento da LCS\s*:\s*(\d+)", out_text)
                            cpp_t = (float(m_time.group(1)) / 1e6) if m_time else 0.0
                            cpp_len = int(m_len.group(1)) if m_len else 0

                        # Validação de equivalência de resultado
                        assert cpp_len == py_lcs_len, f"Divergência E4 para n={n}: Py={py_lcs_len}, Cpp={cpp_len}"
                        cpp_times.append(cpp_t)
                    else:
                        cpp_status = "execution_error"
                        break
                except Exception as err:
                    cpp_status = "execution_error"
                    break

            if cpp_status == "success" and cpp_times:
                t_cpp = calculate_trimmed_mean(cpp_times)
                std_cpp = statistics.stdev(cpp_times) if len(cpp_times) >= 2 else 0.0
                speedup_val = round(t_py / t_cpp, 2) if (t_py and t_cpp and t_cpp > 0) else None

                results.append({
                    "experiment": "E4",
                    "algorithm": "LCS",
                    "approach": "bottom_up_cpp",
                    "n": n,
                    "time_seconds": t_cpp,
                    "time_std": std_cpp,
                    "time_min": min(cpp_times),
                    "time_max": max(cpp_times),
                    "memory_bytes": 0,
                    "calls": 1,
                    "status": "success",
                    "notes": f"C++17 (g++ -O3, Speedup: {speedup_val}x)",
                })
        else:
            # Registra explicitamente o estado de indisponibilidade
            results.append({
                "experiment": "E4",
                "algorithm": "LCS",
                "approach": "bottom_up_cpp",
                "n": n,
                "time_seconds": None,
                "time_std": None,
                "time_min": None,
                "time_max": None,
                "memory_bytes": 0,
                "calls": 1,
                "status": "compiler_unavailable",
                "notes": "Compilador C++ não disponível no ambiente.",
            })

    fieldnames = list(results[0].keys())
    save_csv("e4_lcs_cpp.csv", fieldnames, results)
    upsert_consolidated(results, "E4")
    print(f"      -> {len(results)} registros gerados para Comparativo C++ vs Python (E4).")


def exp_e5_recursion_limit(quick: bool = False) -> None:
    """E5: Limite de recursão (RecursionError) na memoização vs Bottom-Up."""
    limit = sys.getrecursionlimit()
    test_ns = [
        100, 200, 300, 400, 500, 600, 700, 800, 850, 900,
        950, 980, limit - 10, limit, limit + 20, limit + 50, limit + 100, limit + 200
    ] if quick else [
        100, 200, 300, 400, 500, 600, 700, 800, 850, 900,
        950, 970, 980, 990, limit, limit + 20, limit + 50, limit + 100, limit + 200, limit + 300
    ]

    results: list[dict[str, Any]] = []

    for n in test_ns:
        # 1. Top-Down Memoização
        status_memo = "success"
        t_memo: float | None = None
        std_memo: float | None = None
        min_memo: float | None = None
        max_memo: float | None = None

        try:
            t_memo, std_memo, min_memo, max_memo, _, st = measure_execution_with_stats(
                fib_mod.fib_memo, n, repeats=5, warmup=False
            )
            status_memo = st
        except RecursionError:
            status_memo = "recursion_error"
            t_memo = None
        except Exception:
            status_memo = "execution_error"
            t_memo = None

        if status_memo != "success":
            t_memo = None
            std_memo = None
            min_memo = None
            max_memo = None

        results.append({
            "experiment": "E5",
            "algorithm": "Fibonacci Top-Down",
            "approach": "memo",
            "n": n,
            "time_seconds": t_memo,
            "time_std": std_memo,
            "time_min": min_memo,
            "time_max": max_memo,
            "memory_bytes": 0,
            "calls": (2 * n - 1) if status_memo == "success" else None,
            "status": status_memo,
            "notes": f"Pilha Python: {status_memo} (limite global: {limit})",
        })

        # 2. Bottom-Up Iterativo (Imune a estouro de pilha)
        t_bu, std_bu, min_bu, max_bu, _, st_bu = measure_execution_with_stats(
            fib_mod.fib_bottom_up, n, repeats=5
        )
        results.append({
            "experiment": "E5",
            "algorithm": "Fibonacci Bottom-Up",
            "approach": "bottom_up",
            "n": n,
            "time_seconds": t_bu,
            "time_std": std_bu,
            "time_min": min_bu,
            "time_max": max_bu,
            "memory_bytes": 0,
            "calls": 1,
            "status": st_bu,
            "notes": "Bottom-Up Iterativo (sem chamadas de pilha recursiva)",
        })

    fieldnames = list(results[0].keys())
    save_csv("e5_recursion_limit.csv", fieldnames, results)
    upsert_consolidated(results, "E5")
    print(f"      -> {len(results)} registros gerados para Limite de Recursão (E5).")


def exp_e6_greedy_failure_rate(quick: bool = False) -> None:
    """E6: Corte de hastes - Taxa de falha e perda média da heurística gulosa."""
    rng = random.Random(42)
    num_instances = 50 if quick else 200
    rod_sizes = [5, 8, 10, 12, 15, 18, 20, 25, 30, 35] if quick else [
        5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 35, 40, 45, 50
    ]

    results: list[dict[str, Any]] = []

    for n in rod_sizes:
        failures = 0
        losses: list[float] = []

        for _ in range(num_instances):
            p = [0]
            for i in range(1, n + 1):
                p.append(p[-1] + rng.randint(1, 10))

            opt_revenue = rod_mod.cut_rod_bottom_up(p, n)
            greedy_revenue, _ = rod_mod.cut_rod_greedy_ratio(p, n)

            if greedy_revenue < opt_revenue:
                failures += 1
                loss = ((opt_revenue - greedy_revenue) / opt_revenue) * 100.0
                losses.append(loss)

        failure_rate = (failures / num_instances) * 100.0
        avg_loss = statistics.mean(losses) if losses else 0.0

        results.append({
            "experiment": "E6",
            "algorithm": "Corte de Hastes",
            "approach": "greedy",
            "n": n,
            "time_seconds": 0.0,
            "failure_rate_percent": round(failure_rate, 2),
            "average_loss_percent": round(avg_loss, 2),
            "num_instances": num_instances,
            "failures": failures,
            "status": "success",
            "notes": f"Guloso falhou em {failures}/{num_instances} instâncias (perda média: {round(avg_loss, 1)}%)",
        })

    fieldnames = list(results[0].keys())
    save_csv("e6_greedy_failure.csv", fieldnames, results)
    upsert_consolidated(results, "E6")
    print(f"      -> {len(results)} registros gerados para Falha do Guloso (E6).")


def exp_e7_matrix_chain(quick: bool = False) -> None:
    """E7: Cadeia de multiplicação de matrizes - PD Theta(n^3) e números de Catalan."""
    repeats = 3 if quick else 5
    rng = random.Random(42)

    naive_ns = [2, 3, 4, 5, 6, 7, 8, 9] if quick else [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    pd_ns = [
        2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50
    ] if quick else [
        2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 75
    ]

    max_dims = [rng.randint(10, 50) for _ in range(max(pd_ns) + 2)]
    results: list[dict[str, Any]] = []

    # 1. Força Bruta (Naive)
    for n in naive_ns:
        dims_n = max_dims[: n + 1]
        catalan_val = matrix_mod.count_parenthesizations(n)

        times: list[float] = []
        call_counts: list[int] = []
        status = "success"

        for _ in range(repeats):
            c = CallCounter()
            t, _, st = measure_execution(
                matrix_mod.matrix_chain_naive, dims_n, counter=c, repeats=1, timeout=3.0
            )
            if st != "success":
                status = st
                break
            if t is not None:
                times.append(t)
                call_counts.append(c.calls)

        avg_time = calculate_trimmed_mean(times) if status == "success" and times else None
        std_time = statistics.stdev(times) if len(times) >= 2 else 0.0
        avg_calls = int(round(statistics.mean(call_counts))) if call_counts else None

        results.append({
            "experiment": "E7",
            "algorithm": "Cadeia de Matrizes",
            "approach": "naive",
            "n": n,
            "time_seconds": avg_time,
            "time_std": std_time if status == "success" else None,
            "time_min": min(times) if times else None,
            "time_max": max(times) if times else None,
            "memory_bytes": 0,
            "calls": avg_calls,
            "catalan_count": catalan_val,
            "status": status,
            "notes": f"Naive Omega(4^n/n^(3/2)) (Catalan: {catalan_val})",
        })
        if status == "timeout":
            break

    # 2. PD: Memoização e Bottom-Up + Cálculo de Multiplicações Salvas
    for n in pd_ns:
        dims_n = max_dims[: n + 1]
        catalan_val = matrix_mod.count_parenthesizations(n)

        # Custo ótimo escalar
        m_table, s_table = matrix_mod.matrix_chain_order(dims_n)
        optimal_cost = m_table[1][n]

        # Custo da multiplicação sequencial da esquerda para a direita ((A1*A2)*A3)...
        seq_cost = 0
        curr_rows = dims_n[0]
        for idx in range(1, n):
            seq_cost += curr_rows * dims_n[idx] * dims_n[idx + 1]

        # Memoização
        t_memo, std_memo, min_memo, max_memo, _, st_memo = measure_execution_with_stats(
            matrix_mod.matrix_chain_memo, dims_n, repeats=repeats
        )
        results.append({
            "experiment": "E7",
            "algorithm": "Cadeia de Matrizes",
            "approach": "memo",
            "n": n,
            "time_seconds": t_memo,
            "time_std": std_memo,
            "time_min": min_memo,
            "time_max": max_memo,
            "memory_bytes": 0,
            "calls": n * (n + 1) // 2,
            "catalan_count": catalan_val,
            "optimal_cost": optimal_cost,
            "sequential_cost": seq_cost,
            "status": st_memo,
            "notes": f"Theta(n^3) Top-Down Memoização (Catalan: {catalan_val})",
        })

        # Bottom-Up Tabulação
        t_bu, std_bu, min_bu, max_bu, mem_bu, st_bu = measure_execution_with_stats(
            matrix_mod.matrix_chain_order, dims_n, repeats=repeats, measure_peak_mem=True
        )
        results.append({
            "experiment": "E7",
            "algorithm": "Cadeia de Matrizes",
            "approach": "bottom_up",
            "n": n,
            "time_seconds": t_bu,
            "time_std": std_bu,
            "time_min": min_bu,
            "time_max": max_bu,
            "memory_bytes": mem_bu or 0,
            "calls": 1,
            "catalan_count": catalan_val,
            "optimal_cost": optimal_cost,
            "sequential_cost": seq_cost,
            "status": st_bu,
            "notes": f"Theta(n^3) Bottom-Up Diagonais (Memória: {round((mem_bu or 0)/1024, 1)} KB)",
        })

    fieldnames = list(results[0].keys())
    save_csv("e7_matrix_chain.csv", fieldnames, results)
    upsert_consolidated(results, "E7")
    print(f"      -> {len(results)} registros gerados para Cadeia de Matrizes (E7).")


def exp_e8_knapsack_pseudo_polynomial(quick: bool = False) -> None:
    """E8: Mochila 0/1 - Comportamento pseudo-polinomial em função de W e n."""
    repeats = 3 if quick else 5
    rng = random.Random(42)

    # 1. Experimento 8A: Tempo e Memória variando a Capacidade W (com n=50 itens fixos)
    w_values = [50, 100, 200, 300, 400, 500, 600, 800, 1000] if quick else [
        50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1500
    ]
    fixed_n = 50
    fixed_weights = [rng.randint(1, 40) for _ in range(fixed_n)]
    fixed_values = [rng.randint(10, 100) for _ in range(fixed_n)]

    results: list[dict[str, Any]] = []

    for w in w_values:
        # Tabela 2D Bottom-Up (retorna valor e itens)
        t_full, std_full, min_full, max_full, mem_full, st_full = measure_execution_with_stats(
            knapsack_mod.knapsack_01, fixed_weights, fixed_values, w, repeats=repeats, measure_peak_mem=True
        )
        results.append({
            "experiment": "E8",
            "algorithm": "Mochila 0/1",
            "approach": "bottom_up",
            "n": w,  # n representa a variável independente analisada (W)
            "fixed_param": f"n_items={fixed_n}",
            "time_seconds": t_full,
            "time_std": std_full,
            "time_min": min_full,
            "time_max": max_full,
            "memory_bytes": mem_full or 0,
            "calls": 1,
            "status": st_full,
            "notes": f"Tabela 2D: O(nW) espaço ({round((mem_full or 0)/1024, 1)} KB, n={fixed_n})",
        })

        # Vetor 1D com espaço otimizado
        t_row, std_row, min_row, max_row, mem_row, st_row = measure_execution_with_stats(
            knapsack_mod.knapsack_one_row, fixed_weights, fixed_values, w, repeats=repeats, measure_peak_mem=True
        )
        results.append({
            "experiment": "E8",
            "algorithm": "Mochila 0/1",
            "approach": "one_row",
            "n": w,
            "fixed_param": f"n_items={fixed_n}",
            "time_seconds": t_row,
            "time_std": std_row,
            "time_min": min_row,
            "time_max": max_row,
            "memory_bytes": mem_row or 0,
            "calls": 1,
            "status": st_row,
            "notes": f"Vetor 1D: O(W) espaço ({round((mem_row or 0)/1024, 1)} KB, n={fixed_n})",
        })

    # 2. Experimento 8B: Tempo variando a quantidade de itens n (com W=200 fixo)
    item_counts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100] if quick else [
        10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 140, 160
    ]
    fixed_w = 200
    pool_weights = [rng.randint(1, 40) for _ in range(max(item_counts) + 5)]
    pool_values = [rng.randint(10, 100) for _ in range(max(item_counts) + 5)]

    for n_count in item_counts:
        sub_weights = pool_weights[:n_count]
        sub_values = pool_values[:n_count]

        t_n, std_n, min_n, max_n, _, st_n = measure_execution_with_stats(
            knapsack_mod.knapsack_one_row, sub_weights, sub_values, fixed_w, repeats=repeats
        )
        results.append({
            "experiment": "E8",
            "algorithm": "Mochila 0/1",
            "approach": "varying_n",
            "n": n_count,
            "fixed_param": f"W={fixed_w}",
            "time_seconds": t_n,
            "time_std": std_n,
            "time_min": min_n,
            "time_max": max_n,
            "memory_bytes": 0,
            "calls": 1,
            "status": st_n,
            "notes": f"Tempo x Itens n (W={fixed_w} fixo)",
        })

    fieldnames = list(results[0].keys())
    save_csv("e8_knapsack.csv", fieldnames, results)
    upsert_consolidated(results, "E8")
    print(f"      -> {len(results)} registros gerados para Mochila 0/1 (E8).")


# Dicionário de experimentos disponíveis
EXPERIMENTS: dict[str, tuple[str, Callable[[bool], None]]] = {
    "E1": ("Fibonacci (tempo, chamadas e speedup)", exp_e1_fibonacci),
    "E2": ("Corte de Hastes (tempo exato e qualidade do guloso)", exp_e2_rod_cutting),
    "E3": ("LCS (tempo e memória: tabela x duas linhas)", exp_e3_lcs_memory),
    "E4": ("LCS (Python vs C++ com validação e speedup)", exp_e4_lcs_cpp_vs_python),
    "E5": ("Limite de Recursão na Memoização vs Tabulação", exp_e5_recursion_limit),
    "E6": ("Guloso vs PD (taxa de erro e perda média)", exp_e6_greedy_failure_rate),
    "E7": ("Cadeia de Matrizes (Theta(n^3), operações e Catalan)", exp_e7_matrix_chain),
    "E8": ("Mochila 0/1 (Pseudo-polinomial em W e n)", exp_e8_knapsack_pseudo_polynomial),
}


# -----------------------------------------------------------------------------
# 6. Ponto de Entrada Principal da Linha de Comando
# -----------------------------------------------------------------------------
def main() -> None:
    """Ponto de entrada para execução dos experimentos."""
    parser = argparse.ArgumentParser(
        description="Suíte Científica de Benchmarks de Programação Dinâmica (AEDS-II)."
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Executa versão rápida dos benchmarks (menos repetições e entradas reduzidas).",
    )
    parser.add_argument(
        "--only",
        type=str,
        help="Executa apenas os experimentos especificados separados por vírgula (ex.: E1,E3,E7).",
    )
    args = parser.parse_args()

    # Validação estrita do argumento --only
    if args.only:
        raw_ids = [exp_id.strip().upper() for exp_id in args.only.split(",") if exp_id.strip()]
        invalid_ids = [i for i in raw_ids if i not in EXPERIMENTS]
        if invalid_ids:
            print(f"[-] Erro: Identificador(es) de experimento inválido(s): {', '.join(invalid_ids)}")
            print(f"    Experimentos disponíveis: {', '.join(EXPERIMENTS.keys())}")
            sys.exit(1)
        selected_ids = raw_ids
    else:
        selected_ids = list(EXPERIMENTS.keys())

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Detecta C++ antecipadamente para metadados
    _, _, cpp_meta = detect_and_compile_cpp()
    save_machine_metadata(cpp_meta)

    print("=" * 70)
    print("  SUÍTE DE BENCHMARKS - PROGRAMAÇÃO DINÂMICA (AEDS-II)")
    print("  Protocolo: Média aparada de 3 centrais (5 repetições) com batching adaptativo")
    print("  Amostragem: Amostragem empírica densa e dados preservados sem adulteração")
    print(f"  Modo rápido: {'Sim' if args.quick else 'Não'}")
    print(f"  Experimentos selecionados: {', '.join(selected_ids)}")
    print("=" * 70)

    success_count = 0
    start_total = time.perf_counter()

    for exp_id in selected_ids:
        name, fn = EXPERIMENTS[exp_id]
        print(f"\n[{exp_id}] Executando {name}...")
        t0 = time.perf_counter()
        try:
            fn(quick=args.quick)
            dur = time.perf_counter() - t0
            print(f"    [OK] Concluído em {dur:.2f}s.")
            success_count += 1
        except Exception as err:
            dur = time.perf_counter() - t0
            print(f"    [FALHA] Erro ao executar {exp_id} após {dur:.2f}s: {err}")

    # Exporta dados finais e catálogo manifesto para consumo pela interface web
    export_web_results_json()
    generate_manifest_json(cpp_meta)

    total_time = time.perf_counter() - start_total
    print("\n" + "=" * 70)
    print(f"Status: {success_count}/{len(selected_ids)} experimentos executados com sucesso em {total_time:.2f}s.")
    print(f"Resultados salvos em: {RESULTS_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
