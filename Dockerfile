# 1) Use a minimal Python base image
FROM python:3.10-slim

# 2) Create a non-root user and set working directory
RUN useradd --create-home appuser
WORKDIR /home/appuser

# 3) Copy and install dependencies as that user
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copy application code
COPY --chown=appuser:appuser . .

# 5) Expose the port FastAPI listens on
EXPOSE 8080

# 6) Switch to the non-root user and start Uvicorn
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
