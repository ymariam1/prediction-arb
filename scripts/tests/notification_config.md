# Arbitrage Notification Configuration

This document explains how to configure email and SMS notifications for arbitrage opportunities.

## Email Notifications

Add these variables to your `.env` file:

```bash
# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
NOTIFICATION_EMAIL=your-email@gmail.com
```

### Gmail Setup:
1. Enable 2-factor authentication on your Gmail account
2. Generate an "App Password" for this application
3. Use the app password (not your regular password) in `EMAIL_PASSWORD`

## SMS Notifications (Twilio)

Add these variables to your `.env` file:

```bash
# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
NOTIFICATION_PHONE=+1234567890
```

### Twilio Setup:
1. Sign up for a Twilio account at https://www.twilio.com
2. Get your Account SID and Auth Token from the Twilio Console
3. Purchase a phone number from Twilio
4. Add your personal phone number to receive alerts

## Installation

Install the required dependencies:

```bash
pip install twilio
```

## Running the Monitor

Start the continuous monitoring system:

```bash
# Basic monitoring (60s ingestion, 30s analysis)
python scripts/monitor_arbitrage.py

# Custom intervals
python scripts/monitor_arbitrage.py --ingestion-interval 120 --analysis-interval 60

# Custom profit threshold (2% minimum profit)
python scripts/monitor_arbitrage.py --min-profit 0.02

# Custom max executable size ($500)
python scripts/monitor_arbitrage.py --max-size 500
```

## Alert Cooldown

The system has a 5-minute cooldown between alerts for the same market pair to prevent spam. This can be adjusted in the `ArbitrageMonitor` class.

## Logs

All monitoring activity is logged to:
- Console output
- `arbitrage_monitor.log` file

## Example Alert

When a profitable arbitrage opportunity is detected, you'll receive:

```
🚨 ARBITRAGE OPPORTUNITY DETECTED! 🚨

💰 Profit: 3.25% ($32.50)
📊 Strategy: sell_a_buy_b
💵 Executable Size: $1000.00
🎯 Confidence: 0.95

📈 Market A (kalshi):
   Bid: 0.4500 | Ask: 0.4600

📉 Market B (polymarket):
   Bid: 0.4800 | Ask: 0.4900

⏰ Detected: 2025-09-06 11:45:30 UTC
🔗 Signal ID: a1b2c3d4...

⚠️  This is an automated alert. Verify market conditions before trading.
```
