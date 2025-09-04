# Data Ingestion Services

This directory contains the data ingestion services for the Prediction Market Arbitrage System. These services are responsible for fetching real-time market data, order books, and trades from prediction market venues like Kalshi and Polymarket.

## Architecture

### Base Reader (`base_reader.py`)
- Abstract base class defining the interface for venue data ingestion
- Implements common functionality like 7-day resolution filtering
- Handles data persistence to database tables
- Provides rate limiting and error handling

### Venue Readers
- **Kalshi Reader** (`kalshi_reader.py`): Implements Kalshi-specific API integration
- **Polymarket Reader** (`poly_reader.py`): Implements Polymarket-specific API integration

### Ingestion Manager (`ingestion_manager.py`)
- Coordinates multiple venue readers
- Provides unified interface for data ingestion operations
- Manages continuous ingestion processes
- Handles service status and health monitoring

## Features

### Market Data Ingestion
- Fetches available markets from venues
- Filters for markets resolving within 7 days (configurable)
- Stores market rules and metadata in `rules_text` table
- Handles market updates and versioning

### Order Book Ingestion
- Fetches top 10 price levels for both buy and sell sides
- Stores order book data in `book_levels` table
- Maintains price level ordering (bids descending, asks ascending)
- Tracks timestamps for data freshness

### Trade Data Ingestion
- Fetches recent trade history
- Stores trade details (price, size, side, timestamp)
- Handles trade deduplication and updates

### 7-Day Resolution Filter
- Automatically filters markets based on resolution date
- Only processes markets that resolve within the specified window
- Configurable via `max_resolution_days` parameter

## API Endpoints

The data ingestion services expose the following REST API endpoints:

### Market Discovery
- `POST /api/v1/ingestion/discover-markets` - Run market discovery
- `POST /api/v1/ingestion/discover-markets?background=true` - Run in background

### Data Ingestion
- `POST /api/v1/ingestion/ingest-data` - Ingest all data types
- `POST /api/v1/ingestion/ingest-data?background=true` - Run in background

### Continuous Ingestion
- `POST /api/v1/ingestion/start-continuous` - Start continuous ingestion
- `POST /api/v1/ingestion/stop-continuous` - Stop continuous ingestion

### Monitoring
- `GET /api/v1/ingestion/status` - Get ingestion service status
- `GET /api/v1/ingestion/venues` - List available venues
- `GET /api/v1/ingestion/health` - Health check
- `POST /api/v1/ingestion/test-connection/{venue}` - Test venue connectivity

## CLI Usage

The services can also be run from the command line using the `scripts/run_ingestion.py` script:

```bash
# Market discovery
python scripts/run_ingestion.py discover

# Data ingestion
python scripts/run_ingestion.py ingest

# Continuous ingestion
python scripts/run_ingestion.py continuous --interval 30

# Check status
python scripts/run_ingestion.py status

# List venues
python scripts/run_ingestion.py venues

# Test connection
python scripts/run_ingestion.py test --venue-name kalshi
```

## Configuration

### Environment Variables
Set the following environment variables in your `.env` file:

```bash
# Kalshi API credentials
KALSHI_API_KEY_ID=your_kalshi_key_id
KALSHI_API_PRIVATE_KEY=your_kalshi_private_key

# Polymarket API credentials
POLYMARKET_API_KEY=your_polymarket_key
POLYMARKET_API_SECRET=your_polymarket_secret
POLYMARKET_API_PASSPHRASE=your_polymarket_passphrase
```

### Database Setup
Ensure the database contains venue records:

```bash
# Seed venues
python scripts/seed_venues.py
```

## Data Flow

1. **Market Discovery**: Fetches all available markets and filters by resolution date
2. **Data Ingestion**: For each active market, fetches order books and trades
3. **Data Persistence**: Stores data in appropriate database tables with timestamps
4. **Continuous Updates**: Runs at configurable intervals to maintain data freshness

## Error Handling

- **API Failures**: Logs errors and continues with other venues/markets
- **Rate Limiting**: Built-in delays between API calls to respect venue limits
- **Data Validation**: Validates data before persistence
- **Graceful Degradation**: Continues operation even if some venues fail

## Performance Considerations

- **Concurrent Processing**: Multiple venues can be processed simultaneously
- **Rate Limiting**: Configurable delays prevent API rate limit violations
- **Batch Operations**: Database operations are batched for efficiency
- **Background Processing**: Long-running operations can run in background

## Testing

Run the test script to verify the implementation:

```bash
python test_ingestion.py
```

## Monitoring

The services provide comprehensive monitoring capabilities:

- **Service Status**: Active readers, venue health, data counts
- **Health Checks**: API endpoint for monitoring systems
- **Error Tracking**: Detailed error logging and reporting
- **Performance Metrics**: Ingestion rates and timing information

## Future Enhancements

- **WebSocket Support**: Real-time data streaming for lower latency
- **Data Compression**: Efficient storage of historical data
- **Advanced Filtering**: More sophisticated market selection criteria
- **Load Balancing**: Distribute ingestion across multiple instances
- **Alerting**: Notifications for data quality issues or service failures
