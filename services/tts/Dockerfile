FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl libsndfile1 && rm -rf /var/lib/apt/lists/*
# Install piper binary for ARM64
RUN curl -fSL https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz \
    -o /tmp/piper.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /usr/local/bin --strip-components=1 \
    && rm /tmp/piper.tar.gz
WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-m", "services.tts.main"]
