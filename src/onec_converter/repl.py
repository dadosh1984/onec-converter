"""Интерактивная оболочка для исследования базы 1CD (Фаза 39).

`onec-converter shell --source-dir <dir>` — REPL поверх парсера: команды
tables, query/select, describe, help, exit; автодополнение имён таблиц
через readline. Чистые функции (parse_command) тестируются без ввода.
Код авторский.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReplError(Exception):
    """Ошибка команды REPL."""


def parse_command(line: str) -> dict[str, Any]:
    """Разобрать строку команды: {cmd, args, table, sql}. Чувствительно к
    первым ключевым словам: tables|query|select|describe|help|exit|quit."""
    parts = line.strip().split(None, 1)
    if not parts:
        return {'cmd': ''}
    cmd = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ''
    if cmd in ('exit', 'quit'):
        return {'cmd': 'exit'}
    if cmd == 'help':
        return {'cmd': 'help'}
    if cmd == 'tables':
        return {'cmd': 'tables'}
    if cmd in ('query', 'select'):
        # query <table> WHERE <подстрока>
        tname, _, w = rest.replace(';', '').partition(' ')
        w = w.strip()
        if w.lower().startswith('where'):
            w = w[5:].lstrip()
        return {'cmd': 'query', 'table': tname.strip(), 'where': w}
    if cmd == 'describe':
        return {'cmd': 'describe', 'table': rest.split()[0] if rest else ''}
    raise ReplError(f'неизвестная команда: {cmd} (help — список)')


def _tables(cd: Path) -> list[str]:
    from .source_8x_file import Database1CD

    with Database1CD(cd) as db:
        return sorted(db.tables)


def run_command(cmd: dict[str, Any], cd: Path) -> str:
    """Выполнить команду над файлом базы; вернуть текст (JSON для query)."""
    from .source_8x_file import Database1CD, read_table

    k = cmd.get('cmd')
    if k == 'help':
        return ('Команды: tables | describe <таблица> | '
                'query <таблица> [WHERE <подстрока>] | help | exit')
    if k == 'tables':
        return '\n'.join(_tables(cd))
    if k == 'describe':
        t = cmd.get('table', '')
        with Database1CD(cd) as db:
            td = db.tables.get(t)
        if td is None:
            return f'таблица не найдена: {t}'
        fields = ', '.join(f"{n}:{d.type}" for n, d in td.fields.items()) or '(нет полей)'
        return f'{t} (row={td.row_length}) fields: {fields}'
    if k == 'query':
        t = cmd.get('table', '')
        where = (cmd.get('where') or '').lower()
        out: list[str] = []
        for i, row in enumerate(read_table(cd, t)):
            if where and where not in str(row).lower():
                continue
            if len(out) >= 20:
                out.append('... (лимит 20)')
                break
            out.append(json.dumps(row, ensure_ascii=False, default=str))
        return '\n'.join(out) if out else '(нет строк)'
    return ''


def run_shell(source_dir: str | Path,
              input_iter: Any | None = None) -> int:
    """Цикл REPL (input_iter — для интерактивного ввода, по умолчанию input)."""
    cd = Path(source_dir) / '1Cv8.1CD'
    if not cd.is_file():
        raise ReplError(f'нет 1Cv8.1CD в {source_dir}')
    print(f'onec-converter shell — база: {source_dir} (help — список, exit — выход)')
    reader = input_iter or input
    while True:
        try:
            line = reader('> ')
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line is None:
            break
        try:
            cmd = parse_command(line)
            if cmd['cmd'] == 'exit':
                break
            if not cmd['cmd']:
                continue
            print(run_command(cmd, cd))
        except ReplError as exc:
            print(f'  {exc}')
        except (KeyError, ValueError) as exc:
            print(f'  ошибка: {exc}')
    return 0
