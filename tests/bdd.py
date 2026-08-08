"""BDD-обёртка сквозных сценариев (Фаза 28, идея artbear/1bdd).

Минимальный given/when/then-DSL на pytest-фикстурах без новых зависимостей:
шаги — это объекты Step (имя + функция), фикстура `scenario` накапливает
их и запускает по очереди с общим контекстом-словарём. Отчёт сценария —
список (статус, имя) — виден при -v.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

Ctx = dict[str, Any]


@dataclass
class Step:
    """Один шаг BDD: given/when/then с именем и функцией(контекст)."""

    kind: str
    name: str
    fn: Callable[[Ctx], Any]

    def __call__(self, ctx: Ctx) -> Any:
        return self.fn(ctx)


def given(name: str, fn: Callable[[Ctx], Any]) -> Step:
    return Step('given', name, fn)


def when(name: str, fn: Callable[[Ctx], Any]) -> Step:
    return Step('when', name, fn)


def then(name: str, fn: Callable[[Ctx], Any]) -> Step:
    return Step('then', name, fn)


@dataclass
class Scenario:
    """Контекст + цепочка шагов; run() выполняет по порядку."""

    ctx: Ctx = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)
    report: list[tuple[str, str]] = field(default_factory=list)

    def add(self, step: Step) -> None:
        self.steps.append(step)

    def __call__(self, step: Step) -> Step:
        """given/when/then можно использовать и как декоратор шага."""
        self.add(step)
        return step

    def run(self) -> Ctx:
        for step in self.steps:
            step(self.ctx)
            self.report.append((step.kind, step.name))
        return self.ctx

    def dump(self) -> str:
        return '\n'.join(f'{k}: {n}' for k, n in self.report)


@pytest.fixture
def scenario() -> Scenario:
    """Фикстура сценария: `scenario(given(...))` — собрать шаги, run()."""
    return Scenario()
