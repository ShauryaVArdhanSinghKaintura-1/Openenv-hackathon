# ──────────────────────────────────────────────────────────────────────────────
# Dockerfile — Music Content Moderation Environment
# Deploys as a FastAPI app on Hugging Face Spaces (port 7860)
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate the dataset at build time so it's baked into the image
RUN python generate_cases.py

# Expose the Hugging Face Spaces default port
EXPOSE 7860

# Run the FastAPI server via the OpenEnv-compliant app entry point
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
