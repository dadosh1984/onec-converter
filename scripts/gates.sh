#!/usr/bin/env bash
# Ворота проекта onec-converter: pytest, ruff, mypy, vitest, MCP-conformance.
# Использование:
#   bash scripts/gates.sh                 # все ворота
#   bash scripts/gates.sh pytest          # только одну проверку
#   bash scripts/gates.sh conformance     # E2E conformance MCP-сервера (Фаза 23)
#   bash scripts/gates.sh --strict-steps  # все ворота, skip-шаги роняют (для CI)
#   bash scripts/gates.sh --coverage pytest  # pytest + порог покрытия 70%
#       (pytest-cov на модулях Фаз 29-31: objects_filter, jwt_auth, cache,
#        http_client, mcp_server — новые модули; см. Фазу 23)
#
# Временные файлы (копии реальных .1CD, сотни МБ) кладутся в базовый tmp.
# По умолчанию /tmp; для больших баз задайте ONEC_TEST_TMP на диск с местом:
#   ONEC_TEST_TMP=E:/test/.pytest-tmp bash scripts/gates.sh
#
# vitest выполняется только если настроен (есть package.json и *.test.ts);
# иначе — skip с предупреждением (в непростом клоне нет node-инструментов).
set -euo pipefail

ONEC_TEST_TMP="${ONEC_TEST_TMP:-${TMPDIR:-/tmp}/onec-pytest}"

# Тесты всегда в E:\test (см. AGENTS.md): tmp-каталог pytest на диск с местом.
# Задаём basetemp и корневой pytest-кеш (tempfile) на ONEC_TEST_TMP.
if [[ -n "${ONEC_TEST_TMP:-}" ]]; then
  mkdir -p "$ONEC_TEST_TMP"
  export TMPDIR="$ONEC_TEST_TMP"
  export TEMP="$ONEC_TEST_TMP"
  export TMP="$ONEC_TEST_TMP"
  export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} --basetemp=${ONEC_TEST_TMP}"
fi
STRICT_STEPS=0
COVERAGE=0
ARGS=()
for a in "$@"; do
  case "$a" in
    --strict-steps) STRICT_STEPS=1 ;;
    --coverage) COVERAGE=1 ;;
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

# Модули Фаз 29-31 (новые) — порог покрытия 70% (Фаза 23).
COVERAGE_MODULES=(objects_filter jwt_auth cache http_client mcp_server)
COV_ARGS=()
if [[ "$COVERAGE" == "1" ]]; then
  for m in "${COVERAGE_MODULES[@]}"; do
    COV_ARGS+=(--cov=onec_converter.$m)
  done
  COV_ARGS+=(--cov-report=term --cov-fail-under=70)
fi

run_pytest() {
  echo "== pytest ${COV_ARGS[*]:+(${COV_ARGS[*]})} =="
  PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} --basetemp=${ONEC_TEST_TMP}" python -m pytest -q "${COV_ARGS[@]}"
}
run_conformance() {
  echo "== MCP conformance =="
  PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} --basetemp=${ONEC_TEST_TMP}" \
    python -m pytest tests/test_mcp_conformance.py -q
}
run_ruff() {
  echo "== ruff =="
  python -m ruff check src tests
}
run_mypy() {
  echo "== mypy (strict) =="
  python -m mypy src
}

run_bsl() {
  echo "== check_bsl (расширение 1С) =="
  python scripts/check_bsl.py || return 1
}

run_docker() {
  echo "== docker build (опц.) =="
  if ! command -v docker >/dev/null 2>&1; then
    echo "  docker недоступен — пропуск"
    return 0
  fi
  docker build -t onec-converter:ci . >/dev/null 2>&1 || {
    echo "  docker build: недоступен/нет сети — пропуск"; return 0; }
  echo "  docker build ok"
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
  conformance) run_conformance ;;
  bsl)    run_bsl ;;
  docker) run_docker ;;
  all)    run_pytest && run_conformance && run_ruff && run_mypy && run_bsl && run_vitest && run_docker ;;
  *) echo "неизвестная цель: $TARGET (pytest|ruff|mypy|vitest|conformance|bsl|docker|all|--strict-steps|--coverage)" >&2; exit 2 ;;
esac
