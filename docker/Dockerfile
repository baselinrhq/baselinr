FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install Baselinr in development mode
RUN pip install -e .

# Set up Dagster home
ENV DAGSTER_HOME=/opt/dagster/dagster_home
RUN mkdir -p $DAGSTER_HOME

# Copy Dagster configuration
COPY docker/dagster.yaml $DAGSTER_HOME/dagster.yaml
COPY docker/workspace.yaml $DAGSTER_HOME/workspace.yaml

EXPOSE 3000

CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]

