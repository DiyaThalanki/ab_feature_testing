# # frontend/Dockerfile

# FROM python:3.11-slim

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Make sure streamlit runs from the correct directory
CMD ["streamlit", "run", "/app/main.py", "--server.address", "0.0.0.0"]

