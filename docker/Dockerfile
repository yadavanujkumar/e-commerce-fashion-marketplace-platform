# Dockerfile for E-Commerce Fashion Marketplace Platform

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Metadata as described above
LABEL maintainer="your-email@example.com" \
      version="1.0" \
      description="E-Commerce Fashion Marketplace Platform"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Create app directory
WORKDIR $APP_HOME

# Install system dependencies and Python packages
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libffi-dev libssl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Stage 2: Runtime
FROM python:3.11-slim AS runtime

# Create a non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# Create app directory
WORKDIR $APP_HOME

# Copy only the necessary files from the builder stage
COPY --from=builder $APP_HOME .

# Set permissions for the app directory
RUN chown -R appuser:appgroup $APP_HOME && \
    chmod -R 755 $APP_HOME

# Switch to non-root user
USER appuser

# Health check directive
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Command to run the application
ENTRYPOINT ["python", "app.py"]

# Expose the application port
EXPOSE 8000

# Note: Ensure to have a .dockerignore file to exclude unnecessary files from the build context.