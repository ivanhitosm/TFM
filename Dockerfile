# Use an official Python runtime as the base image
FROM python:3.7

# Set the working directory in the container
WORKDIR /app

# Install system packages using apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    apt-utils \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch
RUN pip install torch torchvision torchaudio

# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install the remaining Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

# Define the command to run the application
# CMD ["python", "server.py"]
EXPOSE 5000
ENV FLASK_APP=srver.py
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000" ]
