"""
Notification Service for Arbitrage Alerts

This service handles sending notifications (SMS, email, etc.) when arbitrage
opportunities are detected.
"""

import logging
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

from app.models.arbitrage_signals import ArbitrageSignals


class NotificationService:
    """Service for sending arbitrage opportunity notifications."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Email configuration (set these in your .env file)
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_username = os.getenv("EMAIL_USERNAME")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.notification_email = os.getenv("NOTIFICATION_EMAIL")
        
        # SMS configuration (using Twilio - set these in your .env file)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.notification_phone = os.getenv("NOTIFICATION_PHONE")
        
    async def send_email_alert(self, signal: ArbitrageSignals) -> bool:
        """Send email alert for arbitrage opportunity."""
        if not all([self.email_username, self.email_password, self.notification_email]):
            self.logger.warning("Email configuration incomplete, skipping email alert")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['To'] = self.notification_email
            msg['Subject'] = f"🚨 Arbitrage Opportunity: {signal.strategy} - {((1.0 - signal.total_cost) * 100):.2f}% Profit"
            
            # Create email body
            profit_pct = (1.0 - signal.total_cost) * 100
            profit_amount = signal.executable_size * (1.0 - signal.total_cost)
            
            body = f"""
🚨 ARBITRAGE OPPORTUNITY DETECTED! 🚨

💰 Profit: {profit_pct:.2f}% (${profit_amount:.2f})
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

---
Prediction Market Arbitrage System
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_username, self.email_password)
            text = msg.as_string()
            server.sendmail(self.email_username, self.notification_email, text)
            server.quit()
            
            self.logger.info(f"✅ Email alert sent for signal {signal.id[:8]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send email alert: {e}")
            return False
    
    async def send_sms_alert(self, signal: ArbitrageSignals) -> bool:
        """Send SMS alert for arbitrage opportunity."""
        if not all([self.twilio_account_sid, self.twilio_auth_token, 
                   self.twilio_phone_number, self.notification_phone]):
            self.logger.warning("SMS configuration incomplete, skipping SMS alert")
            return False
        
        try:
            from twilio.rest import Client
            
            # Create Twilio client
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            # Create SMS message
            profit_pct = (1.0 - signal.total_cost) * 100
            profit_amount = signal.executable_size * (1.0 - signal.total_cost)
            
            message = f"""🚨 ARBITRAGE ALERT! 
{signal.strategy} - {profit_pct:.1f}% profit (${profit_amount:.0f})
Size: ${signal.executable_size:.0f}
Conf: {signal.confidence:.2f}
{signal.market_a_venue}↔{signal.market_b_venue}
ID: {signal.id[:8]}"""
            
            # Send SMS
            message = client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=self.notification_phone
            )
            
            self.logger.info(f"✅ SMS alert sent for signal {signal.id[:8]}... (SID: {message.sid})")
            return True
            
        except ImportError:
            self.logger.warning("Twilio not installed. Install with: pip install twilio")
            return False
        except Exception as e:
            self.logger.error(f"❌ Failed to send SMS alert: {e}")
            return False
    
    async def send_alert(self, signal: ArbitrageSignals) -> None:
        """Send all configured alerts for arbitrage opportunity."""
        self.logger.info(f"📤 Sending alerts for arbitrage signal {signal.id[:8]}...")
        
        # Send email alert
        email_sent = await self.send_email_alert(signal)
        
        # Send SMS alert
        sms_sent = await self.send_sms_alert(signal)
        
        if not email_sent and not sms_sent:
            self.logger.warning("No notification methods configured or available")
        else:
            self.logger.info(f"✅ Alerts sent - Email: {email_sent}, SMS: {sms_sent}")


# Global notification service instance
notification_service = NotificationService()
