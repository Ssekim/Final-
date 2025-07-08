import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import numpy as np

from models import (
    ArbitrageOpportunity, ExecutionRequest, ExecutionResult, 
    TradeExecution, ExecutionStatus, TradeStep, AccountBalance, RiskMetrics
)
from config import settings, MAKER_FEE, TAKER_FEE

logger = logging.getLogger(__name__)

class ArbitrageExecutor:
    def __init__(self):
        self.client = Client(
            api_key=settings.BINANCE_API_KEY,
            api_secret=settings.BINANCE_SECRET_KEY,
            testnet=settings.BINANCE_TESTNET
        )
        self.active_executions: Dict[str, ExecutionResult] = {}
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        
    async def execute_arbitrage(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a triangular arbitrage opportunity"""
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create execution result object
        result = ExecutionResult(
            execution_id=execution_id,
            opportunity=request.opportunity,
            status=ExecutionStatus.PENDING,
            position_size_usdt=request.position_size_usdt,
            executions=[],
            dry_run=request.dry_run
        )
        
        self.active_executions[execution_id] = result
        
        try:
            # Pre-execution validation
            if not await self._validate_execution_request(request):
                result.status = ExecutionStatus.FAILED
                result.error_message = "Pre-execution validation failed"
                return result
            
            result.status = ExecutionStatus.EXECUTING
            
            # Execute the three-step arbitrage
            success = await self._execute_triangular_arbitrage(result, request)
            
            if success:
                result.status = ExecutionStatus.COMPLETED
                result.execution_time_ms = int((time.time() - start_time) * 1000)
                result.completed_at = datetime.now()
                
                # Calculate actual profits
                await self._calculate_actual_profit(result)
                
                if not request.dry_run:
                    self._update_daily_metrics(result)
                    
            else:
                result.status = ExecutionStatus.FAILED
                
        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {str(e)}")
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
            
        finally:
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
                
        return result
    
    async def _validate_execution_request(self, request: ExecutionRequest) -> bool:
        """Validate if the execution request is safe and feasible"""
        try:
            # Check if we have enough balance
            balances = await self.get_account_balances()
            usdt_balance = next((b.free for b in balances if b.asset == 'USDT'), 0.0)
            
            if usdt_balance < request.position_size_usdt:
                logger.warning(f"Insufficient USDT balance: {usdt_balance} < {request.position_size_usdt}")
                return False
            
            # Check profit threshold
            if request.opportunity.profit_percent < settings.MIN_PROFIT_THRESHOLD:
                logger.warning(f"Profit below threshold: {request.opportunity.profit_percent}% < {settings.MIN_PROFIT_THRESHOLD}%")
                return False
            
            # Check liquidity
            min_liquidity = request.position_size_usdt * 2  # 2x position size as safety margin
            if (request.opportunity.usdt_liquidity < min_liquidity or 
                request.opportunity.second_liquidity < min_liquidity or 
                request.opportunity.third_liquidity < min_liquidity):
                logger.warning("Insufficient liquidity for execution")
                return False
            
            # Check daily loss limits
            risk_metrics = await self.get_risk_metrics()
            if risk_metrics.daily_pnl_usdt < -settings.DAILY_LOSS_LIMIT_USDT:
                logger.warning("Daily loss limit exceeded")
                return False
            
            # Check concurrent trades limit
            if len(self.active_executions) >= settings.MAX_CONCURRENT_TRADES:
                logger.warning("Maximum concurrent trades limit reached")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return False
    
    async def _execute_triangular_arbitrage(self, result: ExecutionResult, request: ExecutionRequest) -> bool:
        """Execute the three steps of triangular arbitrage"""
        try:
            opportunity = request.opportunity
            position_size = request.position_size_usdt
            
            # Step 1: USDT -> First Asset (e.g., USDT -> BTC)
            step1_quantity = position_size / opportunity.execution_prices[0]
            step1_execution = await self._execute_trade(
                TradeStep.STEP_1,
                opportunity.usdt_pair,
                "BUY",
                step1_quantity,
                opportunity.execution_prices[0],
                request.dry_run
            )
            result.executions.append(step1_execution)
            
            if step1_execution.status != "filled" and not request.dry_run:
                return False
            
            # Step 2: First Asset -> Second Asset (e.g., BTC -> ETH)
            received_quantity = step1_execution.fill_quantity or step1_quantity
            step2_quantity = received_quantity
            step2_execution = await self._execute_trade(
                TradeStep.STEP_2,
                opportunity.second_pair,
                "SELL",
                step2_quantity,
                opportunity.execution_prices[1],
                request.dry_run
            )
            result.executions.append(step2_execution)
            
            if step2_execution.status != "filled" and not request.dry_run:
                return False
            
            # Step 3: Second Asset -> USDT (e.g., ETH -> USDT)
            received_quantity2 = step2_execution.fill_quantity or (step2_quantity * opportunity.execution_prices[1])
            step3_quantity = received_quantity2
            step3_execution = await self._execute_trade(
                TradeStep.STEP_3,
                opportunity.third_pair,
                "SELL",
                step3_quantity,
                opportunity.execution_prices[2],
                request.dry_run
            )
            result.executions.append(step3_execution)
            
            if step3_execution.status != "filled" and not request.dry_run:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Triangular arbitrage execution error: {str(e)}")
            return False
    
    async def _execute_trade(self, step: TradeStep, symbol: str, side: str, 
                           quantity: float, expected_price: float, dry_run: bool) -> TradeExecution:
        """Execute a single trade step"""
        execution = TradeExecution(
            step=step,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=0.0,
            expected_price=expected_price
        )
        
        try:
            if dry_run:
                # Simulate execution for dry run
                execution.fill_price = expected_price
                execution.fill_quantity = quantity
                execution.status = "filled"
                execution.commission = quantity * expected_price * TAKER_FEE
                execution.price = expected_price
                return execution
            
            # Get current market price
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Calculate slippage
            slippage = abs(current_price - expected_price) / expected_price * 100
            max_slippage = settings.MAX_SLIPPAGE_TOLERANCE
            
            if slippage > max_slippage:
                execution.status = "failed"
                execution.error_message = f"Slippage too high: {slippage:.2f}% > {max_slippage:.2f}%"
                return execution
            
            # Place market order for immediate execution
            order = self.client.order_market(
                symbol=symbol,
                side=side,
                quantity=self._format_quantity(symbol, quantity)
            )
            
            execution.order_id = order['orderId']
            execution.fill_price = float(order.get('price', current_price))
            execution.fill_quantity = float(order.get('executedQty', quantity))
            execution.status = order['status'].lower()
            execution.price = current_price
            
            # Calculate commission
            if 'fills' in order:
                total_commission = sum(float(fill['commission']) for fill in order['fills'])
                execution.commission = total_commission
            else:
                execution.commission = execution.fill_quantity * execution.fill_price * TAKER_FEE
            
            logger.info(f"Trade executed: {symbol} {side} {quantity} @ {execution.fill_price}")
            
        except BinanceOrderException as e:
            execution.status = "failed"
            execution.error_message = f"Order error: {str(e)}"
            logger.error(f"Order execution failed: {str(e)}")
            
        except BinanceAPIException as e:
            execution.status = "failed"
            execution.error_message = f"API error: {str(e)}"
            logger.error(f"Binance API error: {str(e)}")
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected trade execution error: {str(e)}")
        
        return execution
    
    def _format_quantity(self, symbol: str, quantity: float) -> str:
        """Format quantity according to symbol's lot size requirements"""
        try:
            info = self.client.get_symbol_info(symbol)
            lot_size_filter = next(f for f in info['filters'] if f['filterType'] == 'LOT_SIZE')
            step_size = float(lot_size_filter['stepSize'])
            
            # Round down to nearest step size
            precision = int(round(-np.log10(step_size), 0))
            formatted_qty = round(quantity, precision)
            
            return f"{formatted_qty:.{precision}f}"
            
        except Exception as e:
            logger.warning(f"Could not format quantity for {symbol}: {str(e)}")
            return f"{quantity:.8f}"
    
    async def _calculate_actual_profit(self, result: ExecutionResult):
        """Calculate the actual profit from the execution"""
        try:
            if len(result.executions) != 3:
                return
            
            # Calculate total fees
            total_fees = sum(ex.commission or 0.0 for ex in result.executions)
            result.total_fees_usdt = total_fees
            
            # Calculate final USDT received
            final_execution = result.executions[-1]
            final_usdt_received = (final_execution.fill_quantity or 0.0) * (final_execution.fill_price or 0.0)
            
            # Calculate profit
            initial_usdt = result.position_size_usdt
            result.actual_profit_usdt = final_usdt_received - initial_usdt - total_fees
            result.actual_profit_percent = (result.actual_profit_usdt / initial_usdt) * 100
            
            # Calculate slippage
            expected_final_usdt = initial_usdt * (1 + result.opportunity.profit_percent / 100)
            result.slippage_percent = ((expected_final_usdt - final_usdt_received) / expected_final_usdt) * 100
            
        except Exception as e:
            logger.error(f"Profit calculation error: {str(e)}")
    
    def _update_daily_metrics(self, result: ExecutionResult):
        """Update daily trading metrics"""
        current_date = datetime.now().date()
        
        # Reset daily metrics if it's a new day
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = current_date
        
        if result.actual_profit_usdt is not None:
            self.daily_pnl += result.actual_profit_usdt
        
        self.daily_trades += 1
    
    async def get_account_balances(self) -> List[AccountBalance]:
        """Get current account balances"""
        try:
            account_info = self.client.get_account()
            balances = []
            
            for balance in account_info['balances']:
                free_balance = float(balance['free'])
                locked_balance = float(balance['locked'])
                
                if free_balance > 0 or locked_balance > 0:
                    balances.append(AccountBalance(
                        asset=balance['asset'],
                        free=free_balance,
                        locked=locked_balance,
                        total=free_balance + locked_balance
                    ))
            
            return balances
            
        except Exception as e:
            logger.error(f"Error getting account balances: {str(e)}")
            return []
    
    async def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
        balances = await self.get_account_balances()
        usdt_balance = next((b.free for b in balances if b.asset == 'USDT'), 0.0)
        
        # Calculate success rate (simplified)
        successful_trades = max(1, int(self.daily_trades * 0.8))  # Assume 80% success rate
        success_rate = (successful_trades / max(1, self.daily_trades)) * 100
        
        return RiskMetrics(
            daily_pnl_usdt=self.daily_pnl,
            total_trades_today=self.daily_trades,
            success_rate_percent=success_rate,
            active_trades=len(self.active_executions),
            max_drawdown_usdt=min(0.0, self.daily_pnl),
            available_balance_usdt=usdt_balance
        )
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an active execution"""
        if execution_id not in self.active_executions:
            return False
        
        result = self.active_executions[execution_id]
        result.status = ExecutionStatus.CANCELLED
        
        # Cancel any pending orders
        for execution in result.executions:
            if execution.order_id and execution.status == "pending":
                try:
                    self.client.cancel_order(
                        symbol=execution.symbol,
                        orderId=execution.order_id
                    )
                    execution.status = "cancelled"
                except Exception as e:
                    logger.error(f"Error cancelling order {execution.order_id}: {str(e)}")
        
        del self.active_executions[execution_id]
        return True