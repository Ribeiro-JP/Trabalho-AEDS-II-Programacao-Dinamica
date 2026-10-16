.PHONY: all setup test bench bench-quick cpp web clean help

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip
PYTEST ?= $(VENV)/bin/pytest

all: help

help:
	@echo "Alvos disponíveis no Makefile:"
	@echo "  make setup        - Cria o ambiente virtual .venv e instala dependências"
	@echo "  make test         - Executa a suíte de testes com pytest"
	@echo "  make bench        - Executa todos os benchmarks"
	@echo "  make bench-quick  - Executa os benchmarks em modo rápido"
	@echo "  make cpp          - Compila a implementação C++ de LCS (cpp/lcs.cpp)"
	@echo "  make web          - Inicia servidor local em http://localhost:8000/web/"
	@echo "  make clean        - Remove caches, binários e artefatos de compilação"

setup:
	@echo "Configurando ambiente virtual e dependências..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "Ambiente configurado com sucesso! Ative com: source $(VENV)/bin/activate"

test:
	@if [ -f "$(PYTEST)" ]; then \
		$(PYTEST) tests/ -v; \
	elif command -v pytest >/dev/null 2>&1; then \
		pytest tests/ -v; \
	else \
		python3 -m pytest tests/ -v; \
	fi

bench:
	@if [ -f "$(PYTHON)" ]; then \
		$(PYTHON) benchmarks/run_benchmarks.py; \
	else \
		python3 benchmarks/run_benchmarks.py; \
	fi

bench-quick:
	@if [ -f "$(PYTHON)" ]; then \
		$(PYTHON) benchmarks/run_benchmarks.py --quick; \
	else \
		python3 benchmarks/run_benchmarks.py --quick; \
	fi

cpp:
	@mkdir -p cpp
	g++ -O3 -std=c++17 cpp/lcs.cpp -o cpp/lcs
	@echo "Binário compilado com sucesso em cpp/lcs"

web:
	@echo "Iniciando servidor web em http://localhost:8000/web/ (Pressione Ctrl+C para encerrar)..."
	python3 -m http.server 8000

clean:
	@echo "Limpando artefatos e arquivos temporários..."
	rm -rf __pycache__ tests/__pycache__ src/__pycache__ src/case_study/__pycache__ benchmarks/__pycache__ .pytest_cache
	rm -f cpp/lcs
	@echo "Limpeza concluída."
