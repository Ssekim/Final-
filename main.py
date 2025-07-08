from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio
from typing import List, Dict
import uvicorn
from datetime import datetime

from models import (
    ArbitrageOpportunity, ExecutionRequest, ExecutionResult, 
    ExecutionResponse, AccountBalance, RiskMetrics
)
from arbitrage_executor import ArbitrageExecutor
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global executor instance
executor = ArbitrageExecutor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Binance Arbitrage Execution API")
    logger.info(f"Testnet mode: {settings.BINANCE_TESTNET}")
    logger.info(f"Max position size: ${settings.MAX_POSITION_SIZE_USDT}")
    yield
    # Shutdown
    logger.info("Shutting down Binance Arbitrage Execution API")

# Initialize FastAPI app
app = FastAPI(
    title="Binance Arbitrage Execution API",
    description="Backend API for executing triangular arbitrage opportunities on Binance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Binance Arbitrage Execution API",
        "version": "1.0.0",
        "status": "running",
        "testnet": settings.BINANCE_TESTNET
    }

@app.post("/execute", response_model=ExecutionResponse)
async def execute_arbitrage(request: ExecutionRequest, background_tasks: BackgroundTasks):
    """Execute a triangular arbitrage opportunity"""
    try:
        logger.info(f"Received execution request for {request.opportunity.usdt_pair} -> {request.opportunity.second_pair} -> {request.opportunity.third_pair}")
        
        # Validate position size
        if request.position_size_usdt > settings.MAX_POSITION_SIZE_USDT:
            raise HTTPException(
                status_code=400, 
                detail=f"Position size {request.position_size_usdt} exceeds maximum allowed {settings.MAX_POSITION_SIZE_USDT}"
            )
        
        # Execute the arbitrage
        result = await executor.execute_arbitrage(request)
        
        if result.status.value == "completed":
            profit_msg = ""
            if result.actual_profit_percent is not None:
                profit_msg = f" Profit: {result.actual_profit_percent:.2f}%"
            return ExecutionResponse(
                success=True,
                execution_id=result.execution_id,
                message=f"Arbitrage executed successfully.{profit_msg}",
                result=result
            )
        else:
            return ExecutionResponse(
                success=False,
                execution_id=result.execution_id,
                message=result.error_message or f"Execution failed with status: {result.status.value}",
                result=result
            )
            
    except Exception as e:
        logger.error(f"Execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")

@app.post("/execute-async", response_model=Dict[str, str])
async def execute_arbitrage_async(request: ExecutionRequest, background_tasks: BackgroundTasks):
    """Execute arbitrage in the background and return execution ID immediately"""
    try:
        # Generate execution ID
        import uuid
        execution_id = str(uuid.uuid4())
        
        # Start background execution
        background_tasks.add_task(execute_background_arbitrage, execution_id, request)
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "message": "Arbitrage execution started in background"
        }
        
    except Exception as e:
        logger.error(f"Background execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")

async def execute_background_arbitrage(execution_id: str, request: ExecutionRequest):
    """Execute arbitrage in the background"""
    try:
        result = await executor.execute_arbitrage(request)
        logger.info(f"Background execution {execution_id} completed with status: {result.status.value}")
    except Exception as e:
        logger.error(f"Background execution {execution_id} failed: {str(e)}")

@app.get("/executions/{execution_id}", response_model=ExecutionResult)
async def get_execution_status(execution_id: str):
    """Get the status of a specific execution"""
    if execution_id in executor.active_executions:
        return executor.active_executions[execution_id]
    else:
        raise HTTPException(status_code=404, detail="Execution not found")

@app.get("/executions", response_model=List[ExecutionResult])
async def get_active_executions():
    """Get all active executions"""
    return list(executor.active_executions.values())

@app.delete("/executions/{execution_id}")
async def cancel_execution(execution_id: str):
    """Cancel an active execution"""
    success = await executor.cancel_execution(execution_id)
    if success:
        return {"message": f"Execution {execution_id} cancelled successfully"}
    else:
        raise HTTPException(status_code=404, detail="Execution not found or already completed")

@app.get("/account/balances", response_model=List[AccountBalance])
async def get_account_balances():
    """Get current account balances"""
    try:
        balances = await executor.get_account_balances()
        return balances
    except Exception as e:
        logger.error(f"Error getting balances: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get balances: {str(e)}")

@app.get("/account/risk-metrics", response_model=RiskMetrics)
async def get_risk_metrics():
    """Get current risk metrics"""
    try:
        metrics = await executor.get_risk_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Error getting risk metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get risk metrics: {str(e)}")

@app.post("/validate-opportunity")
async def validate_opportunity(opportunity: ArbitrageOpportunity):
    """Validate an arbitrage opportunity without executing it"""
    try:
        # Create a dry run execution request
        request = ExecutionRequest(
            opportunity=opportunity,
            position_size_usdt=10.0,  # Small test size
            dry_run=True
        )
        
        # Validate the request
        is_valid = await executor._validate_execution_request(request)
        
        return {
            "valid": is_valid,
            "opportunity": opportunity,
            "message": "Opportunity is valid for execution" if is_valid else "Opportunity validation failed"
        }
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test Binance connection
        balances = await executor.get_account_balances()
        
        return {
            "status": "healthy",
            "binance_connection": "ok",
            "testnet": settings.BINANCE_TESTNET,
            "active_executions": len(executor.active_executions),
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        # Return unhealthy status but don't raise exception
        return {
            "status": "unhealthy",
            "binance_connection": "failed", 
            "error": str(e),
            "testnet": settings.BINANCE_TESTNET,
            "timestamp": str(datetime.now())
        }

@app.get("/config")
async def get_config():
    """Get current configuration (safe parameters only)"""
    return {
        "max_position_size_usdt": settings.MAX_POSITION_SIZE_USDT,
        "min_profit_threshold": settings.MIN_PROFIT_THRESHOLD,
        "max_slippage_tolerance": settings.MAX_SLIPPAGE_TOLERANCE,
        "max_concurrent_trades": settings.MAX_CONCURRENT_TRADES,
        "daily_loss_limit_usdt": settings.DAILY_LOSS_LIMIT_USDT,
        "testnet": settings.BINANCE_TESTNET,
        "order_timeout_seconds": settings.ORDER_TIMEOUT_SECONDS
    }

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.BINANCE_TESTNET else "An error occurred"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )