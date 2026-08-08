# onec-converter — образ для CLI/MCP-сервера переноса данных 1С
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# исходники + метаданные (LICENSE/README нужны pip install -e ., т.к. они в pyproject)
COPY pyproject.toml LICENSE README.md ./
COPY src ./src

# зависимости + сам пакет (после копирования src — pyproject ссылается на where=["src"])
RUN pip install --upgrade pip && pip install -e .

# точка входа — CLI; MCP-сервер: python -m onec_converter.mcp_server
ENTRYPOINT ["onec-converter"]
CMD ["--help"]
