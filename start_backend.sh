#!/bin/bash

# Binance Arbitrage Backend Startup Script

echo "🚀 Starting Binance Arbitrage Execution Backend"
echo "================================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "📝 Please edit .env file with your Binance API credentials before running again."
    echo "   nano .env"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check API keys are configured
echo "🔑 Checking configuration..."
if grep -q "your_binance_api_key_here" .env; then
    echo "❌ Please configure your Binance API keys in .env file"
    echo "   Edit .env and replace 'your_binance_api_key_here' with your actual API key"
    exit 1
fi

echo "✅ Configuration looks good!"
echo ""
echo "🎯 Starting backend server..."
echo "   API will be available at: http://localhost:8000"
echo "   Interactive docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python3 main.py