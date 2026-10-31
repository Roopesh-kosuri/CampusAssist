# Production Dockerfile for CampusAssist (LPU Campus FAQ Chatbot)
# Optimized for Hugging Face Spaces (Docker SDK) and CPU Deployment
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user (Hugging Face Spaces requirement UID 1000)
RUN useradd -m -u 1000 user
WORKDIR /app
RUN chown -R user:user /app

# Install lightweight CPU-only PyTorch first
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and data
COPY --chown=user:user . .

# Switch to non-root user
USER user

# Pre-download sentence-transformers/all-MiniLM-L6-v2 and pre-compute FAISS embeddings cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    python -c "from src.validate_data import load_faqs; from src.config import FAQS_PATH; from src.retrievers.embedding import EmbeddingRetriever; e=EmbeddingRetriever(); e.fit(load_faqs(FAQS_PATH))"

# Expose standard HF Spaces port
EXPOSE 7860

# Launch FastAPI server with the Liquid Glass web interface
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
