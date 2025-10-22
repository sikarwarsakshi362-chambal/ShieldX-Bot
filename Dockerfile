# Use Python 3.13 slim as requested (Render supports custom Dockerfiles)
FROM python:3.13-slim

# Avoid buffering so logs show up immediately
ENV PYTHONUNBUFFERED=1

# Create app user for better security (optional but recommended)
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install system deps needed for some python packages (e.g. cryptography, psycopg2, etc.)
# Keep packages minimal to reduce image size.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirement file first (cache layer)
COPY requirements.txt .

# Install Python deps
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Make appuser own the files and switch to that user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port if you have health checks or web endpoints
EXPOSE 8080

# Optional: healthcheck (Docker will run this to test container health)
# This uses python to attempt a simple connection if MONGO_URI is set.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,sys; from pymongo import MongoClient; uri=os.getenv('MONGO_URI'); 
if not uri: sys.exit(1)
try:
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    client.server_info()
    sys.exit(0)
except Exception as e:
    print(e); sys.exit(1)"

# Start the bot
CMD ["python", "bot.py"]
