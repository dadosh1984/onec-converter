# Задачи — bridge-migrate-фазу-сравнения

Легенда статусов: отмеченный квадрат означает готово, пустой —
открыто; forge переключает каждый квадрат по мере выполнения задачи,
так что ручная сверка не нужна.

- [x] [assumption] Scaffold project structure for bridge-migrate-фазу-сравнения
- [x] [assumption] Build the CLI entry point (arg parsing, sub-commands, exit codes)
- [x] [assumption] Cover the core capability with tests
- [x] [fact] Integrate with the Без новых зависимостей; только копии баз (не оригиналы); pytest+mypy strict+ruff+vitest зелёные; вести через конвейер Orion (think→draft→forge→shield→out); использовать существующие примитивы (read_metadata, classify_objects). platform
- [x] [assumption] Document usage in README
