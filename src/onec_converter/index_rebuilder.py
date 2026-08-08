"""Восстановление индексов после прямой записи (Фаза 34).

Прямая запись (load_direct) изменяет данные таблиц, поэтому индексные
B-деревья источника могут стать неактуальными. 1С восстанавливает их при
открытии ИБ через «Тестирование и исправление», но для автоматизации мы
генерируем скрипт вероятных команд восстановления (chdbfl / 1cv8 /Repair),
который оператор запускает один раз после переноса. Код авторский.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


class IndexRepairError(Exception):
    """Ошибка проверки/поиска инструмента восстановления индексов."""


def _platform_shell() -> str:
    """Расширение/шебанг для текущей или целевой ОС (по запускающему)."""
    if os.name == 'nt':
        return '.bat'
    return '.sh'


def build_repair_script(target_dir: str | Path,
                        tool: str = 'auto') -> dict[str, object]:
    """Собрать скрипт восстановления индексов для каталога приёмника.

    target_dir — каталог с обновлённой 1Cv8.1CD; tool — '1cv8'|'chdbfl'|
    'auto' (подстановка по .cmd/.exe настоящего исполняемого). Возвращает
    {ok, script, path, tool_used, notes}.
    """
    tgt = Path(target_dir)
    cd = tgt / '1Cv8.1CD'
    if not cd.is_file():
        raise IndexRepairError(f'нет 1Cv8.1CD в {target_dir}')

    tool_lower = tool.lower()
    if tool_lower == 'auto':
        # пробуем найти 1cv8 в PATH или в типовой установке
        probe = shutil.which('1cv8')
        if probe:
            tool_lower = '1cv8'
        else:
            for cand in (tgt / 'bin' / '1cv8',):
                if cand.is_file():
                    tool_lower = '1cv8'
                    break
        if tool_lower == 'auto':
            tool_lower = 'chdbfl'  # честный дефолт если ничего не нашли

    if tool_lower == '1cv8':
        cmd = '1cv8 /IBConnectionString="File=%TARGET%" /Execute="%REPAIR_EPF%" /C TestAndRepair'
        script = [
            '@echo off',
            'rem Восстановление индексов и тест целостности ИБ-приёмника (Фаза 34)',
            f'set TARGET={cd}',
            f'{cmd}',
            'echo Готово. Откройте базу в Конфигураторе и выполните Тестирование/Исправление если требуется.',
        ]
        suffix = '.bat'
    else:  # chdbfl
        script = [
            '#!/bin/sh',
            '# Восстановление индексов ИБ-приёмника через chdbfl (Фаза 34)',
            'TARGET_DIR=$(dirname "$0")',
            '1c8_chdbfl "$TARGET_DIR/1Cv8.1CD" -T /m',
            'echo "Готово. Запустите тестирование/исправление в Конфигураторе при необходимости."',
        ]
        suffix = '.sh'
    script_path = tgt / f'repair_indexes_phase34{suffix}'
    text = '\n'.join(script) + os.linesep
    script_path.write_text(text, encoding='utf-8', newline=os.linesep)
    return {'ok': True, 'script': str(script_path),
            'tool_used': tool_lower, 'notes': 'индексы перестраиваются на ИБ-приёмнике'}
