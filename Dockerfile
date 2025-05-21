FROM python:3.9-slim

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for audio files
RUN mkdir -p audio_files

# Expose port
EXPOSE 7860

# Set environment variables
ENV BACKEND_HOST=0.0.0.0
ENV BACKEND_PORT=7860
ENV BASE_URL=https://${SPACE_ID}.hf.space

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"] 