"""
Arbitrage API Endpoints

Provides REST API endpoints for arbitrage detection and signal management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.services.arbitrage_engine import arbitrage_engine
from app.models.arbitrage_signals import ArbitrageSignals
from app.models.pairs import Pairs


router = APIRouter(prefix="/api/v1/arbitrage", tags=["arbitrage"])


@router.post("/analyze")
async def analyze_arbitrage_opportunities(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Analyze all active market pairs for arbitrage opportunities.
    
    This endpoint triggers the arbitrage detection engine to analyze all
    active market pairs and identify profitable opportunities.
    """
    try:
        # Run analysis in background
        background_tasks.add_task(arbitrage_engine.analyze_all_pairs)
        
        return {
            "message": "Arbitrage analysis started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start arbitrage analysis: {str(e)}")


@router.get("/signals", response_model=List[dict])
async def get_arbitrage_signals(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of signals to return"),
    active_only: bool = Query(True, description="Return only active signals"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db)
):
    """
    Get arbitrage signals with optional filtering.
    
    Returns a list of arbitrage opportunities with their details including
    costs, executable sizes, and confidence scores.
    """
    try:
        query = db.query(ArbitrageSignals)
        
        if active_only:
            query = query.filter(
                ArbitrageSignals.status == "active",
                ArbitrageSignals.expires_at > datetime.utcnow()
            )
        
        query = query.filter(ArbitrageSignals.confidence >= min_confidence)
        
        signals = query.order_by(
            ArbitrageSignals.signal_strength.desc(),
            ArbitrageSignals.created_at.desc()
        ).limit(limit).all()
        
        # Convert to response format
        response = []
        for signal in signals:
            response.append({
                "id": signal.id,
                "pair_id": signal.pair_id,
                "market_a_id": signal.market_a_id,
                "market_b_id": signal.market_b_id,
                "is_arbitrage": signal.is_arbitrage,
                "total_cost": signal.total_cost,
                "edge_buffer": signal.edge_buffer,
                "executable_size": signal.executable_size,
                "signal_strength": signal.signal_strength,
                "confidence": signal.confidence,
                "strategy": signal.strategy,
                "direction_a": signal.direction_a,
                "direction_b": signal.direction_b,
                "market_a": {
                    "venue": signal.market_a_venue,
                    "best_bid": signal.market_a_best_bid,
                    "best_ask": signal.market_a_best_ask,
                    "bid_size": signal.market_a_bid_size,
                    "ask_size": signal.market_a_ask_size
                },
                "market_b": {
                    "venue": signal.market_b_venue,
                    "best_bid": signal.market_b_best_bid,
                    "best_ask": signal.market_b_best_ask,
                    "bid_size": signal.market_b_bid_size,
                    "ask_size": signal.market_b_ask_size
                },
                "fees": {
                    "market_a": signal.market_a_fees,
                    "market_b": signal.market_b_fees
                },
                "slippage_buffer": signal.slippage_buffer,
                "status": signal.status,
                "expires_at": signal.expires_at.isoformat() if signal.expires_at else None,
                "created_at": signal.created_at.isoformat()
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get arbitrage signals: {str(e)}")


@router.get("/signals/{signal_id}")
async def get_arbitrage_signal(
    signal_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific arbitrage signal.
    """
    try:
        signal = db.query(ArbitrageSignals).filter(
            ArbitrageSignals.id == signal_id
        ).first()
        
        if not signal:
            raise HTTPException(status_code=404, detail="Arbitrage signal not found")
        
        return {
            "id": signal.id,
            "pair_id": signal.pair_id,
            "market_a_id": signal.market_a_id,
            "market_b_id": signal.market_b_id,
            "is_arbitrage": signal.is_arbitrage,
            "total_cost": signal.total_cost,
            "edge_buffer": signal.edge_buffer,
            "executable_size": signal.executable_size,
            "signal_strength": signal.signal_strength,
            "confidence": signal.confidence,
            "strategy": signal.strategy,
            "direction_a": signal.direction_a,
            "direction_b": signal.direction_b,
            "market_a": {
                "venue": signal.market_a_venue,
                "best_bid": signal.market_a_best_bid,
                "best_ask": signal.market_a_best_ask,
                "bid_size": signal.market_a_bid_size,
                "ask_size": signal.market_a_ask_size
            },
            "market_b": {
                "venue": signal.market_b_venue,
                "best_bid": signal.market_b_best_bid,
                "best_ask": signal.market_b_best_ask,
                "bid_size": signal.market_b_bid_size,
                "ask_size": signal.market_b_ask_size
            },
            "fees": {
                "market_a": signal.market_a_fees,
                "market_b": signal.market_b_fees
            },
            "slippage_buffer": signal.slippage_buffer,
            "status": signal.status,
            "expires_at": signal.expires_at.isoformat() if signal.expires_at else None,
            "created_at": signal.created_at.isoformat(),
            "metadata": signal.calculation_metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get arbitrage signal: {str(e)}")


@router.get("/pairs", response_model=List[dict])
async def get_arbitrage_pairs(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of pairs to return"),
    min_equivalence_score: float = Query(0.7, ge=0.0, le=1.0, description="Minimum equivalence score"),
    db: Session = Depends(get_db)
):
    """
    Get market pairs that are candidates for arbitrage analysis.
    """
    try:
        pairs = db.query(Pairs).filter(
            Pairs.status == "active",
            Pairs.hard_ok == True,
            Pairs.equivalence_score >= min_equivalence_score
        ).order_by(
            Pairs.equivalence_score.desc(),
            Pairs.created_at.desc()
        ).limit(limit).all()
        
        response = []
        for pair in pairs:
            response.append({
                "id": pair.id,
                "market_a_id": pair.market_a_id,
                "market_b_id": pair.market_b_id,
                "equivalence_score": pair.equivalence_score,
                "confidence": pair.confidence,
                "hard_ok": pair.hard_ok,
                "status": pair.status,
                "conflict_list": pair.conflict_list,
                "created_at": pair.created_at.isoformat()
            })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get arbitrage pairs: {str(e)}")


@router.post("/cleanup")
async def cleanup_expired_signals(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Clean up expired arbitrage signals.
    """
    try:
        # Run cleanup in background
        background_tasks.add_task(arbitrage_engine.cleanup_expired_signals)
        
        return {
            "message": "Signal cleanup started in background",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start signal cleanup: {str(e)}")


@router.get("/stats")
async def get_arbitrage_stats(
    db: Session = Depends(get_db)
):
    """
    Get arbitrage system statistics.
    """
    try:
        # Count total signals
        total_signals = db.query(ArbitrageSignals).count()
        
        # Count active signals
        active_signals = db.query(ArbitrageSignals).filter(
            ArbitrageSignals.status == "active",
            ArbitrageSignals.expires_at > datetime.utcnow()
        ).count()
        
        # Count arbitrage opportunities
        arbitrage_opportunities = db.query(ArbitrageSignals).filter(
            ArbitrageSignals.is_arbitrage == True,
            ArbitrageSignals.status == "active",
            ArbitrageSignals.expires_at > datetime.utcnow()
        ).count()
        
        # Count total pairs
        total_pairs = db.query(Pairs).count()
        
        # Count active pairs
        active_pairs = db.query(Pairs).filter(Pairs.status == "active").count()
        
        # Average signal strength
        avg_signal_strength = db.query(ArbitrageSignals).filter(
            ArbitrageSignals.is_arbitrage == True
        ).with_entities(
            db.func.avg(ArbitrageSignals.signal_strength)
        ).scalar() or 0.0
        
        return {
            "signals": {
                "total": total_signals,
                "active": active_signals,
                "arbitrage_opportunities": arbitrage_opportunities,
                "average_signal_strength": round(avg_signal_strength, 4)
            },
            "pairs": {
                "total": total_pairs,
                "active": active_pairs
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get arbitrage stats: {str(e)}")
