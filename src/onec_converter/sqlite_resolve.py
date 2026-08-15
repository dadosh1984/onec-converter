"""Подтверждение кандидатов авто-маппинга.

Читает _object_mapping (status='candidate'), парсит note (JSON candidates),
подтверждает лучшего или всех. После подтверждения заполняет _field_mapping.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def resolve_candidates(source_path: str | Path,
                       target_path: str | Path | None = None,
                       *,
                       json_only: bool = False,
                       accept_best: bool = False,
                       min_score: float = 0.8,
                       accept_all: bool = False) -> dict[str, Any]:
    """Показать или подтвердить кандидатов авто-маппинга.

    Args:
        source_path: путь к source.sqlite
        target_path: путь к target.sqlite (для _field_mapping при accept)
        json_only: только показать, без изменений
        accept_best: подтвердить лучшего кандидата (score >= min_score)
        min_score: порог для accept_best
        accept_all: подтвердить первого кандидата для всех

    Returns:
        {'candidates': [...], 'accepted': N, 'remaining': N}
    """
    src = Path(source_path)
    con = sqlite3.connect(str(src))
    con.row_factory = sqlite3.Row

    # читаем кандидатов
    rows = con.execute(
        "SELECT id, source_name, source_kind, note "
        "FROM _object_mapping WHERE status='candidate'"
    ).fetchall()

    candidates: list[dict[str, Any]] = []
    for r in rows:
        try:
            cand_list = json.loads(r['note'])
        except (json.JSONDecodeError, TypeError):
            cand_list = []
        candidates.append({
            'id': r['id'],
            'source_name': r['source_name'],
            'source_kind': r['source_kind'],
            'candidates': cand_list,
        })

    if json_only:
        con.close()
        return {'candidates': candidates, 'total': len(candidates)}

    if not candidates:
        con.close()
        return {'candidates': [], 'accepted': 0, 'remaining': 0}

    accepted = 0
    tgt_con = None
    if target_path and (accept_best or accept_all):
        tgt_con = sqlite3.connect(str(target_path))
        tgt_con.row_factory = sqlite3.Row

    for c in candidates:
        if not c['candidates']:
            continue

        if accept_all:
            best = c['candidates'][0]
        elif accept_best:
            best = c['candidates'][0]
            if best.get('score', 0) < min_score:
                continue
        else:
            continue

        target_name = best['name']
        # обновить _object_mapping
        con.execute(
            "UPDATE _object_mapping SET target_name=?, status='ready', "
            "note=? WHERE id=?",
            (target_name,
             f'accepted: {best.get("reason", "")} (score={best.get("score", 0)})',
             c['id']))

        # заполнить _field_mapping
        if tgt_con:
            _map_fields_for_object(con, tgt_con, c['id'],
                                   c['source_name'], target_name)

        accepted += 1

    con.commit()
    if tgt_con:
        tgt_con.close()

    remaining = con.execute(
        "SELECT COUNT(*) FROM _object_mapping WHERE status='candidate'"
    ).fetchone()[0]
    con.close()

    return {
        'candidates': candidates,
        'accepted': accepted,
        'remaining': remaining,
    }


def _map_fields_for_object(con: sqlite3.Connection,
                           tgt_con: sqlite3.Connection,
                           om_id: int,
                           src_name: str,
                           tgt_name: str) -> None:
    """Заполнить _field_mapping для одного подтверждённого объекта."""
    # удалить старый маппинг если был
    con.execute('DELETE FROM _field_mapping WHERE object_mapping_id=?', (om_id,))

    src_cols = con.execute(
        "SELECT col_name, field_name, type, length, precision "
        "FROM _columns c JOIN _objects o ON c.object_id=o.id "
        "WHERE o.name=?", (src_name,)
    ).fetchall()

    tgt_cols = {}
    for row in tgt_con.execute(
        "SELECT col_name, type FROM _columns c "
        "JOIN _objects o ON c.object_id=o.id WHERE o.name=?",
        (tgt_name,)
    ).fetchall():
        tgt_cols[row[0]] = row[1]

    for col_name, field_name, src_type, src_len, src_prec in src_cols:
        tgt_type = tgt_cols.get(col_name) or tgt_cols.get(field_name)

        if tgt_type is None:
            con.execute(
                'INSERT INTO _field_mapping '
                '(object_mapping_id, source_field, target_field, '
                'source_type, status) VALUES (?, ?, NULL, ?, ?)',
                (om_id, col_name, src_type, 'unmatched'))
            continue

        status = 'type_mismatch' if src_type != tgt_type else 'ready'
        con.execute(
            'INSERT INTO _field_mapping '
            '(object_mapping_id, source_field, target_field, '
            'source_type, target_type, status) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (om_id, col_name, col_name, src_type, tgt_type, status))
