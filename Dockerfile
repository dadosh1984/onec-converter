# onec-converter — образ для CLI/MCP-сервера переноса данных 1С
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# зависимости отдельно (кеширование слоя)
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

# исходники
COPY src ./src
RUN pip install -e .

# точка входа — CLI; MCP-сервер: python -m onec_converter.mcp_server
ENTRYPOINT ["onec-converter"]
CMD ["--help"]
