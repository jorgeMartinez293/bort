FROM python:3.12-slim
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# services/ is bind-mounted in dev; CMD uses full module path
CMD ["python", "-m", "services.scraper.main"]
