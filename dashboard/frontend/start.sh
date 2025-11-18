#!/bin/bash

# Baselinr Dashboard Frontend - Start Script

echo "=========================================="
echo "Baselinr Dashboard Frontend"
echo "=========================================="

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "Warning: .env.local file not found!"
    echo "Creating .env.local..."
    cat > .env.local << EOL
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
EOL
    echo ".env.local file created."
fi

# Start the development server
echo ""
echo "Starting Next.js development server..."
echo "Dashboard will be available at: http://localhost:3000"
echo ""
npm run dev

