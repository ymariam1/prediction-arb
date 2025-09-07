-- Basic PostgreSQL initialization for prediction-arb
-- This script runs when the container starts

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database if it doesn't exist (this will be handled by Docker environment)
-- The database 'prediction_arb' is created by the POSTGRES_DB environment variable
