import pytest
from config import Config
from src.risk_manager import RiskManager


class TestRiskManager:
    """Test suite for RiskManager."""

    @pytest.fixture
    def risk_manager(self):
        """Create RiskManager instance for testing."""
        return RiskManager(Config)

    def test_can_open_trade_when_conditions_met(self, risk_manager):
        """Test that trade can open when conditions are met."""
        can_open, reason = risk_manager.can_open_trade(2050.0, 'BUY')
        assert can_open is True
        assert reason == 'OK'

    def test_cannot_open_trade_when_max_trades_reached(self, risk_manager):
        """Test that trade cannot open when max trades are reached."""
        # Add mock trades to reach max
        for i in range(Config.MAX_OPEN_TRADES):
            risk_manager.add_trade(
                f'trade_{i}', 2050.0, 'BUY',
                2040.0, 2060.0
            )

        can_open, reason = risk_manager.can_open_trade(2050.0, 'BUY')
        assert can_open is False
        assert 'Max open trades' in reason

    def test_calculate_stop_loss_for_buy(self, risk_manager):
        """Test SL calculation for BUY trade."""
        entry = 2050.0
        sl = risk_manager.calculate_stop_loss(entry, 'BUY')
        assert sl < entry
        assert (entry - sl) == Config.STOP_LOSS_PIPS * 0.01

    def test_calculate_stop_loss_for_sell(self, risk_manager):
        """Test SL calculation for SELL trade."""
        entry = 2050.0
        sl = risk_manager.calculate_stop_loss(entry, 'SELL')
        assert sl > entry
        assert (sl - entry) == Config.STOP_LOSS_PIPS * 0.01

    def test_calculate_take_profit_for_buy(self, risk_manager):
        """Test TP calculation for BUY trade."""
        entry = 2050.0
        tp = risk_manager.calculate_take_profit(entry, 'BUY')
        assert tp > entry
        assert (tp - entry) == Config.TAKE_PROFIT_PIPS * 0.01

    def test_calculate_take_profit_for_sell(self, risk_manager):
        """Test TP calculation for SELL trade."""
        entry = 2050.0
        tp = risk_manager.calculate_take_profit(entry, 'SELL')
        assert tp < entry
        assert (entry - tp) == Config.TAKE_PROFIT_PIPS * 0.01

    def test_add_and_close_trade(self, risk_manager):
        """Test adding and closing a trade."""
        trade_id = 'test_trade_1'
        entry_price = 2050.0
        sl = 2040.0
        tp = 2060.0

        risk_manager.add_trade(trade_id, entry_price, 'BUY', sl, tp)
        assert len(risk_manager.open_trades) == 1

        risk_manager.close_trade(trade_id, 2055.0, 50.0)
        assert risk_manager.open_trades[0]['status'] == 'CLOSED'
        assert risk_manager.open_trades[0]['profit_loss'] == 50.0

    def test_daily_loss_tracking(self, risk_manager):
        """Test daily loss tracking."""
        risk_manager.close_trade('trade_1', 2050.0, -100.0)
        assert risk_manager.daily_loss == 100.0

        risk_manager.close_trade('trade_2', 2050.0, -50.0)
        assert risk_manager.daily_loss == 150.0

    def test_validate_price_levels_buy(self, risk_manager):
        """Test price level validation for BUY."""
        valid, msg = risk_manager.validate_price_levels(2050.0, 2040.0, 2060.0, 'BUY')
        assert valid is True
        assert msg == 'Valid'

    def test_validate_price_levels_invalid_buy(self, risk_manager):
        """Test invalid price levels for BUY."""
        valid, msg = risk_manager.validate_price_levels(2050.0, 2060.0, 2040.0, 'BUY')
        assert valid is False
        assert 'SL must be below entry' in msg

    def test_get_risk_metrics(self, risk_manager):
        """Test risk metrics calculation."""
        risk_manager.add_trade('trade_1', 2050.0, 'BUY', 2040.0, 2060.0)
        risk_manager.close_trade('trade_1', 2055.0, 100.0)

        metrics = risk_manager.get_risk_metrics()
        assert metrics['total_closed_trades'] == 1
        assert metrics['winning_trades'] == 1
        assert metrics['win_rate'] == 100.0

    def test_position_size_reduction(self, risk_manager):
        """Test dynamic position sizing based on losses."""
        # No losses
        multiplier = risk_manager.should_reduce_size_due_to_loss()
        assert multiplier == 1.0

        # 3% loss - should reduce to half size
        risk_manager.daily_loss = Config.INITIAL_BALANCE * 0.03
        multiplier = risk_manager.should_reduce_size_due_to_loss()
        assert multiplier == 0.5
