FROM python:3.12-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Ensure logs are sent straight to stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set default port
ENV PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Make build.sh executable
RUN chmod +x build.sh

# Expose port
EXPOSE 8000

# Run the build script
CMD ["/bin/bash", "build.sh"]