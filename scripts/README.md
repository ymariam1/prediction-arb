# Scripts Directory

This directory contains all executable scripts for the Prediction Market Arbitrage System, organized by purpose.

## 📁 Directory Structure

### `production/`
Production-ready scripts for running the system in production environments.

- **`run_arbitrage.py`** - Run arbitrage detection analysis
- **`run_ingestion.py`** - Run data ingestion from venues
- **`run_integrated_system.py`** - Run the complete integrated system
- **`run_normalization.py`** - Run market normalization pipeline
- **`run_polymarket_onchain.py`** - Run Polymarket on-chain event listener

### `testing/`
Test scripts for validating individual components.

- **`test_kalshi_websocket.py`** - Test Kalshi WebSocket connection
- **`test_polymarket_onchain.py`** - Test Polymarket on-chain listener
- **`test_polymarket_websocket_v2.py`** - Test Polymarket WebSocket (v2)
- **`test_polymarket_websocket.py`** - Test Polymarket WebSocket (v1)

### `utilities/`
Utility scripts for database management, debugging, and data creation.

- **`create_pairs.py`** - Create market pairs for arbitrage analysis
- **`create_profitable_arbitrage.py`** - Create profitable arbitrage opportunities
- **`create_test_pair.py`** - Create test market pairs
- **`debug_pairs.py`** - Debug market pair issues
- **`find_pairs.py`** - Find potential market pairs
- **`init_db.py`** - Initialize database
- **`init.sql`** - SQL initialization script
- **`monitor_arbitrage.py`** - Monitor arbitrage opportunities
- **`seed_venues.py`** - Seed venue data

### `tests/`
Comprehensive test suite for the system.

- **`test_arbitrage.py`** - Test arbitrage engine
- **`test_db.py`** - Test database operations
- **`test_ingestion.py`** - Test data ingestion
- **`test_normalization_*.py`** - Test normalization pipeline
- **`test_vectorization.py`** - Test market vectorization
- **`demo_monitoring.py`** - Demo monitoring system

## 🚀 Quick Start

### Production Scripts
```bash
# Run the complete system
python3 scripts/production/run_integrated_system.py

# Run just data ingestion
python3 scripts/production/run_ingestion.py

# Run arbitrage detection
python3 scripts/production/run_arbitrage.py
```

### Testing Scripts
```bash
# Test on-chain listener
python3 scripts/testing/test_polymarket_onchain.py

# Test WebSocket connections
python3 scripts/testing/test_kalshi_websocket.py
```

### Utility Scripts
```bash
# Initialize database
python3 scripts/utilities/init_db.py

# Create test pairs
python3 scripts/utilities/create_test_pair.py
```

## 📝 Notes

- All scripts should be run from the project root directory
- Make sure to set up your environment variables before running
- Check the main README.md for system requirements
- Production scripts are designed to run continuously
- Test scripts are for validation and debugging
