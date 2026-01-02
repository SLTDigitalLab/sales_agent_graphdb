# 1. Use an official lightweight Python image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install System Dependencies & Google Chrome (Stable Method)
# We install wget to download the deb file, then let apt install it with all dependencies.
RUN apt-get update && apt-get install -y wget unzip && \
    wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4. Copy your dependency file first (for caching speed)
COPY requirements.txt .

# 5. Install Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application code
COPY . .

# 7. Expose the port the app runs on
EXPOSE 8000

# 8. The command to start the server
CMD ["uvicorn", "src.main:api", "--host", "0.0.0.0", "--port", "8000"]