# Base image with Python + Node.js
FROM python:3.12-slim

# Force cache busting
ARG CACHEBUST=1

# Install required tools & Node.js + WhatsApp deps + ffmpeg
RUN apt-get update && \
    apt-get install -y curl gnupg build-essential git ffmpeg \
    libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxss1 libasound2 libatk-bridge2.0-0 libgtk-3-0 && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy Python deps first
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Clean install for WhatsApp service
RUN cd whatsapp-service && \
    rm -rf node_modules package-lock.json && \
    npm install --production

# Expose FastAPI port
EXPOSE 8000
EXPOSE 8002

# Start FastAPI + WhatsApp
CMD ["sh", "-c", "python main.py"]
