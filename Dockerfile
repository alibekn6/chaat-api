FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --timeout=100 -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
