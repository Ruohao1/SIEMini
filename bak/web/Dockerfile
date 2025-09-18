FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py gunicorn.conf.py ./
COPY templates ./templates
COPY static ./static

RUN useradd -m appuser
USER appuser
EXPOSE 8080

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:app"]
