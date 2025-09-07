"""
Polymarket on-chain event listener for real-time market data.
This approach listens to blockchain events instead of WebSocket API.
Based on: https://polygonscan.com/address/0x4D97DCd97eC945f40cF65F87097ACe5EA0476045
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from web3 import Web3, AsyncWeb3
from web3.providers import HTTPProvider, WebSocketProvider
from web3.utils.subscriptions import LogsSubscription, LogsSubscriptionContext

from app.services.base_reader import BaseVenueReader
from app.config import settings
from app.models.rules_text import RulesText
from app.models.book_levels import BookLevels


class PolyOnChainReader(BaseVenueReader):
    """Polymarket on-chain event listener for real-time market data."""
    
    def __init__(self, db: Session):
        super().__init__("polymarket", db)
        
        # On-chain configuration
        self.polygon_rpc_url = "https://polygon-rpc.com"  # Polygon mainnet RPC
        self.polygon_ws_url = "wss://polygon-mainnet.g.alchemy.com/v2/demo"  # Alchemy WebSocket RPC (free tier)
        
        # Polymarket Conditional Token Framework contracts
        self.conditional_tokens_address = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
        self.collateral_token_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC
        
        # Web3 instances
        self.w3_http = None
        self.w3_ws = None
        self.conditional_tokens_contract = None
        
        # Event listeners
        self.order_placed_callbacks: List[Callable] = []
        self.order_cancelled_callbacks: List[Callable] = []
        self.trade_executed_callbacks: List[Callable] = []
        self.market_created_callbacks: List[Callable] = []
        
        # Connection management
        self.connected = False
        self.listening = False
        
        # Conditional Tokens ABI (simplified - focusing on key events)
        self.conditional_tokens_abi = [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "account", "type": "address"},
                    {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "Transfer",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "account", "type": "address"},
                    {"indexed": True, "internalType": "uint256", "name": "tokenId", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}
                ],
                "name": "Approval",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "bytes32", "name": "questionId", "type": "bytes32"},
                    {"indexed": True, "internalType": "address", "name": "oracle", "type": "address"},
                    {"indexed": True, "internalType": "uint32", "name": "outcomeSlotCount", "type": "uint32"},
                    {"indexed": False, "internalType": "uint256", "name": "conditionId", "type": "uint256"}
                ],
                "name": "ConditionPreparation",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "bytes32", "name": "questionId", "type": "bytes32"},
                    {"indexed": True, "internalType": "uint256", "name": "conditionId", "type": "uint256"},
                    {"indexed": True, "internalType": "uint256", "name": "indexSet", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "payout", "type": "uint256"}
                ],
                "name": "ConditionResolution",
                "type": "event"
            }
        ]
        
    async def connect(self):
        """Connect to blockchain RPC."""
        try:
            self.logger.info("Connecting to Polygon RPC for on-chain events...")
            
            # Initialize HTTP provider for contract interactions
            self.w3_http = Web3(HTTPProvider(self.polygon_rpc_url))
            
            # Check HTTP connection
            if not self.w3_http.is_connected():
                raise Exception("Failed to connect to Polygon HTTP RPC")
            
            # Initialize contract
            self.conditional_tokens_contract = self.w3_http.eth.contract(
                address=self.conditional_tokens_address,
                abi=self.conditional_tokens_abi
            )
            
            # Initialize WebSocket provider for event subscriptions
            # For now, let's use HTTP polling as it's more reliable
            self.logger.info("Using HTTP polling for event listening (more reliable)")
            self.w3_ws = None
            
            self.connected = True
            self.logger.info("Connected to Polygon RPC and initialized contracts")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to blockchain: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from blockchain."""
        if self.w3_ws:
            await self.w3_ws.provider.disconnect()
        self.connected = False
        self.listening = False
        self.logger.info("Disconnected from blockchain")
    
    async def listen_for_events(self):
        """Listen for on-chain events using WebSocket subscriptions or HTTP polling."""
        if not self.connected:
            await self.connect()
        
        self.listening = True
        self.logger.info("Starting on-chain event listening...")
        
        try:
            if self.w3_ws:
                # Use WebSocket subscriptions
                await self._listen_with_websocket()
            else:
                # Use HTTP polling as fallback
                await self._listen_with_polling()
            
        except Exception as e:
            self.logger.error(f"Error in on-chain event listening: {e}")
            self.listening = False
    
    async def _listen_with_websocket(self):
        """Listen for events using WebSocket subscriptions."""
        try:
            # Subscribe to Transfer events (trades/transfers)
            transfer_event = self.conditional_tokens_contract.events.Transfer()
            
            # Subscribe to ConditionPreparation events (new markets)
            condition_prep_event = self.conditional_tokens_contract.events.ConditionPreparation()
            
            # Subscribe to ConditionResolution events (market resolutions)
            condition_resolution_event = self.conditional_tokens_contract.events.ConditionResolution()
            
            # Create subscriptions with handlers
            subscriptions = [
                LogsSubscription(
                    label="polymarket-transfers",
                    address=self.conditional_tokens_address,
                    topics=[transfer_event.topic],
                    handler=self._handle_transfer_event,
                    handler_context={"transfer_event": transfer_event}
                ),
                LogsSubscription(
                    label="polymarket-condition-prep",
                    address=self.conditional_tokens_address,
                    topics=[condition_prep_event.topic],
                    handler=self._handle_condition_prep_event,
                    handler_context={"condition_prep_event": condition_prep_event}
                ),
                LogsSubscription(
                    label="polymarket-condition-resolution",
                    address=self.conditional_tokens_address,
                    topics=[condition_resolution_event.topic],
                    handler=self._handle_condition_resolution_event,
                    handler_context={"condition_resolution_event": condition_resolution_event}
                )
            ]
            
            # Subscribe to all events
            await self.w3_ws.subscription_manager.subscribe(subscriptions)
            
            # Handle subscriptions
            await self.w3_ws.subscription_manager.handle_subscriptions(run_forever=True)
            
        except Exception as e:
            self.logger.error(f"Error in WebSocket event listening: {e}")
            raise
    
    async def _listen_with_polling(self):
        """Listen for events using HTTP polling."""
        self.logger.info("Using HTTP polling for event listening...")
        
        # Get the latest block number
        latest_block = self.w3_http.eth.block_number
        from_block = max(0, latest_block - 100)  # Start from 100 blocks ago
        
        self.logger.info(f"Starting HTTP polling from block {from_block}")
        
        while self.listening:
            try:
                # Get current block number
                current_block = self.w3_http.eth.block_number
                
                if current_block > from_block:
                    # Get events from the new blocks
                    await self._poll_events(from_block, current_block)
                    from_block = current_block + 1
                
                # Wait before next poll
                await asyncio.sleep(5)  # Poll every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in HTTP polling: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def _poll_events(self, from_block: int, to_block: int):
        """Poll for events in a block range."""
        try:
            # Get Transfer events
            transfer_events = self.conditional_tokens_contract.events.Transfer.get_logs(
                from_block=from_block,
                to_block=to_block
            )
            
            for event in transfer_events:
                await self._handle_transfer_event_polled(event)
            
            # Get ConditionPreparation events
            condition_prep_events = self.conditional_tokens_contract.events.ConditionPreparation.get_logs(
                from_block=from_block,
                to_block=to_block
            )
            
            for event in condition_prep_events:
                await self._handle_condition_prep_event_polled(event)
            
            # Get ConditionResolution events
            condition_resolution_events = self.conditional_tokens_contract.events.ConditionResolution.get_logs(
                from_block=from_block,
                to_block=to_block
            )
            
            for event in condition_resolution_events:
                await self._handle_condition_resolution_event_polled(event)
            
            if transfer_events or condition_prep_events or condition_resolution_events:
                self.logger.info(f"Found {len(transfer_events)} transfers, {len(condition_prep_events)} condition preps, {len(condition_resolution_events)} resolutions in blocks {from_block}-{to_block}")
                
        except Exception as e:
            self.logger.error(f"Error polling events from block {from_block} to {to_block}: {e}")
    
    async def _handle_transfer_event_polled(self, event):
        """Handle Transfer event from polling."""
        try:
            # Extract event data
            account = event['args']['account']
            token_id = event['args']['tokenId']
            amount = event['args']['amount']
            
            self.logger.info(f"Transfer event (polled): Account {account}, Token {token_id}, Amount {amount}")
            
            # Convert token_id to market information
            market_info = await self._parse_token_id(token_id)
            if market_info:
                await self._process_trade_event(market_info, account, amount)
            
            # Notify callbacks
            for callback in self.trade_executed_callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    self.logger.error(f"Error in trade executed callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling transfer event (polled): {e}")
    
    async def _handle_condition_prep_event_polled(self, event):
        """Handle ConditionPreparation event from polling."""
        try:
            # Extract event data
            question_id = event['args']['questionId']
            oracle = event['args']['oracle']
            outcome_slot_count = event['args']['outcomeSlotCount']
            condition_id = event['args']['conditionId']
            
            self.logger.info(f"New market created (polled): Question {question_id.hex()}, Outcomes {outcome_slot_count}")
            
            # Process new market
            await self._process_new_market_event(question_id, oracle, outcome_slot_count, condition_id)
            
            # Notify callbacks
            for callback in self.market_created_callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    self.logger.error(f"Error in market created callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling condition prep event (polled): {e}")
    
    async def _handle_condition_resolution_event_polled(self, event):
        """Handle ConditionResolution event from polling."""
        try:
            # Extract event data
            question_id = event['args']['questionId']
            condition_id = event['args']['conditionId']
            index_set = event['args']['indexSet']
            payout = event['args']['payout']
            
            self.logger.info(f"Market resolved (polled): Question {question_id.hex()}, Payout {payout}")
            
            # Process market resolution
            await self._process_market_resolution_event(question_id, condition_id, index_set, payout)
                    
        except Exception as e:
            self.logger.error(f"Error handling condition resolution event (polled): {e}")
    
    async def _handle_transfer_event(self, handler_context: LogsSubscriptionContext):
        """Handle Transfer events (trades/transfers)."""
        try:
            # Process the log event
            event_data = handler_context.transfer_event.process_log(handler_context.result)
            
            # Extract event data
            account = event_data.get('args', {}).get('account')
            token_id = event_data.get('args', {}).get('tokenId')
            amount = event_data.get('args', {}).get('amount')
            
            self.logger.info(f"Transfer event: Account {account}, Token {token_id}, Amount {amount}")
            
            # Convert token_id to market information
            market_info = await self._parse_token_id(token_id)
            if market_info:
                await self._process_trade_event(market_info, account, amount)
            
            # Notify callbacks
            for callback in self.trade_executed_callbacks:
                try:
                    await callback(event_data)
                except Exception as e:
                    self.logger.error(f"Error in trade executed callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling transfer event: {e}")
    
    async def _handle_condition_prep_event(self, handler_context: LogsSubscriptionContext):
        """Handle ConditionPreparation events (new markets)."""
        try:
            # Process the log event
            event_data = handler_context.condition_prep_event.process_log(handler_context.result)
            
            # Extract event data
            question_id = event_data.get('args', {}).get('questionId')
            oracle = event_data.get('args', {}).get('oracle')
            outcome_slot_count = event_data.get('args', {}).get('outcomeSlotCount')
            condition_id = event_data.get('args', {}).get('conditionId')
            
            self.logger.info(f"New market created: Question {question_id.hex()}, Outcomes {outcome_slot_count}")
            
            # Process new market
            await self._process_new_market_event(question_id, oracle, outcome_slot_count, condition_id)
            
            # Notify callbacks
            for callback in self.market_created_callbacks:
                try:
                    await callback(event_data)
                except Exception as e:
                    self.logger.error(f"Error in market created callback: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error handling condition prep event: {e}")
    
    async def _handle_condition_resolution_event(self, handler_context: LogsSubscriptionContext):
        """Handle ConditionResolution events (market resolutions)."""
        try:
            # Process the log event
            event_data = handler_context.condition_resolution_event.process_log(handler_context.result)
            
            # Extract event data
            question_id = event_data.get('args', {}).get('questionId')
            condition_id = event_data.get('args', {}).get('conditionId')
            index_set = event_data.get('args', {}).get('indexSet')
            payout = event_data.get('args', {}).get('payout')
            
            self.logger.info(f"Market resolved: Question {question_id.hex()}, Payout {payout}")
            
            # Process market resolution
            await self._process_market_resolution_event(question_id, condition_id, index_set, payout)
                    
        except Exception as e:
            self.logger.error(f"Error handling condition resolution event: {e}")
    
    async def _parse_token_id(self, token_id: int) -> Optional[Dict[str, Any]]:
        """Parse token ID to extract market information."""
        try:
            # Token ID structure in Polymarket:
            # tokenId = keccak256(abi.encodePacked(conditionId, indexSet))
            # We need to reverse engineer this to get market info
            
            # For now, we'll use a simplified approach
            # In a full implementation, you'd need to decode the token ID properly
            
            return {
                'token_id': token_id,
                'market_id': f"market_{token_id}",
                'outcome': f"outcome_{token_id % 2}"  # Simplified
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing token ID {token_id}: {e}")
            return None
    
    async def _process_trade_event(self, market_info: Dict[str, Any], account: str, amount: int):
        """Process a trade event and update order book."""
        try:
            market_id = market_info['market_id']
            outcome = market_info['outcome']
            
            # Convert amount from wei to human readable
            amount_human = amount / 1e18  # Assuming 18 decimals
            
            self.logger.info(f"Trade: Market {market_id}, Outcome {outcome}, Amount {amount_human}")
            
            # Create a simplified order book update based on the trade
            # In a real implementation, you'd need to reconstruct the full order book
            # from multiple events, but for now we'll create a basic representation
            
            order_book = {
                'buys': [],
                'sells': []
            }
            
            # For demonstration, we'll create a basic order book entry
            # In reality, you'd need to track all orders and reconstruct the book
            if amount_human > 0:
                # This is a simplified approach - in reality you'd need to:
                # 1. Determine the actual price from the trade
                # 2. Determine if it's a buy or sell
                # 3. Update the appropriate side of the order book
                
                # For now, we'll just persist a basic order book structure
                await self._persist_order_book(market_id, order_book)
            
        except Exception as e:
            self.logger.error(f"Error processing trade event: {e}")
    
    async def _process_new_market_event(self, question_id: bytes, oracle: str, outcome_slot_count: int, condition_id: int):
        """Process a new market creation event."""
        try:
            market_id = question_id.hex()
            
            self.logger.info(f"New market: {market_id}, Oracle: {oracle}, Outcomes: {outcome_slot_count}")
            
            # Create market record in database
            market = RulesText(
                venue_id=self.venue.id,
                market_id=market_id,
                question=f"Market {market_id}",
                description=f"Condition ID: {condition_id}, Oracle: {oracle}",
                status='active',
                created_at=datetime.utcnow()
            )
            
            self.db.add(market)
            self.db.commit()
            
            self.logger.info(f"Created new market record: {market_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing new market event: {e}")
    
    async def _process_market_resolution_event(self, question_id: bytes, condition_id: int, index_set: int, payout: int):
        """Process a market resolution event."""
        try:
            market_id = question_id.hex()
            
            self.logger.info(f"Market resolved: {market_id}, Payout: {payout}")
            
            # Update market status in database
            market = self.db.query(RulesText).filter(
                RulesText.venue_id == self.venue.id,
                RulesText.market_id == market_id
            ).first()
            
            if market:
                market.status = 'closed'
                market.updated_at = datetime.utcnow()
                self.db.commit()
                
                self.logger.info(f"Updated market status to closed: {market_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing market resolution event: {e}")
    
    # Callback registration methods
    def add_order_placed_callback(self, callback: Callable):
        """Add a callback for order placed events."""
        self.order_placed_callbacks.append(callback)
    
    def add_order_cancelled_callback(self, callback: Callable):
        """Add a callback for order cancelled events."""
        self.order_cancelled_callbacks.append(callback)
    
    def add_trade_executed_callback(self, callback: Callable):
        """Add a callback for trade executed events."""
        self.trade_executed_callbacks.append(callback)
    
    def add_market_created_callback(self, callback: Callable):
        """Add a callback for market created events."""
        self.market_created_callbacks.append(callback)
    
    # Required methods from BaseVenueReader
    async def fetch_markets(self) -> List[Dict[str, Any]]:
        """Fetch available markets - not used in on-chain mode."""
        return []
    
    async def fetch_order_book(self, market_id: str) -> Dict[str, Any]:
        """Fetch order book - not used in on-chain mode."""
        return {'buys': [], 'sells': []}
    
    async def fetch_trades(self, market_id: str) -> List[Dict[str, Any]]:
        """Fetch trades - not used in on-chain mode."""
        return []
    
    async def run_continuous_ingestion(self, interval_seconds: int = 60):
        """Run continuous on-chain event listening."""
        self.logger.info(f"Starting on-chain continuous ingestion for {self.venue_name}")
        
        try:
            await self.listen_for_events()
        except Exception as e:
            self.logger.error(f"Error in on-chain continuous ingestion: {e}")
            raise
    
    async def run_market_discovery(self):
        """Run market discovery - not applicable for on-chain mode."""
        self.logger.info("On-chain mode: Market discovery happens via on-chain events")
        return 0