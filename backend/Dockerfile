# # backend/Dockerfile

# FROM python:3.11-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .
# RUN rm -rf __pycache__ .pytest_cache


# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make sure the CMD uses the correct path
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

