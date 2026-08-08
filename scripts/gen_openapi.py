#!/usr/bin/env python3
"""Генерация OpenAPI-спеки приёмника (Фаза 28, идея swagger-1c).

Спека собирается ИЗ КОДА: пути — из вызовов _request('METHOD', '/path')
в src/onec_converter/http_client.py, обработчики-операции — из экспортных
функций src/onec_converter/extension_83/Module.bsl. Результат —
docs/openapi.yaml (статическая спека HTTP-приёмника для контрактного теста).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect_endpoints() -> list[dict[str, str]]:
    http_client = (ROOT / 'src/onec_converter/http_client.py').read_text(
        encoding='utf-8')
    seen: dict[str, str] = {}
    for m in re.finditer(r"_request\('(GET|POST)',\s*'([^']+)'", http_client):
        seen.setdefault(m.group(2), m.group(1))
    return [{'path': p, 'method': m.lower()} for p, m in seen.items()]


def collect_handlers() -> list[str]:
    bsl = (ROOT / 'src/onec_converter/extension_83/Module.bsl').read_text(
        encoding='utf-8')
    return re.findall(r'Функция\s+([^\s(]+)\(Запрос\) Экспорт', bsl)


def build_openapi(endpoints: list[dict[str, str]],
                  handlers: list[str]) -> str:
    lines = [
        'openapi: 3.0.3',
        'info:',
        '  title: onec-converter receiver (1С HTTP-сервис)',
        '  description: >-',
        '    Приёмник переноса данных: HTTP-сервис 1С (расширение',
        '    extension_83). Спека сгенерирована из кода — scripts/gen_openapi.py.',
        '  version: 0.14.0',
        'servers:',
        '  - url: https://{host}/hsp/onec-converter',
        '    variables:',
        '      host:',
        '        default: localhost',
        'paths:',
    ]
    # соответствие путь → операция (обработчик Module.bsl) по смыслу
    op_by_path = {'/metadata': 'МетаданныеИБ', '/load': 'ЗаписьДанных'}
    for ep in endpoints:
        path, method = ep['path'], ep['method']
        lines.append(f'  {path}:')
        lines.append(f'    {method}:')
        op = op_by_path.get(path, handlers.pop(0) if handlers else 'unknown')
        lines.append(f'      operationId: {op}')
        lines.append('      security:')
        lines.append('        - ApiKeyAuth: []')
        if path == '/load':
            lines.append('        - BearerAuth: []')
        lines.append('      responses:')
        lines.append("        '200':")
        lines.append('          description: Успешный ответ JSON')
        lines.append("        '401':")
        lines.append('          description: Неверный ключ/токен')
    lines += [
        'components:',
        '  securitySchemes:',
        '    ApiKeyAuth:',
        '      type: apiKey',
        '      in: header',
        '      name: X-API-Key',
        '    BearerAuth:',
        '      type: http',
        '      scheme: bearer',
        '      bearerFormat: JWT',
    ]
    return '\n'.join(lines) + '\n'


def main() -> int:
    eps = collect_endpoints()
    hnd = collect_handlers()
    yaml = build_openapi(eps, hnd)
    out = ROOT / 'docs/openapi.yaml'
    out.write_text(yaml, encoding='utf-8')
    print(f'openapi.yaml: {len(eps)} path(s), {len(hnd)} handler(s) -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
