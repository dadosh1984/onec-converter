"""Авто-сопоставление объектов и полей источника с приёмником.

6 уровней поиска:
1-4: точные совпадения по kind+name/synonym → status=ready
5:   нечёткое — подстрока в именах того же kind → status=candidate
6:   нечёткое — 70%+ совпадение реквизитов → status=candidate

Без внешних зависимостей — только stdlib (sqlite3 + re).
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

# ponytail: rung 3 — stdlib re для токенизации имён
_TOKEN_RE = re.compile(r'[А-ЯA-Z][а-яa-z]+|[А-ЯA-Z]{2,}|\d+')


def _tokenize(s: str) -> list[str]:
    """Разбить строку на слова: 'ЗакупкаТоваров' → ['закупка', 'товаров']."""
    return [t.lower() for t in _TOKEN_RE.findall(s)]


def auto_map_sqlite(source_path: str | Path,
                    target_path: str | Path) -> dict[str, Any]:
    """Авто-сопоставить объекты и поля источника с приёмником.

    Заполняет _object_mapping, _field_mapping, _value_mapping в source.sqlite.
    6 уровней: 4 точных (ready) + 2 нечётких (candidate).

    Returns:
        {'total': N, 'matched': N, 'candidate': N, 'unmatched': N,
         'fields_matched': N, 'fields_unmatched': N, 'fields_type_mismatch': N}
    """
    src = Path(source_path)
    tgt = Path(target_path)

    con = sqlite3.connect(str(src))
    con.execute('PRAGMA journal_mode=WAL')
    _create_mapping_tables(con)

    tgt_con = sqlite3.connect(str(tgt))
    tgt_con.row_factory = sqlite3.Row

    _map_objects(con, tgt_con)
    _map_fields(con, tgt_con)

    tgt_con.close()

    matched = con.execute(
        "SELECT COUNT(*) FROM _object_mapping WHERE status='ready'"
    ).fetchone()[0]
    candidate = con.execute(
        "SELECT COUNT(*) FROM _object_mapping WHERE status='candidate'"
    ).fetchone()[0]
    unmatched = con.execute(
        "SELECT COUNT(*) FROM _object_mapping WHERE status='unmatched'"
    ).fetchone()[0]
    total = con.execute(
        "SELECT COUNT(*) FROM _object_mapping").fetchone()[0]

    fields_matched = con.execute(
        "SELECT COUNT(*) FROM _field_mapping WHERE status='ready'"
    ).fetchone()[0]
    fields_unmatched = con.execute(
        "SELECT COUNT(*) FROM _field_mapping WHERE status='unmatched'"
    ).fetchone()[0]
    fields_type_mismatch = con.execute(
        "SELECT COUNT(*) FROM _field_mapping WHERE status='type_mismatch'"
    ).fetchone()[0]

    con.commit()
    con.close()

    return {
        'total': total,
        'matched': matched,
        'candidate': candidate,
        'unmatched': unmatched,
        'fields_matched': fields_matched,
        'fields_unmatched': fields_unmatched,
        'fields_type_mismatch': fields_type_mismatch,
    }


def _create_mapping_tables(con: sqlite3.Connection) -> None:
    con.execute('''CREATE TABLE IF NOT EXISTS _object_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        target_name TEXT,
        source_kind TEXT NOT NULL,
        target_kind TEXT,
        match_level INTEGER DEFAULT 0,
        auto_match BOOLEAN DEFAULT 1,
        status TEXT DEFAULT 'ready',
        note TEXT DEFAULT ''
    )''')
    con.execute('''CREATE TABLE IF NOT EXISTS _field_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_mapping_id INTEGER NOT NULL REFERENCES _object_mapping(id),
        source_field TEXT NOT NULL,
        target_field TEXT,
        source_type TEXT,
        target_type TEXT,
        transform TEXT DEFAULT '',
        default_value TEXT DEFAULT '',
        auto_match BOOLEAN DEFAULT 1,
        status TEXT DEFAULT 'ready'
    )''')
    con.execute('''CREATE TABLE IF NOT EXISTS _value_mapping (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        field_mapping_id INTEGER REFERENCES _field_mapping(id),
        source_value TEXT NOT NULL,
        target_value TEXT NOT NULL
    )''')


def _build_tgt_index(tgt_con: sqlite3.Connection) -> dict[str, Any]:
    """Индексы приёмника: by_name, by_synonym, by_kind, cols_by_obj."""
    by_name: dict[tuple[str, str], tuple[str, str]] = {}
    by_synonym: dict[tuple[str, str], tuple[str, str]] = {}
    by_kind: dict[str, list[tuple[str, str, str]]] = {}
    cols_by_obj: dict[str, set[tuple[str, str]]] = {}

    for row in tgt_con.execute(
        "SELECT kind, name, synonym FROM _objects WHERE category='user'"
    ).fetchall():
        kind, name, syn = row['kind'], row['name'], row['synonym'] or ''
        by_name[(kind, name)] = (kind, name)
        if syn:
            by_synonym[(kind, syn)] = (kind, name)
        by_kind.setdefault(kind, []).append((kind, name, syn))

    # индекс колонок — один запрос, не N
    for row in tgt_con.execute(
        "SELECT o.name, c.col_name, c.type "
        "FROM _columns c JOIN _objects o ON c.object_id=o.id "
        "WHERE o.category='user'"
    ).fetchall():
        cols_by_obj.setdefault(row[0], set()).add((row[1], row[2]))

    return {'by_name': by_name, 'by_synonym': by_synonym,
            'by_kind': by_kind, 'cols_by_obj': cols_by_obj}


def _map_objects(con: sqlite3.Connection,
                 tgt_con: sqlite3.Connection) -> None:
    """6-уровневый поиск для каждого user-объекта источника."""
    con.execute('DELETE FROM _object_mapping')
    con.execute('DELETE FROM _field_mapping')
    con.execute('DELETE FROM _value_mapping')

    tgt_index = _build_tgt_index(tgt_con)

    src_objects = con.execute(
        "SELECT kind, name, synonym FROM _objects WHERE category='user'"
    ).fetchall()

    for kind, name, synonym in src_objects:
        synonym = synonym or ''
        inserted = _find_target(kind, name, synonym, tgt_index, con)

        if not inserted:
            con.execute(
                'INSERT INTO _object_mapping '
                '(source_name, source_kind, match_level, status) '
                'VALUES (?, ?, 0, ?)',
                (name, kind, 'unmatched'))


def _find_target(kind: str, name: str, synonym: str,
                 tgt_index: dict[str, Any],
                 con: sqlite3.Connection) -> bool:
    """6-уровневый поиск. Возвращает True если вставили строку (ready/candidate)."""
    bn = tgt_index['by_name']
    bs = tgt_index['by_synonym']
    bk = tgt_index['by_kind']

    # 1: kind+name → kind+name
    if (kind, name) in bn:
        tk, tn = bn[(kind, name)]
        con.execute(
            'INSERT INTO _object_mapping '
            '(source_name, target_name, source_kind, target_kind, '
            'match_level, status, note) VALUES (?, ?, ?, ?, 1, ?, ?)',
            (name, tn, kind, tk, 'ready', 'exact name'))
        return True

    # 2: kind+synonym → kind+synonym
    if synonym and (kind, synonym) in bs:
        tk, tn = bs[(kind, synonym)]
        con.execute(
            'INSERT INTO _object_mapping '
            '(source_name, target_name, source_kind, target_kind, '
            'match_level, status, note) VALUES (?, ?, ?, ?, 2, ?, ?)',
            (name, tn, kind, tk, 'ready', 'synonym→synonym'))
        return True

    # 3: kind+synonym → kind+name
    if synonym and (kind, synonym) in bn:
        tk, tn = bn[(kind, synonym)]
        con.execute(
            'INSERT INTO _object_mapping '
            '(source_name, target_name, source_kind, target_kind, '
            'match_level, status, note) VALUES (?, ?, ?, ?, 3, ?, ?)',
            (name, tn, kind, tk, 'ready', 'synonym→name'))
        return True

    # 4: kind+name → kind+synonym
    if (kind, name) in bs:
        tk, tn = bs[(kind, name)]
        con.execute(
            'INSERT INTO _object_mapping '
            '(source_name, target_name, source_kind, target_kind, '
            'match_level, status, note) VALUES (?, ?, ?, ?, 4, ?, ?)',
            (name, tn, kind, tk, 'ready', 'name→synonym'))
        return True

    # 5: подстрока
    candidates = _substring_match(kind, name, synonym, bk)
    if candidates:
        con.execute(
            'INSERT INTO _object_mapping '
            '(source_name, source_kind, match_level, status, note) '
            'VALUES (?, ?, 5, ?, ?)',
            (name, kind, 'candidate', json.dumps(candidates, ensure_ascii=False)))
        return True  # candidate — вставили

    # 6: совпадение полей
    candidates = _field_match(kind, name, bk, con)
    if candidates:
        con.execute(
            'INSERT INTO _object_mapping '
            '(source_name, source_kind, match_level, status, note) '
            'VALUES (?, ?, 6, ?, ?)',
            (name, kind, 'candidate', json.dumps(candidates, ensure_ascii=False)))
        return True

    return False


def _substring_match(kind: str, name: str, synonym: str,
                     by_kind: dict[str, list[tuple[str, str, str]]]
                     ) -> list[dict[str, Any]]:
    """Уровень 5: все слова источника есть в имени/синониме цели."""
    src_words = _tokenize(name)
    syn_words = _tokenize(synonym) if synonym else []
    search_words = src_words or syn_words
    if not search_words:
        return []

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    for t_kind, t_name, t_syn in by_kind.get(kind, []):
        if t_name == name:
            continue  # уже проверено на уровнях 1-4
        t_words = _tokenize(t_name)
        t_syn_words = _tokenize(t_syn) if t_syn else []

        # все слова источника в имени цели?
        if search_words and all(w in t_words for w in search_words):
            key = t_name
            if key not in seen:
                seen.add(key)
                candidates.append({
                    'name': t_name,
                    'score': round(len(search_words) / max(len(t_words), 1), 2),
                    'reason': 'подстрока',
                })
        # все слова источника в синониме цели?
        elif search_words and t_syn_words and all(w in t_syn_words for w in search_words):
            key = t_name
            if key not in seen:
                seen.add(key)
                candidates.append({
                    'name': t_name,
                    'score': round(len(search_words) / max(len(t_syn_words), 1), 2),
                    'reason': 'подстрока(synonym)',
                })

    candidates.sort(key=lambda c: -c['score'])
    return candidates[:3]


def _field_match(kind: str, src_name: str,
                 by_kind: dict[str, list[tuple[str, str, str]]],
                 con: sqlite3.Connection
                 ) -> list[dict[str, Any]]:
    """Уровень 6: 70%+ реквизитов совпадает по col_name+type."""
    # ponytail: собираем src_cols один раз (один запрос, не N)
    src_cols = set()
    for row in con.execute(
        "SELECT col_name, type FROM _columns c "
        "JOIN _objects o ON c.object_id=o.id WHERE o.name=?",
        (src_name,)
    ).fetchall():
        src_cols.add((row[0], row[1]))

    if not src_cols:
        return []

    # собираем колонки для всех объектов приёмника того же kind ЗА ОДИН запрос
    tgt_cols_by_obj: dict[str, set[tuple[str, str]]] = {}
    tgt_names = [t[1] for t in by_kind.get(kind, [])]
    if not tgt_names:
        return []

    # один SQL-запрос для всех объектов приёмника этого kind
    placeholders = ','.join(['?'] * len(tgt_names))
    for row in con.execute(
        f"SELECT o.name, c.col_name, c.type FROM _columns c "
        f"JOIN _objects o ON c.object_id=o.id "
        f"WHERE o.name IN ({placeholders})",
        tgt_names
    ).fetchall():
        tgt_cols_by_obj.setdefault(row[0], set()).add((row[1], row[2]))

    candidates: list[dict[str, Any]] = []
    src_names_set = {c[0] for c in src_cols}
    for t_kind, t_name, t_syn in by_kind.get(kind, []):
        if t_name == src_name:
            continue
        tgt_cols = tgt_cols_by_obj.get(t_name, set())
        if not tgt_cols:
            continue

        tgt_names_set = {c[0] for c in tgt_cols}
        common_names = src_names_set & tgt_names_set
        name_score = len(common_names) / max(len(src_names_set), 1)

        common_full = src_cols & tgt_cols
        full_score = len(common_full) / max(len(src_cols), 1)

        score = max(name_score, full_score)
        if score >= 0.7:
            candidates.append({
                'name': t_name,
                'score': round(score, 2),
                'reason': f'поля: {len(common_full)}/{len(src_cols)} общих',
            })

    candidates.sort(key=lambda c: -c['score'])
    return candidates[:3]


def _map_fields(con: sqlite3.Connection,
                tgt_con: sqlite3.Connection) -> None:
    """Заполнить _field_mapping для ready-объектов."""
    mappings = con.execute(
        "SELECT om.id, om.source_name, om.target_name "
        "FROM _object_mapping om WHERE om.status='ready'"
    ).fetchall()

    for om_id, src_name, tgt_name in mappings:
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
