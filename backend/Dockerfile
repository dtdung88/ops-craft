# --- STAGE 1: Builder ---
FROM python:3.12-slim AS builder

# Install dependencies for wheel building
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency list only (maximize caching)
COPY requirements.txt .

# Build wheels for faster + isolated installation
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt


# --- STAGE 2: Final (Runtime) ---
FROM python:3.12-slim AS runtime

ARG APP_USER
ARG APP_GROUP
ARG APP_UID
ARG APP_GID

# Install runtime OS packages only
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Set Python behavior
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Create non-root user
RUN groupadd -g ${APP_GID} ${APP_GROUP} && \
    useradd -u ${APP_UID} -g ${APP_GROUP} -s /sbin/nologin -m ${APP_USER}

# Copy Python wheels from the builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy source code
COPY . .
RUN mkdir -p /app/scripts && \
    chown -R ${APP_UID}:${APP_GID} /app && \
    chmod -R a-w /app

USER ${APP_USER}
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]