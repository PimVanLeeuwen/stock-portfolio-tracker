FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and default config
COPY stock_bot/ ./stock_bot/
COPY app.py .
COPY config.yml .

# Non-root user for security
RUN useradd --create-home appuser
USER appuser

CMD ["python", "/app/app.py"]
