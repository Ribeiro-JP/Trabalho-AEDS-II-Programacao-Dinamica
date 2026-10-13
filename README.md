# Estratégias Avançadas de Projeto e Análise de Algoritmos: Programação Dinâmica

Repositório público com a prova de conceito, suíte de experimentos empíricos, simuladores visuais e relatório técnico desenvolvidos para o Trabalho Teórico Final da disciplina de **Algoritmos e Estruturas de Dados II**.

---

## 1. Contexto Acadêmico

* **Instituição:** Centro Federal de Educação Tecnológica de Minas Gerais (CEFET-MG) -- Campus Divinópolis
* **Departamento:** Departamento de Computação
* **Disciplina:** Algoritmos e Estruturas de Dados II (AEDS-II)
* **Professor:** Michel Pires da Silva
* **Tema do Grupo:** Programação Dinâmica (Capítulo 15 do livro *Algoritmos: Teoria e Prática*, Cormen et al.)

### Equipe de Desenvolvimento

| Integrante | Papel Principal | Foco no Projeto |
| :--- | :--- | :--- |
| **João Gabriel** | Relatório Técnico Completo & Coordenação | Redação integral em LaTeX (Caps. 1 a 6) e coordenação geral |
| **João Pedro** | Códigos de Referência (Python & C++) | Algoritmos do Cormen, estudos de caso e `cpp/lcs.cpp` |
| **Alisson** | Benchmarks, Resultados & Web | Medições empíricas, gráficos a 200 DPI e portal web |
| **Carlos** | Apresentação e Slides do Seminário | Slides da apresentação de 40 min e dinâmicas de sala |
| **Paulo** | Cheat Sheet & Apoio Web | Resumo conciso de 1 a 2 páginas e auxílio no front-end web |

Consulte o checklist detalhado de cada membro em: 👉 [`docs/TAREFAS.md`](docs/TAREFAS.md).

---

## 2. O que é Programação Dinâmica? (Resumo em 5 Linhas)

A **Programação Dinâmica** é uma técnica avançada de projeto de algoritmos aplicada a problemas de otimização que apresentam **subestrutura ótima** e **superposição de subproblemas**. Em vez de recalcular recursivamente as mesmas soluções repetidas vezes (o que gera custo exponencial), ela resolve cada subproblema uma única vez e armazena seu resultado em memória (via **memoização** ou **tabulação bottom-up**). Ao reaproveitar soluções prévias, a técnica reduz complexidades exponenciais $\Theta(2^n)$ para tempos polinomiais como $\Theta(n^2)$ ou $\Theta(n^3)$, permitindo ainda a reconstrução exata da solução ótima a partir dos rastros (*traceback*) armazenados.

---

## 3. Estrutura do Repositório

```text
pd-programacao-dinamica/
├── README.md                     # Documentação principal e instruções de execução
├── LICENSE                       # Licença MIT de código aberto
├── Makefile                      # Automação de compilação, testes, web e relatórios
├── requirements.txt              # Dependências Python (pytest, matplotlib, pandas)
├── .gitignore                    # Filtros de arquivos temporários, caches e binários
├── .editorconfig                 # Padrões uniformes de indentação e codificação
├── conftest.py                   # Hook do pytest para marcar stubs como skipped
├── src/                          # Código fonte de referência em Python
│   ├── __init__.py
│   ├── common.py                 # Infraestrutura de medição (CallCounter e measure)
│   ├── fibonacci.py              # Stubs: Naive, Memo, Bottom-Up, O(1) Espaço
│   ├── rod_cutting.py            # Stubs: Corte de Hastes (Cormen 15.1) e Guloso
│   ├── matrix_chain.py           # Stubs: Multiplicação em Cadeia de Matrizes (Cormen 15.2)
│   ├── lcs.py                    # Stubs: Subsequência Comum Máxima (Cormen 15.4)
│   ├── knapsack.py               # Stubs: Mochila 0/1 (módulo opcional)
│   └── case_study/               # Estudos de caso práticos
│       ├── __init__.py
│       ├── diff_tool.py          # Comparador textual linha a linha via LCS
│       └── dna_alignment.py      # Alinhamento de fitas de DNA e distância de edição
├── cpp/
│   └── lcs.cpp                   # Implementação em C++17 para benchmark comparativo
├── data/                         # Arquivos pequenos de teste para os estudos de caso
├── tests/                        # Suíte completa de testes unitários com pytest
│   ├── test_fibonacci.py
│   ├── test_rod_cutting.py
│   ├── test_matrix_chain.py
│   ├── test_lcs.py
│   └── test_case_study.py
├── benchmarks/                   # Automação e geração de dados experimentais
│   ├── run_benchmarks.py         # Executor CLI com medições e tratamento de pendências
│   ├── plot_results.py           # Script para plotagem de gráficos padronizados (200 DPI)
│   └── results/.gitkeep
├── web/                          # Portal com simuladores visuais interativos
│   ├── index.html                # Menu principal de navegação funcional
│   ├── fib-tree.html             # Árvore de recursão e nós redundantes
│   ├── lcs-table.html            # Preenchimento animado da tabela do LCS e setas
│   ├── rod-cutting-duel.html     # Duelo interativo: Guloso vs. Programação Dinâmica
│   ├── matrix-chain.html         # Preenchimento por diagonais das matrizes m e s
│   ├── benchmarks.html           # Painel de gráficos renderizados a partir do JSON
│   ├── quiz.html                 # Quiz interativo de 8 perguntas com pontuação
│   ├── css/style.css             # Tema claro/escuro e paleta cromática imutável
│   ├── js/shared.js              # Utilitários JavaScript e gerenciador de tema
│   └── data/results.json         # Base consolidada de resultados experimentais
├── relatorio/                    # Relatório técnico-científico em LaTeX
│   ├── main.tex                  # Arquivo mestre com pré-ambulo, capa e seções
│   ├── referencias.bib           # Base de dados BibTeX com citações acadêmicas
│   ├── secoes/                   # Capítulos 1 a 6 e apêndice com anotações TODO
│   ├── tikz/.gitkeep
│   └── figuras/.gitkeep
├── cheatsheet/                   # Guia rápido sintetizado de 1 a 2 páginas
│   ├── cheatsheet.tex            # Documento autônomo compilável
│   └── cheatsheet_body.tex       # Corpo compartilhado também com o apêndice do relatório
├── slides/                       # Apresentação do seminário acadêmico (40 minutos)
│   ├── README.md                 # Diretrizes de elaboração, ferramentas e entregáveis
│   └── assets/.gitkeep
└── docs/                         # Documentação gerencial e de alinhamento da equipe
    ├── TAREFAS.md                # Quadro geral de tarefas e dependências
    ├── COMO_TRABALHAR_EM_GRUPO.md# Guia prático de branches, PRs e colaboração
    ├── RESUMO_TRABALHO.md        # Resumo conceitual dos conceitos e complexidades
    ├── ROTEIRO_SLIDES.md         # Roteiro minuto a minuto da apresentação oral
    ├── DECISOES.md               # Registro arquitetural das decisões de engenharia
    ├── figures/.gitkeep
    └── tarefas/                  # Arquivo individual com checklist para cada integrante
```

---

## 4. Instalação e Preparação do Ambiente

### Pré-requisitos
* Python 3.11 ou superior
* Compilador C++17 (`g++`)
* `latexmk` ou conta no Overleaf (para compilação do relatório)

### Passo a Passo

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/Ribeiro-JP/Trabalho-AEDS-II-Programaco-Dinamica.git
   cd Trabalho-AEDS-II-Programaco-Dinamica
   ```

2. **Criar o ambiente virtual e instalar dependências:**
   ```bash
   make setup
   ```

3. **Ativar o ambiente virtual:**
   ```bash
   source .venv/bin/activate
   ```

---

## 5. Como Executar Cada Parte do Projeto

| Comando | Descrição da Ação |
| :--- | :--- |
| `make test` | Executa a suíte de testes com `pytest`. Testes de funções ainda não implementadas aparecem automaticamente como `SKIPPED`. |
| `make bench` | Executa a suíte completa de experimentos empíricos (E1 a E8). |
| `make bench-quick` | Executa os benchmarks em modo rápido (menos repetições e instâncias menores). |
| `make cpp` | Compila o algoritmo LCS em C++17 (`cpp/lcs.cpp`) gerando o binário `cpp/lcs`. |
| `make web` | Inicia o servidor HTTP local servindo o portal interativo em **`http://localhost:8000/web/`**. |
| `make report` | Compila o relatório acadêmico em PDF utilizando `latexmk` (se instalado localmente). |
| `make clean` | Remove arquivos de cache, `.pytest_cache`, binários compilados e artefatos do LaTeX. |

---

## 6. Quadro de Status por Frente de Trabalho

Acompanhe o detalhamento completo e a ordem sugerida de paralelismo em [`docs/TAREFAS.md`](docs/TAREFAS.md).

- [ ] **Relatório Técnico (LaTeX):**
  - [ ] Capítulos 1, 2 e 6 (P1)
  - [ ] Capítulos 3 e 4 com `algorithm2e` e TikZ (P2)
  - [ ] Capítulo 5 com análise crítica dos benchmarks (P4)
- [ ] **Implementação Base em Python (P3):**
  - [ ] Fibonacci (`fibonacci.py`)
  - [ ] Corte de Hastes (`rod_cutting.py`)
  - [ ] Cadeia de Matrizes (`matrix_chain.py`)
  - [ ] Subsequência Comum Máxima (`lcs.py`)
  - [ ] Mochila 0/1 (`knapsack.py` - opcional)
- [ ] **Estudos de Caso e Benchmarks (P4):**
  - [ ] Mini Diff (`diff_tool.py`) e Alinhamento de DNA (`dna_alignment.py`)
  - [ ] Experimentos E1 a E7 (e E8 opcional) com `run_benchmarks.py`
  - [ ] Gráficos científicos a 200 DPI com `plot_results.py`
  - [ ] Comparativo de linguagem Python vs. C++17 (`cpp/lcs.cpp`)
- [ ] **Portal Web Interativo (P5):**
  - [x] Menu principal responsivo com alternância de tema claro/escuro (`index.html`)
  - [ ] Visualizador de árvore do Fibonacci (`fib-tree.html`)
  - [ ] Duelo Guloso vs. PD no corte de hastes (`rod-cutting-duel.html`)
  - [ ] Preenchimento por diagonais da cadeia de matrizes (`matrix-chain.html`)
  - [ ] Animação passo a passo da tabela do LCS (`lcs-table.html`)
  - [ ] Painel interativo de gráficos de benchmark (`benchmarks.html`)
  - [ ] Quiz conceitual com 8 questões (`quiz.html`)
- [ ] **Comunicação e Apresentação:**
  - [ ] Cheat Sheet de 1 a 2 páginas em LaTeX (`cheatsheet/cheatsheet.tex`) (P5/P2)
  - [ ] Slides do seminário de 40 minutos (`slides/`) (P5/Todos)
  - [ ] Ensaio geral cronometrado com perguntas cruzadas (Todos)

---

## 7. Passo a Passo do Desenvolvimento Planejado

Para consulta rápida da equipe, o cronograma operacional divide-se nas seguintes etapas fundamentais:
1. **Infraestrutura e Contratos:** Estrutura de diretórios, Makefile, `conftest.py`, `src/common.py` e assinaturas com `raise NotImplementedError`.
2. **Testes Unitários:** Casos canônicos do livro do Cormen, casos de borda e equivalências assintóticas validadas em `tests/`.
3. **Desenvolvimento Algorítmico (P3):** Preenchimento sucessivo dos algoritmos base até todos os testes passarem.
4. **Instrumentação Empírica (P4):** Execução dos experimentos com corte de 10s, medição de pico de memória via `tracemalloc` e compilação do LCS em C++17.
5. **Comunicação Visual e Web (P5):** Desenvolvimento dos simuladores em HTML/JS puros e confecção dos slides para 40 minutos.
6. **Redação do Relatório (P1 e P2):** Formalização teórica, pseudocódigos em `algorithm2e`, diagramas TikZ e montagem no Overleaf.
7. **Revisão Cruzada e Ensaio:** Validação mútua do código e ensaio da apresentação oral.

---

## 8. Resultados Experimentais

Esta seção sintetiza os principais achados práticos obtidos a partir dos benchmarks automatizados (experimentos E1 a E8), confrontando as previsões assintóticas do livro do Cormen com medições reais de tempo de execução, consumo de memória e qualidade das soluções.

### Tabela-Resumo dos Experimentos

| Experimento | Resultado observado | O que isso demonstra |
| :--- | :--- | :--- |
| **E1 — Fibonacci**<br>([gráfico](docs/figures/e1_fibonacci_tempo.png)) | Em $n=30$, a força bruta consumiu **0,84 s**, enquanto a PD com espaço $O(1)$ levou **1,32 $\mu$s** (speedup $> 600.000\times$). Para $n > 32$, a força bruta foi interrompida por timeout. | A superposição massiva de subproblemas torna a recursão ingênua $\Theta(2^n)$ impraticável em poucos passos, enquanto a PD reduz o custo para tempo linear $\Theta(n)$. |
| **E2 — Corte de Hastes**<br>([gráfico](docs/figures/e2_rod_cutting_tempo.png)) | A força bruta atingiu **31,9 ms** em $n=15$, dobrando o tempo a cada novo centímetro. A PD resolveu $n=100$ em apenas **2,08 ms**. | Substituir uma árvore recursiva redundante $\Theta(2^n)$ por uma tabela de subproblemas $\Theta(n^2)$ permite resolver instâncias de produção em milissegundos. |
| **E3 — Memória no LCS**<br>([gráfico](docs/figures/e3_lcs_memoria.png)) | Em cadeias de $n=1000$, a matriz completa consumiu **19,6 MB** de heap, enquanto a técnica de duas linhas exigiu apenas **42,9 KB** (redução de **99,8%**). | A dependência de transição do LCS exige apenas a linha anterior. Quando o rastreamento da string (*traceback*) não é exigido, a economia de espaço é drástica. |
| **E4 — CPython vs. C++17**<br>([gráfico](docs/figures/e4_lcs_python_cpp.png)) | Para sequências de $n=1000$, o C++ (`-O3`) executou em **8,5 ms** contra **446 ms** do Python 3.11 (speedup empírico de **$52{,}2\times$**). | Ambos possuem a mesma complexidade assintótica $\Theta(mn)$, mas fatores constantes (alocação estática contígua, compilação nativa e ausência de *boxing*) tornam o C++ muito mais veloz. |
| **E5 — Limite de Recursão**<br>([gráfico](docs/figures/e5_recursao_limites.png)) | A memoização Top-Down falhou com `RecursionError` exatamente em $n=1000$ (limite da pilha do interpretador). O Bottom-Up iterativo seguiu estável em $n=1200$ (**0,61 ms**). | O modelo Bottom-Up possui maior robustez de engenharia, pois opera iterativamente na memória heap, imune a limitações de profundidade da pilha recursiva. |
| **E6 — Falha do Guloso**<br>([gráfico](docs/figures/e6_guloso_erro.png)) | A heurística gulosa pela razão de densidade ($p_i / i$) falhou em até **34%** das instâncias randômicas testadas (ex.: em $n=25$), com perda média de receita de até **6,04%**. | Problemas que não satisfazem a *propriedade da escolha gulosa* exigem Programação Dinâmica; decisões localmente atraentes não garantem a solução ótima global. |
| **E7 — Cadeia de Matrizes**<br>([gráfico](docs/figures/e7_matrix_chain_tempo.png)) | Para $n=50$ matrizes, existem $\approx 5{,}1 \times 10^{26}$ ordens possíveis de parênteses (números de Catalan). A PD Bottom-Up encontrou a ordem ótima em apenas **11,7 ms**. | A busca exaustiva combinatória é inexecutável na prática, enquanto a PD resolve o problema em tempo cúbico $\Theta(n^3)$ reaproveitando soluções parciais. |
| **E8 — Mochila 0/1**<br>([gráfico](docs/figures/e8_knapsack_memoria.png)) | O vetor 1D reduziu o pico de memória de **1,6 MB** para **39,2 KB** em $W=1000$ (**97,5%** de economia). O tempo de execução cresceu linearmente com o valor da capacidade $W$. | Comprova experimentalmente o caráter *pseudo-polinomial* $\Theta(nW)$: a complexidade do algoritmo depende da magnitude numérica de $W$, e não apenas da quantidade de itens. |

> 📊 **Dashboard Unificado:** Para visualizar o contraste empírico direto entre as ordens assintóticas ($\Theta(2^n)$, $\Theta(n^3)$, $\Theta(n^2)$ e $\Theta(n)$), consulte [`docs/figures/summary_complexity_dashboard.png`](docs/figures/summary_complexity_dashboard.png).

### Principais Conclusões Didáticas

1. **Quando a Programação Dinâmica é indispensável?** Quando o problema exibe *subestrutura ótima* e *superposição de subproblemas*, mas a *propriedade da escolha gulosa* não se sustenta. O experimento E6 prova que tentar simplificar o problema com uma heurística gulosa sem prova teórica gera perdas financeiras concretas em até 1 a cada 3 instâncias.
2. **Top-Down (Memoização) vs. Bottom-Up (Tabulação):** Ambas as abordagens oferecem a mesma complexidade assintótica de tempo. No entanto, o Bottom-Up evita o overhead da pilha de execução de funções e elimina riscos de interrupção abrupta por limite de recursão, como evidenciado no E5.
3. **Trade-off clássico de Espaço vs. Recuperação da Solução:** Se o objetivo é apenas obter o valor ótimo (ex.: comprimento da subsequência ou lucro máximo da mochila), vetores rotativos ou de linha única economizam mais de 97% de memória (E3 e E8). Já quando é necessário reconstruir a solução concreta (*traceback*), a matriz bidimensional completa torna-se obrigatória.
4. **Constantes Ocultas na Notação Big-O:** O experimento E4 comprova aos estudantes que dois algoritmos $\Theta(mn)$ podem ter tempos drasticamente diferentes na prática ($52\times$ de diferença entre C++ e Python), ressaltando a relevância da arquitetura de execução e alocação de memória do hardware.

> [!WARNING]
> **Limitações Experimentais Observadas:**
> * **Timeouts de Segurança:** Nos algoritmos puramente recursivos (E1 e E2), as medições foram truncadas em $n \le 30$ e $n \le 15$ por limite de tempo (10s) para evitar travamento do ambiente.
> * **Ausência de Dados Pós-Limite:** No experimento E5, não há tempos de execução para a memoização Top-Down acima de $n=1000$ em virtude do `RecursionError`.
> * **Medições vs. Provas Matemáticas:** Os tempos reportados foram aferidos empiricamente com `time.perf_counter()` em CPython 3.11 / GCC 6.3. As classes de complexidade indicam o comportamento assintótico teórico, mas flutuações de hardware e sistema operacional geram variações nas ordens de grandeza das constantes.

---

## 9. Gargalos Observados

*(a preencher por P4 depois dos benchmarks)*

> [!NOTE]
> Esta seção documentará os gargalos reais de hardware e arquitetura identificados durante os testes práticos (limite de recursão da pilha do interpretador Python, estouro de memória da tabela bidimensional do LCS em sequências biológicas longas e o impacto da localidade espacial de cache).

---

## 10. Limitações da Técnica

*(a preencher por P4 depois dos benchmarks)*

> [!NOTE]
> Esta seção sintetizará os cenários computacionais onde a Programação Dinâmica se torna inviável ou ineficaz (problemas sem subestrutura ótima como o caminho simples mais longo, complexidade pseudo-polinomial da mochila e explosão combinatória do espaço de estados em problemas NP-difíceis como o Caixeiro Viajante).

---

## 11. Referências

1. CORMEN, Thomas H.; LEISERSON, Charles E.; RIVEST, Ronald L.; STEIN, Clifford. **Algoritmos: Teoria e Prática**. 3. ed. Rio de Janeiro: Elsevier, 2012. Capítulo 15: Programação Dinâmica, p. 263-305.
2. BELLMAN, Richard. **Dynamic Programming**. Princeton University Press, 1957.
3. NEEDLEMAN, Saul B.; WUNSCH, Christian D. A general method applicable to the search for similarities in the amino acid sequence of two proteins. **Journal of Molecular Biology**, v. 48, n. 3, p. 443-453, 1970.

---

## 12. Licença

Este projeto é distribuído sob a licença **MIT**. Consulte o arquivo [`LICENSE`](LICENSE) para mais detalhes.
