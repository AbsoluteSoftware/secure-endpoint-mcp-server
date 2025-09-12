# Use a multi-stage build for a smaller final image
# Stage 1: Build the application
FROM python:3.13-slim AS builder

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY main.py .
COPY openapi.json .
COPY secure_endpoint_mcp ./secure_endpoint_mcp

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Install dependencies
RUN uv pip install --system --no-cache-dir -e .

# Stage 2: Create the final image using distroless Python
FROM cgr.dev/chainguard/python:latest

# Set working directory
WORKDIR /app

# Copy installed packages and application from builder
# Note: The path might be different in the distroless image, adjust if needed
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/lib/python3.13/site-packages
COPY --from=builder /app/main.py .
COPY --from=builder /app/openapi.json .
COPY --from=builder /app/secure_endpoint_mcp ./secure_endpoint_mcp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVER_HOST=0.0.0.0
ENV SERVER_PORT=8000
ENV PYTHONPATH=/app
ENV TRANSPORT_MODE=stdio

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["main.py"]
