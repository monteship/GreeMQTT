FROM python:3.13-slim
LABEL authors="monteship"

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the MQTT port (default: 1883)
EXPOSE 1883

# Set the default command to run the application
CMD ["python", "main.py"]