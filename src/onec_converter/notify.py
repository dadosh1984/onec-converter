"""Уведомления по завершении переноса (Фаза 27).

Webhook-хук (простой HTTP POST JSON) и Telegram: `notify_telegram` строит
URL `https://api.telegram.org/bot<token>/sendMessage` и шлёт текст.
Используется в `load` (CLI --notify-url / --notify-telegram).
Код авторский.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class NotifyError(Exception):
    """Ошибка отправки уведомления."""


def send_webhook(url: str, payload: dict[str, Any], timeout: int = 15
                 ) -> dict[str, Any]:
    """HTTP POST JSON по URL. Возвращает {ok, status}; не бросает на
    4xx/5xx — статус фиксируется в ответе (best-effort уведомление)."""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        url, data=body, method='POST',
        headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {'ok': resp.status < 400, 'status': resp.status}
    except urllib.error.HTTPError as exc:
        return {'ok': False, 'status': exc.code}
    except urllib.error.URLError as exc:
        raise NotifyError(f'уведомление не доставлено: {exc}') from exc


def telegram_url(token: str, chat_id: str) -> str:
    """URL Telegram Bot API для sendMessage."""
    return (f'https://api.telegram.org/bot{token}/sendMessage'
            f'?chat_id={chat_id}')


def notify_telegram(token: str, chat_id: str, text: str,
                    timeout: int = 15) -> dict[str, Any]:
    """Отправить текст в Telegram-чат через бота."""
    return send_webhook(telegram_url(token, chat_id), {'text': text},
                        timeout=timeout)
