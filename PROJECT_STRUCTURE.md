# Project Structure

This document outlines the clean, organized structure of the Prediction Market Arbitrage System.

## 📁 Directory Structure

```
prediction-arb/
├── 📁 app/                          # Main application code
│   ├── 📁 api/                      # REST API endpoints
│   │   ├── arbitrage.py            # Arbitrage API endpoints
│   │   └── ingestion.py            # Data ingestion API endpoints
│   ├── 📁 models/                   # Database models
│   │   ├── arbitrage_signals.py    # Arbitrage signals model
│   │   ├── book_levels.py          # Order book data model
│   │   ├── canonical_market.py     # Canonical market model
│   │   ├── pairs.py                # Market pairs model
│   │   ├── rules_text.py           # Market rules model
│   │   └── ...                     # Other models
│   ├── 📁 services/                 # Business logic services
│   │   ├── arbitrage_engine.py     # Core arbitrage detection
│   │   ├── ingestion_manager.py    # Data ingestion coordination
│   │   ├── kalshi_reader.py        # Kalshi API integration
│   │   ├── kalshi_websocket_reader.py # Kalshi WebSocket integration
│   │   ├── poly_reader.py          # Polymarket API integration
│   │   ├── poly_onchain_reader.py  # Polymarket on-chain integration
│   │   └── ...                     # Other services
│   ├── config.py                   # Application configuration
│   ├── database.py                 # Database connection
│   └── main.py                     # FastAPI application
│
├── 📁 scripts/                      # Executable scripts
│   ├── 📁 production/               # Production scripts
│   │   ├── run_arbitrage.py        # Run arbitrage detection
│   │   ├── run_ingestion.py        # Run data ingestion
│   │   ├── run_integrated_system.py # Run complete system
│   │   └── run_polymarket_onchain.py # Run on-chain listener
│   ├── 📁 testing/                  # Test scripts
│   │   ├── test_kalshi_websocket.py # Test Kalshi WebSocket
│   │   └── test_polymarket_onchain.py # Test on-chain listener
│   ├── 📁 utilities/                # Utility scripts
│   │   ├── create_pairs.py         # Create market pairs
│   │   ├── init_db.py              # Initialize database
│   │   └── seed_venues.py          # Seed venue data
│   └── 📁 tests/                    # Comprehensive test suite
│       ├── test_arbitrage.py       # Test arbitrage engine
│       ├── test_ingestion.py       # Test data ingestion
│       └── ...                     # Other tests
│
├── 📁 docs/                         # Documentation
│   ├── ONCHAIN_INTEGRATION.md      # On-chain integration guide
│   └── QUICK_START.md              # Quick start guide
│
├── 📁 logs/                         # Log files
│   ├── arbitrage_monitor.log       # Arbitrage monitoring logs
│   ├── ingestion.log               # Data ingestion logs
│   └── normalization.log           # Normalization logs
│
├── 📁 data/                         # Data files
│   └── 📁 normalization_cache/      # Normalization cache
│       └── normalized_markets.pkl  # Cached normalized markets
│
├── 📁 alembic/                      # Database migrations
│   ├── env.py                      # Alembic environment
│   └── script.py.mako              # Migration template
│
├── 📄 README.md                     # Main project documentation
├── 📄 PROJECT_STRUCTURE.md          # This file
├── 📄 requirements.txt              # Python dependencies
├── 📄 docker-compose.yml            # Docker configuration
├── 📄 env.example                   # Environment variables template
├── 📄 .gitignore                    # Git ignore rules
└── 📄 start_monitor.sh              # System startup script
```

## 🎯 Key Components

### **Core Services**
- **Arbitrage Engine**: Detects arbitrage opportunities between markets
- **Ingestion Manager**: Coordinates data collection from multiple venues
- **On-Chain Reader**: Real-time blockchain event monitoring
- **API Readers**: REST API integration for venue data

### **Data Models**
- **BookLevels**: Order book data storage
- **RulesText**: Market metadata and rules
- **Pairs**: Market pair relationships
- **ArbitrageSignals**: Detected arbitrage opportunities

### **Scripts Organization**
- **Production**: Scripts for running the system in production
- **Testing**: Scripts for validating individual components
- **Utilities**: Scripts for database management and debugging
- **Tests**: Comprehensive test suite

## 🚀 Getting Started

1. **Setup Environment**: Copy `env.example` to `.env` and configure
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Initialize Database**: `python3 scripts/utilities/init_db.py`
4. **Run System**: `python3 scripts/production/run_integrated_system.py`

## 📝 Notes

- All scripts should be run from the project root directory
- Logs are automatically organized in the `logs/` directory
- Cache files are stored in `data/normalization_cache/`
- Database files are excluded from version control
- The system is designed for both development and production use
