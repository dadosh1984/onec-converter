# Релиз onec-converter

Публикация новой версии в **TestPyPI**, **PyPI** и **GitHub Release**.

## Процесс (в конце каждой фазы)

1. **Бамп версии** — `pyproject.toml` (`version = "x.y.z"`) и `src/onec_converter/cli.py`
   (`--version`). Версия растёт по фазам: 0.22.0, 0.23.0, … (или patch/minor по смыслу).
2. **Сборка**: `python -m build` (нужны `build`, `twine`: `pip install build twine`).
3. **Проверка**: `python -m twine check dist/*`.
4. **Публикация**:
   - TestPyPI: `python -m twine upload --repository testpypi dist/*`
   - PyPI:    `python -m twine upload dist/*`
5. **GitHub Release** (тег + релиз):
   ```
   gh release create v<x.y.z> --title "v<x.y.z>" --notes "<что нового>"
   ```
   (тег ставится на коммит публикации).
6. **Проверка**: `pip install onec-converter==<x.y.z>` в чистом venv
   (`onec-converter doctor`, `--version`).

## Требования
- Токены: `TWINE_USERNAME`/`TWINE_PASSWORD` (или `TWINE_API_KEY`) для TestPyPI и PyPI.
  Удобно хранить в переменных окружения / в CI-секретах.
- GitHub CLI `gh` аутентифицирован.

## Скрипт
`bash scripts/release.sh <version>` выполняет шаги 2–6 (см. ниже). Он не покрывает
аутентификацию (`twine`/`gh` читают из окружения).

## Автоматизация (опционально)
- `.github/workflows/publish.yml` — публикация на PyPI + GitHub Release **по тегу**
  `v*` (GitHub Actions). Настройте секреты `PYPI_TOKEN`/`TESTPYPI_TOKEN`.
  Тогда локально достаточно сделать `git tag v<x.y.z> && git push --tags`.

## Контрольный список перед релизом
- [ ] Ворота зелёные: `bash scripts/gates.sh ruff mypy pytest` (+ vitest).
- [ ] `twine check dist/*` — PASSED.
- [ ] Версия в `pyproject.toml` и `cli.py` совпадают.
- [ ] `CHANGELOG.md` обновлён (что появилось для пользователя).
- [ ] Пакет установлен с PyPI и `onec-converter doctor` работает.
