#!/usr/bin/env bash
# Установка MCP-сервера onec-converter для агента pi (и глобально).
#
# 1) Обновляет глобальный пакет onec-converter до свежей версии с PyPI
#    (CLI + MCP-сервер, точка входа `onec-converter mcp --stdio`).
# 2) Дописывает MCP-сервер в конфиг pi `~/.pi/agent/mcp.json`
#    (обрабатывается расширением pi-mcp-extension).
#
# Использование:
#   bash scripts/install-pi-mcp.sh
set -euo pipefail

MCP_FILE="$HOME/.pi/agent/mcp.json"
SERVER_NAME="onec-converter"

echo "== 1/2: глобальная установка onec-converter =="
python -m pip install --upgrade "onec-converter"
onec-converter --version
echo

echo "== 2/2: регистрация MCP-сервера в pi =="
mkdir -p "$(dirname "$MCP_FILE")"
if [ -f "$MCP_FILE" ]; then
  # добавить сервер, сохранив бэкап
  cp "$MCP_FILE" "$MCP_FILE.bak.$(date +%s)"
  python - "$MCP_FILE" "$SERVER_NAME" <<'PY'
import json, sys
path, name = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    cfg = json.load(f)
servers = cfg.setdefault('mcpServers', {})
if name in servers:
    print(f'[info] сервер "{name}" уже есть — обновляю команду')
servers[name] = {
    'transport': 'stdio',
    'command': 'onec-converter',
    'args': ['mcp', '--stdio'],
    'lifecycle': 'lazy',
}
cfg.setdefault('settings', {})['requestTimeoutMs'] = 300000
with open(path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print(f'[ok] сервер "{name}" добавлен в {path}')
PY
else
  cat > "$MCP_FILE" <<JSON
{
  "settings": { "requestTimeoutMs": 300000 },
  "mcpServers": { "$SERVER_NAME": {
    "transport": "stdio",
    "command": "onec-converter",
    "args": ["mcp", "--stdio"],
    "lifecycle": "lazy"
  } }
}
JSON
  echo "[ok] создан $MCP_FILE с сервером $SERVER_NAME"
fi

echo
echo "Проверка сервера (tools/list должен вернуть 18 тулов):"
cd "$(dirname "$0")/.."
{ printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}\n'
  printf '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
  printf '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n'
} | timeout 20 onec-converter mcp --stdio 2>/dev/null \
  | python -c "import sys,json
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    try: m=json.loads(line)
    except: continue
    r=m.get('result',{})
    if 'tools' in r: print('OK: тулов =', len(r['tools']))"
echo "Готово. Перезапустите pi (или /reload) — тулы onec-converter будут доступны."
