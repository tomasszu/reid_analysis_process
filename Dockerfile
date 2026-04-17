FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# set dir for your code
WORKDIR /app/

# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better caching)
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN pip uninstall -y opencv-python opencv-python-headless && \
    pip install opencv-python-headless==4.13.0.92

# Copy app
COPY . .

ENTRYPOINT ["python", "main.py"]