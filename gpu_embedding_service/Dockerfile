FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY secure_embedding_api.py .

# Download model during build to cache it
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Run as non-root user for security
RUN useradd -m -u 1000 embedder
USER embedder

EXPOSE 8080

CMD ["python3", "-m", "uvicorn", "secure_embedding_api:app", "--host", "0.0.0.0", "--port", "8080"]