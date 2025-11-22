FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# System deps for Playwright + uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src ./src

# Install project dependencies into a local virtualenv
RUN uv sync --frozen --no-dev

# Install browser runtime
RUN /app/.venv/bin/playwright install --with-deps chromium

# Runtime defaults
ENV PATH="/app/.venv/bin:$PATH"
RUN mkdir -p data playwright/.auth

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src", "--proxy-headers"]
