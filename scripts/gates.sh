#!/usr/bin/env bash
# Ворота проекта onec-converter: pytest, ruff, mypy, vitest.
# Использование:
#   bash scripts/gates.sh                 # все ворота
#   bash scripts/gates.sh pytest          # только одну проверку
#
# Временные файлы (копии реальных .1CD, сотни МБ) кладутся в базовый tmp.
# По умолчанию /tmp; для больших баз задайте ONEC_TEST_TMP на диск с местом:
#   ONEC_TEST_TMP=E:/test/.pytest-tmp bash scripts/gates.sh
set -euo pipefail

ONEC_TEST_TMP="${ONEC_TEST_TMP:-${TMPDIR:-/tmp}/onec-pytest}"

run_pytest() {
  echo "== pytest =="
  PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} --basetemp=${ONEC_TEST_TMP}" python -m pytest -q
}
run_ruff() {
  echo "== ruff =="
  python -m ruff check src tests
}
run_mypy() {
  echo "== mypy (strict) =="
  python -m mypy src
}
run_vitest() {
  echo "== vitest =="
  npx vitest run
}

case "${1:-all}" in
  pytest) run_pytest ;;
  ruff)   run_ruff ;;
  mypy)   run_mypy ;;
  vitest) run_vitest ;;
  all)    run_pytest && run_ruff && run_mypy && run_vitest ;;
  *) echo "неизвестная цель: $1 (pytest|ruff|mypy|vitest|all)" >&2; exit 2 ;;
esac
