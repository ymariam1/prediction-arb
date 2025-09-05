# Prediction Market Arbitrage System

A sophisticated system for identifying and executing arbitrage opportunities across prediction market venues like Kalshi and Polymarket.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Git

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd prediction-arb

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Database Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Wait for services to be healthy
docker-compose ps
```

### 3. Initialize Database

```bash
# Create tables and seed initial data
python scripts/init_db.py
```

### 4. Run the Application

```bash
# Start the FastAPI server
python -m app.main

# Or use uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access the API

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Root Endpoint: http://localhost:8000/

## 🏗️ Project Structure

```
prediction-arb/
├── app/                    # Main application code
│   ├── models/            # Database models
│   ├── config.py          # Configuration settings
│   ├── database.py        # Database connection
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
├── docker-compose.yml     # Local development services
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🗄️ Database Schema

The system uses PostgreSQL with the following core tables:

- **venue**: Prediction market venues (Kalshi, Polymarket)
- **rules_text**: Raw market rules from venues
- **canonical_market**: Normalized market data
- **pairs**: Matched market pairs for arbitrage
- **book_levels**: Order book data from venues
- **orders**: Trading orders
- **fills**: Order fills
- **positions**: User positions
- **settlements**: Market settlements
- **audit_log**: System audit trail
- **users**: User authentication and management

## 🔧 Development

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

### Code Formatting

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
```

## 🌐 API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)

## 🔐 Authentication

The system uses JWT-based authentication with role-based access control:

- **viewer**: Read-only access to market data
- **trader**: Can place orders and manage positions
- **admin**: Full system access

## 📊 Monitoring

- Health checks for all services
- Structured logging with structlog
- Database connection pooling
- Comprehensive audit trail

## 🚀 Deployment

### Local Development

- PostgreSQL 15 via Docker
- Redis 7 via Docker
- FastAPI with hot reload

### Production Considerations

- Use environment variables for sensitive data
- Configure proper CORS settings
- Set up SSL/TLS termination
- Implement rate limiting
- Use production-grade database and Redis instances
