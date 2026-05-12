# docker/Dockerfile — QAForge runtime image
# Built from the official Playwright image which already contains all browsers
# and OS-level dependencies (libnss, libgbm, fonts, etc.). This avoids the
# common "playwright works on my laptop but not in CI" trap.
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy framework
COPY . .

ENV PYTHONPATH=/app/src \
    QAFORGE_ENV=dev \
    QAFORGE_LOG_LEVEL=INFO

# Install Playwright browsers (matches the base image, so it's a no-op verification)
RUN playwright install --with-deps chromium firefox webkit

# Default: run smoke suite. Override with `docker run ... bash scripts/run.sh regression staging`.
CMD ["bash", "scripts/run.sh", "smoke", "dev", "chromium", "4"]
