FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
RUN mkdir -p /app/data

EXPOSE 8006
EXPOSE 5560

CMD ["python", "src/main.py"]
