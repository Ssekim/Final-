#!/usr/bin/env python3
"""
Example client for the Binance Arbitrage Execution Backend

This script demonstrates how to:
1. Validate arbitrage opportunities
2. Execute arbitrage trades
3. Monitor execution status
4. Check account balances and risk metrics

Usage:
    python3 client_example.py
"""

import requests
import json
import time
from datetime import datetime

# Backend API configuration
API_BASE_URL = "http://localhost:8000"

def print_separator(title):
    """Print a formatted separator"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def check_api_health():
    """Check if the API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        data = response.json()
        
        print(f"API Status: {data.get('status', 'unknown')}")
        print(f"Binance Connection: {data.get('binance_connection', 'unknown')}")
        print(f"Testnet Mode: {data.get('testnet', 'unknown')}")
        print(f"Active Executions: {data.get('active_executions', 0)}")
        
        return data.get('status') == 'healthy'
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def get_account_balances():
    """Get current account balances"""
    try:
        response = requests.get(f"{API_BASE_URL}/account/balances")
        balances = response.json()
        
        print("Account Balances:")
        for balance in balances[:10]:  # Show first 10 balances
            if balance['total'] > 0:
                print(f"  {balance['asset']}: {balance['free']:.8f} (Free) + {balance['locked']:.8f} (Locked) = {balance['total']:.8f}")
        
        return balances
    except Exception as e:
        print(f"Error getting balances: {e}")
        return []

def get_risk_metrics():
    """Get current risk metrics"""
    try:
        response = requests.get(f"{API_BASE_URL}/account/risk-metrics")
        metrics = response.json()
        
        print("Risk Metrics:")
        print(f"  Daily P&L: ${metrics.get('daily_pnl_usdt', 0):.2f}")
        print(f"  Total Trades Today: {metrics.get('total_trades_today', 0)}")
        print(f"  Success Rate: {metrics.get('success_rate_percent', 0):.1f}%")
        print(f"  Active Trades: {metrics.get('active_trades', 0)}")
        print(f"  Available Balance: ${metrics.get('available_balance_usdt', 0):.2f}")
        
        return metrics
    except Exception as e:
        print(f"Error getting risk metrics: {e}")
        return {}

def validate_opportunity(opportunity):
    """Validate an arbitrage opportunity"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/validate-opportunity",
            json=opportunity,
            headers={"Content-Type": "application/json"}
        )
        result = response.json()
        
        print(f"Validation Result: {'✅ Valid' if result.get('valid') else '❌ Invalid'}")
        print(f"Message: {result.get('message', 'No message')}")
        
        return result.get('valid', False)
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def execute_arbitrage(opportunity, position_size=50.0, dry_run=True):
    """Execute an arbitrage opportunity"""
    execution_request = {
        "opportunity": opportunity,
        "position_size_usdt": position_size,
        "dry_run": dry_run
    }
    
    try:
        print(f"Executing arbitrage {'(DRY RUN)' if dry_run else '(LIVE)'}...")
        print(f"Position Size: ${position_size}")
        print(f"Expected Profit: {opportunity['profit_percent']:.2f}%")
        
        response = requests.post(
            f"{API_BASE_URL}/execute",
            json=execution_request,
            headers={"Content-Type": "application/json"}
        )
        result = response.json()
        
        if result.get('success'):
            print("✅ Execution successful!")
            execution_result = result.get('result')
            if execution_result:
                print(f"  Execution ID: {execution_result.get('execution_id')}")
                print(f"  Status: {execution_result.get('status')}")
                if execution_result.get('actual_profit_percent') is not None:
                    print(f"  Actual Profit: {execution_result['actual_profit_percent']:.2f}%")
                if execution_result.get('actual_profit_usdt') is not None:
                    print(f"  Actual Profit: ${execution_result['actual_profit_usdt']:.2f}")
                print(f"  Execution Time: {execution_result.get('execution_time_ms', 0)}ms")
        else:
            print("❌ Execution failed!")
            print(f"  Error: {result.get('message', 'Unknown error')}")
        
        return result
    except Exception as e:
        print(f"Execution error: {e}")
        return None

def monitor_execution(execution_id):
    """Monitor an execution status"""
    try:
        response = requests.get(f"{API_BASE_URL}/executions/{execution_id}")
        execution = response.json()
        
        print(f"Execution {execution_id}:")
        print(f"  Status: {execution.get('status')}")
        print(f"  Steps Completed: {len(execution.get('executions', []))}/3")
        
        for i, step in enumerate(execution.get('executions', []), 1):
            print(f"  Step {i}: {step.get('symbol')} {step.get('side')} - {step.get('status')}")
        
        return execution
    except Exception as e:
        print(f"Monitoring error: {e}")
        return None

def main():
    """Main function demonstrating the API usage"""
    print_separator("Binance Arbitrage Backend Client Example")
    
    # Check API health
    print_separator("Health Check")
    if not check_api_health():
        print("❌ API is not healthy. Please check the backend server.")
        return
    
    # Get account information
    print_separator("Account Information")
    balances = get_account_balances()
    
    print_separator("Risk Metrics")
    risk_metrics = get_risk_metrics()
    
    # Example arbitrage opportunity (you would get this from your frontend)
    print_separator("Example Arbitrage Opportunity")
    example_opportunity = {
        "usdt_pair": "BTCUSDT",
        "second_pair": "BTCETH",
        "third_pair": "ETHUSDT",
        "profit_percent": 1.2,
        "usdt_liquidity": 5000.0,
        "second_liquidity": 3000.0,
        "third_liquidity": 4000.0,
        "execution_prices": [45000.0, 15.2, 2960.0],
        "ai_score": 85,
        "is_valid": True,
        "timestamp": datetime.now().isoformat()
    }
    
    print("Example Opportunity:")
    print(f"  Path: {example_opportunity['usdt_pair']} → {example_opportunity['second_pair']} → {example_opportunity['third_pair']}")
    print(f"  Profit: {example_opportunity['profit_percent']:.2f}%")
    print(f"  Execution Prices: {example_opportunity['execution_prices']}")
    
    # Validate the opportunity
    print_separator("Opportunity Validation")
    is_valid = validate_opportunity(example_opportunity)
    
    if not is_valid:
        print("❌ Opportunity is not valid for execution.")
        return
    
    # Execute the arbitrage (dry run)
    print_separator("Arbitrage Execution")
    
    # Ask user for confirmation
    confirm = input("Execute this arbitrage opportunity? (y/N): ").lower().strip()
    if confirm != 'y':
        print("Execution cancelled by user.")
        return
    
    result = execute_arbitrage(
        opportunity=example_opportunity,
        position_size=50.0,  # $50 position
        dry_run=True  # Always use dry run in examples
    )
    
    if result and result.get('success'):
        execution_id = result['result']['execution_id']
        
        # Monitor execution for a few seconds
        print_separator("Execution Monitoring")
        for i in range(3):
            time.sleep(1)
            execution_status = monitor_execution(execution_id)
            if execution_status and execution_status.get('status') == 'completed':
                break
    
    print_separator("Example Complete")
    print("This example demonstrated:")
    print("✓ Health checking")
    print("✓ Account balance retrieval")
    print("✓ Risk metrics monitoring")
    print("✓ Opportunity validation")
    print("✓ Arbitrage execution (dry run)")
    print("✓ Execution monitoring")
    print("\nTo use with live trading:")
    print("1. Set BINANCE_TESTNET=False in your .env file")
    print("2. Add your real Binance API keys")
    print("3. Set dry_run=False in execution requests")
    print("4. Start with small position sizes")

if __name__ == "__main__":
    main()