FROM python:3.10

WORKDIR /app

# Install curl for health checks and redis-cli for connection checking
RUN apt-get update && apt-get install -y curl redis-tools && rm -rf /var/lib/apt/lists/*

COPY . /app

# Convert line endings and make the wait script executable
RUN sed -i 's/\r$//' /app/wait-for-redis.sh && \
    chmod +x /app/wait-for-redis.sh && \
    ls -la /app/wait-for-redis.sh

# Create log directory and ensure proper permissions
RUN mkdir -p /app/logs && \
    chmod 777 /app/logs

RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Use the wait script to ensure Redis is available before starting
CMD ["./wait-for-redis.sh", "redis", "6379", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5679"]
