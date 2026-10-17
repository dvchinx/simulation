FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY config.py simulation.py server.py ./
COPY rules/ rules/

RUN useradd --create-home --uid 10001 sim
USER sim

EXPOSE 8765
CMD ["python", "server.py"]
