"""
Tests for leaderboard/copy-trader analysis.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from leaderboard.fetcher import LeaderboardFetcher, TraderProfile
from leaderboard.validator import ConfidenceValidator, ConfidenceValidation


class TestLeaderboardFetcher:
    """Test leaderboard fetcher."""
    
    def test_fetcher_creation(self):
        """Test fetcher can be created."""
        fetcher = LeaderboardFetcher()
        assert fetcher is not None
    
    def test_fetch_top_traders(self):
        """Test fetching top traders."""
        fetcher = LeaderboardFetcher()
        
        traders = fetcher.fetch_top_traders(limit=10)
        
        assert isinstance(traders, list)
        # Mock data should return some traders
        assert len(traders) > 0
        assert all(isinstance(t, TraderProfile) for t in traders)
    
    def test_fetch_with_filters(self):
        """Test fetching with filters."""
        fetcher = LeaderboardFetcher()
        
        traders = fetcher.fetch_top_traders(
            limit=10,
            min_winrate=0.60,
            min_roi=0.15
        )
        
        # All traders should meet criteria
        assert all(t.winrate >= 0.60 for t in traders)
        assert all(t.roi >= 0.15 for t in traders)


class TestConfidenceValidator:
    """Test confidence validator."""
    
    def test_validator_creation(self):
        """Test validator can be created."""
        validator = ConfidenceValidator()
        assert validator is not None
    
    def test_validate_good_trade(self):
        """Test validating a good trade."""
        validator = ConfidenceValidator()
        
        result = validator.validate(
            trader_metrics={"winrate": 0.65, "roi": 0.20},
            entry_analysis={"entry_quality_score": 0.80}
        )
        
        assert isinstance(result, ConfidenceValidation)
        assert result.is_confident is True
        assert result.recommendation in ["REPLICATE", "REDUCE_SIZE"]
    
    def test_validate_poor_trade(self):
        """Test validating a poor trade."""
        validator = ConfidenceValidator()
        
        result = validator.validate(
            trader_metrics={"winrate": 0.40, "roi": 0.05},
            entry_analysis={"entry_quality_score": 0.30}
        )
        
        assert isinstance(result, ConfidenceValidation)
        assert result.is_confident is False
        assert result.recommendation == "SKIP"
        assert len(result.risk_factors) > 0
    
    def test_validate_high_volatility(self):
        """Test validation with high volatility."""
        validator = ConfidenceValidator()
        
        result = validator.validate(
            trader_metrics={"winrate": 0.60, "roi": 0.15},
            entry_analysis={"entry_quality_score": 0.75},
            market_conditions={"volatility": 0.9}  # High volatility
        )
        
        # High volatility should be flagged as risk
        assert any('volatility' in str(r).lower() for r in result.risk_factors)
