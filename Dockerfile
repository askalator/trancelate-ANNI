FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# app
COPY anni_copy_gate.py anni_copy_service.py /app/

# run as non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8094
CMD ["uvicorn","anni_copy_service:app","--host","0.0.0.0","--port","8094"]
