FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY client.py cli.py mcp_server.py pdf.py ./

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["epstein-search-mcp", "--http"]
