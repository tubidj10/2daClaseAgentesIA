#!/usr/bin/env bash
# Comando único de ejecución: instala dependencias y corre el runner.
# Uso: ./run.sh "mensaje del usuario"
#
# Requisito previo (una sola vez, no automatizable por diseño: es una
# credencial secreta que nunca debe vivir en un script versionado):
#   cp .env.example .env   # y completar ANTHROPIC_API_KEY
set -euo pipefail

if [ $# -eq 0 ]; then
  echo 'Uso: ./run.sh "mensaje del usuario"' >&2
  exit 1
fi

cd "$(dirname "$0")"
pip install -q -r requirements.txt
python3 runner.py "$1"
