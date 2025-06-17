# Base image with Python + Node.js
FROM python:3.12-slim

# Install required tools & Node.js
RUN apt-get update && \
    apt-get install -y curl gnupg build-essential git && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy Python files first to cache Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend (including whatsapp-service)
COPY . .

# ✅ Clean install in whatsapp-service, remove lock + node_modules
RUN cd whatsapp-service && \
    rm -rf node_modules package-lock.json && \
    npm install

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI + WhatsApp in one script
CMD ["python", "main.py"]
