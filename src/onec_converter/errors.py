"""Иерархия исключений onec-converter.

Единый базовый класс OnecConverterError вместо россыпи независимых Exception.
"""


class OnecConverterError(Exception):
    """Базовое исключение onec-converter."""


# Парсинг/формат
class ParseError(OnecConverterError):
    """Ошибка разбора формата 1CD, DAT, OLE."""


class FormatError(ParseError):
    """Ошибка формата данных (невалидная сигнатура, размер и т.д.)."""


# Конфигурация/маппинг
class ConfigError(OnecConverterError):
    """Ошибка конфигурации, правил маппинга или трансформации."""


class MappingError(ConfigError):
    """Ошибка правил маппинга (TOON)."""


class TransformError(ConfigError):
    """Ошибка трансформации объекта."""


# Исполнение пайплайна
class ConverterRuntimeError(OnecConverterError):
    """Ошибка выполнения (запись/чтение/загрузка)."""


class LoadError(ConverterRuntimeError):
    """Ошибка прямой загрузки в 1CD."""


class WriteError(ConverterRuntimeError):
    """Ошибка прямой записи в 1CD."""


class LockError(WriteError):
    """База открыта/используется — запись запрещена."""


class HealthError(ConverterRuntimeError):
    """Ошибка health-check."""


# Безопасность
class SecurityError(OnecConverterError):
    """Ошибка безопасности (JWT, SSRF, секреты)."""


class JwtError(SecurityError):
    """Ошибка проверки JWT."""


# Запросы
class QueryError(ParseError):
    """Ошибка разбора или выполнения SQL-подобного запроса."""


# Уведомления
class NotifyError(ConverterRuntimeError):
    """Ошибка отправки уведомления."""


# Отчёты
class PiiReportError(OnecConverterError):
    """Ошибка генерации PII-отчёта."""


class SonarReportError(OnecConverterError):
    """Ошибка генерации Sonar-отчёта."""
