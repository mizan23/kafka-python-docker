FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure token file directory exists
RUN mkdir -p /app

# Run app
CMD ["python", "-u", "0_full_flow_main.py"]