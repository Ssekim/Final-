import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Binance API Configuration
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    BINANCE_TESTNET: bool = True  # Set to False for live trading
    
    # Trading Configuration
    MAX_POSITION_SIZE_USDT: float = 100.0  # Maximum position size per trade
    MIN_PROFIT_THRESHOLD: float = 0.5  # Minimum profit % to execute
    MAX_SLIPPAGE_TOLERANCE: float = 0.1  # Maximum acceptable slippage %
    
    # Risk Management
    MAX_CONCURRENT_TRADES: int = 3
    DAILY_LOSS_LIMIT_USDT: float = 500.0
    MAX_SINGLE_TRADE_LOSS_USDT: float = 50.0
    
    # Execution Settings
    ORDER_TIMEOUT_SECONDS: int = 30
    PRICE_CHECK_INTERVAL_MS: int = 100
    MAX_RETRIES: int = 3
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Redis Configuration (for caching and rate limiting)
    REDIS_URL: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()

# Trading pairs configuration
STABLE_COINS = {'USDT', 'USDC', 'BUSD', 'FDUSD'}
MIN_LIQUIDITY_THRESHOLD = 1000.0  # Minimum liquidity in USDT value

# Fee structure (Binance spot trading fees)
MAKER_FEE = 0.001  # 0.1%
TAKER_FEE = 0.001  # 0.1%
TOTAL_FEE_ESTIMATE = 0.003  # 0.3% total for three trades