#!/bin/bash
# Deployment script for Cloudflare Pages
# Usage: ./scripts/deploy.sh

set -e

echo "🚀 Deploying Baselinr Demo to Cloudflare Pages..."

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Error: wrangler CLI not found. Install it with: npm install -g wrangler"
    exit 1
fi

# Navigate to frontend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$FRONTEND_DIR"

echo "📦 Building frontend for demo mode..."
npm run build:demo

if [ ! -d "out" ]; then
    echo "❌ Error: Build output directory 'out' not found!"
    exit 1
fi

echo "☁️  Deploying to Cloudflare Pages..."
wrangler pages deploy out --project-name=baselinr-demo

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🌐 Your demo should be available at: https://baselinr-demo.pages.dev"
else
    echo "❌ Deployment failed!"
    exit 1
fi
