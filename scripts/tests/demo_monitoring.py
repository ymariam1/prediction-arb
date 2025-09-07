#!/usr/bin/env python3
"""
Demo script to show how the monitoring system works

This script simulates the monitoring system finding a profitable arbitrage opportunity
and sending an alert.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.notification_service import notification_service


async def demo_arbitrage_alert():
    """Demonstrate what an arbitrage alert looks like."""
    
    print("🎯 ARBITRAGE MONITORING SYSTEM DEMO")
    print("=" * 60)
    print("This demonstrates what happens when the system detects")
    print("a profitable arbitrage opportunity in real-time.")
    print("=" * 60)
    
    # Simulate finding a profitable arbitrage opportunity
    print("\n🔍 Monitoring system running...")
    print("📊 Analyzing market pairs...")
    print("💰 PROFITABLE ARBITRAGE DETECTED!")
    
    # Create a mock arbitrage signal for demonstration
    class MockSignal:
        def __init__(self):
            self.id = "demo-signal-123"
            self.strategy = "sell_a_buy_b"
            self.total_cost = 0.95  # 5% profit
            self.executable_size = 1000.0
            self.confidence = 0.92
            self.market_a_venue = "kalshi"
            self.market_b_venue = "polymarket"
            self.market_a_best_bid = 0.45
            self.market_a_best_ask = 0.46
            self.market_b_best_bid = 0.48
            self.market_b_best_ask = 0.49
            self.created_at = datetime.utcnow()
    
    mock_signal = MockSignal()
    
    # Calculate profit
    profit_pct = (1.0 - mock_signal.total_cost) * 100
    profit_amount = mock_signal.executable_size * (1.0 - mock_signal.total_cost)
    
    # Display the alert
    alert_message = f"""
🚨 ARBITRAGE OPPORTUNITY DETECTED! 🚨

💰 Profit: {profit_pct:.2f}% (${profit_amount:.2f})
📊 Strategy: {mock_signal.strategy}
💵 Executable Size: ${mock_signal.executable_size:.2f}
🎯 Confidence: {mock_signal.confidence:.2f}

📈 Market A ({mock_signal.market_a_venue}):
   Bid: {mock_signal.market_a_best_bid:.4f} | Ask: {mock_signal.market_a_best_ask:.4f}

📉 Market B ({mock_signal.market_b_venue}):
   Bid: {mock_signal.market_b_best_bid:.4f} | Ask: {mock_signal.market_b_best_ask:.4f}

⏰ Detected: {mock_signal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
🔗 Signal ID: {mock_signal.id}...

⚠️  This is an automated alert. Verify market conditions before trading.
    """.strip()
    
    print("\n" + "="*80)
    print(alert_message)
    print("="*80)
    
    print(f"\n📱 NOTIFICATION SYSTEM:")
    print(f"✅ Console alert displayed (above)")
    print(f"📧 Email notification would be sent (if configured)")
    print(f"📱 SMS notification would be sent (if configured)")
    print(f"📝 Alert logged to arbitrage_monitor.log")
    
    print(f"\n🔄 MONITORING CONTINUES:")
    print(f"⏰ Next analysis in 30 seconds...")
    print(f"🔄 Next data ingestion in 60 seconds...")
    print(f"🎯 System will continue monitoring for more opportunities")
    
    print(f"\n✅ DEMO COMPLETE!")
    print(f"The monitoring system is ready to detect real arbitrage opportunities")
    print(f"and send you alerts when profitable trades are found.")


async def main():
    """Main demo function."""
    await demo_arbitrage_alert()


if __name__ == "__main__":
    asyncio.run(main())
