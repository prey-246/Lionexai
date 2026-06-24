'use client';

import { useState, useEffect, useRef } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, Server, CheckCircle2, AlertTriangle, Clock, Zap, XCircle, Ban, Percent } from 'lucide-react';
import { format } from 'date-fns';
import { exchangeAPI } from '@/lib/api';
import { createChart, ColorType, Time } from 'lightweight-charts';

export default function ExecutionMonitorPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedExchange, setSelectedExchange] = useState('binance');
  const [error, setError] = useState<string | null>(null);
  const [cancellingOrder, setCancellingOrder] = useState<string | null>(null);
  const [latencyHistory, setLatencyHistory] = useState<any[]>([]);

  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);

  const fetchData = async () => {
    // Don't show loader on background refresh
    if (!data) setLoading(true);
    setError(null);
    try {
      const statusData = await exchangeAPI.getStatus(selectedExchange);
      
      // Update latency history
      setLatencyHistory(prev => {
        const newHistory = [...prev, { time: Math.floor(Date.now() / 1000), value: statusData.api_latency_ms }];
        // Keep only the last 50 data points to prevent memory leak
        return newHistory.slice(-50);
      });

      setData(statusData);
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLatencyHistory([]);
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRef.current = null;
    }
    fetchData();
    const interval = setInterval(fetchData, 15000);

    return () => clearInterval(interval);
  }, [selectedExchange]);

  // Chart: create once, update data on each latency sample
  useEffect(() => {
    if (!chartContainerRef.current || latencyHistory.length === 0) return;

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#8A94A6',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11,
        },
        grid: { vertLines: { color: 'rgba(255, 255, 255, 0.04)' }, horzLines: { color: 'rgba(255, 255, 255, 0.05)' } },
        height: 160,
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: true },
        crosshair: {
          vertLine: { color: 'rgba(207, 164, 59, 0.4)', labelBackgroundColor: '#CFA43B' },
          horzLine: { color: 'rgba(207, 164, 59, 0.4)', labelBackgroundColor: '#CFA43B' },
        },
      });

      seriesRef.current = chartRef.current.addLineSeries({
        color: '#CFA43B',
        lineWidth: 2,
        priceLineVisible: false,
      });
    }

    seriesRef.current?.setData(latencyHistory);
    chartRef.current.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [latencyHistory]);

  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, []);

  const handleCancelOrder = async (orderId: string, symbol: string) => {
    if (!confirm(`Are you sure you want to cancel order ${orderId} for ${symbol}?`)) return;
    setCancellingOrder(orderId);
    try {
      await exchangeAPI.cancelOrder(selectedExchange, orderId, symbol);
      alert('Order cancelled successfully!');
      await fetchData(); // Immediately refresh data after cancellation
    } catch (err: any) {
      alert(`Failed to cancel order: ${err.message}`);
    } finally {
      setCancellingOrder(null);
    }
  };

  const renderContent = () => {
    if (loading && !data) {
      return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
    }

    if (error) {
      return (
        <div className="card red text-center p-8">
          <AlertTriangle className="w-12 h-12 text-danger mx-auto mb-4" />
          <h3 className="text-xl font-bold text-text-primary mb-2">Connection Failed</h3>
          <p className="text-text-secondary">{error}</p>
        </div>
      );
    }

    if (!data) return null;

    const RELEVANT_ASSETS = new Set(['USDT', 'FDUSD', 'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'AVAX', 'LINK', 'DOT', 'TRX']);
    const balances = Object.values(data.balance || {}).filter((bal: any) => RELEVANT_ASSETS.has(bal.asset));
    // Sort the balances to have major currencies first
    balances.sort((a: any, b: any) => (b.asset === 'USDT' || b.asset === 'BTC' || b.asset === 'ETH') ? 1 : -1);

    const tradeHistory = data.trade_history || [];
    const positions = data.positions || [];

    return (
      <>
        {/* Health & Latency Metrics */}
        <div className="g4">
          <MetricDisplay 
            label="Exchange Status" 
            value={data.status} 
            icon={data.status === 'OPERATIONAL' ? CheckCircle2 : AlertTriangle}
            trend={data.status === 'OPERATIONAL' ? 'up' : 'down'}
          />
          <MetricDisplay 
            label="API Latency" 
            value={`${data.api_latency_ms.toFixed(0)} ms`} 
            icon={Clock}
            trend={data.api_latency_ms < 500 ? 'up' : 'down'}
          />
          <MetricDisplay 
            label="Trade Count (Recent)" 
            value={data.trade_count} 
            icon={Zap}
          />
          <MetricDisplay 
            label="Est. Success Rate" 
            value={`${data.success_rate_pct}%`} 
            icon={Percent}
            trend="up"
          />
        </div>

        {/* Latency Chart */}
        <div className="card p-5">
          <h3 className="sec-head">Real-time API Latency (ms)</h3>
          <div ref={chartContainerRef} className="w-full" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Balances */}
          <div className="lg:col-span-1 card p-5">
            <h3 className="sec-head">{data.exchange_id.toUpperCase()} Testnet Balances</h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {balances.length > 0 ? balances.map((bal: any) => (
                <div key={bal.asset} className="flex justify-between items-center text-[13px] border-b border-border-subtle pb-2">
                  <span className="font-mono text-text-primary">{bal.asset}</span>
                  <span className="font-mono text-text-secondary">{(Number(bal.total) || 0).toFixed(6)}</span>
                </div>
              )) : (
                <p className="text-[13px] text-text-muted text-center py-4">No balances found.</p>
              )}
            </div>
          </div>

          {/* Open Orders */}
          <div className="lg:col-span-2 card p-0">
            <h3 className="sec-head px-5 pt-5 pb-4 border-b border-border-default">Live Open Orders on {data.exchange_id.toUpperCase()}</h3>
            <div className="overflow-x-auto">
              <table className="nexa-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Symbol</th>
                    <th>Side</th>
                    <th>Amount</th>
                    <th>Price</th>
                    <th>Filled</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.open_orders.length > 0 ? data.open_orders.map((order: any) => (
                    <tr key={order.id}>
                      <td className="font-mono whitespace-nowrap">{format(new Date(order.timestamp), 'HH:mm:ss.SSS')}</td>
                      <td className="font-mono text-primary-gold-bright">{order.symbol}</td>
                      <td className={`font-bold ${order.side === 'buy' ? 'text-primary-emerald' : 'text-danger'}`}>{order.side.toUpperCase()}</td>
                      <td className="font-mono">{order.amount}</td>
                      <td className="font-mono">{order.price ? `$${order.price.toFixed(2)}` : 'Market'}</td>
                      <td className="font-mono">{((order.filled / order.amount) * 100).toFixed(0)}%</td>
                      <td className="text-right">
                        <button 
                          onClick={() => handleCancelOrder(order.id, order.symbol)}
                          disabled={cancellingOrder === order.id}
                          className="btn-sm red flex items-center gap-1 disabled:opacity-50"
                        >
                          {cancellingOrder === order.id 
                            ? <Loader2 className="w-3 h-3 animate-spin" /> 
                            : <Ban className="w-3 h-3" />}
                        </button>
                      </td>
                    </tr>
                  )) : (
                    <tr>
                      <td colSpan={7} className="text-center p-8 text-text-muted">No open orders on the exchange.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Trade History */}
            <div className="card p-0">
                <h3 className="sec-head px-5 pt-5 pb-4 border-b border-border-default">Recent Trade History on {data.exchange_id.toUpperCase()}</h3>
                <div className="overflow-x-auto max-h-96">
                    <table className="nexa-table">
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>Symbol</th>
                            <th>Side</th>
                            <th>Price</th>
                            <th>Amount</th>
                            <th>Cost</th>
                          </tr>
                        </thead>
                        <tbody>
                            {tradeHistory.length > 0 ? tradeHistory.map((trade: any) => (
                                <tr key={trade.id}>
                                  <td className="font-mono whitespace-nowrap">{format(new Date(trade.timestamp), 'HH:mm:ss')}</td>
                                  <td className="font-mono text-primary-gold-bright">{trade.symbol}</td>
                                  <td className={`font-bold ${trade.side === 'buy' ? 'text-primary-emerald' : 'text-danger'}`}>{trade.side.toUpperCase()}</td>
                                  <td className="font-mono">${trade.price?.toFixed(2) ?? 'N/A'}</td>
                                  <td className="font-mono">{trade.amount}</td>
                                  <td className="font-mono">${trade.cost?.toFixed(2) ?? 'N/A'}</td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan={6} className="text-center py-8 text-text-muted">No recent trades found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Positions */}
            <div className="card p-0">
                <h3 className="sec-head px-5 pt-5 pb-4 border-b border-border-default">Live Positions on {data.exchange_id.toUpperCase()}</h3>
                <div className="overflow-x-auto max-h-96">
                    <table className="nexa-table">
                        <thead>
                          <tr>
                            <th>Symbol</th>
                            <th>Size</th>
                            <th>Entry Price</th>
                            <th>Unrealized PNL</th>
                          </tr>
                        </thead>
                        <tbody>
                            {positions.length > 0 ? positions.map((pos: any) => (
                                <tr key={pos.symbol}>
                                  <td className="font-mono text-primary-gold-bright">{pos.symbol}</td>
                                  <td className="font-mono">{pos.contracts}</td>
                                  <td className="font-mono">${pos.entryPrice?.toFixed(2)}</td>
                                  <td className={`font-mono ${pos.unrealizedPnl > 0 ? 'text-primary-emerald' : 'text-danger'}`}>{pos.unrealizedPnl?.toFixed(2)}</td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan={4} className="text-center py-8 text-text-muted">No open positions found. (Note: Spot balances act as positions)</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
      </>
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader 
        title="Exchange Execution Monitor" 
        subtitle="Live status and order flow for connected exchange testnets." 
      >
        <div className="w-48">
          <select 
            value={selectedExchange}
            onChange={(e) => setSelectedExchange(e.target.value)}
            className="block w-full px-3 py-2 bg-background-base border border-border-default rounded-lg text-text-primary text-[14px] focus:outline-none focus:border-primary-gold"
          >
            <option value="binance">Binance Testnet</option>
            <option value="bybit">Bybit Testnet</option>
          </select>
        </div>
      </PageHeader>
      {renderContent()}
    </div>
  );
}