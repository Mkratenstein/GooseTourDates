FROM python:3.11-slim

# Install Chrome and its dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    default-jdk \
    curl \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set up Chrome options for running in container
ENV CHROME_BIN=/usr/bin/google-chrome

# Install ChromeDriver using webdriver-manager
RUN pip install webdriver-manager

# Set up working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install our package in development mode
RUN pip install -e .

# Set up ChromeDriver directory and permissions
RUN mkdir -p /root/.wdm/drivers/chromedriver/linux64 \
    && mkdir -p /root/.cache/selenium \
    && chmod -R 777 /root/.wdm \
    && chmod -R 777 /root/.cache

# Set environment variables for Selenium
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV PYTHONPATH=/app
ENV WDM_LOCAL_CACHE=1
ENV WDM_SSL_VERIFY=0

# Command to run the application
CMD ["python", "scraper/discord_bot.py"] 