#!/usr/bin/env python3
"""
Continuous Arbitrage Monitoring System

This script runs continuously, monitoring for arbitrage opportunities and sending
text alerts when profitable opportunities are detected.
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.arbitrage_engine import arbitrage_engine
from app.services.ingestion_manager import create_ingestion_manager
from app.services.notification_service import notification_service
from app.database import get_db
from app.models.arbitrage_signals import ArbitrageSignals


class ArbitrageMonitor:
    """Continuous arbitrage monitoring with alert system."""
    
    def __init__(self, 
                 ingestion_interval: int = 60,
                 analysis_interval: int = 30,
                 min_profit_threshold: float = 0.02,
                 max_executable_size: float = 1000.0):
        """
        Initialize the arbitrage monitor.
        
        Args:
            ingestion_interval: Seconds between data ingestion runs
            analysis_interval: Seconds between arbitrage analysis runs
            min_profit_threshold: Minimum profit percentage to trigger alert (0.02 = 2%)
            max_executable_size: Maximum executable size to consider for alerts
        """
        self.ingestion_interval = ingestion_interval
        self.analysis_interval = analysis_interval
        self.min_profit_threshold = min_profit_threshold
        self.max_executable_size = max_executable_size
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('arbitrage_monitor.log')
            ]
        )
        
        # Track last alert times to avoid spam
        self.last_alert_times = {}
        self.alert_cooldown = 300  # 5 minutes between alerts for same pair
        
    async def send_alert(self, signal: ArbitrageSignals) -> None:
        """Send arbitrage opportunity alert."""
        try:
            # Check cooldown to avoid spam
            pair_id = signal.pair_id
            now = datetime.utcnow()
            
            if pair_id in self.last_alert_times:
                time_since_last = (now - self.last_alert_times[pair_id]).total_seconds()
                if time_since_last < self.alert_cooldown:
                    self.logger.info(f"Alert for pair {pair_id[:8]}... on cooldown ({time_since_last:.0f}s remaining)")
                    return
            
            # Calculate profit percentage
            profit_pct = (1.0 - signal.total_cost) * 100
            
            # Create alert message
            alert_message = f"""
🚨 ARBITRAGE OPPORTUNITY DETECTED! 🚨

💰 Profit: {profit_pct:.2f}% (${signal.executable_size * (1.0 - signal.total_cost):.2f})
📊 Strategy: {signal.strategy}
💵 Executable Size: ${signal.executable_size:.2f}
🎯 Confidence: {signal.confidence:.2f}

📈 Market A ({signal.market_a_venue}):
   Bid: {signal.market_a_best_bid:.4f} | Ask: {signal.market_a_best_ask:.4f}

📉 Market B ({signal.market_b_venue}):
   Bid: {signal.market_b_best_bid:.4f} | Ask: {signal.market_b_best_ask:.4f}

⏰ Detected: {signal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
🔗 Signal ID: {signal.id[:8]}...

⚠️  This is an automated alert. Verify market conditions before trading.
            """.strip()
            
            # For now, just log the alert (you can add SMS/email here)
            self.logger.info(f"🚨 ARBITRAGE ALERT: {alert_message}")
            
            # Print to console for immediate visibility
            print("\n" + "="*80)
            print(alert_message)
            print("="*80 + "\n")
            
            # Send notifications (email/SMS)
            await notification_service.send_alert(signal)
            
            # Update last alert time
            self.last_alert_times[pair_id] = now
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")
    
    async def run_data_ingestion(self) -> bool:
        """Run data ingestion for all venues."""
        try:
            self.logger.info("🔄 Starting data ingestion...")
            
            db = next(get_db())
            try:
                manager = create_ingestion_manager(db)
                
                # Run ingestion for both venues
                results = await manager.run_market_discovery(['kalshi', 'polymarket'])
                
                # Check if ingestion was successful
                success = all(result == 1 for result in results.values())
                
                if success:
                    self.logger.info("✅ Data ingestion completed successfully")
                else:
                    self.logger.warning(f"⚠️ Data ingestion had issues: {results}")
                
                return success
                
            finally:
                db.close()
                
        except Exception as e:
            self.logger.error(f"❌ Data ingestion failed: {e}")
            return False
    
    async def run_arbitrage_analysis(self) -> List[ArbitrageSignals]:
        """Run arbitrage analysis and return profitable opportunities."""
        try:
            self.logger.info("🔍 Running arbitrage analysis...")
            
            # Run analysis
            signals = await arbitrage_engine.analyze_all_pairs()
            
            # Filter for profitable opportunities
            profitable_signals = [
                signal for signal in signals
                if (signal.is_arbitrage and 
                    signal.executable_size <= self.max_executable_size and
                    (1.0 - signal.total_cost) >= self.min_profit_threshold)
            ]
            
            if profitable_signals:
                self.logger.info(f"💰 Found {len(profitable_signals)} profitable arbitrage opportunities!")
            else:
                self.logger.info("📊 No profitable arbitrage opportunities found")
            
            return profitable_signals
            
        except Exception as e:
            self.logger.error(f"❌ Arbitrage analysis failed: {e}")
            return []
    
    async def monitor_loop(self) -> None:
        """Main monitoring loop."""
        self.logger.info("🚀 Starting arbitrage monitoring system...")
        self.logger.info(f"📊 Ingestion interval: {self.ingestion_interval}s")
        self.logger.info(f"🔍 Analysis interval: {self.analysis_interval}s")
        self.logger.info(f"💰 Min profit threshold: {self.min_profit_threshold*100:.1f}%")
        self.logger.info(f"💵 Max executable size: ${self.max_executable_size}")
        
        last_ingestion = datetime.utcnow() - timedelta(seconds=self.ingestion_interval)
        last_analysis = datetime.utcnow() - timedelta(seconds=self.analysis_interval)
        
        while True:
            try:
                now = datetime.utcnow()
                
                # Run data ingestion if enough time has passed
                if (now - last_ingestion).total_seconds() >= self.ingestion_interval:
                    await self.run_data_ingestion()
                    last_ingestion = now
                
                # Run arbitrage analysis if enough time has passed
                if (now - last_analysis).total_seconds() >= self.analysis_interval:
                    profitable_signals = await self.run_arbitrage_analysis()
                    
                    # Send alerts for profitable opportunities
                    for signal in profitable_signals:
                        await self.send_alert(signal)
                    
                    last_analysis = now
                
                # Sleep for a short interval before next check
                await asyncio.sleep(10)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Continuous Arbitrage Monitoring System")
    parser.add_argument("--ingestion-interval", type=int, default=60,
                       help="Seconds between data ingestion runs (default: 60)")
    parser.add_argument("--analysis-interval", type=int, default=30,
                       help="Seconds between arbitrage analysis runs (default: 30)")
    parser.add_argument("--min-profit", type=float, default=0.02,
                       help="Minimum profit percentage to trigger alert (default: 0.02 = 2 percent)")
    parser.add_argument("--max-size", type=float, default=1000.0,
                       help="Maximum executable size to consider for alerts (default: 1000)")
    
    args = parser.parse_args()
    
    # Create and run monitor
    monitor = ArbitrageMonitor(
        ingestion_interval=args.ingestion_interval,
        analysis_interval=args.analysis_interval,
        min_profit_threshold=args.min_profit,
        max_executable_size=args.max_size
    )
    
    await monitor.monitor_loop()


if __name__ == "__main__":
    asyncio.run(main())
