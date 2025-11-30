# Use a lightweight Python Linux image
FROM python:3.9-slim

# Set environment variables
# 1. Force Python to show logs immediately (Fixes empty logs)
# 2. Stop Python from creating .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system libraries needed for Geo tools
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Install Python libraries
# ADDED: folium and streamlit-folium
RUN pip install pandas sqlalchemy psycopg2-binary streamlit plotly folium streamlit-folium

# Copy all files from your laptop to the container
COPY . .

# Tell Docker to open port 8501
EXPOSE 8501

# Default command: Launch Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
