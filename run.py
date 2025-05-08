# ~/aura_ide/run.py
import sys
import os

# Adiciona o diretório 'src' ao sys.path para que o pacote 'aura_ide' seja encontrado
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from aura_ide.main import run_app

if __name__ == '__main__':
    run_app()