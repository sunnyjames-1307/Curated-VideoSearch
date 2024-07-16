# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install any necessary system dependencies
# RUN apt-get update && apt-get install -y \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt ./

# COPY /cipher.py /usr/local/lib/python3.9/site-packages/pytube/cipher.py

# Install the dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Patch pytube's cipher.py to fix the throttling issue

# Specify the command to run the application
CMD ["python", "app.py"]
