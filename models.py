from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ExecutionStatus(str, Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TradeStep(str, Enum):
    STEP_1 = "step_1"  # USDT -> First Asset
    STEP_2 = "step_2"  # First Asset -> Second Asset  
    STEP_3 = "step_3"  # Second Asset -> USDT

class ArbitrageOpportunity(BaseModel):
    usdt_pair: str = Field(..., description="First trading pair (e.g., BTCUSDT)")
    second_pair: str = Field(..., description="Second trading pair (e.g., BTCETH)")
    third_pair: str = Field(..., description="Third trading pair (e.g., ETHUSDT)")
    profit_percent: float = Field(..., description="Expected profit percentage")
    usdt_liquidity: float = Field(..., description="Available liquidity on USDT pair")
    second_liquidity: float = Field(..., description="Available liquidity on second pair")
    third_liquidity: float = Field(..., description="Available liquidity on third pair")
    execution_prices: List[float] = Field(..., description="[ask1, ask2, bid3] prices for execution")
    ai_score: Optional[int] = Field(default=None, description="AI confidence score")
    is_valid: bool = Field(..., description="Whether opportunity is currently valid")
    timestamp: datetime = Field(default_factory=datetime.now)

class ExecutionRequest(BaseModel):
    opportunity: ArbitrageOpportunity
    position_size_usdt: float = Field(..., description="Position size in USDT")
    max_slippage: Optional[float] = Field(default=None, description="Maximum acceptable slippage")
    dry_run: bool = Field(default=True, description="Whether to execute in simulation mode")

class TradeExecution(BaseModel):
    step: TradeStep
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    price: float
    expected_price: float
    order_id: Optional[str] = None
    fill_price: Optional[float] = None
    fill_quantity: Optional[float] = None
    commission: Optional[float] = None
    status: str = "pending"
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: Optional[str] = None

class ExecutionResult(BaseModel):
    execution_id: str
    opportunity: ArbitrageOpportunity
    status: ExecutionStatus
    position_size_usdt: float
    executions: List[TradeExecution]
    actual_profit_usdt: Optional[float] = None
    actual_profit_percent: Optional[float] = None
    total_fees_usdt: Optional[float] = None
    slippage_percent: Optional[float] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    dry_run: bool = True

class AccountBalance(BaseModel):
    asset: str
    free: float
    locked: float
    total: float

class RiskMetrics(BaseModel):
    daily_pnl_usdt: float
    total_trades_today: int
    success_rate_percent: float
    active_trades: int
    max_drawdown_usdt: float
    available_balance_usdt: float

class ExecutionResponse(BaseModel):
    success: bool
    execution_id: Optional[str] = None
    message: str
    result: Optional[ExecutionResult] = None