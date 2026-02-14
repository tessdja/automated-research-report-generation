# Use official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set workdir
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
#CMD ["uvicorn", "research_and_analyst.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Replace last CMD in prod
CMD ["uvicorn", "research_and_analyst.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# optional improvement - ECS controls port via env var PORT
# CMD ["sh", "-c", "uvicorn research_and_analyst.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

