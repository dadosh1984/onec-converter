#!/usr/bin/env bash
# Публикация релиза onec-converter: TestPyPI → PyPI → GitHub Release.
# Использование:
#   bash scripts/release.sh 0.23.0            # собрать и опубликовать (все шаги)
#   bash scripts/release.sh 0.23.0 --dry-run  # только сборка+проверка, без публикации
#
# Аутентификация: twine читает токены из окружения (TWINE_USERNAME/PASSWORD или
# TWINE_API_KEY); gh должен быть аутентифицирован (`gh auth login`).
set -euo pipefail

VER="${1:?укажите версию, напр. 0.23.0}"
DRY=0
[[ "${2:-}" == "--dry-run" ]] && DRY=1

# --- 1. бамп версии в едином источнике (src/onec_converter/__init__.py) ---
if grep -q "__version__ = \"$VER\"" src/onec_converter/__init__.py; then
  echo "версия $VER уже в __version__"
else
  sed -i "s/__version__ = \".*\"/__version__ = \"$VER\"/" src/onec_converter/__init__.py
  echo "__init__.py -> __version__ $VER"
fi

# --- 2. сборка ---
echo "== build =="
rm -rf dist build *.egg-info
python -m build

# --- 3. проверка ---
echo "== twine check =="
python -m twine check dist/*

if [[ "$DRY" == "1" ]]; then
  echo "dry-run: пропускаю публикацию. Готово: dist/*"
  exit 0
fi

# --- 4a. TestPyPI ---
echo "== twine upload (testpypi) =="
python -m twine upload --repository testpypi dist/*

# --- 4b. PyPI ---
echo "== twine upload (pypi) =="
python -m twine upload dist/*

# --- 5. GitHub Release (если gh доступен и токен есть) ---
TAG="v$VER"
if gh repo view >/dev/null 2>&1; then
  NOTES="${NOTES:-Релиз onec-converter $VER (авто, см. CHANGELOG.md)}"
  echo "== gh release =="
  gh release create "$TAG" --title "$TAG" --notes "$NOTES" || echo "релиз уже существует (пропуск)"
else
  echo "gh не аутентифицирован — пропускаю GitHub Release; создайте тег вручную: git tag $TAG"
fi

echo "Готово: $VER опубликован в TestPyPI, PyPI и GitHub Release."
echo "Проверка: pip install onec-converter==$VER"
