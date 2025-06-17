# Use Python as base
FROM python:3.12-slim

# Install Node.js and npm
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# Set working directory
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js dependencies for the WhatsApp service
RUN cd whatsapp-service && npm install

# Expose FastAPI port
EXPOSE 8000

# Start your main.py — it handles FastAPI + WhatsApp subprocess
CMD ["python", "main.py"]
