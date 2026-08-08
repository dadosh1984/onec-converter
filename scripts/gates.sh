#!/usr/bin/env bash
# Ворота проекта onec-converter: pytest, ruff, mypy, vitest.
# Использование:
#   bash scripts/gates.sh                 # все ворота
#   bash scripts/gates.sh pytest          # только одну проверку
#   bash scripts/gates.sh --strict-steps  # все ворота, skip-шаги роняют (для CI)
#
# Временные файлы (копии реальных .1CD, сотни МБ) кладутся в базовый tmp.
# По умолчанию /tmp; для больших баз задайте ONEC_TEST_TMP на диск с местом:
#   ONEC_TEST_TMP=E:/test/.pytest-tmp bash scripts/gates.sh
#
# vitest выполняется только если настроен (есть package.json и *.test.ts);
# иначе — skip с предупреждением (в непростом клоне нет node-инструментов).
set -euo pipefail

ONEC_TEST_TMP="${ONEC_TEST_TMP:-${TMPDIR:-/tmp}/onec-pytest}"
STRICT_STEPS=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --strict-steps) STRICT_STEPS=1 ;;
    *) ARGS+=("$a") ;;
  esac
done

vitest_configured() {
  # vitest есть, только когда настроен JS-воркспейс (package.json + тесты)
  [[ -f package.json ]] && compgen -G 'tests/*.test.ts' >/dev/null
}

skip_or_fail() {
  # шаг без реальной проверки: при --strict-steps падаем, иначе skip
  echo "[skip] $1"
  if [[ "$STRICT_STEPS" == "1" ]]; then
    return 1
  fi
  return 0
}

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
  if vitest_configured; then
    echo "== vitest =="
    npx vitest run
  else
    skip_or_fail "vitest (не настроен: нет package.json/*.test.ts)"
    return "$?"
  fi
}

TARGET="${ARGS[0]:-all}"
case "$TARGET" in
  pytest) run_pytest ;;
  ruff)   run_ruff ;;
  mypy)   run_mypy ;;
  vitest) run_vitest ;;
  all)    run_pytest && run_ruff && run_mypy && run_vitest ;;
  *) echo "неизвестная цель: $TARGET (pytest|ruff|mypy|vitest|all|--strict-steps)" >&2; exit 2 ;;
esac
