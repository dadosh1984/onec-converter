"""Единый движок пайплайна загрузки.

Содержит только чистое ядро load-этапа (из intermediate JSON в 1CD).
CLI (cli.py) и MCP-сервер (mcp_server.py) — тонкие адаптеры, вызывающие
run_pipeline() и добавляющие свою оркестрацию (audit, progress, notify).

Полный ETL (extract→transform→load) — отдельная функция run_full_pipeline(),
которая собирает шаги из extractor, transform и load_direct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PipelineResult:
    """Результат прогона пайплайна загрузки."""

    ok: bool
    total: int
    tables: dict[str, int] = field(default_factory=dict)
    ref_warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    copy_path: str | None = None
    snapshot: str | None = None
    verify: dict[str, Any] | None = None


def run_pipeline(
    objects: list[dict[str, Any]],
    target_dir: str | Path,
    workdir: str | Path | None = None,
    verify_after: bool = True,
    max_objects: int | None = None,
    strict: bool = False,
    snapshot: bool = True,
    audit: Any = None,
    index_repair: bool = False,
) -> PipelineResult:
    """Загрузить intermediate-объекты в целевую 1CD.

    Это замена ядра cmd_load --direct из cli.py.
    Принимает уже преобразованные объекты (intermediate JSON),
    вызывает load_direct, опционально repair индексы.

    Аргументы:
        objects: список intermediate-объектов (после transform).
        target_dir: каталог с целевой 1Cv8.1CD.
        workdir: временный каталог.
        verify_after: roundtrip-верификация.
        max_objects: лимит батча.
        strict: пре-валидация.
        snapshot: копия приёмника до изменений.
        audit: опциональный AuditLog (если None — глобальный get_audit()).
        index_repair: собрать скрипт восстановления индексов.

    Возвращает PipelineResult.
    """
    from .load_8x import load_direct

    try:
        result = load_direct(
            target_dir,
            objects,
            workdir=workdir,
            verify_after=verify_after,
            max_objects=max_objects,
            strict=strict,
            snapshot=snapshot,
            audit=audit,
        )
    except Exception as exc:
        return PipelineResult(
            ok=False,
            total=0,
            errors=[f'{type(exc).__name__}: {exc}'],
        )

    rep: dict[str, Any] = result  # load_direct возвращает dict

    pr = PipelineResult(
        ok=rep.get('ok', False),
        total=rep.get('total', 0),
        tables=rep.get('tables', {}),
        ref_warnings=rep.get('ref_warnings', []),
        copy_path=str(rep.get('copy_path', '')),
        snapshot=str(rep.get('snapshot', '')) if rep.get('snapshot') else None,
        verify=rep.get('verify'),
    )

    if pr.ok and index_repair:
        try:
            from .index_rebuilder import build_repair_script
            build_repair_script(target_dir)
        except Exception as exc:
            pr.errors.append(f'index_repair: {exc}')

    return pr
