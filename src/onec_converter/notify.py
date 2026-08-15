"""Уведомления по завершении переноса .

Webhook-хук (простой HTTP POST JSON) и Telegram: `notify_telegram` строит
URL `https://api.telegram.org/bot<token>/sendMessage` и шлёт текст.
Используется в `load` (CLI --notify-url / --notify-telegram).
Код авторский.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any


class NotifyError(Exception):
    """Ошибка отправки уведомления."""


def _retry_delivery(url: str, body: bytes, timeout: int,
                    attempts: int, backoff: float) -> dict[str, Any]:
    """Отправка с retry (attempts попыток, экспоненциальный backoff).

    Ретраятся: сетевые сбои (URLError) и 5xx (транзиентные ошибки шлюза. 4xx (HTTPError) — не ретраятся: это стабильный отказ контракта,
    ретрай не поможет. После исчерпания попыток — NotifyError.
    """
    last: Exception | None = None
    last_status: int | None = None
    for i in range(max(attempts, 1)):
        req = urllib.request.Request(
            url, data=body, method='POST',
            headers={'Content-Type': 'application/json; charset=utf-8'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return {'ok': resp.status < 400, 'status': resp.status}
        except urllib.error.HTTPError as exc:
            if exc.code >= 500:
                last = exc
                last_status = exc.code
                if i + 1 < max(attempts, 1):
                    time.sleep(backoff * (2 ** i))
                continue
            return {'ok': False, 'status': exc.code}
        except urllib.error.URLError as exc:
            last = exc
            if i + 1 < max(attempts, 1):
                time.sleep(backoff * (2 ** i))
    detail = last_status if last_status is not None else last
    raise NotifyError(f'уведомление не доставлено за {max(attempts, 1)} попыток: {detail}') from last


def send_webhook(url: str, payload: dict[str, Any], timeout: int = 15,
                 attempts: int = 3, backoff: float = 0.5) -> dict[str, Any]:
    """HTTP POST JSON по URL. Возвращает {ok, status}; не бросает на
    4xx/5xx — статус фиксируется в ответе (best-effort уведомление). При
    сетевых сбоях — до attempts попыток с экспоненциальным backoff."""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    return _retry_delivery(url, body, timeout, attempts, backoff)


def telegram_url(token: str, chat_id: str) -> str:
    """URL Telegram Bot API для sendMessage (chat_id/token экранируются)."""
    from urllib.parse import quote

    return (f'https://api.telegram.org/bot{quote(token, safe="")}/sendMessage'
            f'?chat_id={quote(chat_id, safe="")}')


def notify_telegram(token: str, chat_id: str, text: str,
                    timeout: int = 15) -> dict[str, Any]:
    """Отправить текст в Telegram-чат через бота."""
    return send_webhook(telegram_url(token, chat_id), {'text': text},
                        timeout=timeout)
