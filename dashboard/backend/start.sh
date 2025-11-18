#!/bin/bash

# Baselinr Dashboard Backend - Start Script

echo "=========================================="
echo "Baselinr Dashboard Backend"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Creating .env from example..."
    cat > .env << EOL
BASELINR_DB_URL=postgresql://baselinr:baselinr@localhost:5433/baselinr
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
EOL
    echo ".env file created. Please review and update if needed."
fi

# Start the server
echo ""
echo "Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
python main.py

