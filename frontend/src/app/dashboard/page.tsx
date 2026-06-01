"use client";

import React, { useState, useEffect } from "react";
import { portfolioAPI, tradeAPI } from "@/lib/api";
import { ArrowUpRight, ArrowDownLeft, TrendingUp, AlertCircle } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { MetricDisplay } from "@/components/ui/MetricDisplay";

export default function ClientDashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const portfolioData = await tradeAPI.getPortfolio();
        setPortfolio(portfolioData);

        const statsData = await portfolioAPI.getStats(portfolioData.id);
        setStats(statsData);

        const tradesData = await portfolioAPI.getTrades(portfolioData.id);
        setTrades(tradesData.slice(0, 10));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen p-6 md:p-8 max-w-7xl mx-auto">
        <div className="text-center text-gray-400">Loading portfolio data...</div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen p-6 md:p-8 max-w-7xl mx-auto">
        <div className="flex items-center gap-2 text-red-400 bg-red-900/10 p-4 rounded border border-red-900/30">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      </main>
    );
  }

  const returnPct = portfolio ? ((portfolio.total_equity - 100000) / 100000) * 100 : 0;
  const winRate = stats?.win_rate || 0;

  return (
    <main className="min-h-screen p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* HEADER */}
      <header className="border-b border-gray-800 pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-white">Portfolio Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">Real-time performance & position monitoring</p>
      </header>

      {/* KEY METRICS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricDisplay
          label="Current Equity"
          value={`$${(portfolio?.total_equity || 0).toFixed(2)}`}
          change={returnPct}
          icon={TrendingUp}
        />
        <MetricDisplay
          label="Available Margin"
          value={`$${(portfolio?.available_margin || 0).toFixed(2)}`}
          change={0}
          icon={TrendingUp}
        />
        <MetricDisplay
          label="Total Return"
          value={`${returnPct.toFixed(2)}%`}
          change={returnPct}
          icon={returnPct >= 0 ? ArrowUpRight : ArrowDownLeft}
        />
        <MetricDisplay
          label="Win Rate"
          value={`${winRate.toFixed(1)}%`}
          change={0}
          icon={TrendingUp}
        />
      </div>

      {/* PERFORMANCE OVERVIEW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="p-6">
          <div className="text-gray-400 text-sm mb-2">Drawdown Risk</div>
          <div className="text-2xl font-semibold text-white">{(portfolio?.current_drawdown_pct || 0).toFixed(2)}%</div>
          <div className="text-xs text-gray-500 mt-2">Current peak-to-trough</div>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="text-gray-400 text-sm mb-2">Total Trades</div>
          <div className="text-2xl font-semibold text-white">{stats?.total_trades || 0}</div>
          <div className="text-xs text-gray-500 mt-2">Closed positions</div>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="text-gray-400 text-sm mb-2">Total P&L</div>
          <div className={`text-2xl font-semibold ${(stats?.total_pnl || 0) >= 0 ? "text-green-400" : "text-red-400"}`}>
            ${(stats?.total_pnl || 0).toFixed(2)}
          </div>
          <div className="text-xs text-gray-500 mt-2">Realized gains/losses</div>
        </GlassCard>
      </div>

      {/* RECENT TRADES */}
      <section className="space-y-4">
        <div className="border-b border-gray-800 pb-2">
          <h2 className="text-lg font-medium tracking-tight text-white">Recent Trades</h2>
        </div>
        <GlassCard className="overflow-hidden border border-gray-800 bg-[#0B1020]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-black/40 text-gray-400 uppercase tracking-wider text-[10px] border-b border-gray-800">
                <tr>
                  <th className="px-6 py-4 font-medium">Symbol</th>
                  <th className="px-6 py-4 font-medium">Side</th>
                  <th className="px-6 py-4 font-medium">Size</th>
                  <th className="px-6 py-4 font-medium">Entry</th>
                  <th className="px-6 py-4 font-medium">Exit</th>
                  <th className="px-6 py-4 font-medium">P&L</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-850">
                {trades.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-gray-500 italic">
                      No trades yet. Start trading to build your track record.
                    </td>
                  </tr>
                ) : (
                  trades.map((trade) => (
                    <tr key={trade.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-[#22D3EE] text-xs">{trade.symbol}</td>
                      <td className="px-6 py-4">
                        <span className={`font-semibold ${trade.side === "BUY" ? "text-green-400" : "text-red-400"}`}>
                          {trade.side}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-200 font-mono">{trade.size}</td>
                      <td className="px-6 py-4 text-gray-400 font-mono">${trade.entry_price?.toFixed(2)}</td>
                      <td className="px-6 py-4 text-gray-400 font-mono">{trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : "—"}</td>
                      <td className={`px-6 py-4 font-semibold font-mono ${trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                        ${trade.pnl.toFixed(2)}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider ${
                          trade.status === "CLOSED"
                            ? "bg-blue-900/20 text-blue-300 border border-blue-900/30"
                            : trade.status === "OPEN"
                            ? "bg-yellow-900/20 text-yellow-300 border border-yellow-900/30"
                            : "bg-red-900/20 text-red-300 border border-red-900/30"
                        }`}>
                          {trade.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </section>
    </main>
  );
}
