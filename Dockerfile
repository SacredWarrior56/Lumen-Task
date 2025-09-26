# Use a slim Python image as the base
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies, including Chrome's dependencies
# and tools for adding the repository key and list
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    unzip \
    gnupg \
    ca-certificates \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxext6 \
    libxi6 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xvfb \
    fonts-liberation

# Add the Google Chrome repository and GPG key to ensure the download is trusted
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-archive-keyring.gpg
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list

# Install the latest stable version of Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Install Python dependencies from requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application files into the container
COPY . .

# Set the command to run your script
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
