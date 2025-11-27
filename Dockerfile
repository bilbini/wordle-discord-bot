FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Pillow (image processing)
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for images
RUN mkdir -p wordle_images

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "bot.py"]