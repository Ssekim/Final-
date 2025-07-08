# Binance Arbitrage Execution Backend

A Python backend service for executing triangular arbitrage opportunities on Binance. This backend works with your existing frontend arbitrage scanner to automatically execute profitable trades.

## Features

- **Triangular Arbitrage Execution**: Automatically execute 3-step arbitrage trades
- **Risk Management**: Built-in position sizing, loss limits, and slippage protection
- **Real-time Validation**: Validates opportunities before execution
- **Dry Run Mode**: Test executions without placing real orders
- **RESTful API**: Complete API for frontend integration
- **Account Monitoring**: Track balances, PnL, and risk metrics
- **Background Execution**: Async trade execution with status monitoring

## Quick Start

### 1. Validate Setup

```bash
python3 validate_setup.py
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your Binance API credentials
```

### 4. Run the Server

```bash
python3 main.py
```

The API will be available at `http://localhost:8000`

### 4. View API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Configuration

Edit the `.env` file with your settings:

### Binance API
- `BINANCE_API_KEY`: Your Binance API key
- `BINANCE_SECRET_KEY`: Your Binance secret key  
- `BINANCE_TESTNET`: Set to `True` for testnet, `False` for live trading

### Trading Parameters
- `MAX_POSITION_SIZE_USDT`: Maximum position size per trade (default: 100)
- `MIN_PROFIT_THRESHOLD`: Minimum profit % to execute (default: 0.5%)
- `MAX_SLIPPAGE_TOLERANCE`: Maximum acceptable slippage (default: 0.1%)

### Risk Management
- `MAX_CONCURRENT_TRADES`: Maximum simultaneous trades (default: 3)
- `DAILY_LOSS_LIMIT_USDT`: Daily loss limit (default: 500)
- `MAX_SINGLE_TRADE_LOSS_USDT`: Single trade loss limit (default: 50)

## API Endpoints

### Execute Arbitrage
```http
POST /execute
```

Execute a triangular arbitrage opportunity:

```json
{
  "opportunity": {
    "usdt_pair": "BTCUSDT",
    "second_pair": "BTCETH", 
    "third_pair": "ETHUSDT",
    "profit_percent": 1.2,
    "usdt_liquidity": 5000,
    "second_liquidity": 3000,
    "third_liquidity": 4000,
    "execution_prices": [45000, 15.2, 2960],
    "is_valid": true
  },
  "position_size_usdt": 50.0,
  "dry_run": true
}
```

### Account Information
```http
GET /account/balances        # Get account balances
GET /account/risk-metrics    # Get risk metrics
```

### Execution Monitoring
```http
GET /executions              # Get active executions
GET /executions/{id}         # Get specific execution status
DELETE /executions/{id}      # Cancel execution
```

### Validation
```http
POST /validate-opportunity   # Validate opportunity without executing
```

### Health Check
```http
GET /health                  # Check API and Binance connection status
```

## Frontend Integration

### JavaScript Example

```javascript
// Execute arbitrage opportunity from your frontend
async function executeArbitrage(opportunity) {
  const response = await fetch('http://localhost:8000/execute', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      opportunity: opportunity,
      position_size_usdt: 50.0,
      dry_run: true  // Set to false for live trading
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    console.log('Execution successful:', result.result);
    console.log('Profit:', result.result.actual_profit_percent + '%');
  } else {
    console.error('Execution failed:', result.message);
  }
}

// Monitor execution status
async function checkExecutionStatus(executionId) {
  const response = await fetch(`http://localhost:8000/executions/${executionId}`);
  const execution = await response.json();
  
  console.log('Status:', execution.status);
  console.log('Profit:', execution.actual_profit_percent + '%');
  
  return execution;
}
```

### Modify Your Frontend

Update your existing `script.js` to integrate with the backend:

```javascript
// Add this to your existing script.js after validating an opportunity
async function executeValidOpportunity(opportunity) {
  if (!opportunity.isValid) return;
  
  try {
    const response = await fetch('http://localhost:8000/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        opportunity: {
          usdt_pair: opportunity.usdtPair,
          second_pair: opportunity.secondPair,
          third_pair: opportunity.thirdPair,
          profit_percent: opportunity.profitPercent,
          usdt_liquidity: opportunity.usdtLiquidity || 1000,
          second_liquidity: opportunity.secondLiquidity || 1000, 
          third_liquidity: opportunity.thirdLiquidity || 1000,
          execution_prices: opportunity.desiredPrices || [0, 0, 0],
          is_valid: opportunity.isValid
        },
        position_size_usdt: 50.0,  // Adjust as needed
        dry_run: true  // Set to false for live trading
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('✅ Arbitrage executed successfully!');
      console.log('Profit:', result.result.actual_profit_percent?.toFixed(2) + '%');
    } else {
      console.log('❌ Execution failed:', result.message);
    }
  } catch (error) {
    console.error('Execution error:', error);
  }
}
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **API Keys**: Never commit your API keys to version control
2. **CORS**: Configure CORS properly for production
3. **HTTPS**: Use HTTPS in production
4. **Testnet First**: Always test on Binance testnet first
5. **Position Sizing**: Start with small position sizes
6. **Monitoring**: Monitor executions closely

## Trading Flow

1. **Frontend detects opportunity**: Your existing frontend identifies arbitrage opportunities
2. **Validation**: Backend validates the opportunity (balance, liquidity, risk limits)
3. **Execution**: Three-step trade execution:
   - Step 1: USDT → First Asset (e.g., USDT → BTC)
   - Step 2: First Asset → Second Asset (e.g., BTC → ETH)  
   - Step 3: Second Asset → USDT (e.g., ETH → USDT)
4. **Monitoring**: Track execution progress and calculate actual profits
5. **Risk Management**: Automatic position sizing and loss protection

## Error Handling

The backend includes comprehensive error handling for:

- Insufficient balance
- Market volatility/slippage
- API rate limits
- Network connectivity issues
- Order execution failures
- Risk limit violations

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Test with dry run mode first
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{...}'  # Your test data
```

## Production Deployment

1. Set up proper environment variables
2. Configure reverse proxy (nginx)
3. Set up SSL certificates
4. Configure monitoring and logging
5. Set `BINANCE_TESTNET=False` for live trading
6. Implement proper backup and recovery

## Support

This backend is designed to work with your existing Binance arbitrage frontend. Make sure to:

1. Test thoroughly on testnet first
2. Start with small position sizes
3. Monitor all executions closely
4. Keep your API keys secure

For issues or questions, check the logs at `/var/log/arbitrage/` or review the execution results in the API responses.