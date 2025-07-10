# Use a lightweight Python base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy the operator code
COPY operator.py .

# Install required Python libraries
RUN pip install --no-cache-dir kopf kubernetes

# Run the Kopf operator in standalone mode
ENTRYPOINT ["kopf", "run", "--standalone", "operator.py"]
