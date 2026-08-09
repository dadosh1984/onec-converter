# onec-converter — стандартные цели разработки (Фаза 39).
# Прогон ворот: по умолчанию полные (pytest/ruff/mypy/bsl/vitest).
# Замечание: тесты используют basetemp на E: (см. scripts/gates.sh).

PY ?= python
TARGET ?= all

.PHONY: install lint type bsl test bdd gates release bench clean

install:
	$(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check src tests scripts

type:
	$(PY) -m mypy src

bsl:
	$(PY) scripts/check_bsl.py

test:
	ONEC_TEST_TMP="E:/tmp/.pytest-tmp" $(PY) -m pytest -q

# сквозные BDD-сценарии миграции
bdd:
	ONEC_TEST_TMP="E:/tmp/.pytest-tmp" $(PY) -m pytest tests/test_bdd_scenario.py -q

# полные ворота через scripts/gates.sh (ставит basetemp на E:)
gates:
	bash scripts/gates.sh $(TARGET)

# короткий бенчмарк парсинга
bench:
	$(PY) scripts/benchmark.py /tmp/onec_bench

clean:
	rm -rf .pytest_cache .coverage dist changes/archive_build *.egg-info
