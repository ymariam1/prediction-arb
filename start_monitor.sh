#!/bin/bash

# Arbitrage Monitoring Startup Script
# This script starts the continuous arbitrage monitoring system

echo "🚀 Starting Prediction Market Arbitrage Monitor..."
echo "=================================================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create one based on env.example"
    echo "   Make sure to configure your API keys and notification settings."
    exit 1
fi

# Check if Python dependencies are installed
echo "📦 Checking dependencies..."
python -c "import twilio" 2>/dev/null || {
    echo "⚠️  Twilio not installed. Installing..."
    pip install twilio
}

# Start the monitoring system
echo "🔍 Starting continuous monitoring..."
echo "   - Data ingestion every 60 seconds"
echo "   - Arbitrage analysis every 30 seconds"
echo "   - Minimum profit threshold: 2%"
echo "   - Maximum executable size: $1000"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo "=================================================="

python scripts/monitor_arbitrage.py \
    --ingestion-interval 60 \
    --analysis-interval 30 \
    --min-profit 0.02 \
    --max-size 1000
