"""Multiplicação em Cadeia de Matrizes (Matrix-Chain Multiplication) - Cormen Seção 15.2.

Dada uma cadeia de n matrizes <A_1, A_2, ..., A_n> onde a matriz A_i tem dimensão
p_{i-1} x p_i (representada pelo vetor dims de tamanho n+1), determinar a ordem de
parentização ótima que minimiza o número total de multiplicações escalares.

Recorrência fundamental:
    m[i, i] = 0, para todo 1 <= i <= n
    m[i, j] = min_{i <= k < j} { m[i, k] + m[k+1, j] + p_{i-1} * p_k * p_j }, para i < j

A tabela auxiliar s[i, j] registra o índice k que produziu o custo mínimo para o subproblema (i, j).
"""
from __future__ import annotations

import math

from .common import CallCounter


def matrix_chain_naive(dims: list[int], counter: CallCounter | None = None,
        i: int = 1, j: int | None = None) -> int:
    """Calcula o custo mínimo de multiplicação por recursão ingênua sem memoização.

    Explora exaustivamente todas as divisões possíveis da cadeia.

    Complexidade:
        Tempo: Executa 3^(n-1) chamadas recursivas (ou 2*3^(n-1) - 1, limitadas inferiormente por Omega(2^n)),
               enquanto o espaço combinatório total de parentizações corresponde aos números de
               Catalan C_{n-1} = Omega(4^n / n^(3/2)) (Cormen §15.2).
        Espaço: O(n) na pilha de recursão.

    Args:
        dims: Lista de dimensões onde matriz i tem tamanho dims[i-1] x dims[i].
        counter: Instância opcional de CallCounter para registrar invocações.

    Returns:
        O número mínimo de multiplicações escalares necessárias.
    """
    if counter is not None:
        counter.increment()

    if j is None:
        j = len(dims) - 1

    if len(dims) < 3 or i >= j:
        return 0

    min_cost = float('inf')

    for k in range(i, j):
        cost = (
            matrix_chain_naive(dims, counter, i, k)
            + matrix_chain_naive(dims, counter, k + 1, j)
            + dims[i - 1] * dims[k] * dims[j]
        )
        if cost < min_cost:
            min_cost = cost

    return min_cost


def matrix_chain_memo(    dims: list[int], 
    counter: CallCounter | None = None, 
    i: int = 1, 
    j: int | None = None,
    memo: dict[tuple[int, int], int] | None = None) -> int:
    """Calcula o custo mínimo com recursão e memoização (Top-Down).

    Utiliza uma tabela/dicionário para salvar os custos dos subproblemas (i, j).

    Complexidade:
        Tempo: Theta(n^3).
        Espaço: Theta(n^2) para a tabela de memoização e O(n) de pilha.

    Args:
        dims: Lista de dimensões onde matriz i tem tamanho dims[i-1] x dims[i].

    Returns:
        O número mínimo de multiplicações escalares necessárias.
    """
    if counter is not None:
        counter.increment()

    if j is None:
        j = len(dims) - 1
    if memo is None:
        memo = {}

    if len(dims) < 3 or i >= j:
        return 0

    if (i, j) in memo:
        return memo[(i, j)]

    min_cost = float('inf')

    for k in range(i, j):
        cost = (
            matrix_chain_memo(dims, counter, i, k, memo)
            + matrix_chain_memo(dims, counter, k + 1, j, memo)
            + dims[i - 1] * dims[k] * dims[j]
        )
        if cost < min_cost:
            min_cost = cost

    memo[(i, j)] = min_cost
    return min_cost


def matrix_chain_order(dims: list[int]) -> tuple[list[list[int]], list[list[int]]]:
    """Calcula a ordem ótima de multiplicação usando Bottom-Up (Matrix-Chain-Order do Cormen).

    Preenche as tabelas m e s por comprimento crescente de subcadeia (l = 2..n),
    calculando as diagonais sucessivas.

    Complexidade:
        Tempo: Theta(n^3) - laço triplo (comprimento l, início i, ponto de corte k).
        Espaço: Theta(n^2) para as matrizes m (custos) e s (pontos de corte).

    Args:
        dims: Lista de dimensões com comprimento n + 1 para n matrizes.

    Returns:
        Tupla contendo:
            - m: Tabela 2D onde m[i][j] é o custo mínimo de multiplicar A_i..A_j (1-indexado).
            - s: Tabela 2D onde s[i][j] é o ponto de corte ótimo k (1-indexado).
    """
    n = len(dims) - 1
    
    m = [[0] * (n + 1) for _ in range(n + 1)]
    s = [[0] * (n + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        m[i][i] = 0
        
    for l in range(2, n + 1):
        for i in range(1, n - l + 2):
            j = i + l - 1
            m[i][j] = float('inf')
            
            for k in range(i, j):
                cost = m[i][k] + m[k + 1][j] + dims[i - 1] * dims[k] * dims[j]
                
                if cost < m[i][j]:
                    m[i][j] = cost
                    s[i][j] = k  
                    
    return m, s


def optimal_parens(s: list[list[int]], i: int, j: int) -> str:
    """Reconstrói a expressão com a parentização ótima das matrizes de i a j.

    Produz uma string legível como '((A1(A2A3))((A4A5)A6))' correspondente
    ao algoritmo Print-Optimal-Parens do Cormen.

    Args:
        s: Tabela com os pontos ótimos de corte k gerada por matrix_chain_order.
        i: Índice inicial da subcadeia (1-indexado).
        j: Índice final da subcadeia (1-indexado).

    Returns:
        String representando a parentização ótima.
    """
    if i == j:
        return f"A{i}"
        
    k = s[i][j]
    
    left_side = optimal_parens(s, i, k)
    right_side = optimal_parens(s, k + 1, j)
    
    return f"({left_side}{right_side})"


def count_parenthesizations(n: int) -> int:
    """Calcula a quantidade de parentizações possíveis para uma cadeia de n matrizes.

    Corresponde ao número de Catalan C(n-1):
        P(n) = C(n-1) = (1 / n) * binom(2n - 2, n - 1)
    Para n = 1..6, gera respectivamente 1, 1, 2, 5, 14, 42.

    Complexidade:
        Tempo: O(n).
        Espaço: O(1).

    Args:
        n: Quantidade de matrizes na cadeia (n >= 1).

    Returns:
        Número total de maneiras distintas de parentizar o produto de n matrizes.
    """
    if n <= 1:
        return 1
        
    k = n - 1
    return math.comb(2 * k, k) // (k + 1)
