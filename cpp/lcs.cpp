/**
 * @file lcs.cpp
 * @brief Implementação de referência em C++17 do algoritmo LCS (Cormen 15.4)
 *        para o experimento E4 (comparativo de desempenho Python x C++).
 *
 * Responsável: Integrante P4 (ver docs/tarefas/P4_estudo_de_caso_e_benchmarks.md).
 */

#include <iostream>
#include <string>
#include <vector>
#include <chrono>
#include <algorithm>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

int main(int argc, char* argv[]) {
    std::vector<std::string> positional;
    bool json_mode = false;
    for (int idx = 1; idx < argc; ++idx) {
        std::string arg = argv[idx];
        if (arg == "--json") {
            json_mode = true;
        } else {
            positional.push_back(arg);
        }
    }

    std::string a = "ABCBDAB";
    std::string b = "BDCABA";
    if (positional.size() >= 2) {
        a = positional[0];
        b = positional[1];
    }

    if (!json_mode) {
        std::cout << "[CPP - LCS] Iniciando experimento E4..." << std::endl;
        std::cout << "String A: \"" << a << "\" (len=" << a.length() << ")" << std::endl;
        std::cout << "String B: \"" << b << "\" (len=" << b.length() << ")\n" << std::endl;
    }

    int m = a.length();
    int n = b.length();

    // Batching adaptativo para entradas pequenas garantindo resolução do clock
    int iterations = 1;
    if (m * n < 50000 && m * n > 0) {
        iterations = std::max(1, 50000 / (m * n));
    }

    // Tabela DP inicializada com zeros
    std::vector<std::vector<int>> c(m + 1, std::vector<int>(n + 1, 0));
    std::string lcs_str = "";

    // Início da medição de tempo de CPU
#ifdef _WIN32
    LARGE_INTEGER qpc_freq, qpc_start, qpc_end;
    QueryPerformanceFrequency(&qpc_freq);
    QueryPerformanceCounter(&qpc_start);
#else
    auto start_time = std::chrono::high_resolution_clock::now();
#endif

    for (int iter = 0; iter < iterations; ++iter) {
        // 2. Construção da Tabela DP (Bottom-Up)
        for (int i = 1; i <= m; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (a[i - 1] == b[j - 1]) {
                    c[i][j] = c[i - 1][j - 1] + 1;
                } else {
                    c[i][j] = std::max(c[i - 1][j], c[i][j - 1]);
                }
            }
        }

        // 3. Reconstrução (Traceback) na última iteração
        if (iter == iterations - 1) {
            lcs_str.clear();
            int i = m;
            int j = n;

            while (i > 0 && j > 0) {
                if (a[i - 1] == b[j - 1]) {
                    lcs_str.push_back(a[i - 1]);
                    i--;
                    j--;
                } else if (c[i - 1][j] >= c[i][j - 1]) {
                    i--;
                } else {
                    j--;
                }
            }
            std::reverse(lcs_str.begin(), lcs_str.end());
        }
    }

    // Fim da medição de tempo
#ifdef _WIN32
    QueryPerformanceCounter(&qpc_end);
    double elapsed_seconds = static_cast<double>(qpc_end.QuadPart - qpc_start.QuadPart) / (qpc_freq.QuadPart * iterations);
    double elapsed_us = elapsed_seconds * 1000000.0;
    double elapsed_ms = elapsed_seconds * 1000.0;
#else
    auto end_time = std::chrono::high_resolution_clock::now();
    auto total_us = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time).count();
    double elapsed_us = static_cast<double>(total_us) / iterations;
    double elapsed_ms = elapsed_us / 1000.0;
    double elapsed_seconds = elapsed_us / 1000000.0;
#endif


    if (json_mode) {
        std::cout << "{\"length\":" << c[m][n]
                  << ",\"lcs\":\"" << lcs_str << "\""
                  << ",\"time_seconds\":" << (elapsed_us / 1000000.0)
                  << ",\"time_us\":" << elapsed_us << "}" << std::endl;
    } else {
        // 4. Saída formatada dos resultados para o Benchmark
        std::cout << "---------------- RESULTADOS ----------------" << std::endl;
        std::cout << "Comprimento da LCS : " << c[m][n] << std::endl;
        std::cout << "String da LCS      : \"" << lcs_str << "\"" << std::endl;
        std::cout << "Tempo de Execução  : " << elapsed_us << " us (" << elapsed_ms << " ms)" << std::endl;
        std::cout << "--------------------------------------------" << std::endl;
    }

    return 0;
}
