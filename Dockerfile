FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and ChromeDriver in separate steps for better error handling
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver with retry logic
RUN for i in 1 2 3; do \
        wget -q "https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.165/linux64/chromedriver-linux64.zip" && \
        unzip chromedriver-linux64.zip && \
        mv chromedriver-linux64/chromedriver /usr/local/bin/ && \
        chmod +x /usr/local/bin/chromedriver && \
        rm -rf chromedriver-linux64.zip chromedriver-linux64 && \
        break || \
        if [ $i -eq 3 ]; then exit 1; fi; \
        sleep 5; \
    done

# Set up working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python files
COPY scraper.py .
COPY data_processor.py .
COPY cache_manager.py .
COPY discord_bot.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV RAILWAY_DATA_DIR=/data
ENV PYTHONIOENCODING=utf-8
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Create data directory with proper permissions
RUN mkdir -p /data && chmod 777 /data

# Run the script with output redirection
CMD ["python", "-u", "discord_bot.py"] 