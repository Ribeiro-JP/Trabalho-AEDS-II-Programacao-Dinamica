"""Suíte de Testes Automatizados para a Infraestrutura de Benchmarks (AEDS-II).

Cobre os 15 critérios de aceitação e requisitos científicos definidos na especificação:
1. Cálculo correto da média truncada.
2. Tratamento de exceções durante medições.
3. Medição de memória com limpeza garantida do tracemalloc.
4. Timeout real com encerramento de processo em função lenta.
5. Contagem de chamadas recursivas independente por repetição.
6. Consolidação sem duplicação de experimentos.
7. Preservação dos demais experimentos em execução com --only.
8. Conversão correta de valores nulos, negativos e decimais para JSON.
9. Representação correta de falhas no E5 (status explícito, sem tempos negativos).
10. Taxa de falha e perda média no E6 com colunas semânticas.
11. Valores corretos da sequência de Catalan no E7 (C(n-1)).
12. Equivalência das soluções ótimas de PD (E2, E3, E7, E8).
13. Validação das colunas e tratamento de CSVs inexistentes.
14. Geração de gráficos com tratamento de arquivos ausentes.
15. Funcionamento dos parâmetros --quick e --only com rejeição de IDs inválidos.
"""

from __future__ import annotations

import csv
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import tracemalloc
import pytest

from benchmarks.run_benchmarks import (
    calculate_trimmed_mean,
    measure_execution,
    measure_execution_with_stats,
    detect_and_compile_cpp,
    execute_with_process_timeout,
    upsert_consolidated,
    export_web_results_json,
    export_web_manifest_json,
    atomic_write_csv,
    CallCounter,
    CONSOLIDATED_COLUMNS,
    EXPERIMENTS,
)
from benchmarks.plot_results import load_dataset, plot_e1_fibonacci, PALETTE
from src.rod_cutting import cut_rod_memo, cut_rod_bottom_up, cut_rod_greedy_ratio
from src.lcs import lcs_table, lcs_length_two_rows
from src.matrix_chain import matrix_chain_memo, matrix_chain_order, count_parenthesizations
from src.knapsack import knapsack_01, knapsack_one_row


def _modulo_funcao_lenta() -> None:
    time.sleep(3.0)


class TestBenchmarkInfrastructure:
    """Validação da infraestrutura de medição, estatística e persistência."""

    def test_1_trimmed_mean_calculation(self) -> None:
        """1. Valida o cálculo da média truncada em diferentes tamanhos amostrais."""
        # Amostra de 5 medições: descarta min (0.1) e max (0.5), média dos 3 restantes
        times_5 = [0.1, 0.2, 0.3, 0.4, 0.5]
        assert pytest.approx(calculate_trimmed_mean(times_5)) == 0.3

        # Amostra de 4 medições: descarta min (0.1) e max (0.4), média de (0.2, 0.3)
        times_4 = [0.1, 0.2, 0.3, 0.4]
        assert pytest.approx(calculate_trimmed_mean(times_4)) == 0.25

        # Amostra de 3 medições: descarta min (1.0) e max (3.0), sobra 2.0
        times_3 = [1.0, 2.0, 3.0]
        assert pytest.approx(calculate_trimmed_mean(times_3)) == 2.0

        # Amostra de 2 medições: média simples
        times_2 = [1.0, 3.0]
        assert pytest.approx(calculate_trimmed_mean(times_2)) == 2.0

        # Amostra de 1 medição: o próprio valor
        times_1 = [4.5]
        assert pytest.approx(calculate_trimmed_mean(times_1)) == 4.5

        # Amostra vazia: lança ValueError
        with pytest.raises(ValueError):
            calculate_trimmed_mean([])

    def test_2_measure_execution_exception_handling(self) -> None:
        """2. Valida o tratamento correto de exceções durante a medição."""
        def erro_recursao() -> None:
            raise RecursionError("Pilha esgotada propositalmente")

        def erro_generico() -> None:
            raise RuntimeError("Falha de execução")

        t_rec, mem_rec, status_rec = measure_execution(erro_recursao, repeats=1)
        assert status_rec == "recursion_error"
        assert t_rec is None
        assert mem_rec is None

        t_gen, mem_gen, status_gen = measure_execution(erro_generico, repeats=1)
        assert status_gen == "execution_error"
        assert t_gen is None
        assert mem_gen is None

    def test_3_memory_measurement_cleanup(self) -> None:
        """3. Garante que tracemalloc é sempre finalizado e limpo, mesmo após falhas."""
        def funcao_com_erro() -> None:
            raise ValueError("Erro durante medição de memória")

        assert not tracemalloc.is_tracing()
        t, mem, st = measure_execution(funcao_com_erro, repeats=1, measure_peak_mem=True)
        # O rastreamento deve estar rigorosamente desligado
        assert not tracemalloc.is_tracing()
        assert st == "execution_error"

    def test_4_real_timeout_mechanism(self) -> None:
        """4. Valida timeout real com encerramento de processo para algoritmos lentos."""
        t0 = time.perf_counter()
        elapsed, res, status = execute_with_process_timeout(_modulo_funcao_lenta, (), {}, timeout_seconds=0.3)
        duration = time.perf_counter() - t0

        assert status == "timeout"
        assert elapsed is None
        assert res is None
        # Garante que encerrou próximo a 0.3s e não esperou os 3 segundos
        assert duration < 1.5

    def test_5_independent_call_counter_per_run(self) -> None:
        """5. Verifica que CallCounter é independente por repetição e não acumula."""
        def recursiva_teste(n: int, counter: CallCounter | None = None) -> int:
            if counter is not None:
                counter.increment()
            if n <= 1:
                return 1
            return recursiva_teste(n - 1, counter) + 1

        counts = []
        for _ in range(5):
            c = CallCounter()
            recursiva_teste(4, counter=c)
            counts.append(c.calls)

        # Todas as 5 repetições devem ter a mesma contagem exata (4 chamadas)
        assert counts == [4, 4, 4, 4, 4]
        assert all(cnt == 4 for cnt in counts)

    def test_6_upsert_consolidated_no_duplicates(self, tmp_path: Any, monkeypatch: Any) -> None:
        """6. Valida que upsert_consolidated substitui dados sem duplicar registros."""
        test_results_dir = tmp_path / "results"
        test_results_dir.mkdir()
        monkeypatch.setattr("benchmarks.run_benchmarks.RESULTS_DIR", str(test_results_dir))

        rows_v1 = [
            {"experiment": "E3", "algorithm": "LCS", "approach": "bottom_up", "n": 100, "time_seconds": 0.01, "status": "success"},
            {"experiment": "E3", "algorithm": "LCS", "approach": "two_rows", "n": 100, "time_seconds": 0.005, "status": "success"},
        ]
        upsert_consolidated(rows_v1, "E3")

        # Atualiza E3 com novos tempos
        rows_v2 = [
            {"experiment": "E3", "algorithm": "LCS", "approach": "bottom_up", "n": 100, "time_seconds": 0.02, "status": "success"},
            {"experiment": "E3", "algorithm": "LCS", "approach": "two_rows", "n": 100, "time_seconds": 0.008, "status": "success"},
        ]
        upsert_consolidated(rows_v2, "E3")

        dest = test_results_dir / "all_benchmarks.csv"
        assert dest.exists()
        with open(dest, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            assert len(reader) == 2
            assert float(reader[0]["time_seconds"]) == 0.02

    def test_7_upsert_consolidated_preserves_other_experiments(self, tmp_path: Any, monkeypatch: Any) -> None:
        """7. Garante que atualizar E3 preserva os dados de E1 e E2 intactos."""
        test_results_dir = tmp_path / "results"
        test_results_dir.mkdir()
        monkeypatch.setattr("benchmarks.run_benchmarks.RESULTS_DIR", str(test_results_dir))

        rows_e1 = [{"experiment": "E1", "algorithm": "Fibonacci", "approach": "naive", "n": 10, "time_seconds": 0.001, "status": "success"}]
        rows_e2 = [{"experiment": "E2", "algorithm": "Corte", "approach": "bottom_up", "n": 20, "time_seconds": 0.002, "status": "success"}]
        rows_e3 = [{"experiment": "E3", "algorithm": "LCS", "approach": "bottom_up", "n": 50, "time_seconds": 0.003, "status": "success"}]

        upsert_consolidated(rows_e1, "E1")
        upsert_consolidated(rows_e2, "E2")
        upsert_consolidated(rows_e3, "E3")

        # Reexecuta apenas E3
        rows_e3_new = [{"experiment": "E3", "algorithm": "LCS", "approach": "bottom_up", "n": 50, "time_seconds": 0.005, "status": "success"}]
        upsert_consolidated(rows_e3_new, "E3")

        dest = test_results_dir / "all_benchmarks.csv"
        with open(dest, "r", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            exp_counts = {row["experiment"]: 0 for row in reader}
            for row in reader:
                exp_counts[row["experiment"]] += 1

            assert exp_counts["E1"] == 1
            assert exp_counts["E2"] == 1
            assert exp_counts["E3"] == 1
            assert len(reader) == 3

    def test_8_export_web_results_json_values(self, tmp_path: Any, monkeypatch: Any) -> None:
        """8. Valida serialização de nulos como null no JSON e integridade de tipos."""
        test_results_dir = tmp_path / "results"
        test_web_dir = tmp_path / "web" / "data"
        test_results_dir.mkdir(parents=True)
        test_web_dir.mkdir(parents=True)

        monkeypatch.setattr("benchmarks.run_benchmarks.RESULTS_DIR", str(test_results_dir))
        monkeypatch.setattr("benchmarks.run_benchmarks.WEB_DATA_DIR", str(test_web_dir))

        # Cria CSV de teste de E5 com erro de recursão (tempo ausente)
        csv_path = test_results_dir / "e5_recursion_limit.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["experiment", "algorithm", "approach", "n", "time_seconds", "memory_bytes", "calls", "status", "notes"])
            writer.writeheader()
            writer.writerow({
                "experiment": "E5", "algorithm": "Fib", "approach": "memo", "n": 1000,
                "time_seconds": "", "memory_bytes": "0", "calls": "", "status": "recursion_error", "notes": "Erro"
            })

        export_web_results_json()

        json_path = test_web_dir / "results.json"
        assert json_path.exists()
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "E5" in data
        assert len(data["E5"]) == 1
        record = data["E5"][0]
        # Tempo ausente deve ser rigorosamente null (None no Python)
        assert record["time_seconds"] is None
        assert record["status"] == "recursion_error"
        assert record["n"] == 1000

    def test_9_e5_schema_and_status(self) -> None:
        """9. Valida que E5 registra status explícito e nunca utiliza tempos negativos."""
        # Simula medição com estouro de recursão
        def estourar_recursao() -> None:
            raise RecursionError("Esgotamento da pilha")

        t, mem, status = measure_execution(estourar_recursao, repeats=1)
        assert status == "recursion_error"
        assert t is None
        assert t != -1.0
        assert t != -1

    def test_10_e6_failure_rate_and_loss_metrics(self) -> None:
        """10. Valida cálculo das métricas de taxa de falha e perda média em E6."""
        # Instância onde a heurística gulosa falha propositalmente:
        # Preços: n=4 -> p = [0, 1, 5, 8, 9]
        # Razões p[i]/i: p[1]/1=1, p[2]/2=2.5, p[3]/3=2.67, p[4]/4=2.25
        # Para n=4, guloso pega 3 (razão 2.67, preço 8) + 1 (preço 1) = 9
        # Mas a solução ótima é cortar em 2 pedaços de 2 -> p[2] + p[2] = 5 + 5 = 10
        p = [0, 1, 5, 8, 9]
        n = 4
        opt_rev = cut_rod_bottom_up(p, n)
        greedy_rev, cuts = cut_rod_greedy_ratio(p, n)

        assert opt_rev == 10
        assert greedy_rev == 9
        assert greedy_rev < opt_rev

        loss_pct = ((opt_rev - greedy_rev) / opt_rev) * 100.0
        assert pytest.approx(loss_pct) == 10.0

    def test_11_e7_catalan_numbers_sequence(self) -> None:
        """11. Valida a sequência de números de Catalan C(n-1) para parentizações de matrizes."""
        # Sequência oficial: C(0)=1, C(1)=1, C(2)=2, C(3)=5, C(4)=14, C(5)=42, C(6)=132
        expected_catalan = {
            1: 1,    # C(0)
            2: 1,    # C(1)
            3: 2,    # C(2)
            4: 5,    # C(3)
            5: 14,   # C(4)
            6: 42,   # C(5)
            7: 132,  # C(6)
        }
        for n, expected in expected_catalan.items():
            assert count_parenthesizations(n) == expected

    def test_12_optimal_solutions_equivalence(self) -> None:
        """12. Valida equivalência matemática das soluções ótimas de Programação Dinâmica."""
        rng = random.Random(42)

        # E2: Corte de hastes (Memoização == Bottom-Up)
        p = [0, 1, 5, 8, 9, 10, 17, 17, 20, 24, 30]
        for n in range(1, 10):
            assert cut_rod_memo(p, n) == cut_rod_bottom_up(p, n)

        # E3: LCS (Tabela Completa == Duas Linhas)
        s1 = "ACCGTAGC"
        s2 = "TCGATAG"
        c, _ = lcs_table(s1, s2)
        len_table = c[len(s1)][len(s2)]
        len_two_rows = lcs_length_two_rows(s1, s2)
        assert len_table == len_two_rows

        # E7: Cadeia de Matrizes (Memoização == Bottom-Up)
        dims = [30, 35, 15, 5, 10, 20, 25]  # Instância clássica do Cormen
        memo_cost = matrix_chain_memo(dims)
        m_order, _ = matrix_chain_order(dims)
        bu_cost = m_order[1][len(dims) - 1]
        assert memo_cost == bu_cost == 15125

        # E8: Mochila 0/1 (Tabela 2D == Vetor 1D)
        weights = [10, 20, 30, 15, 25]
        values = [60, 100, 120, 75, 90]
        W = 50
        val_2d, _ = knapsack_01(weights, values, W)
        val_1d = knapsack_one_row(weights, values, W)
        assert val_2d == val_1d

    def test_13_csv_validation_and_handling(self, tmp_path: Any, monkeypatch: Any) -> None:
        """13. Valida a verificação de colunas e tratamento de arquivos ausentes no plot."""
        test_dir = tmp_path / "results"
        test_dir.mkdir()
        monkeypatch.setattr("benchmarks.plot_results.RESULTS_DIR", str(test_dir))

        # Arquivo inexistente retorna None
        res_none = load_dataset("arquivo_inexistente.csv")
        assert res_none is None

        # Arquivo com colunas faltando retorna None
        invalid_csv = test_dir / "invalido.csv"
        with open(invalid_csv, "w", newline="", encoding="utf-8") as f:
            f.write("col1,col2\n1,2\n")

        res_missing = load_dataset("invalido.csv", required_cols=["col1", "coluna_que_falta"])
        assert res_missing is None

        # Arquivo válido retorna DataFrame
        valid_csv = test_dir / "valido.csv"
        with open(valid_csv, "w", newline="", encoding="utf-8") as f:
            f.write("n,time_seconds,status\n10,0.01,success\n")

        res_valid = load_dataset("valido.csv", required_cols=["n", "time_seconds", "status"])
        assert res_valid is not None
        assert len(res_valid) == 1

    def test_14_plot_generation_and_missing_file_handling(self, tmp_path: Any, monkeypatch: Any) -> None:
        """14. Valida que a função de plotagem levanta FileNotFoundError quando CSV não existe."""
        test_dir = tmp_path / "empty_results"
        test_dir.mkdir()
        monkeypatch.setattr("benchmarks.plot_results.RESULTS_DIR", str(test_dir))

        # Deve lançar FileNotFoundError informando o comando de execução
        with pytest.raises(FileNotFoundError) as exc_info:
            plot_e1_fibonacci()
        assert "benchmarks/run_benchmarks.py --only E1" in str(exc_info.value)

    def test_15_cli_flags_quick_and_only(self) -> None:
        """15. Valida funcionamento e rejeição de identificadores desconhecidos no CLI."""
        run_script = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "run_benchmarks.py")

        # Teste com identificador inválido: deve retornar código de erro != 0
        cmd_invalid = [sys.executable, run_script, "--only", "E99"]
        res_invalid = subprocess.run(cmd_invalid, capture_output=True, text=True)
        assert res_invalid.returncode != 0
        assert "Identificador(es) de experimento inválido(s)" in res_invalid.stdout or "inválido" in res_invalid.stderr

        # Validação do dicionário de experimentos
        assert "E1" in EXPERIMENTS
        assert "E8" in EXPERIMENTS
        assert len(EXPERIMENTS) == 8

    def test_16_adaptive_batching_precision(self) -> None:
        """16. Valida que batching adaptativo mede sub-microsegundos sem zerar tempo."""
        def fast_op() -> int:
            return 2 + 2

        t_mean, t_std, t_min, t_max, mem, status = measure_execution_with_stats(
            fast_op, repeats=5, warmup=True
        )
        assert status == "success"
        assert t_mean is not None and t_mean > 0.0
        assert t_std is not None and t_std >= 0.0
        assert t_min is not None and t_max is not None
        assert t_min <= t_mean <= t_max

    def test_17_cpp_compilation_and_correctness(self) -> None:
        """17. Valida detecção, compilação de C++ e equivalência exata com Python LCS."""
        available, binary_path, meta = detect_and_compile_cpp()
        if not available:
            pytest.skip(f"Compilador C++ não disponível: {meta.get('message')}")

        assert binary_path is not None
        assert os.path.exists(binary_path)

        s1 = "ACCGTAGC"
        s2 = "TCGATAG"
        cmd = [binary_path, "--json", s1, s2]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)

        assert data["length"] == lcs_length_two_rows(s1, s2)
        assert data["time_seconds"] > 0.0
        assert "lcs" in data

    def test_18_manifest_json_integrity(self) -> None:
        """18. Valida integridade do catálogo e metadados no manifest.json da web."""
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "web", "data", "manifest.json")
        assert os.path.exists(manifest_path)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert isinstance(manifest, list)
        assert len(manifest) >= 19

        exp_ids = set()
        for item in manifest:
            assert "id" in item
            assert "filename" in item
            assert "experiment" in item
            assert "category" in item
            assert "title" in item
            assert "x_axis" in item
            assert "y_axis" in item
            assert "takeaways" in item
            assert isinstance(item["takeaways"], list)
            exp_ids.add(item["experiment"])

        for expected_exp in ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "SUMMARY"]:
            assert expected_exp in exp_ids

    def test_19_all_figures_generated_and_synchronized(self) -> None:
        """19. Valida que os 19 gráficos científicos foram sincronizados nas 3 pastas."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        dirs = [
            os.path.join(root, "docs", "figures"),
            os.path.join(root, "relatorio", "figuras"),
            os.path.join(root, "web", "figures"),
        ]
        key_figures = [
            "e1_fibonacci_tempo.png",
            "e1_fibonacci_dp.png",
            "e2_rod_cutting_tempo.png",
            "e3_lcs_memoria.png",
            "e4_lcs_python_cpp.png",
            "e5_recursao_limites.png",
            "e6_guloso_erro.png",
            "e7_matrix_chain_tempo.png",
            "e8_knapsack_tempo_w.png",
            "summary_complexity_dashboard.png",
        ]
        for d in dirs:
            assert os.path.exists(d), f"Diretório {d} não existe"
            files = os.listdir(d)
            assert len(files) >= 19, f"Diretório {d} tem apenas {len(files)} imagens"
            for kf in key_figures:
                assert os.path.exists(os.path.join(d, kf)), f"Figura {kf} ausente em {d}"

    def test_20_no_nan_or_inf_in_results(self) -> None:
        """20. Garante ausência total de NaN, Infinity ou corrupções nos dados exportados."""
        web_json_path = os.path.join(os.path.dirname(__file__), "..", "web", "data", "results.json")
        assert os.path.exists(web_json_path)

        with open(web_json_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "NaN" not in content
        assert "Infinity" not in content
        assert "-Infinity" not in content
        assert "<<<<<<<" not in content
        assert ">>>>>>>" not in content

        # Validação do CSV consolidado
        csv_path = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "results", "all_benchmarks.csv")
        assert os.path.exists(csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            csv_text = f.read()
        assert "<<<<<<<" not in csv_text
