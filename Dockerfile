# Base image
FROM python:3.10.11-slim

# Prevent Python from buffering stdout/stderr (helpful for logs)
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy and install requirements first (leverages layer cache)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port for health checks (optional)
EXPOSE 8080

# Default command
CMD ["python", "bot.py"]

