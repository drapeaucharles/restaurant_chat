# Dockerfile with ML support for RAG
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Chrome dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    wget \
    gnupg \
    unzip \
    curl \
    libxss1 \
    libnss3 \
    libnss3-dev \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome path
ENV CHROME_PATH=/usr/bin/google-chrome-stable

# Copy requirements files
COPY requirements.txt requirements-ml.txt ./

# Install base requirements
RUN pip install --no-cache-dir -r requirements.txt

# Install ML requirements (this layer can be cached)
RUN pip install --no-cache-dir -r requirements-ml.txt

# Copy application code
COPY . .

# Set environment to enable RAG
ENV USE_RAG=true

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]