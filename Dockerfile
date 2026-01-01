# 1. Use an official lightweight Python image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Install System Dependencies & Google Chrome (Crucial for Selenium)
# We need wget and gnupg to download Chrome, and Chrome itself for the scrapers.
RUN apt-get update && apt-get install -y wget gnupg2 unzip curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

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