# Quick Start Guide

## 5-Minute Setup (Docker Compose)

### Prerequisites
- Docker & Docker Compose installed
- Git

### Steps

1. **Clone & Navigate**
```bash
git clone <repo-url>
cd Lionexai
```

2. **Start Services**
```bash
docker-compose up -d
```

3. **Wait for Health**
```bash
# Wait 30 seconds for database initialization
sleep 30

# Verify all services are running
docker-compose ps
# All should show "Up" status
```

4. **Access Applications**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

5. **Test Basic Flow**

Visit http://localhost:3000 → Click "Operations" → View risk mandates

## What Gets Auto-Initialized

✅ PostgreSQL 15 with TimescaleDB  
✅ Redis cache  
✅ FastAPI backend with all endpoints  
✅ Next.js frontend with all dashboards  
✅ Sample risk mandates (PRESERVE, BALANCE, VAULT)  
✅ Default operations user & portfolio  
✅ Database migrations applied automatically  

## Common Tasks

### View Backend Logs
```bash
docker-compose logs backend -f
```

### View Frontend Logs
```bash
docker-compose logs frontend -f
```

### Access Database Directly
```bash
docker exec nexa_db psql -U nexa_admin -d nexa_mvp
```

### Stop All Services
```bash
docker-compose down
```

### Reset Everything (Warning: Deletes Data)
```bash
docker-compose down -v
docker-compose up -d
```

## Next Steps

1. **Explore the Dashboards**
   - Operations Dashboard: http://localhost:3000
   - Client Dashboard: http://localhost:3000/dashboard
   - Backtest Engine: http://localhost:3000/backtest
   - Execution Terminal: http://localhost:3000/trade

2. **Try the API**
   ```bash
   # Get mandates
   curl http://localhost:8000/api/mandates
   
   # Run a backtest
   curl -X POST http://localhost:8000/api/backtest/run \
     -H "Content-Type: application/json" \
     -d '{"symbol":"BTC/USDT","timeframe":"1d","strategy":"MA_CROSSOVER"}'
   ```

3. **Interactive API Docs**
   Visit http://localhost:8000/docs and try endpoints

4. **Read Full Documentation**
   - `docs/ARCHITECTURE.md` - System design
   - `docs/API.md` - Complete API reference
   - `docs/DEPLOYMENT.md` - Production deployment
   - `README.md` - Project overview

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Clean and retry
docker-compose down -v
docker-compose up -d
```

### Frontend shows API error
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify docker networking
docker network inspect nexa_default
```

### Port already in use
```bash
# Change ports in docker-compose.yml
# Example: change 3000:3000 to 3001:3000
# Then: docker-compose restart frontend
```

## Demo Scenario

1. **Open Operations Dashboard** (http://localhost:3000)
   - View active mandates with risk parameters
   - See engine status

2. **Open Client Dashboard** (http://localhost:3000/dashboard)
   - View portfolio equity ($100,000 starting)
   - Check performance metrics

3. **Try Execution Terminal** (http://localhost:3000/trade)
   - Enter: Symbol=BTC/USDT, Side=BUY, Size=0.1
   - Click EXECUTE
   - Should fill (or show risk rejection if constraints violated)

4. **Run Backtest** (http://localhost:3000/backtest)
   - Select Symbol: BTC/USDT, Timeframe: 1d, Strategy: MA_CROSSOVER
   - Click "Launch Simulation"
   - View performance metrics

5. **Check Reports** (http://localhost:3000/reports)
   - Generate Weekly/Monthly reports
   - View performance breakdown

6. **Monitor Risk** (http://localhost:3000/risk)
   - See all risk events and rejections
   - Check kill switch status

## System Architecture

```
Your Browser
    ↓ (HTTP/WebSocket)
    ├─► Next.js Frontend (port 3000)
    │
    ├─► FastAPI Backend (port 8000)
    │    ├─ Risk Engine
    │    ├─ Backtester
    │    └─ Market Data
    │
    └─► PostgreSQL (port 5432)
         + TimescaleDB
```

## Key Features Working

✅ **Risk Management**
- Kill switch enforcement
- Daily/weekly loss limits
- Leverage validation
- Asset whitelisting
- Position sizing

✅ **Paper Trading**
- Order execution
- Portfolio tracking
- P&L calculation
- Trade history

✅ **Backtesting**
- Moving Average Crossover strategy
- Performance metrics (Sharpe, Drawdown, Win Rate)
- Historical data from CCXT

✅ **Dashboards**
- Real-time portfolio status
- Operations monitoring
- Risk event tracking
- Performance reporting

## Production Deployment

When ready for production:
1. Review `docs/DEPLOYMENT.md`
2. Update `.env` with production credentials
3. Setup SSL/TLS (Certbot)
4. Configure reverse proxy (Nginx)
5. Setup backups and monitoring
6. Run security audit

## Getting Help

1. **API Documentation**: http://localhost:8000/docs
2. **Architecture**: See `docs/ARCHITECTURE.md`
3. **API Reference**: See `docs/API.md`
4. **GitHub Issues**: Report bugs with full logs
5. **Logs**: `docker-compose logs [service]`

---

**That's it! You now have a fully functional quantitative trading platform running locally.**

Happy trading! 🚀
