FROM python:3.12-slim

ARG APP_USER \
    APP_GROUP \
    APP_UID \
    APP_GID

RUN echo ${APP_USER} ${APP_GROUP} ${APP_UID} ${APP_GID}

RUN apt-get update && apt-get install -y gcc postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN groupadd -g ${APP_GID} ${APP_GROUP} && \
    useradd -u ${APP_UID} -g ${APP_GROUP} -s /sbin/nologin -m ${APP_USER}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/scripts
RUN chown -R ${APP_UID}:${APP_GID} /app

USER ${APP_USER}
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]