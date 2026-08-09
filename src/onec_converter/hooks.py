"""Python-хуки моста — замена код-событий 1С epf (Перед/ПриЗаписиОбъекта, «Вычислять»).

Хук — строка из подвала настроек моста:
  * ``module:func`` — функция из импортируемого модуля: ``hook(ctx) -> Any``;
  * иначе — ограниченное выражение Python (sandbox): без импортов, доступны
    только имена контекста и разрешённые встроенные.

Честное ограничение: sandbox блокирует импорты и глобальные встроенные, но
НЕ гарантирует полную изоляцию от атрибутных атак — мост должен поступать из
доверенного источника (как и xlsx-мост в целом).
"""
from __future__ import annotations

import importlib
from datetime import date, datetime
from typing import Any

_SAFE_BUILTINS: dict[str, Any] = {
    'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
    'abs': abs, 'min': min, 'max': max, 'round': round, 'sum': sum,
    'datetime': datetime, 'date': date, 'True': True, 'False': False,
    'None': None,
}


def run_hook(code: str, ctx: dict[str, Any]) -> Any:
    """Выполнить хук; пустой код -> None."""
    if not code or not code.strip():
        return None
    code = code.strip()
    if ':' in code and not code.startswith(('(', '{')):
        mod_name, _, fn_name = code.partition(':')
        mod = importlib.import_module(mod_name)
        return getattr(mod, fn_name)(ctx)
    ns: dict[str, Any] = {'__builtins__': _SAFE_BUILTINS}
    ns.update(ctx)
    return eval(code, ns, {})


def before_write(code: str, ctx: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Обработать ПередЗаписьюОбъекта.

    Возвращает (продолжать, значения): False -> строку пропустить;
    dict-результат хука -> значения обновлены.
    """
    res = run_hook(code, ctx)
    if res is False:
        return False, ctx['values']
    if isinstance(res, dict):
        merged = dict(ctx['values'])
        merged.update(res)
        return True, merged
    return True, ctx['values']
