FROM python:3-slim

ENV LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends curl netcat && \
    curl -Lo /usr/local/bin/wait-for https://raw.githubusercontent.com/eficode/wait-for/master/wait-for && \
    chmod +x /usr/local/bin/wait-for && \
    pip install --no-cache-dir Django psycopg2-binary && \
    rm -rf /var/lib/apt/lists/*

COPY . /history

WORKDIR /history

CMD ["wait-for", "postgres:5432", "--", "python", "manage.py", "test"]
